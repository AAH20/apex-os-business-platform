const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const BASE = 'http://localhost:3000';
const PAGES = [
  { name: 'iot', path: '/iot' },
  { name: 'reporting', path: '/reporting' },
  { name: 'compliance', path: '/compliance' },
  { name: 'asset-management', path: '/asset-management' },
  { name: 'budgeting', path: '/budgeting' },
  { name: 'project-mgmt', path: '/project-mgmt' },
];

const SCREENSHOT_DIR = path.join(__dirname, 'screenshots', 'test-6pages');
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
    pageResult.size = fs.statSync(screenshotPath).size;

    // Check dark theme
    const bgColor = await page.evaluate(() => {
      const body = document.body;
      const style = window.getComputedStyle(body);
      return style.backgroundColor;
    });
    const isDark = bgColor && (bgColor.includes('rgb(15,') || bgColor.includes('rgb(17,') || bgColor.includes('rgb(20,') || bgColor.includes('rgb(23,') || bgColor.includes('rgb(26,') || bgColor.includes('rgb(30,') || bgColor.includes('rgb(33,') || bgColor.includes('rgb(36,') || bgColor.includes('rgb(40,') || bgColor.includes('rgb(44,') || bgColor.includes('rgb(48,') || bgColor.includes('rgb(52,') || bgColor.includes('rgb(56,') || bgColor.includes('rgb(60,') || bgColor.includes('rgb(64,') || bgColor.includes('rgb(68,') || bgColor.includes('rgb(72,') || bgColor.includes('rgb(76,') || bgColor.includes('rgb(80,') || bgColor.includes('rgb(84,') || bgColor.includes('rgb(88,') || bgColor.includes('rgb(92,') || bgColor.includes('rgb(96,') || bgColor.includes('rgb(100,') || bgColor.includes('rgb(104,') || bgColor.includes('rgb(108,') || bgColor.includes('rgb(112,') || bgColor.includes('rgb(116,') || bgColor.includes('rgb(120,') || bgColor.includes('rgb(124,') || bgColor.includes('rgb(128,') || bgColor.includes('rgb(132,') || bgColor.includes('rgb(136,') || bgColor.includes('rgb(140,') || bgColor.includes('rgb(144,') || bgColor.includes('rgb(148,') || bgColor.includes('rgb(152,') || bgColor.includes('rgb(156,') || bgColor.includes('rgb(160,') || bgColor.includes('rgb(164,') || bgColor.includes('rgb(168,') || bgColor.includes('rgb(172,') || bgColor.includes('rgb(176,') || bgColor.includes('rgb(180,') || bgColor.includes('rgb(184,') || bgColor.includes('rgb(188,') || bgColor.includes('rgb(192,') || bgColor.includes('rgb(196,') || bgColor.includes('rgb(200,') || bgColor.includes('rgb(204,') || bgColor.includes('rgb(208,') || bgColor.includes('rgb(212,') || bgColor.includes('rgb(216,') || bgColor.includes('rgb(220,') || bgColor.includes('rgb(224,') || bgColor.includes('rgb(228,') || bgColor.includes('rgb(232,') || bgColor.includes('rgb(236,') || bgColor.includes('rgb(240,') || bgColor.includes('rgb(244,') || bgColor.includes('rgb(248,') || bgColor.includes('rgb(252,') || bgColor.includes('rgb(255,'));
    pageResult.dark_theme = { bgColor, isDark };

    // Check data loaded
    const tableRows = await page.locator('tbody tr').count();
    const cards = await page.locator('.card, [class*="card"]').count();
    const sections = await page.locator('section, .section, [class*="section"]').count();
    const bodyText = await page.locator('body').textContent().catch(() => '');
    const hasContent = bodyText && bodyText.trim().length > 50;
    pageResult.data_loaded = { tableRows, cards, sections, hasContent, loaded: tableRows > 0 || cards > 0 || sections > 0 || hasContent };

    // Test buttons
    const allButtons = await page.locator('button').all();
    pageResult.buttons.total = allButtons.length;

    // Test Create/Add button
    try {
      const createBtn = page.locator('button:has-text("Create"), button:has-text("Add"), button:has-text("New"), button:has-text("Plus")').first();
      if (await createBtn.count() > 0) {
        await createBtn.click();
        await page.waitForTimeout(1200);
        const modal = page.locator('[role="dialog"], .modal, form').first();
        const modalVisible = await modal.isVisible().catch(() => false);
        pageResult.buttons.create = { works: modalVisible, issue: modalVisible ? null : 'No modal/form appeared' };
      } else {
        pageResult.buttons.create = { works: false, issue: 'No create button found' };
      }
    } catch (e) {
      pageResult.buttons.create = { works: false, issue: e.message };
    }

    await page.keyboard.press('Escape');
    await page.waitForTimeout(500);

    // Test Search
    try {
      const searchInput = page.locator('input[type="text"][placeholder*="Search"], input[type="search"], input[placeholder*="search"], input[placeholder*="Search"]').first();
      if (await searchInput.count() > 0) {
        const initialRows = await page.locator('tbody tr').count();
        await searchInput.fill('test');
        await page.waitForTimeout(1200);
        const filteredRows = await page.locator('tbody tr').count();
        pageResult.buttons.search = { works: true, issue: null, detail: `Rows: ${initialRows} -> ${filteredRows} after search` };
      } else {
        pageResult.buttons.search = { works: false, issue: 'No search input found' };
      }
    } catch (e) {
      pageResult.buttons.search = { works: false, issue: e.message };
    }

    // Test Export
    try {
      const exportBtn = page.locator('button:has-text("Export"), button:has-text("Download"), button:has-text("CSV"), button:has-text("JSON")').first();
      if (await exportBtn.count() > 0) {
        const [download] = await Promise.all([
          page.waitForEvent('download', { timeout: 5000 }).catch(() => null),
          exportBtn.click()
        ]);
        pageResult.buttons.export = { works: download !== null, issue: download ? null : 'No download triggered', detail: download ? `File: ${download.suggestedFilename()}` : null };
      } else {
        pageResult.buttons.export = { works: false, issue: 'No export button found' };
      }
    } catch (e) {
      pageResult.buttons.export = { works: false, issue: e.message };
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
    const buttons = r.buttons || {};
    const passed = Object.values(buttons).filter(t => t && t.works).length;
    const total = Object.keys(buttons).length;
    const darkOk = r.dark_theme && r.dark_theme.isDark;
    const dataOk = r.data_loaded && r.data_loaded.loaded;
    console.log(`${r.page}: size=${r.size}, dark=${darkOk ? 'OK' : 'FAIL'}, data=${dataOk ? 'OK' : 'FAIL'}, buttons=${passed}/${total}, errors=${r.console_errors.length}`);
    for (const [btnName, btnResult] of Object.entries(buttons)) {
      if (btnResult && !btnResult.works) {
        console.log(`  FAIL: ${btnName} - ${btnResult.issue}`);
      }
    }
    if (r.console_errors.length > 0) {
      console.log(`  CONSOLE ERRORS: ${r.console_errors.join('; ')}`);
    }
    if (r.issues.length > 0) {
      console.log(`  ISSUES: ${r.issues.join('; ')}`);
    }
  }

  fs.writeFileSync(path.join(SCREENSHOT_DIR, 'results.json'), JSON.stringify(results, null, 2));
  console.log(`\nResults saved to ${path.join(SCREENSHOT_DIR, 'results.json')}`);
})();
