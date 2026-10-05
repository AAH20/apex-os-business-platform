const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const BASE = 'http://localhost:3000';
const PAGES = [
  { name: 'notifications', path: '/notifications' },
  { name: 'export-templates', path: '/export-templates' },
  { name: 'workflows', path: '/workflows' },
  { name: 'data-warehouse', path: '/data-warehouse' },
  { name: 'knowledge-base', path: '/knowledge-base' },
  { name: 'monitoring', path: '/monitoring' },
];

const SCREENSHOT_DIR = path.join(__dirname, 'screenshots', '6pages-test');
if (!fs.existsSync(SCREENSHOT_DIR)) fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });

(async () => {
  const browser = await chromium.launch({
    headless: true,
    executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  });
  const results = [];

  for (const page of PAGES) {
    console.log(`\n=== ${page.name} ===`);
    const context = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
    const pg = await context.newPage();
    const consoleErrors = [];
    pg.on('console', msg => { if (msg.type() === 'error') consoleErrors.push(msg.text()); });
    pg.on('pageerror', err => consoleErrors.push(err.message));

    try {
      await pg.goto(BASE + page.path, { waitUntil: 'networkidle', timeout: 20000 });
      await pg.waitForTimeout(2000);

      // Screenshot
      const ssPath = path.join(SCREENSHOT_DIR, `${page.name}.png`);
      await pg.screenshot({ path: ssPath, fullPage: true });
      const size = fs.statSync(ssPath).size;

      // Dark theme check
      const darkTheme = await pg.evaluate(() => {
        const body = document.body;
        const style = window.getComputedStyle(body);
        const bg = style.backgroundColor;
        const color = style.color;
        // Check if background is dark (low RGB values)
        const bgMatch = bg.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/);
        const isDark = bgMatch && (parseInt(bgMatch[1]) + parseInt(bgMatch[2]) + parseInt(bgMatch[3])) / 3 < 128;
        return { bg, color, isDark };
      });

      // Data loaded check
      const dataLoaded = await pg.evaluate(() => {
        const bodyText = document.body.innerText;
        const hasTable = !!document.querySelector('table, [role="grid"], [class*="table"]');
        const hasCards = !!document.querySelector('[class*="card"], [class*="Card"]');
        const hasContent = bodyText.length > 200;
        const hasError = /error|failed|not found|404|500/i.test(bodyText.substring(0, 1000));
        return { hasTable, hasCards, hasContent, hasError, textLength: bodyText.length };
      });

      // Buttons check
      const buttons = await pg.evaluate(() => {
        const btns = Array.from(document.querySelectorAll('button, [role="button"], a.btn'));
        return btns.map(b => ({
          text: (b.innerText || b.textContent || '').trim().substring(0, 60),
          disabled: b.disabled || false,
        })).filter(b => b.text.length > 0);
      });

      const result = {
        page: page.name,
        url: BASE + page.path,
        screenshot: ssPath,
        size_bytes: size,
        dark_theme: darkTheme.isDark,
        dark_theme_bg: darkTheme.bg,
        data_loaded: dataLoaded.hasContent && !dataLoaded.hasError,
        has_table: dataLoaded.hasTable,
        has_cards: dataLoaded.hasCards,
        text_length: dataLoaded.textLength,
        buttons_count: buttons.length,
        buttons: buttons.slice(0, 10).map(b => b.text),
        console_errors: consoleErrors,
        issues: [],
      };

      if (!darkTheme.isDark) result.issues.push('Dark theme not detected');
      if (!dataLoaded.hasContent) result.issues.push('No significant content loaded');
      if (dataLoaded.hasError) result.issues.push('Error text detected on page');
      if (buttons.length === 0) result.issues.push('No buttons found');
      if (consoleErrors.length > 0) result.issues.push(`${consoleErrors.length} console errors`);

      results.push(result);
      console.log(`  Screenshot: ${size} bytes`);
      console.log(`  Dark theme: ${darkTheme.isDark ? 'YES' : 'NO'} (bg: ${darkTheme.bg})`);
      console.log(`  Data loaded: ${dataLoaded.hasContent ? 'YES' : 'NO'} (${dataLoaded.textLength} chars, table: ${dataLoaded.hasTable}, cards: ${dataLoaded.hasCards})`);
      console.log(`  Buttons: ${buttons.length}`);
      console.log(`  Console errors: ${consoleErrors.length}`);
      if (result.issues.length > 0) console.log(`  Issues: ${result.issues.join(', ')}`);

    } catch (e) {
      results.push({
        page: page.name,
        url: BASE + page.path,
        error: e.message,
        issues: [e.message],
      });
      console.log(`  ERROR: ${e.message}`);
    }

    await context.close();
  }

  await browser.close();

  fs.writeFileSync(path.join(SCREENSHOT_DIR, 'results.json'), JSON.stringify(results, null, 2));
  console.log(`\nResults saved to ${path.join(SCREENSHOT_DIR, 'results.json')}`);
})();
