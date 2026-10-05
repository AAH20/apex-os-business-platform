const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const BASE = 'http://localhost:3000';
const PAGES = [
  { name: 'iot', path: '/iot' },
  { name: 'reporting', path: '/reporting' },
  { name: 'compliance', path: '/compliance' },
  { name: 'asset-management', path: '/asset-management' },
  { name: 'budgeting', path: '/budgeting' },
  { name: 'project-mgmt', path: '/project-mgmt' },
];

const SCREENSHOT_DIR = path.join(__dirname, 'screenshots', 'authfix-retest');
if (!fs.existsSync(SCREENSHOT_DIR)) fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });

const results = [];

async function testPage(browser, pageInfo) {
  const { name, path: pagePath } = pageInfo;
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  const consoleErrors = [];
  page.on('console', msg => { if (msg.type() === 'error') consoleErrors.push(msg.text()); });
  page.on('pageerror', err => consoleErrors.push(err.message));

  const result = { page: name, render: null, data: null, buttons: {}, issues: [] };

  try {
    const response = await page.goto(`${BASE}${pagePath}`, { waitUntil: 'networkidle', timeout: 20000 });
    await page.waitForTimeout(2000);

    // Render check
    const bodyText = await page.locator('body').textContent().catch(() => '');
    const hasContent = bodyText && bodyText.trim().length > 50;
    const title = await page.title();
    result.render = {
      status: response ? response.status() : 'unknown',
      title,
      hasContent,
      ok: response && response.status() === 200 && hasContent
    };

    // Screenshot
    const ssPath = path.join(SCREENSHOT_DIR, `${name}.png`);
    await page.screenshot({ path: ssPath, fullPage: true });
    result.screenshot = ssPath;

    // Data check - look for table rows, cards, or data indicators
    const tableRows = await page.locator('tbody tr').count();
    const cards = await page.locator('[class*="card"], [class*="Card"]').count();
    const dataElements = await page.locator('[class*="data"], [class*="table"], [class*="list"]').count();
    result.data = { tableRows, cards, dataElements, hasData: tableRows > 0 || cards > 0 || dataElements > 0 };

    // Get all buttons
    const buttons = await page.evaluate(() => {
      const btns = Array.from(document.querySelectorAll('button, [role="button"], a.btn'));
      return btns.map(b => ({
        text: (b.innerText || b.textContent || '').trim().substring(0, 50),
        tag: b.tagName,
        disabled: b.disabled || false,
      })).filter(b => b.text.length > 0);
    });
    result.buttonsFound = buttons.length;

    // Test Create/Add button
    const createBtn = buttons.find(b => /create|new|add/i.test(b.text));
    if (createBtn) {
      try {
        const el = await page.$(`button:has-text("${createBtn.text}"), [role="button"]:has-text("${createBtn.text}")`);
        if (el) {
          await el.click({ timeout: 3000 });
          await page.waitForTimeout(800);
          const modal = await page.evaluate(() => !!document.querySelector('[role="dialog"], .modal, form, [class*="modal"], [class*="drawer"]'));
          result.buttons.create = modal ? 'OK' : 'OK (no modal)';
          const closeBtn = await page.$('[role="dialog"] button:has-text("Close"), [role="dialog"] button:has-text("Cancel"), button[aria-label="Close"]');
          if (closeBtn) { await closeBtn.click(); await page.waitForTimeout(300); }
          else { await page.keyboard.press('Escape'); await page.waitForTimeout(300); }
        }
      } catch (e) { result.buttons.create = `ERROR: ${e.message.substring(0, 60)}`; }
    } else { result.buttons.create = 'NOT FOUND'; }

    // Test Edit button
    const editBtn = buttons.find(b => /edit/i.test(b.text));
    if (editBtn) {
      try {
        const el = await page.$(`button:has-text("${editBtn.text}"), [role="button"]:has-text("${editBtn.text}")`);
        if (el) {
          await el.click({ timeout: 3000 });
          await page.waitForTimeout(800);
          const modal = await page.evaluate(() => !!document.querySelector('[role="dialog"], .modal, form, [class*="modal"], [class*="drawer"]'));
          result.buttons.edit = modal ? 'OK' : 'OK (no modal)';
          const closeBtn = await page.$('[role="dialog"] button:has-text("Close"), [role="dialog"] button:has-text("Cancel"), button[aria-label="Close"]');
          if (closeBtn) { await closeBtn.click(); await page.waitForTimeout(300); }
          else { await page.keyboard.press('Escape'); await page.waitForTimeout(300); }
        }
      } catch (e) { result.buttons.edit = `ERROR: ${e.message.substring(0, 60)}`; }
    } else { result.buttons.edit = 'NOT FOUND'; }

    // Test Delete button
    const deleteBtn = buttons.find(b => /delete|remove/i.test(b.text));
    if (deleteBtn) {
      try {
        const el = await page.$(`button:has-text("${deleteBtn.text}"), [role="button"]:has-text("${deleteBtn.text}")`);
        if (el) {
          const isDisabled = await el.isDisabled();
          result.buttons.delete = isDisabled ? 'DISABLED' : 'OK (clickable)';
        }
      } catch (e) { result.buttons.delete = `ERROR: ${e.message.substring(0, 60)}`; }
    } else { result.buttons.delete = 'NOT FOUND'; }

    // Test Search
    const searchInput = await page.$('input[type="search"], input[placeholder*="search" i], input[placeholder*="Search" i]');
    if (searchInput) {
      try {
        await searchInput.fill('test');
        await page.waitForTimeout(500);
        result.buttons.search = 'OK';
      } catch (e) { result.buttons.search = `ERROR: ${e.message.substring(0, 60)}`; }
    } else { result.buttons.search = 'NOT FOUND'; }

    // Test Export
    const exportBtn = buttons.find(b => /export|download|csv|excel/i.test(b.text));
    if (exportBtn) {
      result.buttons.export = 'OK (found)';
    } else { result.buttons.export = 'NOT FOUND'; }

    if (consoleErrors.length > 0) result.issues.push(...consoleErrors.slice(0, 3));

  } catch (e) {
    result.issues.push(e.message);
  } finally {
    await context.close();
  }

  return result;
}

(async () => {
  const browser = await chromium.launch({
    headless: true,
    executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    args: ['--no-sandbox', '--disable-dev-shm-usage']
  });

  for (const pageInfo of PAGES) {
    console.log(`Testing ${pageInfo.name}...`);
    const result = await testPage(browser, pageInfo);
    results.push(result);
    console.log(`  render=${result.render?.ok ? 'OK' : 'FAIL'}, data=${result.data?.hasData ? 'YES' : 'NO'}, buttons=${result.buttonsFound}`);
  }

  await browser.close();

  const reportPath = path.join(__dirname, 'authfix-retest-results.json');
  fs.writeFileSync(reportPath, JSON.stringify(results, null, 2));
  console.log(`\nResults saved to ${reportPath}`);

  console.log('\n=== SUMMARY ===');
  for (const r of results) {
    console.log(`${r.page}: render=${r.render?.ok ? 'OK' : 'FAIL'}, data=${r.data?.hasData ? 'YES' : 'NO'}, buttons=${r.buttonsFound}`);
    for (const [k, v] of Object.entries(r.buttons)) {
      if (v.includes('ERROR') || v === 'NOT FOUND') console.log(`  ${k}: ${v}`);
    }
    if (r.issues.length > 0) console.log(`  issues: ${r.issues.join('; ')}`);
  }
})();
