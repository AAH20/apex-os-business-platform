const { chromium } = require('playwright');

const BASE = 'http://localhost:5173';
const PAGES = [
  'opportunities-crud',
  'campaigns-crud',
  'alerts-crud',
  'user-management',
  'lead-management',
  'report-management',
];

(async () => {
  const browser = await chromium.launch({ headless: true });
  const results = [];

  for (const page of PAGES) {
    const ctx = await browser.newContext();
    const p = await ctx.newPage();
    const pageResult = { page, tests: {} };

    try {
      await p.goto(`${BASE}/${page}`, { waitUntil: 'networkidle', timeout: 15000 });
      await p.waitForTimeout(2000);

      // 1. Create button
      try {
        const createBtn = p.locator('button:has-text("Create"), button:has-text("Add"), button:has-text("New")').first();
        await createBtn.click({ timeout: 3000 });
        await p.waitForTimeout(1000);
        const formVisible = await p.locator('form, [role="dialog"], .modal, input, select').first().isVisible().catch(() => false);
        pageResult.tests.create = formVisible ? 'PASS' : 'FAIL: form not visible';
        // Close form
        const cancelBtn = p.locator('button:has-text("Cancel"), button:has-text("Close")').first();
        if (await cancelBtn.isVisible().catch(() => false)) await cancelBtn.click();
        await p.waitForTimeout(500);
      } catch (e) {
        pageResult.tests.create = `FAIL: ${e.message.split('\n')[0]}`;
      }

      // 2. Edit button
      try {
        const editBtn = p.locator('button:has-text("Edit"), button:has-text("Update"), a:has-text("Edit")').first();
        await editBtn.click({ timeout: 3000 });
        await p.waitForTimeout(1000);
        const editFormVisible = await p.locator('form, [role="dialog"], .modal, input').first().isVisible().catch(() => false);
        pageResult.tests.edit = editFormVisible ? 'PASS' : 'FAIL: edit form not visible';
        const cancelBtn2 = p.locator('button:has-text("Cancel"), button:has-text("Close")').first();
        if (await cancelBtn2.isVisible().catch(() => false)) await cancelBtn2.click();
        await p.waitForTimeout(500);
      } catch (e) {
        pageResult.tests.edit = `FAIL: ${e.message.split('\n')[0]}`;
      }

      // 3. Delete button
      try {
        const deleteBtn = p.locator('button:has-text("Delete"), button:has-text("Remove")').first();
        await deleteBtn.click({ timeout: 3000 });
        await p.waitForTimeout(1000);
        const confirmVisible = await p.locator('text=/confirm|are you sure|delete.*\?/i, [role="alertdialog"], .modal').first().isVisible().catch(() => false);
        pageResult.tests.delete = confirmVisible ? 'PASS' : 'FAIL: no confirmation dialog';
        // Dismiss
        const cancelDel = p.locator('button:has-text("Cancel"), button:has-text("No")').first();
        if (await cancelDel.isVisible().catch(() => false)) await cancelDel.click();
        await p.waitForTimeout(500);
      } catch (e) {
        pageResult.tests.delete = `FAIL: ${e.message.split('\n')[0]}`;
      }

      // 4. Search
      try {
        const searchInput = p.locator('input[type="search"], input[placeholder*="search" i], input[placeholder*="Search" i], input[placeholder*="filter" i]').first();
        await searchInput.fill('test', { timeout: 3000 });
        await p.waitForTimeout(1000);
        pageResult.tests.search = 'PASS';
        await searchInput.fill('');
        await p.waitForTimeout(500);
      } catch (e) {
        pageResult.tests.search = `FAIL: ${e.message.split('\n')[0]}`;
      }

      // 5. Export
      try {
        const [download] = await Promise.all([
          p.waitForEvent('download', { timeout: 5000 }).catch(() => null),
          p.locator('button:has-text("Export"), button:has-text("Download"), button:has-text("CSV"), button:has-text("Excel")').first().click({ timeout: 3000 }),
        ]);
        pageResult.tests.export = download ? `PASS (${download.suggestedFilename()})` : 'FAIL: no download triggered';
      } catch (e) {
        pageResult.tests.export = `FAIL: ${e.message.split('\n')[0]}`;
      }

    } catch (e) {
      pageResult.error = e.message.split('\n')[0];
    }

    results.push(pageResult);
    await ctx.close();
  }

  await browser.close();
  console.log(JSON.stringify(results, null, 2));
})();
