const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const BASE = 'http://localhost:3000';
const PAGES = [
  { name: 'data-warehouse', path: '/data-warehouse' },
  { name: 'knowledge-base', path: '/knowledge-base' },
  { name: 'monitoring', path: '/monitoring' },
];

const SCREENSHOT_DIR = path.join(__dirname, 'screenshots', 'retest-6pages');
fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });

const results = [];

async function testPage(browser, pageInfo) {
  const { name, path: pagePath } = pageInfo;
  const page = await browser.newPage();
  const pageResult = { page: name, render: null, buttons: {}, issues: [] };

  try {
    const response = await page.goto(`${BASE}${pagePath}`, { waitUntil: 'networkidle', timeout: 15000 });
    await page.waitForTimeout(2000);

    const bodyText = await page.locator('body').textContent().catch(() => '');
    const hasContent = bodyText && bodyText.trim().length > 50;
    pageResult.render = {
      status: response ? response.status() : 'unknown',
      hasContent: hasContent,
      ok: response && response.status() === 200 && hasContent
    };

    const screenshotPath = path.join(SCREENSHOT_DIR, `${name}.png`);
    await page.screenshot({ path: screenshotPath, fullPage: true });
    pageResult.screenshot = screenshotPath;

    // 1. Create
    try {
      const createBtn = page.locator('button:has-text("Create"), button:has-text("Add"), button:has-text("New"), button:has-text("Plus")').first();
      if (await createBtn.count() > 0) {
        await createBtn.click({ timeout: 5000 });
        await page.waitForTimeout(1000);
        const modal = page.locator('[role="dialog"], .modal, form').first();
        const modalVisible = await modal.isVisible().catch(() => false);
        pageResult.buttons.create = { works: modalVisible, issue: modalVisible ? null : 'No modal/form appeared' };
      } else {
        pageResult.buttons.create = { works: false, issue: 'No create button found' };
      }
    } catch (e) {
      pageResult.buttons.create = { works: false, issue: e.message.substring(0, 100) };
    }

    await page.keyboard.press('Escape').catch(() => {});
    await page.waitForTimeout(300);

    // 2. Edit
    try {
      const editBtn = page.locator('button:has-text("Edit"), button:has-text("Pencil"), button:has-text("Update")').first();
      if (await editBtn.count() > 0) {
        await editBtn.click({ timeout: 5000 });
        await page.waitForTimeout(1000);
        const modal = page.locator('[role="dialog"], .modal, form').first();
        const modalVisible = await modal.isVisible().catch(() => false);
        pageResult.buttons.edit = { works: modalVisible, issue: modalVisible ? null : 'No edit form appeared' };
      } else {
        pageResult.buttons.edit = { works: false, issue: 'No edit button found' };
      }
    } catch (e) {
      pageResult.buttons.edit = { works: false, issue: e.message.substring(0, 100) };
    }

    await page.keyboard.press('Escape').catch(() => {});
    await page.waitForTimeout(300);

    // 3. Delete
    try {
      const deleteBtn = page.locator('button:has-text("Delete"), button:has-text("Trash"), button:has-text("Remove")').first();
      if (await deleteBtn.count() > 0) {
        await deleteBtn.click({ timeout: 5000 });
        await page.waitForTimeout(1000);
        const confirm = page.locator('button:has-text("Confirm"), button:has-text("Yes"), button:has-text("Delete"), [role="alertdialog"], .confirmation').first();
        const confirmVisible = await confirm.isVisible().catch(() => false);
        pageResult.buttons.delete = { works: confirmVisible, issue: confirmVisible ? null : 'No confirmation dialog appeared' };
      } else {
        pageResult.buttons.delete = { works: false, issue: 'No delete button found' };
      }
    } catch (e) {
      pageResult.buttons.delete = { works: false, issue: e.message.substring(0, 100) };
    }

    await page.keyboard.press('Escape').catch(() => {});
    await page.waitForTimeout(300);

    // 4. Search
    try {
      const searchInput = page.locator('input[type="text"][placeholder*="Search"], input[type="search"], input[placeholder*="search"], input[placeholder*="Search"]').first();
      if (await searchInput.count() > 0) {
        const initialRows = await page.locator('tbody tr').count();
        await searchInput.fill('test');
        await page.waitForTimeout(1000);
        const filteredRows = await page.locator('tbody tr').count();
        pageResult.buttons.search = { works: true, issue: null, detail: `Rows: ${initialRows} -> ${filteredRows}` };
      } else {
        pageResult.buttons.search = { works: false, issue: 'No search input found' };
      }
    } catch (e) {
      pageResult.buttons.search = { works: false, issue: e.message.substring(0, 100) };
    }

    // 5. Export
    try {
      const exportBtn = page.locator('button:has-text("Export"), button:has-text("Download"), button:has-text("CSV"), button:has-text("JSON")').first();
      if (await exportBtn.count() > 0) {
        const [download] = await Promise.all([
          page.waitForEvent('download', { timeout: 5000 }).catch(() => null),
          exportBtn.click({ timeout: 5000 })
        ]);
        pageResult.buttons.export = { works: download !== null, issue: download ? null : 'No download triggered' };
      } else {
        pageResult.buttons.export = { works: false, issue: 'No export button found' };
      }
    } catch (e) {
      pageResult.buttons.export = { works: false, issue: e.message.substring(0, 100) };
    }

  } catch (e) {
    pageResult.issues.push(e.message.substring(0, 200));
  } finally {
    await page.close().catch(() => {});
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
    try {
      const result = await testPage(browser, pageInfo);
      results.push(result);
      console.log(JSON.stringify(result, null, 2));
    } catch (e) {
      console.log(`FAILED ${pageInfo.name}: ${e.message.substring(0, 200)}`);
      results.push({ page: pageInfo.name, error: e.message.substring(0, 200) });
    }
  }

  await browser.close();

  console.log('\n=== SUMMARY ===');
  for (const r of results) {
    const buttons = r.buttons || {};
    const passed = Object.values(buttons).filter(t => t.works).length;
    const total = Object.keys(buttons).length;
    const renderOk = r.render && r.render.ok;
    console.log(`${r.page}: render=${renderOk ? 'OK' : 'FAIL'}, buttons=${passed}/${total}`);
    for (const [btnName, btnResult] of Object.entries(buttons)) {
      if (!btnResult.works) {
        console.log(`  FAIL: ${btnName} - ${btnResult.issue}`);
      }
    }
  }

  fs.writeFileSync(path.join(SCREENSHOT_DIR, 'results-remaining.json'), JSON.stringify(results, null, 2));
})();
