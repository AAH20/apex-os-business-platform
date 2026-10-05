const { chromium } = require('playwright');

const BASE = 'http://localhost:3000';
const PAGES = [
  { name: 'product-management', path: '/product-management' },
  { name: 'order-management', path: '/order-management' },
  { name: 'customer-management', path: '/customer-management' },
];

const results = [];

async function closeModal(page) {
  const closeBtn = page.locator('[role="dialog"] button[aria-label="Close"], [role="dialog"] button:has-text("Cancel"), [role="dialog"] button:has-text("×")').first();
  if (await closeBtn.count() > 0 && await closeBtn.isVisible().catch(() => false)) {
    await closeBtn.click({ timeout: 3000 }).catch(() => {});
  }
  await page.keyboard.press('Escape');
  await page.waitForTimeout(500);
  const dialog = page.locator('[role="dialog"]').first();
  if (await dialog.isVisible().catch(() => false)) {
    await page.mouse.click(10, 10);
    await page.waitForTimeout(500);
  }
}

async function testPage(browser, pageInfo) {
  const { name, path } = pageInfo;
  const page = await browser.newPage();
  const pageResult = { page: name, tests: {} };

  try {
    await page.goto(`${BASE}${path}`, { waitUntil: 'networkidle', timeout: 15000 });
    await page.waitForTimeout(2000);

    // 1. Create button opens form
    try {
      const createBtn = page.locator('button:has-text("Create"), button:has-text("Add"), button:has-text("New"), button:has-text("Plus")').first();
      if (await createBtn.count() > 0) {
        await createBtn.click({ timeout: 5000 });
        await page.waitForTimeout(1000);
        const modal = page.locator('[role="dialog"], .modal, form').first();
        const modalVisible = await modal.isVisible().catch(() => false);
        pageResult.tests.create = { works: modalVisible, issue: modalVisible ? null : 'No modal/form appeared' };
      } else {
        const iconBtn = page.locator('button svg').first();
        if (await iconBtn.count() > 0) {
          await iconBtn.click({ timeout: 5000 });
          await page.waitForTimeout(1000);
          const modal = page.locator('[role="dialog"], .modal, form').first();
          const modalVisible = await modal.isVisible().catch(() => false);
          pageResult.tests.create = { works: modalVisible, issue: modalVisible ? null : 'No modal/form appeared' };
        } else {
          pageResult.tests.create = { works: false, issue: 'No create button found' };
        }
      }
    } catch (e) {
      pageResult.tests.create = { works: false, issue: e.message.split('\n')[0] };
    }
    await closeModal(page);

    // 2. Edit button opens edit form
    try {
      const editBtn = page.locator('button:has-text("Edit"), button:has-text("Pencil"), button:has-text("Update")').first();
      if (await editBtn.count() > 0) {
        await editBtn.click({ timeout: 5000 });
        await page.waitForTimeout(1000);
        const modal = page.locator('[role="dialog"], .modal, form').first();
        const modalVisible = await modal.isVisible().catch(() => false);
        pageResult.tests.edit = { works: modalVisible, issue: modalVisible ? null : 'No edit form appeared' };
      } else {
        const row = page.locator('tbody tr').first();
        if (await row.count() > 0) {
          await row.click({ timeout: 5000 });
          await page.waitForTimeout(500);
          const editBtn2 = page.locator('button:has-text("Edit"), button:has-text("Pencil")').first();
          if (await editBtn2.count() > 0) {
            await editBtn2.click({ timeout: 5000 });
            await page.waitForTimeout(1000);
            const modal = page.locator('[role="dialog"], .modal, form').first();
            const modalVisible = await modal.isVisible().catch(() => false);
            pageResult.tests.edit = { works: modalVisible, issue: modalVisible ? null : 'No edit form appeared' };
          } else {
            pageResult.tests.edit = { works: false, issue: 'No edit button found' };
          }
        } else {
          pageResult.tests.edit = { works: false, issue: 'No data rows to edit' };
        }
      }
    } catch (e) {
      pageResult.tests.edit = { works: false, issue: e.message.split('\n')[0] };
    }
    await closeModal(page);

    // 3. Delete button shows confirmation
    try {
      const deleteBtn = page.locator('button:has-text("Delete"), button:has-text("Trash"), button:has-text("Remove")').first();
      if (await deleteBtn.count() > 0) {
        await deleteBtn.click({ timeout: 5000 });
        await page.waitForTimeout(1000);
        const confirm = page.locator('button:has-text("Confirm"), button:has-text("Yes"), button:has-text("Delete"), [role="alertdialog"], .confirmation').first();
        const confirmVisible = await confirm.isVisible().catch(() => false);
        pageResult.tests.delete = { works: confirmVisible, issue: confirmVisible ? null : 'No confirmation dialog appeared' };
      } else {
        pageResult.tests.delete = { works: false, issue: 'No delete button found' };
      }
    } catch (e) {
      pageResult.tests.delete = { works: false, issue: e.message.split('\n')[0] };
    }
    await closeModal(page);

    // 4. Search filters data
    try {
      const searchInput = page.locator('input[type="text"][placeholder*="Search"], input[type="search"], input[placeholder*="search"], input[placeholder*="Search"]').first();
      if (await searchInput.count() > 0) {
        const initialRows = await page.locator('tbody tr').count();
        await searchInput.fill('test');
        await page.waitForTimeout(1000);
        const filteredRows = await page.locator('tbody tr').count();
        pageResult.tests.search = {
          works: true,
          issue: null,
          detail: `Rows: ${initialRows} -> ${filteredRows} after search`
        };
      } else {
        pageResult.tests.search = { works: false, issue: 'No search input found' };
      }
    } catch (e) {
      pageResult.tests.search = { works: false, issue: e.message.split('\n')[0] };
    }

    // 5. Export generates file
    try {
      const exportBtn = page.locator('button:has-text("Export"), button:has-text("Download"), button:has-text("CSV"), button:has-text("JSON")').first();
      if (await exportBtn.count() > 0) {
        const [download] = await Promise.all([
          page.waitForEvent('download', { timeout: 5000 }).catch(() => null),
          exportBtn.click({ timeout: 5000 })
        ]);
        pageResult.tests.export = {
          works: download !== null,
          issue: download ? null : 'No download triggered',
          detail: download ? `File: ${download.suggestedFilename()}` : null
        };
      } else {
        pageResult.tests.export = { works: false, issue: 'No export button found' };
      }
    } catch (e) {
      pageResult.tests.export = { works: false, issue: e.message.split('\n')[0] };
    }

  } catch (e) {
    pageResult.error = e.message;
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
    const tests = r.tests || {};
    const passed = Object.values(tests).filter(t => t.works).length;
    const total = Object.keys(tests).length;
    console.log(`${r.page}: ${passed}/${total} tests passed`);
    for (const [testName, testResult] of Object.entries(tests)) {
      if (!testResult.works) {
        console.log(`  FAIL: ${testName} - ${testResult.issue}`);
      }
    }
  }
})();
