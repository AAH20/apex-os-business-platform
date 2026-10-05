const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const BASE = 'http://localhost:3000';
const PAGES = [
  { name: 'product-management', path: '/product-management' },
  { name: 'order-management', path: '/order-management' },
  { name: 'customer-management', path: '/customer-management' },
  { name: 'employee-management', path: '/employee-management' },
  { name: 'project-management', path: '/project-management' },
  { name: 'task-management', path: '/task-management' },
];

const SCREENSHOT_DIR = path.join(__dirname, 'screenshots', 'chrome-6pages');
if (!fs.existsSync(SCREENSHOT_DIR)) fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });

(async () => {
  const browser = await chromium.launch({
    headless: true,
    executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

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
      await pg.waitForTimeout(2000);

      // Screenshot
      const ssPath = path.join(SCREENSHOT_DIR, `${page.name}.png`);
      await pg.screenshot({ path: ssPath, fullPage: true });
      const ssSize = fs.statSync(ssPath).size;
      console.log(`  Screenshot: ${ssPath} (${ssSize} bytes)`);

      // Check dark theme
      const darkTheme = await pg.evaluate(() => {
        const body = document.body;
        const html = document.documentElement;
        const bodyBg = window.getComputedStyle(body).backgroundColor;
        const htmlBg = window.getComputedStyle(html).backgroundColor;
        const bodyColor = window.getComputedStyle(body).color;
        // Check for dark background (low RGB values)
        const isDark = (bg) => {
          const match = bg.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/);
          if (!match) return false;
          const [_, r, g, b] = match.map(Number);
          return r < 50 && g < 50 && b < 50;
        };
        return {
          bodyBg, htmlBg, bodyColor,
          isDark: isDark(bodyBg) || isDark(htmlBg),
          hasDarkClass: html.classList.contains('dark') || body.classList.contains('dark') || html.getAttribute('data-theme') === 'dark'
        };
      });
      console.log(`  Dark theme: ${darkTheme.isDark || darkTheme.hasDarkClass ? 'YES' : 'NO'} (bodyBg=${darkTheme.bodyBg})`);

      // Check data loaded
      const dataLoaded = await pg.evaluate(() => {
        const tables = document.querySelectorAll('table');
        const rows = document.querySelectorAll('table tbody tr, [class*="row"], [class*="item"], [class*="card"]');
        const lists = document.querySelectorAll('[class*="list"], [class*="grid"]');
        const text = document.body.innerText;
        return {
          tables: tables.length,
          rows: rows.length,
          lists: lists.length,
          textLength: text.length,
          hasContent: text.length > 200,
          hasTable: tables.length > 0,
          hasRows: rows.length > 0
        };
      });
      console.log(`  Data: ${dataLoaded.hasContent ? 'LOADED' : 'EMPTY'} (text=${dataLoaded.textLength}, tables=${dataLoaded.tables}, rows=${dataLoaded.rows})`);

      // Check buttons
      const buttons = await pg.evaluate(() => {
        const btns = Array.from(document.querySelectorAll('button, [role="button"], a.btn, input[type="submit"]'));
        return btns.map(b => ({
          text: (b.innerText || b.textContent || '').trim().substring(0, 50),
          tag: b.tagName,
          disabled: b.disabled || false,
        })).filter(b => b.text.length > 0);
      });
      console.log(`  Buttons: ${buttons.length}`);
      const buttonTexts = buttons.map(b => b.text).join(', ');

      // Test Create button
      const createBtn = buttons.find(b => /create|new|add/i.test(b.text));
      let createTest = 'NOT FOUND';
      if (createBtn) {
        try {
          const el = await pg.$(`button:has-text("${createBtn.text}"), [role="button"]:has-text("${createBtn.text}")`);
          if (el) {
            await el.click({ timeout: 3000 });
            await pg.waitForTimeout(500);
            const modalOrForm = await pg.evaluate(() => !!document.querySelector('[role="dialog"], .modal, form, [class*="modal"], [class*="drawer"]'));
            createTest = modalOrForm ? 'OK (modal/form opened)' : 'OK (clicked, no modal)';
            const closeBtn = await pg.$('[role="dialog"] button:has-text("Close"), [role="dialog"] button:has-text("Cancel"), .modal button:has-text("Close"), .modal button:has-text("Cancel"), button[aria-label="Close"]');
            if (closeBtn) { await closeBtn.click(); await pg.waitForTimeout(300); }
            else { await pg.keyboard.press('Escape'); await pg.waitForTimeout(300); }
          }
        } catch (e) { createTest = `ERROR: ${e.message.substring(0, 60)}`; }
      }

      // Test Edit button
      const editBtn = buttons.find(b => /edit/i.test(b.text));
      let editTest = 'NOT FOUND';
      if (editBtn) {
        try {
          const el = await pg.$(`button:has-text("${editBtn.text}"), [role="button"]:has-text("${editBtn.text}")`);
          if (el) {
            await el.click({ timeout: 3000 });
            await pg.waitForTimeout(500);
            const modalOrForm = await pg.evaluate(() => !!document.querySelector('[role="dialog"], .modal, form, [class*="modal"], [class*="drawer"]'));
            editTest = modalOrForm ? 'OK (modal/form opened)' : 'OK (clicked, no modal)';
            const closeBtn = await pg.$('[role="dialog"] button:has-text("Close"), [role="dialog"] button:has-text("Cancel"), .modal button:has-text("Close"), .modal button:has-text("Cancel"), button[aria-label="Close"]');
            if (closeBtn) { await closeBtn.click(); await pg.waitForTimeout(300); }
            else { await pg.keyboard.press('Escape'); await pg.waitForTimeout(300); }
          }
        } catch (e) { editTest = `ERROR: ${e.message.substring(0, 60)}`; }
      }

      // Test Delete button
      const deleteBtn = buttons.find(b => /delete|remove/i.test(b.text));
      let deleteTest = 'NOT FOUND';
      if (deleteBtn) {
        try {
          const el = await pg.$(`button:has-text("${deleteBtn.text}"), [role="button"]:has-text("${deleteBtn.text}")`);
          if (el) {
            const isDisabled = await el.isDisabled();
            deleteTest = isDisabled ? 'DISABLED' : 'OK (clickable)';
          }
        } catch (e) { deleteTest = `ERROR: ${e.message.substring(0, 60)}`; }
      }

      // Test Search
      const searchInput = await pg.$('input[type="search"], input[placeholder*="search" i], input[placeholder*="Search" i], input[name="search"], input[name="q"]');
      let searchTest = 'NOT FOUND';
      if (searchInput) {
        try {
          await searchInput.click({ timeout: 3000 });
          await searchInput.fill('test');
          await pg.waitForTimeout(500);
          searchTest = 'OK (search works)';
        } catch (e) { searchTest = `ERROR: ${e.message.substring(0, 60)}`; }
      }

      // Test Export
      const exportBtn = buttons.find(b => /export|download|csv|excel/i.test(b.text));
      let exportTest = 'NOT FOUND';
      if (exportBtn) {
        try {
          const el = await pg.$(`button:has-text("${exportBtn.text}"), [role="button"]:has-text("${exportBtn.text}")`);
          if (el) {
            const isDisabled = await el.isDisabled();
            exportTest = isDisabled ? 'DISABLED' : 'OK (clickable)';
          }
        } catch (e) { exportTest = `ERROR: ${e.message.substring(0, 60)}`; }
      }

      results.push({
        page: page.name,
        url: BASE + page.path,
        screenshot: ssPath,
        screenshotSize: ssSize,
        darkTheme: darkTheme.isDark || darkTheme.hasDarkClass,
        darkThemeDetail: darkTheme,
        dataLoaded: dataLoaded.hasContent,
        dataDetail: dataLoaded,
        buttons: buttons.length,
        buttonTexts: buttonTexts,
        buttonTests: { create: createTest, edit: editTest, delete: deleteTest, search: searchTest, export: exportTest },
        consoleErrors: consoleErrors.slice(0, 5),
        consoleErrorCount: consoleErrors.length,
      });

    } catch (e) {
      console.log(`  ERROR: ${e.message}`);
      results.push({
        page: page.name,
        url: BASE + page.path,
        error: e.message,
        screenshot: null,
      });
    }

    await context.close();
  }

  await browser.close();

  // Write results
  const reportPath = path.join(__dirname, 'chrome-6pages-results.json');
  fs.writeFileSync(reportPath, JSON.stringify(results, null, 2));
  console.log(`\n=== Results written to ${reportPath} ===`);

  // Summary
  console.log('\n=== SUMMARY ===');
  for (const r of results) {
    console.log(`\n${r.page}:`);
    if (r.error) { console.log(`  ERROR: ${r.error}`); continue; }
    console.log(`  Screenshot: ${r.screenshotSize} bytes`);
    console.log(`  Dark theme: ${r.darkTheme ? 'YES' : 'NO'}`);
    console.log(`  Data loaded: ${r.dataLoaded ? 'YES' : 'NO'} (${r.dataDetail?.textLength || 0} chars, ${r.dataDetail?.tables || 0} tables, ${r.dataDetail?.rows || 0} rows)`);
    console.log(`  Buttons: ${r.buttons} (${r.buttonTexts?.substring(0, 80)})`);
    console.log(`  Create: ${r.buttonTests?.create}`);
    console.log(`  Edit: ${r.buttonTests?.edit}`);
    console.log(`  Delete: ${r.buttonTests?.delete}`);
    console.log(`  Search: ${r.buttonTests?.search}`);
    console.log(`  Export: ${r.buttonTests?.export}`);
    console.log(`  Console errors: ${r.consoleErrorCount || 0}`);
    if (r.consoleErrors && r.consoleErrors.length > 0) {
      for (const err of r.consoleErrors) console.log(`    - ${err.substring(0, 100)}`);
    }
  }
})();
