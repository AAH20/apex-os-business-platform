const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const BASE = 'http://localhost:3000';
const PAGES = [
  { name: 'bigdata-crud', path: '/bigdata-crud' },
  { name: 'datascience-crud', path: '/datascience-crud' },
  { name: 'continuous-bi-crud', path: '/continuous-bi-crud' },
];

const SCREENSHOT_DIR = path.join(__dirname, 'screenshots', 'final-3pages');
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
      await pg.goto(BASE + page.path, { waitUntil: 'commit', timeout: 10000 });
      await pg.waitForTimeout(4000);

      // Screenshot
      const ssPath = path.join(SCREENSHOT_DIR, `${page.name}.png`);
      await pg.screenshot({ path: ssPath, fullPage: true });
      console.log(`  Screenshot: ${ssPath}`);

      // Check dark theme
      const darkTheme = await pg.evaluate(() => {
        const body = document.body;
        const styles = window.getComputedStyle(body);
        const bg = styles.backgroundColor;
        const color = styles.color;
        const bgMatch = bg.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/);
        if (bgMatch) {
          const [r, g, b] = [parseInt(bgMatch[1]), parseInt(bgMatch[2]), parseInt(bgMatch[3])];
          const isDark = (r + g + b) / 3 < 128;
          return { isDark, bg, color };
        }
        return { isDark: false, bg, color };
      });
      console.log(`  Dark theme: ${darkTheme.isDark ? 'YES' : 'NO'} (bg: ${darkTheme.bg})`);

      // Check data loaded
      const dataLoaded = await pg.evaluate(() => {
        const bodyText = document.body.innerText;
        const hasTable = !!document.querySelector('table, [role="grid"], [class*="table"]');
        const hasCards = !!document.querySelector('[class*="card"], [class*="Card"]');
        const hasContent = bodyText.length > 200;
        const hasError = /error|failed|not found|404/i.test(bodyText.substring(0, 500));
        return { hasTable, hasCards, hasContent, hasError, textLen: bodyText.length };
      });
      console.log(`  Data loaded: table=${dataLoaded.hasTable}, cards=${dataLoaded.hasCards}, content=${dataLoaded.hasContent}, error=${dataLoaded.hasError}`);

      // Check buttons
      const buttons = await pg.evaluate(() => {
        const btns = Array.from(document.querySelectorAll('button, [role="button"], a.btn, input[type="submit"]'));
        return btns.map(b => ({
          text: (b.innerText || b.textContent || '').trim().substring(0, 50),
          tag: b.tagName,
          disabled: b.disabled || false,
        })).filter(b => b.text.length > 0);
      });
      console.log(`  Buttons found: ${buttons.length}`);
      for (const btn of buttons.slice(0, 10)) {
        console.log(`    - ${btn.text} (${btn.tag})${btn.disabled ? ' [disabled]' : ''}`);
      }

      // Check for CRUD-specific elements
      const crudElements = await pg.evaluate(() => {
        const btns = Array.from(document.querySelectorAll('button, [role="button"]'));
        const texts = btns.map(b => (b.innerText || b.textContent || '').toLowerCase());
        const hasCreate = texts.some(t => /create|new|add/.test(t)) || !!document.querySelector('[class*="create"],[class*="new"]');
        const hasEdit = texts.some(t => /edit/.test(t)) || !!document.querySelector('[class*="edit"]');
        const hasDelete = texts.some(t => /delete|remove/.test(t)) || !!document.querySelector('[class*="delete"]');
        const hasSearch = !!document.querySelector('input[type="search"], input[placeholder*="search" i]');
        const hasExport = texts.some(t => /export|download|csv/.test(t));
        return { hasCreate, hasEdit, hasDelete, hasSearch, hasExport };
      });
      console.log(`  CRUD elements: create=${crudElements.hasCreate}, edit=${crudElements.hasEdit}, delete=${crudElements.hasDelete}, search=${crudElements.hasSearch}, export=${crudElements.hasExport}`);

      results.push({
        page: page.name,
        url: BASE + page.path,
        screenshot: ssPath,
        darkTheme: darkTheme.isDark,
        dataLoaded: dataLoaded.hasContent && !dataLoaded.hasError,
        buttons: buttons.length,
        buttonTexts: buttons.map(b => b.text),
        crudElements,
        consoleErrors: consoleErrors.slice(0, 5),
        issues: [],
      });

    } catch (e) {
      console.log(`  ERROR: ${e.message}`);
      results.push({
        page: page.name,
        url: BASE + page.path,
        screenshot: null,
        darkTheme: false,
        dataLoaded: false,
        buttons: 0,
        buttonTexts: [],
        crudElements: {},
        consoleErrors: consoleErrors.slice(0, 5),
        issues: [e.message],
      });
    }

    await context.close();
  }

  await browser.close();

  // Write results
  const reportPath = path.join(__dirname, 'final-3pages-results.json');
  fs.writeFileSync(reportPath, JSON.stringify(results, null, 2));
  console.log(`\n=== Results written to ${reportPath} ===`);

  // Summary
  console.log('\n=== SUMMARY ===');
  for (const r of results) {
    const issues = [];
    if (!r.darkTheme) issues.push('not dark theme');
    if (!r.dataLoaded) issues.push('no data');
    if (r.buttons === 0) issues.push('no buttons');
    if (r.consoleErrors.length > 0) issues.push(`${r.consoleErrors.length} console errors`);
    if (r.issues.length > 0) issues.push(...r.issues);
    
    console.log(`${r.page}: ${issues.length === 0 ? 'PASS' : 'FAIL'} (${issues.join(', ') || 'all checks passed'})`);
  }
})();
