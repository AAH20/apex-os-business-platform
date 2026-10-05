const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({
    headless: true,
    executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    args: ['--virtual-time-budget=10000'],
  });

  // ── Test Search on Employee Management ──
  console.log('=== SEARCH DIAGNOSTIC ===');
  const page = await browser.newPage();
  await page.goto('http://localhost:5173/employee-management', { waitUntil: 'networkidle', timeout: 15000 });
  await page.waitForTimeout(2000);

  // Get initial state
  const initialRows = await page.locator('tbody tr').count();
  console.log(`Initial rows: ${initialRows}`);

  // Find search input
  const searchInput = page.locator('input[aria-label*="Search"], input[placeholder*="Search"]').first();
  const searchVisible = await searchInput.isVisible().catch(() => false);
  console.log(`Search input visible: ${searchVisible}`);

  if (searchVisible) {
    // Type a search term that should match
    await searchInput.fill('Alice');
    await page.waitForTimeout(1000);
    const afterSearch = await page.locator('tbody tr').count();
    const bodyText = await page.locator('tbody').textContent().catch(() => '');
    console.log(`After searching "Alice": ${afterSearch} rows`);
    console.log(`Body contains "Alice": ${bodyText.includes('Alice')}`);
    console.log(`Body contains "No employees": ${bodyText.includes('No employees')}`);

    // Try a non-matching search
    await searchInput.fill('zzzznonexistent');
    await page.waitForTimeout(1000);
    const afterNoMatch = await page.locator('tbody tr').count();
    const noMatchText = await page.locator('tbody').textContent().catch(() => '');
    console.log(`After searching "zzzznonexistent": ${afterNoMatch} rows`);
    console.log(`Body contains "No employees": ${noMatchText.includes('No employees')}`);
  }
  await page.close();

  // ── Test Delete on Task Management ──
  console.log('\n=== TASK DELETE DIAGNOSTIC ===');
  const page2 = await browser.newPage();
  await page2.goto('http://localhost:5173/task-management', { waitUntil: 'networkidle', timeout: 15000 });
  await page2.waitForTimeout(2000);

  const taskRows = await page2.locator('tbody tr').count();
  console.log(`Task rows: ${taskRows}`);

  // Find delete button
  const deleteBtn = page2.locator('button:has-text("Delete")').first();
  const deleteVisible = await deleteBtn.isVisible().catch(() => false);
  console.log(`Delete button visible: ${deleteVisible}`);

  if (deleteVisible) {
    await deleteBtn.click();
    await page2.waitForTimeout(1000);

    // Check for dialog
    const dialog = page2.locator('[role="dialog"]');
    const dialogCount = await dialog.count();
    console.log(`Dialogs found: ${dialogCount}`);

    // Check for any modal/overlay
    const modal = page2.locator('.fixed.inset-0');
    const modalCount = await modal.count();
    console.log(`Modals found: ${modalCount}`);

    // Check body text for confirmation
    const bodyText = await page2.locator('body').textContent();
    console.log(`Body contains "Are you sure": ${bodyText.includes('Are you sure')}`);
    console.log(`Body contains "Delete Task": ${bodyText.includes('Delete Task')}`);
    console.log(`Body contains "cannot be undone": ${bodyText.includes('cannot be undone')}`);

    // Try to find any button with "Delete" text in a modal context
    const allButtons = await page2.locator('button').all();
    console.log(`\nAll buttons after delete click:`);
    for (const btn of allButtons) {
      const text = await btn.textContent().catch(() => '');
      const visible = await btn.isVisible().catch(() => false);
      if (visible) {
        console.log(`  - "${text.trim()}" (visible: ${visible})`);
      }
    }
  }
  await page2.close();

  await browser.close();
})();
