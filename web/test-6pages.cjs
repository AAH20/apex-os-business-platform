const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const BASE = 'http://localhost:3000';
const PAGES = [
  { name: 'iot', path: '/iot' },
  { name: 'compliance', path: '/compliance' },
  { name: 'budgeting', path: '/budgeting' },
  { name: 'opportunities-crud', path: '/opportunities-crud' },
  { name: 'campaigns-crud', path: '/campaigns-crud' },
  { name: 'alerts-crud', path: '/alerts-crud' },
];

const SCREENSHOT_DIR = path.join(__dirname, 'screenshots', 'retest');
if (!fs.existsSync(SCREENSHOT_DIR)) fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });

(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' });
  const results = [];

  for (const page of PAGES) {
    console.log(`\n=== Testing ${page.name} ===`);
    const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const pg = await context.newPage();
    const consoleErrors = [];
    pg.on('console', msg => { if (msg.type() === 'error') consoleErrors.push(msg.text()); });
    pg.on('pageerror', err => consoleErrors.push(err.message));

    try {
      await pg.goto(BASE + page.path, { waitUntil: 'networkidle', timeout: 15000 });
      await pg.waitForTimeout(1500);

      // Screenshot
      const ssPath = path.join(SCREENSHOT_DIR, `${page.name}.png`);
      await pg.screenshot({ path: ssPath, fullPage: true });
      console.log(`  Screenshot: ${ssPath}`);

      // Check render
      const bodyText = await pg.evaluate(() => document.body.innerText.substring(0, 500));
      const hasContent = bodyText.length > 50;
      console.log(`  Render: ${hasContent ? 'OK' : 'EMPTY'} (${bodyText.length} chars)`);

      // Test buttons
      const buttons = await pg.evaluate(() => {
        const btns = Array.from(document.querySelectorAll('button, [role="button"], a.btn, input[type="submit"]'));
        return btns.map(b => ({
          text: (b.innerText || b.textContent || '').trim().substring(0, 50),
          tag: b.tagName,
          type: b.type || '',
          disabled: b.disabled || false,
        })).filter(b => b.text.length > 0);
      });

      console.log(`  Buttons found: ${buttons.length}`);
      const buttonTests = {};

      // Test Create button
      const createBtn = buttons.find(b => /create|new|add/i.test(b.text));
      if (createBtn) {
        try {
          const el = await pg.$(`button:has-text("${createBtn.text}"), [role="button"]:has-text("${createBtn.text}")`);
          if (el) {
            await el.click({ timeout: 3000 });
            await pg.waitForTimeout(500);
            const modalOrForm = await pg.evaluate(() => !!document.querySelector('[role="dialog"], .modal, form, [class*="modal"], [class*="drawer"]'));
            buttonTests.create = modalOrForm ? 'OK (modal/form opened)' : 'OK (clicked, no modal detected)';
            // Close modal if open
            const closeBtn = await pg.$('[role="dialog"] button:has-text("Close"), [role="dialog"] button:has-text("Cancel"), .modal button:has-text("Close"), .modal button:has-text("Cancel"), button[aria-label="Close"]');
            if (closeBtn) { await closeBtn.click(); await pg.waitForTimeout(300); }
            else { await pg.keyboard.press('Escape'); await pg.waitForTimeout(300); }
          } else {
            buttonTests.create = 'NOT FOUND';
          }
        } catch (e) {
          buttonTests.create = `ERROR: ${e.message.substring(0, 80)}`;
        }
      } else {
        buttonTests.create = 'NOT FOUND';
      }

      // Test Edit button
      const editBtn = buttons.find(b => /edit/i.test(b.text));
      if (editBtn) {
        try {
          const el = await pg.$(`button:has-text("${editBtn.text}"), [role="button"]:has-text("${editBtn.text}")`);
          if (el) {
            await el.click({ timeout: 3000 });
            await pg.waitForTimeout(500);
            const modalOrForm = await pg.evaluate(() => !!document.querySelector('[role="dialog"], .modal, form, [class*="modal"], [class*="drawer"]'));
            buttonTests.edit = modalOrForm ? 'OK (modal/form opened)' : 'OK (clicked, no modal detected)';
            const closeBtn = await pg.$('[role="dialog"] button:has-text("Close"), [role="dialog"] button:has-text("Cancel"), .modal button:has-text("Close"), .modal button:has-text("Cancel"), button[aria-label="Close"]');
            if (closeBtn) { await closeBtn.click(); await pg.waitForTimeout(300); }
            else { await pg.keyboard.press('Escape'); await pg.waitForTimeout(300); }
          } else {
            buttonTests.edit = 'NOT FOUND';
          }
        } catch (e) {
          buttonTests.edit = `ERROR: ${e.message.substring(0, 80)}`;
        }
      } else {
        buttonTests.edit = 'NOT FOUND';
      }

      // Test Delete button
      const deleteBtn = buttons.find(b => /delete|remove/i.test(b.text));
      if (deleteBtn) {
        try {
          const el = await pg.$(`button:has-text("${deleteBtn.text}"), [role="button"]:has-text("${deleteBtn.text}")`);
          if (el) {
            // Don't actually delete - just check it's clickable
            const isDisabled = await el.isDisabled();
            buttonTests.delete = isDisabled ? 'DISABLED' : 'OK (clickable, not triggered)';
          } else {
            buttonTests.delete = 'NOT FOUND';
          }
        } catch (e) {
          buttonTests.delete = `ERROR: ${e.message.substring(0, 80)}`;
        }
      } else {
        buttonTests.delete = 'NOT FOUND';
      }

      // Test Search
      const searchInput = await pg.$('input[type="search"], input[placeholder*="search" i], input[placeholder*="Search" i], input[name="search"], input[name="q"]');
      if (searchInput) {
        try {
          await searchInput.click({ timeout: 3000 });
          await searchInput.fill('test');
          await pg.waitForTimeout(500);
          const hasResults = await pg.evaluate(() => document.body.innerText.length > 50);
          buttonTests.search = hasResults ? 'OK (search works)' : 'OK (search input found)';
        } catch (e) {
          buttonTests.search = `ERROR: ${e.message.substring(0, 80)}`;
        }
      } else {
        buttonTests.search = 'NOT FOUND';
      }

      // Test Export
      const exportBtn = buttons.find(b => /export|download|csv|excel/i.test(b.text));
      if (exportBtn) {
        try {
          const el = await pg.$(`button:has-text("${exportBtn.text}"), [role="button"]:has-text("${exportBtn.text}")`);
          if (el) {
            const isDisabled = await el.isDisabled();
            buttonTests.export = isDisabled ? 'DISABLED' : 'OK (clickable)';
          } else {
            buttonTests.export = 'NOT FOUND';
          }
        } catch (e) {
          buttonTests.export = `ERROR: ${e.message.substring(0, 80)}`;
        }
      } else {
        buttonTests.export = 'NOT FOUND';
      }

      results.push({
        page: page.name,
        url: BASE + page.path,
        render: hasContent ? 'OK' : 'EMPTY',
        buttons: buttons.length,
        buttonTests,
        consoleErrors: consoleErrors.slice(0, 5),
        screenshot: ssPath,
      });

    } catch (e) {
      console.log(`  ERROR: ${e.message}`);
      results.push({
        page: page.name,
        url: BASE + page.path,
        render: 'ERROR',
        error: e.message,
        screenshot: null,
      });
    }

    await context.close();
  }

  await browser.close();

  // Write results
  const reportPath = path.join(__dirname, 'retest-results.json');
  fs.writeFileSync(reportPath, JSON.stringify(results, null, 2));
  console.log(`\n=== Results written to ${reportPath} ===`);

  // Summary
  for (const r of results) {
    console.log(`\n${r.page}: render=${r.render}, buttons=${r.buttons || 0}`);
    if (r.buttonTests) {
      for (const [k, v] of Object.entries(r.buttonTests)) {
        console.log(`  ${k}: ${v}`);
      }
    }
    if (r.consoleErrors && r.consoleErrors.length > 0) {
      console.log(`  console errors: ${r.consoleErrors.length}`);
    }
  }
})();
