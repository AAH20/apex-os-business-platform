const { chromium } = require('playwright-core');

const BASE = 'http://localhost:3000';
const PAGES = ['iot', 'reporting', 'compliance', 'asset-management', 'budgeting', 'project-mgmt'];

(async () => {
  const browser = await chromium.launch({
    executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    headless: true,
    args: ['--virtual-time-budget=10000', '--no-sandbox', '--disable-setuid-sandbox']
  });
  const results = [];

  for (const pageName of PAGES) {
    const page = await browser.newPage();
    const url = `${BASE}/${pageName}`;
    console.log(`\n=== Testing: ${pageName} ===`);

    try {
      await page.goto(url, { waitUntil: 'networkidle', timeout: 15000 });
      await page.waitForTimeout(2000);

      // Test Create button
      try {
        const createBtn = page.locator('button:has-text("Create"), button:has-text("Add"), button:has-text("New")').first();
        await createBtn.click({ timeout: 5000 });
        await page.waitForTimeout(1000);
        const formVisible = await page.locator('form, [role="dialog"], .modal, [class*="form"], [class*="modal"]').first().isVisible().catch(() => false);
        results.push({ page: pageName, button: 'Create', works: formVisible, issues: formVisible ? null : 'Form not visible after click' });
        console.log(`  Create: ${formVisible ? 'PASS' : 'FAIL'}`);
        await page.keyboard.press('Escape');
        await page.locator('button:has-text("Cancel"), button:has-text("Close")').first().click({ timeout: 2000 }).catch(() => {});
        await page.waitForTimeout(500);
      } catch (e) {
        results.push({ page: pageName, button: 'Create', works: false, issues: e.message });
        console.log(`  Create: ERROR - ${e.message}`);
      }

      // Test Edit button
      try {
        const editBtn = page.locator('button:has-text("Edit"), button:has-text("edit"), [title*="Edit"], [aria-label*="Edit"]').first();
        await editBtn.click({ timeout: 5000 });
        await page.waitForTimeout(1000);
        const editFormVisible = await page.locator('form, [role="dialog"], .modal, [class*="form"], [class*="modal"]').first().isVisible().catch(() => false);
        results.push({ page: pageName, button: 'Edit', works: editFormVisible, issues: editFormVisible ? null : 'Edit form not visible after click' });
        console.log(`  Edit: ${editFormVisible ? 'PASS' : 'FAIL'}`);
        await page.keyboard.press('Escape');
        await page.locator('button:has-text("Cancel"), button:has-text("Close")').first().click({ timeout: 2000 }).catch(() => {});
        await page.waitForTimeout(500);
      } catch (e) {
        results.push({ page: pageName, button: 'Edit', works: false, issues: e.message });
        console.log(`  Edit: ERROR - ${e.message}`);
      }

      // Test Delete button
      try {
        const deleteBtn = page.locator('button:has-text("Delete"), button:has-text("delete"), [title*="Delete"], [aria-label*="Delete"]').first();
        await deleteBtn.click({ timeout: 5000 });
        await page.waitForTimeout(1000);
        const confirmVisible = await page.locator('text=/confirm|are you sure|delete.*\?/i, [role="alertdialog"], [class*="confirm"]').first().isVisible().catch(() => false);
        results.push({ page: pageName, button: 'Delete', works: confirmVisible, issues: confirmVisible ? null : 'No confirmation dialog shown' });
        console.log(`  Delete: ${confirmVisible ? 'PASS' : 'FAIL'}`);
        await page.keyboard.press('Escape');
        await page.locator('button:has-text("Cancel"), button:has-text("No")').first().click({ timeout: 2000 }).catch(() => {});
        await page.waitForTimeout(500);
      } catch (e) {
        results.push({ page: pageName, button: 'Delete', works: false, issues: e.message });
        console.log(`  Delete: ERROR - ${e.message}`);
      }

      // Test Search
      try {
        const searchInput = page.locator('input[type="search"], input[placeholder*="search" i], input[placeholder*="Search" i], input[name*="search" i]').first();
        await searchInput.fill('test', { timeout: 5000 });
        await page.waitForTimeout(1000);
        results.push({ page: pageName, button: 'Search', works: true, issues: null });
        console.log(`  Search: PASS`);
        await searchInput.fill('');
        await page.waitForTimeout(500);
      } catch (e) {
        results.push({ page: pageName, button: 'Search', works: false, issues: e.message });
        console.log(`  Search: ERROR - ${e.message}`);
      }

      // Test Export
      try {
        const exportBtn = page.locator('button:has-text("Export"), button:has-text("export"), [title*="Export"], [aria-label*="Export"]').first();
        const [download] = await Promise.all([
          page.waitForEvent('download', { timeout: 5000 }).catch(() => null),
          exportBtn.click({ timeout: 5000 })
        ]);
        const exportWorked = download !== null;
        results.push({ page: pageName, button: 'Export', works: exportWorked, issues: exportWorked ? null : 'No download triggered' });
        console.log(`  Export: ${exportWorked ? 'PASS' : 'FAIL'}`);
      } catch (e) {
        results.push({ page: pageName, button: 'Export', works: false, issues: e.message });
        console.log(`  Export: ERROR - ${e.message}`);
      }

    } catch (e) {
      console.log(`  PAGE ERROR: ${e.message}`);
      results.push({ page: pageName, button: 'Page Load', works: false, issues: e.message });
    }
    await page.close();
  }

  await browser.close();
  console.log('\n=== RESULTS ===');
  console.log(JSON.stringify(results, null, 2));
})();
