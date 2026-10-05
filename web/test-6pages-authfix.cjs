const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const BASE = 'http://localhost:3000';
const PAGES = [
  { name: 'capacity-planning', path: '/capacity-planning' },
  { name: 'cost-management', path: '/cost-management' },
  { name: 'disaster-recovery', path: '/disaster-recovery' },
  { name: 'integrations', path: '/integrations' },
  { name: 'roles-crud', path: '/roles-crud' },
  { name: 'permissions-crud', path: '/permissions-crud' },
];

const SCREENSHOT_DIR = path.join(__dirname, 'screenshots', 'retest-authfix');
fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });

const results = [];

async function testPage(browser, pageInfo) {
  const { name, path: pagePath } = pageInfo;
  const page = await browser.newPage();
  const pageResult = { page: name, render: null, data: null, buttons: {}, issues: [] };

  try {
    const response = await page.goto(`${BASE}${pagePath}`, { waitUntil: 'networkidle', timeout: 20000 });
    await page.waitForTimeout(2500);

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

    // Check data loaded (table rows or content sections)
    const tableRows = await page.locator('tbody tr').count();
    const cards = await page.locator('.card, [class*="card"]').count();
    const sections = await page.locator('section, .section, [class*="section"]').count();
    pageResult.data = { tableRows, cards, sections, loaded: tableRows > 0 || cards > 0 || sections > 0 };

    // 1. Test Create button
    try {
      const createBtn = page.locator('button:has-text("Create"), button:has-text("Add"), button:has-text("New"), button:has-text("Plus")').first();
      if (await createBtn.count() > 0) {
        await createBtn.click();
        await page.waitForTimeout(1200);
        const modal = page.locator('[role="dialog"], .modal, form').first();
        const modalVisible = await modal.isVisible().catch(() => false);
        pageResult.buttons.create = { works: modalVisible, issue: modalVisible ? null : 'No modal/form appeared' };
      } else {
        const iconBtn = page.locator('button svg').first();
        if (await iconBtn.count() > 0) {
          await iconBtn.click();
          await page.waitForTimeout(1200);
          const modal = page.locator('[role="dialog"], .modal, form').first();
          const modalVisible = await modal.isVisible().catch(() => false);
          pageResult.buttons.create = { works: modalVisible, issue: modalVisible ? null : 'No modal/form appeared' };
        } else {
          pageResult.buttons.create = { works: false, issue: 'No create button found' };
        }
      }
    } catch (e) {
      pageResult.buttons.create = { works: false, issue: e.message };
    }

    await page.keyboard.press('Escape');
    await page.waitForTimeout(500);

    // 2. Test Edit button
    try {
      const editBtn = page.locator('button:has-text("Edit"), button:has-text("Pencil"), button:has-text("Update")').first();
      if (await editBtn.count() > 0) {
        await editBtn.click();
        await page.waitForTimeout(1200);
        const modal = page.locator('[role="dialog"], .modal, form').first();
        const modalVisible = await modal.isVisible().catch(() => false);
        pageResult.buttons.edit = { works: modalVisible, issue: modalVisible ? null : 'No edit form appeared' };
      } else {
        const row = page.locator('tbody tr').first();
        if (await row.count() > 0) {
          await row.click();
          await page.waitForTimeout(500);
          const editBtn2 = page.locator('button:has-text("Edit"), button:has-text("Pencil")').first();
          if (await editBtn2.count() > 0) {
            await editBtn2.click();
            await page.waitForTimeout(1200);
            const modal = page.locator('[role="dialog"], .modal, form').first();
            const modalVisible = await modal.isVisible().catch(() => false);
            pageResult.buttons.edit = { works: modalVisible, issue: modalVisible ? null : 'No edit form appeared' };
          } else {
            pageResult.buttons.edit = { works: false, issue: 'No edit button found' };
          }
        } else {
          pageResult.buttons.edit = { works: false, issue: 'No data rows to edit' };
        }
      }
    } catch (e) {
      pageResult.buttons.edit = { works: false, issue: e.message };
    }

    await page.keyboard.press('Escape');
    await page.waitForTimeout(500);

    // 3. Test Delete button
    try {
      const deleteBtn = page.locator('button:has-text("Delete"), button:has-text("Trash"), button:has-text("Remove")').first();
      if (await deleteBtn.count() > 0) {
        await deleteBtn.click();
        await page.waitForTimeout(1200);
        const confirm = page.locator('button:has-text("Confirm"), button:has-text("Yes"), button:has-text("Delete"), [role="alertdialog"], .confirmation').first();
        const confirmVisible = await confirm.isVisible().catch(() => false);
        pageResult.buttons.delete = { works: confirmVisible, issue: confirmVisible ? null : 'No confirmation dialog appeared' };
      } else {
        pageResult.buttons.delete = { works: false, issue: 'No delete button found' };
      }
    } catch (e) {
      pageResult.buttons.delete = { works: false, issue: e.message };
    }

    await page.keyboard.press('Escape');
    await page.waitForTimeout(500);

    // 4. Test Search
    try {
      const searchInput = page.locator('input[type="text"][placeholder*="Search"], input[type="search"], input[placeholder*="search"], input[placeholder*="Search"]').first();
      if (await searchInput.count() > 0) {
        const initialRows = await page.locator('tbody tr').count();
        await searchInput.fill('test');
        await page.waitForTimeout(1200);
        const filteredRows = await page.locator('tbody tr').count();
        pageResult.buttons.search = {
          works: true,
          issue: null,
          detail: `Rows: ${initialRows} -> ${filteredRows} after search`
        };
      } else {
        pageResult.buttons.search = { works: false, issue: 'No search input found' };
      }
    } catch (e) {
      pageResult.buttons.search = { works: false, issue: e.message };
    }

    // 5. Test Export
    try {
      const exportBtn = page.locator('button:has-text("Export"), button:has-text("Download"), button:has-text("CSV"), button:has-text("JSON")').first();
      if (await exportBtn.count() > 0) {
        const [download] = await Promise.all([
          page.waitForEvent('download', { timeout: 5000 }).catch(() => null),
          exportBtn.click()
        ]);
        pageResult.buttons.export = {
          works: download !== null,
          issue: download ? null : 'No download triggered',
          detail: download ? `File: ${download.suggestedFilename()}` : null
        };
      } else {
        pageResult.buttons.export = { works: false, issue: 'No export button found' };
      }
    } catch (e) {
      pageResult.buttons.export = { works: false, issue: e.message };
    }

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
    const passed = Object.values(buttons).filter(t => t.works).length;
    const total = Object.keys(buttons).length;
    const renderOk = r.render && r.render.ok;
    const dataOk = r.data && r.data.loaded;
    console.log(`${r.page}: render=${renderOk ? 'OK' : 'FAIL'}, data=${dataOk ? 'OK' : 'FAIL'}, buttons=${passed}/${total}`);
    for (const [btnName, btnResult] of Object.entries(buttons)) {
      if (!btnResult.works) {
        console.log(`  FAIL: ${btnName} - ${btnResult.issue}`);
      }
    }
    if (r.issues.length > 0) {
      console.log(`  ERRORS: ${r.issues.join('; ')}`);
    }
  }

  // Write results JSON
  fs.writeFileSync(path.join(SCREENSHOT_DIR, 'results.json'), JSON.stringify(results, null, 2));
  console.log(`\nResults saved to ${path.join(SCREENSHOT_DIR, 'results.json')}`);
})();
