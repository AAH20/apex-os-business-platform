import { chromium } from 'playwright';
import fs from 'fs';

const BASE_URL = 'http://localhost:5173';
const API_KEY = 'test-api-key-12345';
const results = [];

function log(page, button, works, issues) {
  results.push({ page, button, works, issues });
  console.log(`[${page}] ${button}: ${works ? 'PASS' : 'FAIL'}${issues ? ' - ' + issues : ''}`);
}

async function closeModals(page) {
  // Close any open modals
  const cancelBtns = await page.locator('button:has-text("Cancel"), button:has-text("Close")').all();
  for (const btn of cancelBtns) {
    try { await btn.click({ timeout: 1000 }); } catch {}
  }
  await page.keyboard.press('Escape');
  await page.waitForTimeout(300);
}

async function testPage(pageName, url, tests) {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();
  page.setDefaultTimeout(10000);
  
  await page.route('**/api/**', route => {
    const headers = { ...route.request().headers(), 'X-API-Key': API_KEY };
    route.continue({ headers });
  });

  try {
    await page.goto(url, { waitUntil: 'networkidle', timeout: 15000 });
    await page.waitForTimeout(2000);
    
    for (const test of tests) {
      try {
        await closeModals(page);
        await test.fn(page, log.bind(null, pageName));
      } catch (e) {
        log(pageName, test.name, false, e.message.split('\n')[0]);
      }
    }
  } catch (e) {
    log(pageName, 'PAGE_LOAD', false, e.message.split('\n')[0]);
  } finally {
    await browser.close();
  }
}

const dashboardTests = [
  {
    name: 'Create',
    fn: async (page, log) => {
      const btn = page.locator('button:has-text("Create Widget")').first();
      await btn.click({ timeout: 5000 });
      await page.waitForTimeout(500);
      const modal = await page.locator('text=Create Widget').count();
      log('Create', modal > 0, modal === 0 ? 'Modal not found' : null);
      await closeModals(page);
    }
  },
  {
    name: 'Edit',
    fn: async (page, log) => {
      const btn = page.locator('button:has-text("Edit")').first();
      if (await btn.count() === 0) { log('Edit', false, 'No edit button'); return; }
      await btn.click({ timeout: 5000 });
      await page.waitForTimeout(500);
      const modal = await page.locator('text=Edit Widget').count();
      log('Edit', modal > 0, modal === 0 ? 'Edit modal not found' : null);
      await closeModals(page);
    }
  },
  {
    name: 'Delete',
    fn: async (page, log) => {
      const btn = page.locator('button:has-text("Delete")').first();
      if (await btn.count() === 0) { log('Delete', false, 'No delete button'); return; }
      await btn.click({ timeout: 5000 });
      await page.waitForTimeout(500);
      log('Delete', true, null);
    }
  },
  {
    name: 'Search',
    fn: async (page, log) => {
      const input = page.locator('input[placeholder*="Search"]').first();
      if (await input.count() === 0) { log('Search', false, 'No search input'); return; }
      await input.fill('Total');
      await page.waitForTimeout(500);
      const cards = await page.locator('text=Total Revenue').count();
      log('Search', cards > 0, cards === 0 ? 'No results after search' : null);
      await input.fill('');
      await page.waitForTimeout(300);
    }
  },
  {
    name: 'Export',
    fn: async (page, log) => {
      const [download] = await Promise.all([
        page.waitForEvent('download', { timeout: 5000 }).catch(() => null),
        page.locator('button:has-text("Export CSV")').first().click({ timeout: 5000 })
      ]);
      log('Export', download !== null, download === null ? 'No download triggered' : null);
    }
  }
];

const accountingTests = [
  {
    name: 'Create',
    fn: async (page, log) => {
      await page.locator('button:has-text("Chart of Accounts")').click();
      await page.waitForTimeout(500);
      const btn = page.locator('button:has-text("Create")').first();
      await btn.click({ timeout: 5000 });
      await page.waitForTimeout(500);
      const modal = await page.locator('text=Name').count();
      log('Create', modal > 0, modal === 0 ? 'Create form not found' : null);
      await closeModals(page);
    }
  },
  {
    name: 'Edit',
    fn: async (page, log) => {
      const btn = page.locator('button[title="Edit"]').first();
      if (await btn.count() === 0) { log('Edit', false, 'No edit button'); return; }
      await btn.click({ timeout: 5000 });
      await page.waitForTimeout(500);
      const modal = await page.locator('text=Edit Account').count();
      log('Edit', modal > 0, modal === 0 ? 'Edit form not found' : null);
      await closeModals(page);
    }
  },
  {
    name: 'Delete',
    fn: async (page, log) => {
      const btn = page.locator('button[title="Delete"]').first();
      if (await btn.count() === 0) { log('Delete', false, 'No delete button'); return; }
      await btn.click({ timeout: 5000 });
      await page.waitForTimeout(500);
      const confirm = await page.locator('text=Delete Account?').count();
      log('Delete', confirm > 0, confirm === 0 ? 'No confirmation dialog' : null);
      await closeModals(page);
    }
  },
  {
    name: 'Search',
    fn: async (page, log) => {
      const input = page.locator('input[placeholder*="Search"]').first();
      if (await input.count() === 0) { log('Search', false, 'No search input'); return; }
      await input.fill('Cash');
      await page.waitForTimeout(500);
      const rows = await page.locator('td:has-text("Cash")').count();
      log('Search', rows > 0, rows === 0 ? 'No results after search' : null);
      await input.fill('');
      await page.waitForTimeout(300);
    }
  },
  {
    name: 'Export',
    fn: async (page, log) => {
      const [download] = await Promise.all([
        page.waitForEvent('download', { timeout: 5000 }).catch(() => null),
        page.locator('button:has-text("Export")').first().click({ timeout: 5000 })
      ]);
      log('Export', download !== null, download === null ? 'No download triggered' : null);
    }
  }
];

const crmTests = [
  {
    name: 'Create',
    fn: async (page, log) => {
      const btn = page.locator('button:has-text("Create")').first();
      if (await btn.count() === 0) { log('Create', false, 'No create button'); return; }
      await btn.click({ timeout: 5000 });
      await page.waitForTimeout(500);
      const modal = await page.locator('text=Create New Lead').count();
      log('Create', modal > 0, modal === 0 ? 'Create form not found' : null);
      await closeModals(page);
    }
  },
  {
    name: 'Edit',
    fn: async (page, log) => {
      const btn = page.locator('button[title="Edit"]').first();
      if (await btn.count() === 0) { log('Edit', false, 'No edit button'); return; }
      await btn.click({ timeout: 5000 });
      await page.waitForTimeout(500);
      const modal = await page.locator('text=Edit Lead').count();
      log('Edit', modal > 0, modal === 0 ? 'Edit form not found' : null);
      await closeModals(page);
    }
  },
  {
    name: 'Delete',
    fn: async (page, log) => {
      const btn = page.locator('button[title="Delete"]').first();
      if (await btn.count() === 0) { log('Delete', false, 'No delete button'); return; }
      await btn.click({ timeout: 5000 });
      await page.waitForTimeout(500);
      log('Delete', true, null);
    }
  },
  {
    name: 'Search',
    fn: async (page, log) => {
      const input = page.locator('input[placeholder*="Search"]').first();
      if (await input.count() === 0) { log('Search', false, 'No search input'); return; }
      await input.fill('Acme');
      await page.waitForTimeout(500);
      const rows = await page.locator('td:has-text("Acme")').count();
      log('Search', rows > 0, rows === 0 ? 'No results after search' : null);
      await input.fill('');
      await page.waitForTimeout(300);
    }
  },
  {
    name: 'Export',
    fn: async (page, log) => {
      const [download] = await Promise.all([
        page.waitForEvent('download', { timeout: 5000 }).catch(() => null),
        page.locator('button:has-text("CSV")').first().click({ timeout: 5000 })
      ]);
      log('Export', download !== null, download === null ? 'No download triggered' : null);
    }
  }
];

const analyticsTests = [
  {
    name: 'Create',
    fn: async (page, log) => {
      const form = await page.locator('text=Create Analytics Entry').count();
      log('Create', form > 0, form === 0 ? 'Create form not visible' : null);
    }
  },
  {
    name: 'Edit',
    fn: async (page, log) => {
      const btn = page.locator('button:has-text("Edit")').first();
      if (await btn.count() === 0) { log('Edit', false, 'No edit button'); return; }
      await btn.click({ timeout: 5000 });
      await page.waitForTimeout(500);
      const form = await page.locator('text=Edit Analytics Entry').count();
      log('Edit', form > 0, form === 0 ? 'Edit form not visible' : null);
    }
  },
  {
    name: 'Delete',
    fn: async (page, log) => {
      const btn = page.locator('button:has-text("Delete")').first();
      if (await btn.count() === 0) { log('Delete', false, 'No delete button'); return; }
      await btn.click({ timeout: 5000 });
      await page.waitForTimeout(500);
      const confirm = await page.locator('text=Confirm Delete').count();
      log('Delete', confirm > 0, confirm === 0 ? 'No confirmation dialog' : null);
      await closeModals(page);
    }
  },
  {
    name: 'Search',
    fn: async (page, log) => {
      const input = page.locator('input[placeholder*="Search"]').first();
      if (await input.count() === 0) { log('Search', false, 'No search input'); return; }
      await input.fill('Revenue');
      await page.waitForTimeout(500);
      const rows = await page.locator('td:has-text("Revenue")').count();
      log('Search', rows > 0, rows === 0 ? 'No results after search' : null);
      await input.fill('');
      await page.waitForTimeout(300);
    }
  },
  {
    name: 'Export',
    fn: async (page, log) => {
      const hasExport = await page.evaluate(() => typeof exportToCSV === 'function');
      log('Export', hasExport, hasExport ? null : 'Export function not found');
    }
  }
];

const agentReachTests = [
  {
    name: 'Create',
    fn: async (page, log) => {
      const btn = page.locator('button:has-text("Create"), button:has-text("New Agent"), button:has-text("Add")').first();
      if (await btn.count() === 0) { log('Create', false, 'No create button'); return; }
      await btn.click({ timeout: 5000 });
      await page.waitForTimeout(500);
      const modal = await page.locator('text=Create').count();
      log('Create', modal > 0, modal === 0 ? 'Create form not found' : null);
      await closeModals(page);
    }
  },
  {
    name: 'Edit',
    fn: async (page, log) => {
      const btn = page.locator('button[title="Edit"], button:has-text("Edit")').first();
      if (await btn.count() === 0) { log('Edit', false, 'No edit button'); return; }
      await btn.click({ timeout: 5000 });
      await page.waitForTimeout(500);
      const modal = await page.locator('text=Edit').count();
      log('Edit', modal > 0, modal === 0 ? 'Edit form not found' : null);
      await closeModals(page);
    }
  },
  {
    name: 'Delete',
    fn: async (page, log) => {
      const btn = page.locator('button[title="Delete"], button:has-text("Delete")').first();
      if (await btn.count() === 0) { log('Delete', false, 'No delete button'); return; }
      await btn.click({ timeout: 5000 });
      await page.waitForTimeout(500);
      const confirm = await page.locator('text=Delete').count();
      log('Delete', confirm > 0, confirm === 0 ? 'No confirmation' : null);
      await closeModals(page);
    }
  },
  {
    name: 'Search',
    fn: async (page, log) => {
      const input = page.locator('input[placeholder*="Search"]').first();
      if (await input.count() === 0) { log('Search', false, 'No search input'); return; }
      await input.fill('Data');
      await page.waitForTimeout(500);
      const rows = await page.locator('td:has-text("Data")').count();
      log('Search', rows > 0, rows === 0 ? 'No results after search' : null);
      await input.fill('');
      await page.waitForTimeout(300);
    }
  },
  {
    name: 'Export',
    fn: async (page, log) => {
      const [download] = await Promise.all([
        page.waitForEvent('download', { timeout: 5000 }).catch(() => null),
        page.locator('button:has-text("Export"), button:has-text("CSV")').first().click({ timeout: 5000 }).catch(() => {})
      ]);
      log('Export', download !== null, download === null ? 'No download triggered' : null);
    }
  }
];

const bigdataTests = [
  {
    name: 'Create',
    fn: async (page, log) => {
      const btn = page.locator('button:has-text("New Dataset")').first();
      if (await btn.count() === 0) { log('Create', false, 'No create button'); return; }
      await btn.click({ timeout: 5000 });
      await page.waitForTimeout(500);
      const form = await page.locator('text=Create Dataset').count();
      log('Create', form > 0, form === 0 ? 'Create form not found' : null);
      await closeModals(page);
    }
  },
  {
    name: 'Edit',
    fn: async (page, log) => {
      const btn = page.locator('button:has-text("Edit")').first();
      if (await btn.count() === 0) { log('Edit', false, 'No edit button'); return; }
      await btn.click({ timeout: 5000 });
      await page.waitForTimeout(500);
      const form = await page.locator('text=Edit Dataset').count();
      log('Edit', form > 0, form === 0 ? 'Edit form not found' : null);
      await closeModals(page);
    }
  },
  {
    name: 'Delete',
    fn: async (page, log) => {
      const btn = page.locator('button:has-text("Delete")').first();
      if (await btn.count() === 0) { log('Delete', false, 'No delete button'); return; }
      await btn.click({ timeout: 5000 });
      await page.waitForTimeout(500);
      const confirm = await page.locator('text=Delete dataset').count();
      log('Delete', confirm > 0, confirm === 0 ? 'No confirmation dialog' : null);
      await closeModals(page);
    }
  },
  {
    name: 'Search',
    fn: async (page, log) => {
      const input = page.locator('input[placeholder*="Search"]').first();
      if (await input.count() === 0) { log('Search', false, 'No search input'); return; }
      await input.fill('transactions');
      await page.waitForTimeout(500);
      const rows = await page.locator('td:has-text("transactions")').count();
      log('Search', rows > 0, rows === 0 ? 'No results after search' : null);
      await input.fill('');
      await page.waitForTimeout(300);
    }
  },
  {
    name: 'Export',
    fn: async (page, log) => {
      const hasExport = await page.evaluate(() => typeof exportToCSV === 'function');
      log('Export', hasExport, hasExport ? null : 'Export function not found');
    }
  }
];

console.log('Starting dynamic button tests...\n');

await testPage('dashboard', `${BASE_URL}/dashboard`, dashboardTests);
await testPage('accounting', `${BASE_URL}/accounting`, accountingTests);
await testPage('crm', `${BASE_URL}/crm`, crmTests);
await testPage('analytics', `${BASE_URL}/analytics`, analyticsTests);
await testPage('agent-reach', `${BASE_URL}/agent-reach`, agentReachTests);
await testPage('bigdata', `${BASE_URL}/bigdata`, bigdataTests);

console.log('\n=== SUMMARY ===');
const passed = results.filter(r => r.works).length;
const failed = results.filter(r => !r.works).length;
console.log(`Total: ${results.length}, Passed: ${passed}, Failed: ${failed}`);

if (failed > 0) {
  console.log('\nFailures:');
  results.filter(r => !r.works).forEach(r => {
    console.log(`  [${r.page}] ${r.button}: ${r.issues}`);
  });
}

fs.writeFileSync('/tmp/button-test-results.json', JSON.stringify(results, null, 2));
console.log('\nResults saved to /tmp/button-test-results.json');
