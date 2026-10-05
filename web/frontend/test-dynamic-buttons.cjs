const { chromium } = require('playwright');

const BASE = 'http://localhost:5173';
const PAGES = [
  { name: 'employee-management', label: 'Employee Management' },
  { name: 'project-management', label: 'Project Management' },
  { name: 'task-management', label: 'Task Management' },
];

const results = [];

function record(page, button, works, issues) {
  results.push({ page, button, works, issues });
  console.log(`  [${works ? 'PASS' : 'FAIL'}] ${page} / ${button}${issues ? ' — ' + issues : ''}`);
}

async function testPage(browser, pageInfo) {
  const page = await browser.newPage();
  const url = `${BASE}/${pageInfo.name}`;
  console.log(`\n=== ${pageInfo.label} (${url}) ===`);

  await page.goto(url, { waitUntil: 'networkidle', timeout: 15000 });
  await page.waitForTimeout(1000);

  // Wait for table or loading to finish
  await page.waitForTimeout(2000);

  // ── 1. Create / Add button ──
  try {
    const createBtn = page.locator('button:has-text("Add"), button:has-text("New"), button:has-text("Create")').first();
    await createBtn.waitFor({ state: 'visible', timeout: 5000 });
    await createBtn.click();
    await page.waitForTimeout(500);

    // Check if a form/dialog appeared
    const dialog = page.locator('[role="dialog"], form').first();
    const dialogVisible = await dialog.isVisible().catch(() => false);
    if (dialogVisible) {
      record(pageInfo.name, 'Create', true, 'Form/dialog opened');
      // Close it
      const cancelBtn = page.locator('button:has-text("Cancel")').first();
      if (await cancelBtn.isVisible().catch(() => false)) {
        await cancelBtn.click();
      } else {
        await page.keyboard.press('Escape');
      }
      await page.waitForTimeout(300);
    } else {
      record(pageInfo.name, 'Create', false, 'No form/dialog appeared after click');
    }
  } catch (e) {
    record(pageInfo.name, 'Create', false, e.message);
  }

  // ── 2. Edit button ──
  try {
    // Wait for table rows
    await page.waitForTimeout(1000);
    const editBtn = page.locator('button:has-text("Edit")').first();
    const editVisible = await editBtn.isVisible().catch(() => false);
    if (!editVisible) {
      record(pageInfo.name, 'Edit', false, 'No Edit button visible (empty table?)');
    } else {
      await editBtn.click();
      await page.waitForTimeout(500);
      const dialog = page.locator('[role="dialog"], form').first();
      const dialogVisible = await dialog.isVisible().catch(() => false);
      if (dialogVisible) {
        record(pageInfo.name, 'Edit', true, 'Edit form opened');
        const cancelBtn = page.locator('button:has-text("Cancel")').first();
        if (await cancelBtn.isVisible().catch(() => false)) {
          await cancelBtn.click();
        } else {
          await page.keyboard.press('Escape');
        }
        await page.waitForTimeout(300);
      } else {
        record(pageInfo.name, 'Edit', false, 'No edit form appeared');
      }
    }
  } catch (e) {
    record(pageInfo.name, 'Edit', false, e.message);
  }

  // ── 3. Delete button ──
  try {
    await page.waitForTimeout(500);
    const deleteBtn = page.locator('button:has-text("Delete")').first();
    const deleteVisible = await deleteBtn.isVisible().catch(() => false);
    if (!deleteVisible) {
      record(pageInfo.name, 'Delete', false, 'No Delete button visible');
    } else {
      await deleteBtn.click();
      await page.waitForTimeout(500);
      // Check for delete confirmation by looking for "Are you sure" text in body
      const bodyText = await page.locator('body').textContent().catch(() => '');
      const hasConfirmText = bodyText.includes('Are you sure') && bodyText.toLowerCase().includes('delete');
      if (hasConfirmText) {
        record(pageInfo.name, 'Delete', true, 'Confirmation dialog shown');
        // Cancel the delete
        const cancelBtn = page.locator('button:has-text("Cancel")').first();
        if (await cancelBtn.isVisible().catch(() => false)) {
          await cancelBtn.click();
        } else {
          await page.keyboard.press('Escape');
        }
        await page.waitForTimeout(300);
      } else {
        record(pageInfo.name, 'Delete', false, 'No confirmation dialog appeared');
      }
    }
  } catch (e) {
    record(pageInfo.name, 'Delete', false, e.message);
  }

  // ── 4. Search filter ──
  try {
    const searchInput = page.locator('input[type="text"], input[placeholder*="Search"], input[aria-label*="Search"], input[aria-label*="search"]').first();
    const searchVisible = await searchInput.isVisible().catch(() => false);
    if (!searchVisible) {
      record(pageInfo.name, 'Search', false, 'No search input found');
    } else {
      // Get initial row count
      const initialRows = await page.locator('tbody tr').count();
      // Type a search query that should match at least one row
      await searchInput.fill('Alice');
      await page.waitForTimeout(1000);
      const afterSearch = await page.locator('tbody tr').count();
      const bodyText = await page.locator('tbody').textContent().catch(() => '');
      const hasAlice = bodyText.includes('Alice');

      // Clear and try non-matching
      await searchInput.fill('zzzznonexistent999');
      await page.waitForTimeout(1000);
      const afterNoMatch = await page.locator('tbody tr').count();
      const noMatchText = await page.locator('tbody').textContent().catch(() => '');
      const showsEmpty = noMatchText.includes('No ') && (noMatchText.includes('found') || noMatchText.includes('yet'));

      // Restore
      await searchInput.fill('');
      await page.waitForTimeout(500);

      if (hasAlice && afterSearch < initialRows) {
        record(pageInfo.name, 'Search', true, `Filtered ${initialRows} → ${afterSearch} rows`);
      } else if (showsEmpty || afterNoMatch === 0) {
        record(pageInfo.name, 'Search', true, `Empty state shown for non-matching search`);
      } else {
        record(pageInfo.name, 'Search', false, `Filter had no effect (${initialRows} → ${afterSearch} → ${afterNoMatch}), Alice visible: ${hasAlice}`);
      }
    }
  } catch (e) {
    record(pageInfo.name, 'Search', false, e.message);
  }

  // ── 5. Export button ──
  try {
    const exportBtn = page.locator('button:has-text("Export"), button:has-text("export"), button[aria-label*="Export"], button[aria-label*="export"]').first();
    const exportVisible = await exportBtn.isVisible().catch(() => false);
    if (!exportVisible) {
      record(pageInfo.name, 'Export', false, 'No Export button found on page');
    } else {
      // Set up download listener
      const [download] = await Promise.all([
        page.waitForEvent('download', { timeout: 5000 }).catch(() => null),
        exportBtn.click(),
      ]);
      if (download) {
        record(pageInfo.name, 'Export', true, `File downloaded: ${download.suggestedFilename()}`);
      } else {
        record(pageInfo.name, 'Export', false, 'Button clicked but no download triggered');
      }
    }
  } catch (e) {
    record(pageInfo.name, 'Export', false, e.message);
  }

  await page.close();
}

(async () => {
  const browser = await chromium.launch({
    headless: true,
    executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    args: ['--virtual-time-budget=10000'],
  });

  for (const p of PAGES) {
    try {
      await testPage(browser, p);
    } catch (e) {
      console.error(`  ERROR testing ${p.name}: ${e.message}`);
      record(p.name, 'PAGE_LOAD', false, e.message);
    }
  }

  await browser.close();

  // ── Summary ──
  console.log('\n\n========== RESULTS SUMMARY ==========');
  console.log('Page | Button | Works | Issues');
  console.log('-----|--------|-------|-------');
  for (const r of results) {
    console.log(`${r.page} | ${r.button} | ${r.works ? 'YES' : 'NO'} | ${r.issues}`);
  }
  console.log('=====================================\n');

  const passed = results.filter(r => r.works).length;
  const failed = results.filter(r => !r.works).length;
  console.log(`Total: ${results.length} tests, ${passed} passed, ${failed} failed`);
})();
