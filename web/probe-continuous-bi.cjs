const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const pg = await context.newPage();
  const consoleErrors = [];
  pg.on('console', msg => { if (msg.type() === 'error') consoleErrors.push(msg.text()); });
  pg.on('pageerror', err => consoleErrors.push(err.message));

  // Hard timeout
  const killTimer = setTimeout(() => {
    console.log('HARD TIMEOUT - forcing exit');
    process.exit(1);
  }, 25000);

  try {
    console.log('Navigating...');
    const resp = await pg.goto('http://localhost:3000/continuous-bi-crud', { waitUntil: 'commit', timeout: 10000 });
    console.log('Navigation committed, status:', resp ? resp.status() : 'no response');
    
    console.log('Waiting 5s for content...');
    await pg.waitForTimeout(5000);
    
    const title = await pg.title();
    console.log('Title:', title);
    
    const bodyLen = await pg.evaluate(() => document.body.innerText.length);
    console.log('Body text length:', bodyLen);
    
    const hasTable = await pg.evaluate(() => !!document.querySelector('table'));
    console.log('Has table:', hasTable);
    
    const bodySnippet = await pg.evaluate(() => document.body.innerText.substring(0, 300));
    console.log('Body snippet:', bodySnippet);
    
    console.log('Console errors:', consoleErrors.length);
    for (const e of consoleErrors.slice(0, 5)) console.log('  -', e);
    
  } catch (e) {
    console.log('ERROR:', e.message);
  }
  
  clearTimeout(killTimer);
  await browser.close();
  console.log('Done');
})();
