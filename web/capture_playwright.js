const { chromium } = require('playwright');
const path = require('path');

const SCREENSHOTS_DIR = '/Users/ahmedhassan/apex-os-business-platform/web/screenshots';

const PAGES = [
  { name: 'dashboard', url: 'http://localhost:3000/' },
  { name: 'accounting', url: 'http://localhost:3000/accounting' },
  { name: 'crm', url: 'http://localhost:3000/crm' },
  { name: 'analytics', url: 'http://localhost:3000/analytics' },
  { name: 'agent-reach', url: 'http://localhost:3000/agent-reach' },
  { name: 'bigdata', url: 'http://localhost:3000/bigdata' },
  { name: 'datascience', url: 'http://localhost:3000/datascience' },
  { name: 'continuous-bi', url: 'http://localhost:3000/continuous-bi' },
];

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
  const page = await context.newPage();
  
  for (const { name, url } of PAGES) {
    await page.goto(url, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(3000); // Wait for animations
    
    const filepath = path.join(SCREENSHOTS_DIR, `${name}.png`);
    await page.screenshot({ path: filepath, fullPage: true });
    console.log(`✅ ${name}.png`);
  }
  
  await browser.close();
  console.log('\n✅ All screenshots captured!');
})();
