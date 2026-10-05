const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const BASE = 'http://localhost:3000';
const SCREENSHOT_DIR = path.join(__dirname, 'screenshots', 'retest-3pages-authfix');
const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';

(async () => {
  const browser = await chromium.launch({ headless: true, args: ['--no-sandbox', '--disable-dev-shm-usage'] });
  const page = await browser.newPage();
  const errors = [];
  page.on('pageerror', err => errors.push(err.message));

  try {
    const resp = await page.goto(BASE + '/monitoring', { waitUntil: 'networkidle', timeout: 20000 });
    await page.waitForTimeout(3000);

    const title = await page.title();
    const h1 = await page.locator('h1').first().textContent().catch(() => null);
    const bodyText = await page.locator('body').textContent();
    const hasContent = bodyText && bodyText.trim().length > 50;
    const tableRows = await page.locator('tbody tr').count();
    const cards = await page.locator('.card, [class*="card"]').count();
    const buttons = await page.locator('button').all();
    const btnTexts = [];
    for (const b of buttons) {
      const t = await b.textContent().catch(() => '');
      if (t.trim()) btnTexts.push(t.trim());
    }

    // Screenshot
    const ssPath = path.join(SCREENSHOT_DIR, 'monitoring.png');
    try {
      execSync('"' + CHROME + '" --headless --disable-gpu --no-sandbox --disable-dev-shm-usage --window-size=1920,1080 --screenshot="' + ssPath + '" --virtual-time-budget=5000 "' + BASE + '/monitoring" 2>/dev/null', { timeout: 30000 });
    } catch(e) {}

    const result = {
      page: 'monitoring',
      render: { status: resp.status(), title, h1, hasContent, ok: resp.status() === 200 && hasContent },
      data: { tableRows, cards, loaded: tableRows > 0 || cards > 0 },
      buttonsFound: btnTexts.slice(0, 15),
      screenshot: fs.existsSync(ssPath) ? ssPath : null,
      screenshotSize: fs.existsSync(ssPath) ? fs.statSync(ssPath).size : 0,
      errors: errors
    };
    console.log(JSON.stringify(result, null, 2));
  } catch(e) {
    console.log('Error:', e.message);
  }
  await browser.close();
})();
