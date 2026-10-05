const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const BASE = 'http://localhost:3000';
const SCREENSHOT_DIR = path.join(__dirname, 'screenshots', 'final-3pages');

(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const pg = await context.newPage();
  const consoleErrors = [];
  pg.on('console', msg => { if (msg.type() === 'error') consoleErrors.push(msg.text()); });
  pg.on('pageerror', err => consoleErrors.push(err.message));

  try {
    await pg.goto(BASE + '/continuous-bi-crud', { waitUntil: 'domcontentloaded', timeout: 15000 });
    await pg.waitForTimeout(4000);

    const ssPath = path.join(SCREENSHOT_DIR, 'continuous-bi-crud.png');
    await pg.screenshot({ path: ssPath, fullPage: true });
    console.log(`Screenshot: ${ssPath}`);

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
    console.log(`Dark theme: ${darkTheme.isDark ? 'YES' : 'NO'} (bg: ${darkTheme.bg})`);

    const dataLoaded = await pg.evaluate(() => {
      const bodyText = document.body.innerText;
      const hasTable = !!document.querySelector('table, [role="grid"], [class*="table"]');
      const hasCards = !!document.querySelector('[class*="card"], [class*="Card"]');
      const hasContent = bodyText.length > 200;
      const hasError = /error|failed|not found|404/i.test(bodyText.substring(0, 500));
      return { hasTable, hasCards, hasContent, hasError, textLen: bodyText.length };
    });
    console.log(`Data loaded: table=${dataLoaded.hasTable}, cards=${dataLoaded.hasCards}, content=${dataLoaded.hasContent}, error=${dataLoaded.hasError}`);

    const buttons = await pg.evaluate(() => {
      const btns = Array.from(document.querySelectorAll('button, [role="button"], a.btn, input[type="submit"]'));
      return btns.map(b => ({
        text: (b.innerText || b.textContent || '').trim().substring(0, 50),
        tag: b.tagName,
        disabled: b.disabled || false,
      })).filter(b => b.text.length > 0);
    });
    console.log(`Buttons found: ${buttons.length}`);
    for (const btn of buttons.slice(0, 10)) {
      console.log(`  - ${btn.text} (${btn.tag})${btn.disabled ? ' [disabled]' : ''}`);
    }

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
    console.log(`CRUD elements: create=${crudElements.hasCreate}, edit=${crudElements.hasEdit}, delete=${crudElements.hasDelete}, search=${crudElements.hasSearch}, export=${crudElements.hasExport}`);

    console.log(`Console errors: ${consoleErrors.length}`);
    for (const e of consoleErrors.slice(0, 5)) console.log(`  - ${e}`);

    const result = {
      page: 'continuous-bi-crud',
      url: BASE + '/continuous-bi-crud',
      screenshot: ssPath,
      darkTheme: darkTheme.isDark,
      dataLoaded: dataLoaded.hasContent && !dataLoaded.hasError,
      buttons: buttons.length,
      buttonTexts: buttons.map(b => b.text),
      crudElements,
      consoleErrors: consoleErrors.slice(0, 5),
      issues: [],
    };
    console.log('\nRESULT: ' + JSON.stringify(result, null, 2));

  } catch (e) {
    console.log(`ERROR: ${e.message}`);
  }

  await browser.close();
})();
