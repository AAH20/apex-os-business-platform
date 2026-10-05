const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const BASE = 'http://localhost:3000';
const PAGES = [
  { name: 'asset-management', path: '/asset-management' },
  { name: 'budgeting', path: '/budgeting' },
  { name: 'project-mgmt', path: '/project-mgmt' },
];

const SCREENSHOT_DIR = path.join(__dirname, 'screenshots', 'final-3pages-asset-budget-project-v2');
fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });

const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';

function isDarkColor(rgbStr) {
  const m = rgbStr.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/);
  if (!m) return false;
  const [_, r, g, b] = m.map(Number);
  return r < 100 && g < 100 && b < 100;
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const results = [];

  for (const { name, path: pagePath } of PAGES) {
    const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
    const consoleErrors = [];
    page.on('console', msg => { if (msg.type() === 'error') consoleErrors.push(msg.text()); });
    page.on('pageerror', err => consoleErrors.push(err.message));

    const r = { page: name, size: 0, dark_theme: false, data_loaded: false, buttons: 0, console_errors: [], issues: [] };

    try {
      // 1. Navigate
      const resp = await page.goto(`${BASE}${pagePath}`, { waitUntil: 'networkidle', timeout: 30000 });
      await page.waitForTimeout(3000);
      r.status = resp ? resp.status() : 'unknown';

      // 2. Screenshot with Chrome headless (increased timeout)
      const ssPath = path.join(SCREENSHOT_DIR, `${name}.png`);
      try {
        execSync(`"${CHROME}" --headless --disable-gpu --no-sandbox --disable-dev-shm-usage --window-size=1920,1080 --screenshot="${ssPath}" --virtual-time-budget=5000 "${BASE}${pagePath}" 2>/dev/null`, { timeout: 60000 });
        r.size = fs.existsSync(ssPath) ? fs.statSync(ssPath).size : 0;
      } catch (e) {
        r.issues.push(`Chrome screenshot failed: ${e.message}`);
        // Fallback to Playwright screenshot
        try {
          await page.screenshot({ path: ssPath, fullPage: false, timeout: 15000 });
          r.size = fs.existsSync(ssPath) ? fs.statSync(ssPath).size : 0;
          r.issues.push('Used Playwright fallback for screenshot');
        } catch (e2) {
          r.issues.push(`Playwright screenshot also failed: ${e2.message}`);
        }
      }

      // 3. Dark theme
      const bgColor = await page.evaluate(() => window.getComputedStyle(document.body).backgroundColor);
      r.bg_color = bgColor;
      r.dark_theme = isDarkColor(bgColor);

      // 4. Data loaded
      const contentLength = await page.evaluate(() => document.body.innerText.length);
      const tableRows = await page.locator('tbody tr').count();
      const cards = await page.locator('.card, [class*="card"]').count();
      r.content_length = contentLength;
      r.table_rows = tableRows;
      r.cards = cards;
      r.data_loaded = contentLength > 200 || tableRows > 0 || cards > 0;

      // 5. Buttons
      r.buttons = await page.locator('button').count();

      // 6. Console errors
      r.console_errors = consoleErrors;
      if (consoleErrors.length > 0) r.issues.push(...consoleErrors.slice(0, 5));

      console.log(`${name}: ${r.size}B, dark=${r.dark_theme}, data=${r.data_loaded}, buttons=${r.buttons}, errors=${consoleErrors.length}`);
    } catch (err) {
      r.issues.push(err.message);
      console.log(`${name}: ERROR - ${err.message}`);
    }

    results.push(r);
    await page.close();
  }

  await browser.close();

  fs.writeFileSync(path.join(SCREENSHOT_DIR, 'results.json'), JSON.stringify(results, null, 2));
  console.log('\nResults saved to', path.join(SCREENSHOT_DIR, 'results.json'));
})();
