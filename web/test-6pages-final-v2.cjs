const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const PAGES = [
  { name: 'opportunities-crud', url: 'http://localhost:3002/opportunities-crud' },
  { name: 'campaigns-crud', url: 'http://localhost:3002/campaigns-crud' },
  { name: 'alerts-crud', url: 'http://localhost:3002/alerts-crud' },
  { name: 'user-management', url: 'http://localhost:3002/user-management' },
  { name: 'lead-management', url: 'http://localhost:3002/lead-management' },
  { name: 'report-management', url: 'http://localhost:3002/report-management' },
];

const SCREENSHOT_DIR = path.join(__dirname, 'screenshots', 'final-6pages-v2');
fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });

function isDarkColor(rgbStr) {
  const m = rgbStr.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/);
  if (!m) return false;
  const [_, r, g, b] = m.map(Number);
  return r < 100 && g < 100 && b < 100;
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
  const page = await context.newPage();

  const results = [];

  for (const { name, url } of PAGES) {
    const consoleErrors = [];
    page.removeAllListeners('console');
    page.removeAllListeners('pageerror');
    page.on('console', msg => {
      if (msg.type() === 'error') consoleErrors.push(msg.text());
    });
    page.on('pageerror', err => consoleErrors.push(err.message));

    try {
      await page.goto(url, { waitUntil: 'networkidle', timeout: 15000 });
      await page.waitForTimeout(2000);

      const screenshotPath = path.join(SCREENSHOT_DIR, `${name}.png`);
      await page.screenshot({ path: screenshotPath, fullPage: true });
      const size = fs.statSync(screenshotPath).size;

      const bgColor = await page.evaluate(() => {
        return window.getComputedStyle(document.body).backgroundColor;
      });
      const isDark = isDarkColor(bgColor);

      const contentLength = await page.evaluate(() => document.body.innerText.length);
      const hasData = contentLength > 200;

      const buttonCount = await page.evaluate(() => document.querySelectorAll('button').length);

      results.push({
        page: name,
        url,
        size_bytes: size,
        dark_theme: isDark,
        bg_color: bgColor,
        data_loaded: hasData,
        content_length: contentLength,
        buttons: buttonCount,
        console_errors: consoleErrors,
        issues: consoleErrors.length > 0 ? consoleErrors : []
      });

      console.log(`${name}: ${size}B, dark=${isDark}, data=${hasData}, buttons=${buttonCount}, errors=${consoleErrors.length}`);
    } catch (err) {
      results.push({
        page: name,
        url,
        error: err.message,
        console_errors: consoleErrors,
        issues: [err.message]
      });
      console.log(`${name}: ERROR - ${err.message}`);
    }
  }

  await browser.close();

  fs.writeFileSync(
    path.join(SCREENSHOT_DIR, 'results.json'),
    JSON.stringify(results, null, 2)
  );

  console.log('\nResults saved to', path.join(SCREENSHOT_DIR, 'results.json'));
})();
