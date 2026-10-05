import { chromium } from 'playwright';
import fs from 'fs';

const BASE = 'http://localhost:5173';

const pages = [
  { name: 'capacity-planning', path: '/capacity-planning' },
  { name: 'cost-management', path: '/cost-management' },
  { name: 'disaster-recovery', path: '/disaster-recovery' },
  { name: 'integrations', path: '/integrations' },
  { name: 'roles-crud', path: '/roles-crud' },
  { name: 'permissions-crud', path: '/permissions-crud' },
];

const results = [];

async function testPage(browser, page) {
  const context = await browser.newContext();
  const p = await context.newPage();
  const record = { page: page.name, tests: [] };

  try {
    await p.goto(`${BASE}${page.path}`, { waitUntil: 'networkidle', timeout: 15000 });
    await p.waitForTimeout(1500);

    // Test 1: Create button opens form
    try {
      const createBtn = p.locator('button:has-text("New")').first();
      await createBtn.waitFor({ state: 'visible', timeout: 5000 });
      await createBtn.click();
      await p.waitForTimeout(500);
      const formVisible = await p.locator('form').first().isVisible().catch(() => false);
      const createHeading = await p.locator('h2:has-text("Create"), h2:has-text("New")').first().isVisible().catch(() => false);
      record.tests.push({ button: 'Create', works: formVisible || createHeading, details: formVisible || createHeading ? 'Form opened' : 'No form appeared' });
      const cancelBtn = p.locator('button:has-text("Cancel")').first();
      if (await cancelBtn.isVisible().catch(() => false)) await cancelBtn.click();
      await p.waitForTimeout(300);
    } catch (e) {
      record.tests.push({ button: 'Create', works: false, details: e.message });
    }

    // Test 2: Edit button opens edit form
    try {
      const editBtn = p.locator('button:has-text("Edit")').first();
      await editBtn.waitFor({ state: 'visible', timeout: 5000 });
      await editBtn.click();
      await p.waitForTimeout(500);
      const formVisible = await p.locator('form').first().isVisible().catch(() => false);
      const editHeading = await p.locator('h2:has-text("Edit")').first().isVisible().catch(() => false);
      record.tests.push({ button: 'Edit', works: formVisible || editHeading, details: formVisible || editHeading ? 'Edit form opened' : 'No edit form appeared' });
      const cancelBtn = p.locator('button:has-text("Cancel")').first();
      if (await cancelBtn.isVisible().catch(() => false)) await cancelBtn.click();
      await p.waitForTimeout(300);
    } catch (e) {
      record.tests.push({ button: 'Edit', works: false, details: e.message });
    }

    // Test 3: Delete button shows confirmation
    try {
      const deleteBtn = p.locator('button:has-text("Delete")').first();
      await deleteBtn.waitFor({ state: 'visible', timeout: 5000 });
      await deleteBtn.click();
      await p.waitForTimeout(500);
      const confirmVisible = await p.locator('text=Confirm Delete').first().isVisible().catch(() => false);
      const confirmText = await p.locator('text=Are you sure').first().isVisible().catch(() => false);
      record.tests.push({ button: 'Delete', works: confirmVisible || confirmText, details: confirmVisible || confirmText ? 'Confirmation shown' : 'No confirmation appeared' });
      const cancelBtn = p.locator('button:has-text("Cancel")').first();
      if (await cancelBtn.isVisible().catch(() => false)) await cancelBtn.click();
      await p.waitForTimeout(300);
    } catch (e) {
      record.tests.push({ button: 'Delete', works: false, details: e.message });
    }

    // Test 4: Search filters data
    try {
      const searchInput = p.locator('input[type="text"], input[placeholder*="Search"]').first();
      await searchInput.waitFor({ state: 'visible', timeout: 5000 });
      const initialRows = await p.locator('tbody tr').count();
      await searchInput.fill('zzzznonexistent');
      await p.waitForTimeout(500);
      const filteredRows = await p.locator('tbody tr').count();
      const emptyMsg = await p.locator('text=No ').first().isVisible().catch(() => false);
      record.tests.push({ button: 'Search', works: filteredRows < initialRows || emptyMsg, details: `Filtered from ${initialRows} to ${filteredRows} rows` });
      await searchInput.fill('');
      await p.waitForTimeout(300);
    } catch (e) {
      record.tests.push({ button: 'Search', works: false, details: e.message });
    }

    // Test 5: Export generates file
    try {
      const exportBtn = p.locator('button:has-text("Export")').first();
      await exportBtn.waitFor({ state: 'visible', timeout: 5000 });
      const [download] = await Promise.all([
        p.waitForEvent('download', { timeout: 5000 }),
        exportBtn.click(),
      ]);
      const path = await download.path();
      const content = fs.readFileSync(path, 'utf-8');
      record.tests.push({ button: 'Export', works: content.length > 0, details: `Downloaded ${download.suggestedFilename()} (${content.length} bytes)` });
    } catch (e) {
      record.tests.push({ button: 'Export', works: false, details: e.message });
    }

  } catch (e) {
    record.error = e.message;
  } finally {
    await context.close();
  }

  return record;
}

async function main() {
  const browser = await chromium.launch({
    headless: true,
    channel: 'chromium',
  });

  for (const page of pages) {
    console.log(`\nTesting: ${page.name}...`);
    const result = await testPage(browser, page);
    results.push(result);
    console.log(`  ${result.tests.map(t => `${t.button}: ${t.works ? 'PASS' : 'FAIL'}`).join(' | ')}`);
  }

  await browser.close();

  fs.writeFileSync('/Users/ahmedhassan/apex-os-business-platform/web/frontend/test-results.json', JSON.stringify(results, null, 2));
  console.log('\nResults written to test-results.json');
}

main().catch(e => { console.error(e); process.exit(1); });
