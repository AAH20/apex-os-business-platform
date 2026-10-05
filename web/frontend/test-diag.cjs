const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({
    headless: true,
    executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    args: ['--virtual-time-budget=10000'],
  });

  const page = await browser.newPage();

  // Capture console messages
  const consoleMsgs = [];
  page.on('console', msg => {
    consoleMsgs.push(`[${msg.type()}] ${msg.text()}`);
  });

  // Capture network requests
  const networkReqs = [];
  page.on('request', req => {
    if (req.url().includes('/api/')) {
      networkReqs.push(`REQ: ${req.method()} ${req.url()}`);
    }
  });
  page.on('response', res => {
    if (res.url().includes('/api/')) {
      networkReqs.push(`RES: ${res.status()} ${res.url()}`);
    }
  });

  // Capture page errors
  const pageErrors = [];
  page.on('pageerror', err => {
    pageErrors.push(err.message);
  });

  await page.goto('http://localhost:5173/employee-management', { waitUntil: 'networkidle', timeout: 15000 });
  await page.waitForTimeout(3000);

  // Check table state
  const rowCount = await page.locator('tbody tr').count();
  const bodyText = await page.locator('tbody').textContent().catch(() => 'N/A');
  const hasEmptyState = bodyText.includes('No employees yet');

  console.log('=== DIAGNOSTICS ===');
  console.log(`Table rows: ${rowCount}`);
  console.log(`Empty state shown: ${hasEmptyState}`);
  console.log(`\nConsole messages (${consoleMsgs.length}):`);
  consoleMsgs.forEach(m => console.log(`  ${m}`));
  console.log(`\nNetwork requests (${networkReqs.length}):`);
  networkReqs.forEach(r => console.log(`  ${r}`));
  console.log(`\nPage errors (${pageErrors.length}):`);
  pageErrors.forEach(e => console.log(`  ${e}`));

  // Check what the fetch actually returns
  const fetchResult = await page.evaluate(async () => {
    try {
      const res = await fetch('/api/employees/');
      const text = await res.text();
      return { status: res.status, body: text.substring(0, 500) };
    } catch (e) {
      return { error: e.message };
    }
  });
  console.log(`\nDirect fetch from page context:`);
  console.log(`  Status: ${fetchResult.status}`);
  console.log(`  Body: ${fetchResult.body || fetchResult.error}`);

  await browser.close();
})();
