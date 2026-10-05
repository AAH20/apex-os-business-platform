const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const PAGES = [
  { name: 'notifications', url: 'http://localhost:3000/notifications' },
  { name: 'export-templates', url: 'http://localhost:3000/export-templates' },
  { name: 'workflows', url: 'http://localhost:3000/workflows' },
  { name: 'data-warehouse', url: 'http://localhost:3000/data-warehouse' },
  { name: 'knowledge-base', url: 'http://localhost:3000/knowledge-base' },
  { name: 'monitoring', url: 'http://localhost:3000/monitoring' },
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
    const networkErrors = [];
    page.removeAllListeners('console');
    page.removeAllListeners('pageerror');
    page.removeAllListeners('requestfailed');
    page.on('console', msg => {
      if (msg.type() === 'error') consoleErrors.push(msg.text());
    });
    page.on('pageerror', err => consoleErrors.push(err.message));
    page.on('requestfailed', req => {
      networkErrors.push(`${req.url()} - ${req.failure()?.errorText}`);
    });
    page.on('response', res => {
      if (res.status() >= 400) {
        networkErrors.push(`${res.url()} - ${res.status()}`);
      }
    });

    try {
      await page.goto(url, { waitUntil: 'networkidle', timeout: 15000 });
      await page.waitForTimeout(3000);

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
      const rootHTML = await page.evaluate(() => document.getElementById('root')?.innerHTML?.substring(0, 200) || 'NO ROOT');

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
        network_errors: networkErrors,
        root_html_preview: rootHTML,
        issues: [...consoleErrors, ...networkErrors]
      });

      console.log(`${name}: ${size}B, dark=${isDark}, data=${hasData}, buttons=${buttonCount}, errors=${consoleErrors.length}, net_errors=${networkErrors.length}`);
      if (consoleErrors.length > 0) console.log(`  console: ${consoleErrors.join('; ')}`);
      if (networkErrors.length > 0) console.log(`  network: ${networkErrors.join('; ')}`);
    } catch (err) {
      results.push({
        page: name,
        url,
        error: err.message,
        console_errors: consoleErrors,
        network_errors: networkErrors,
        issues: [err.message, ...consoleErrors, ...networkErrors]
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
