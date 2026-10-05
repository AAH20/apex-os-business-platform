const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const BASE = 'http://127.0.0.1:5173';
const PAGES = [
  { name: 'inventory-management', path: '/inventory-management' },
  { name: 'payment-management', path: '/payment-management' },
  { name: 'invoice-management', path: '/invoice-management' },
  { name: 'journal-entries-crud', path: '/journal-entries-crud' },
  { name: 'dashboard-crud', path: '/dashboard-crud' },
  { name: 'accounting-crud', path: '/accounting-crud' },
];

const SCREENSHOT_DIR = path.join(__dirname, 'screenshots', 'six-pages-test');
fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });

const results = [];

async function testPage(browser, pageInfo) {
  const { name, path: pagePath } = pageInfo;
  const page = await browser.newPage();
  const pageResult = { page: name, size: null, dark_theme: null, data_loaded: null, buttons: {}, console_errors: [], issues: [] };

  try {
    const consoleErrors = [];
    page.on('console', msg => {
      if (msg.type() === 'error') consoleErrors.push(msg.text());
    });
    page.on('pageerror', err => consoleErrors.push(err.message));

    const response = await page.goto(`${BASE}${pagePath}`, { waitUntil: 'networkidle', timeout: 20000 });
    await page.waitForTimeout(2500);

    // Screenshot
    const screenshotPath = path.join(SCREENSHOT_DIR, `${name}.png`);
    await page.screenshot({ path: screenshotPath, fullPage: true });
    pageResult.screenshot = screenshotPath;

    // Page size
    const dimensions = await page.evaluate(() => ({
      width: document.documentElement.scrollWidth,
      height: document.documentElement.scrollHeight,
      bodyWidth: document.body.scrollWidth,
      bodyHeight: document.body.scrollHeight
    }));
    pageResult.size = dimensions;

    // Dark theme check
    const darkTheme = await page.evaluate(() => {
      const body = document.body;
      const styles = window.getComputedStyle(body);
      const bgColor = styles.backgroundColor;
      const textColor = styles.color;
      // Check if background is dark (low RGB values)
      const bgMatch = bgColor.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/);
      const isDark = bgMatch && (parseInt(bgMatch[1]) < 80 && parseInt(bgMatch[2]) < 80 && parseInt(bgMatch[3]) < 80);
      return { bgColor, textColor, isDark };
    });
    pageResult.dark_theme = darkTheme;

    // Data loaded check
    const dataInfo = await page.evaluate(() => {
      const tableRows = document.querySelectorAll('tbody tr').length;
      const cards = document.querySelectorAll('[class*="card"], [class*="Card"]').length;
      const hasTable = document.querySelectorAll('table').length > 0;
      const hasContent = document.body.textContent.trim().length > 100;
      const h1 = document.querySelector('h1')?.textContent || '';
      return { tableRows, cards, hasTable, hasContent, h1, hasData: tableRows > 0 || cards > 0 || hasContent };
    });
    pageResult.data_loaded = dataInfo;

    // Button checks
    const buttonTests = [
      { key: 'create', selector: 'button:has-text("Create"), button:has-text("Add"), button:has-text("New"), button:has-text("Plus")' },
      { key: 'edit', selector: 'button:has-text("Edit"), button:has-text("Pencil"), button:has-text("Update")' },
      { key: 'delete', selector: 'button:has-text("Delete"), button:has-text("Remove")' },
      { key: 'search', selector: 'input[type="text"][placeholder*="Search"], input[type="search"], input[placeholder*="search"], input[placeholder*="Search"]' },
      { key: 'export', selector: 'button:has-text("Export"), button:has-text("Download"), button:has-text("CSV"), button:has-text("JSON")' },
    ];

    for (const btn of buttonTests) {
      try {
        const el = page.locator(btn.selector).first();
        const count = await el.count();
        if (count > 0) {
          const isVisible = await el.isVisible().catch(() => false);
          pageResult.buttons[btn.key] = { found: true, visible: isVisible };
        } else {
          pageResult.buttons[btn.key] = { found: false, visible: false };
        }
      } catch (e) {
        pageResult.buttons[btn.key] = { found: false, visible: false, error: e.message };
      }
    }

    pageResult.console_errors = consoleErrors;

  } catch (e) {
    pageResult.issues.push(e.message);
  } finally {
    await page.close();
  }

  return pageResult;
}

(async () => {
  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-dev-shm-usage']
  });

  for (const pageInfo of PAGES) {
    console.log(`Testing ${pageInfo.name}...`);
    const result = await testPage(browser, pageInfo);
    results.push(result);
    console.log(JSON.stringify(result, null, 2));
  }

  await browser.close();

  console.log('\n=== SUMMARY ===');
  for (const r of results) {
    const darkOk = r.dark_theme && r.dark_theme.isDark;
    const dataOk = r.data_loaded && r.data_loaded.hasData;
    const btnCount = Object.values(r.buttons).filter(b => b.found).length;
    const errCount = r.console_errors.length;
    console.log(`${r.page}: dark=${darkOk ? 'OK' : 'FAIL'}, data=${dataOk ? 'OK' : 'FAIL'}, buttons=${btnCount}/5, errors=${errCount}`);
    if (errCount > 0) {
      console.log(`  ERRORS: ${r.console_errors.join('; ')}`);
    }
  }

  fs.writeFileSync(path.join(SCREENSHOT_DIR, 'results.json'), JSON.stringify(results, null, 2));
  console.log(`\nResults saved to ${path.join(SCREENSHOT_DIR, 'results.json')}`);
})();
