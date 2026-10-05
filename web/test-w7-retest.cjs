const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const BASE = 'http://localhost:3000';
const PAGES = [
  { name: 'iot', path: '/iot' },
  { name: 'reporting', path: '/reporting' },
  { name: 'compliance', path: '/compliance' },
];

const SCREENSHOT_DIR = path.join(__dirname, 'screenshots', 'retest-w7');
fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });

const results = [];

async function testPage(browser, pageInfo) {
  const { name, path: pagePath } = pageInfo;
  const page = await browser.newPage();
  const pageResult = { page: name, render: null, data: null, buttons: {}, issues: [] };

  try {
    const response = await page.goto(`${BASE}${pagePath}`, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(3000);

    // Check render
    const title = await page.title();
    const h1 = await page.locator('h1').first().textContent().catch(() => null);
    const bodyText = await page.locator('body').textContent().catch(() => '');
    const hasContent = bodyText && bodyText.trim().length > 50;
    pageResult.render = {
      status: response ? response.status() : 'unknown',
      title: title,
      h1: h1,
      hasContent: hasContent,
      ok: response && response.status() === 200 && hasContent
    };

    // Screenshot
    const screenshotPath = path.join(SCREENSHOT_DIR, `${name}.png`);
    await page.screenshot({ path: screenshotPath, fullPage: true });
    pageResult.screenshot = screenshotPath;

    // Check data loads
    const tableRows = await page.locator('tbody tr').count();
    const cards = await page.locator('[class*="card"], [class*="Card"]').count();
    const hasTable = await page.locator('table').count() > 0;
    const hasData = tableRows > 0 || cards > 0;
    pageResult.data = {
      tableRows: tableRows,
      cards: cards,
      hasTable: hasTable,
      hasData: hasData,
      ok: hasData
    };

    // Test all buttons
    const buttons = await page.locator('button').all();
    pageResult.buttons.total = buttons.length;
    pageResult.buttons.list = [];
    for (let i = 0; i < Math.min(buttons.length, 10); i++) {
      const btnText = await buttons[i].textContent().catch(() => '');
      const btnVisible = await buttons[i].isVisible().catch(() => false);
      pageResult.buttons.list.push({ text: btnText.trim(), visible: btnVisible });
    }

    // Test Create/Add button
    try {
      const createBtn = page.locator('button:has-text("Create"), button:has-text("Add"), button:has-text("New"), button:has-text("Plus")').first();
      if (await createBtn.count() > 0) {
        await createBtn.click();
        await page.waitForTimeout(1500);
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

    // Test Export/Download button
    try {
      const exportBtn = page.locator('button:has-text("Export"), button:has-text("Download"), button:has-text("CSV"), button:has-text("PDF")').first();
      if (await exportBtn.count() > 0) {
        const exportVisible = await exportBtn.isVisible().catch(() => false);
        pageResult.buttons.export = { works: exportVisible, issue: exportVisible ? null : 'Export button not visible' };
      } else {
        pageResult.buttons.export = { works: false, issue: 'No export button found' };
      }
    } catch (e) {
      pageResult.buttons.export = { works: false, issue: e.message };
    }

    // Check for error messages
    const errorElements = await page.locator('[class*="error"], [class*="Error"], .alert-danger, .text-danger').all();
    if (errorElements.length > 0) {
      for (const el of errorElements) {
        const errText = await el.textContent().catch(() => '');
        if (errText.trim()) pageResult.issues.push(errText.trim());
      }
    }

  } catch (e) {
    pageResult.issues.push(e.message);
  }

  await page.close();
  return pageResult;
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  for (const pageInfo of PAGES) {
    console.log(`Testing ${pageInfo.name}...`);
    const result = await testPage(browser, pageInfo);
    results.push(result);
    console.log(`  Render: ${result.render.ok ? 'OK' : 'FAIL'} | Data: ${result.data.ok ? 'OK' : 'FAIL'} | Buttons: ${result.buttons.total}`);
  }
  await browser.close();

  fs.writeFileSync(path.join(__dirname, 'retest-w7-results.json'), JSON.stringify(results, null, 2));
  console.log('\nResults saved to retest-w7-results.json');
  console.log(JSON.stringify(results, null, 2));
})();
