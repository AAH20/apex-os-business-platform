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

const SCREENSHOT_DIR = path.join(__dirname, 'screenshots', 'debug-6pages');
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
    
    const consoleMessages = [];
    const networkRequests = [];
    const networkResponses = [];
    const failedRequests = [];
    
    pg.on('console', msg => {
      consoleMessages.push({ type: msg.type(), text: msg.text() });
    });
    pg.on('pageerror', err => {
      consoleMessages.push({ type: 'pageerror', text: err.message });
    });
    pg.on('request', req => {
      networkRequests.push({ url: req.url(), method: req.method() });
    });
    pg.on('response', res => {
      networkResponses.push({ url: res.url(), status: res.status() });
      if (res.status() >= 400) {
        failedRequests.push({ url: res.url(), status: res.status() });
      }
    });
    pg.on('requestfailed', req => {
      failedRequests.push({ url: req.url(), failure: req.failure()?.errorText });
    });

    try {
      await pg.goto(BASE + page.path, { waitUntil: 'networkidle', timeout: 15000 });
      await pg.waitForTimeout(3000);

      // Screenshot
      const ssPath = path.join(SCREENSHOT_DIR, `${page.name}.png`);
      await pg.screenshot({ path: ssPath, fullPage: true });
      const ssSize = fs.statSync(ssPath).size;
      console.log(`  Screenshot: ${ssPath} (${ssSize} bytes)`);

      // Check DOM content
      const domInfo = await pg.evaluate(() => {
        const root = document.getElementById('root');
        const body = document.body;
        const html = document.documentElement;
        const bodyBg = window.getComputedStyle(body).backgroundColor;
        const htmlBg = window.getComputedStyle(html).backgroundColor;
        const bodyColor = window.getComputedStyle(body).color;
        const isDark = (bg) => {
          const match = bg.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/);
          if (!match) return false;
          const [_, r, g, b] = match.map(Number);
          return r < 50 && g < 50 && b < 50;
        };
        return {
          rootChildCount: root?.childElementCount || 0,
          rootHTML: root?.innerHTML?.substring(0, 1000) || 'NO ROOT',
          bodyText: body.innerText.substring(0, 500),
          bodyTextLength: body.innerText.length,
          bodyBg, htmlBg, bodyColor,
          isDark: isDark(bodyBg) || isDark(htmlBg),
          hasDarkClass: html.classList.contains('dark') || body.classList.contains('dark') || html.getAttribute('data-theme') === 'dark',
          tables: document.querySelectorAll('table').length,
          rows: document.querySelectorAll('table tbody tr, [class*="row"], [class*="item"], [class*="card"]').length,
          buttons: document.querySelectorAll('button, [role="button"], a.btn, input[type="submit"]').length,
          allElements: document.querySelectorAll('*').length,
        };
      });
      console.log(`  DOM: rootChildren=${domInfo.rootChildCount}, allElements=${domInfo.allElements}, textLen=${domInfo.bodyTextLength}`);
      console.log(`  Dark theme: ${domInfo.isDark || domInfo.hasDarkClass ? 'YES' : 'NO'} (bodyBg=${domInfo.bodyBg})`);
      console.log(`  Data: tables=${domInfo.tables}, rows=${domInfo.rows}, buttons=${domInfo.buttons}`);
      console.log(`  Body text: "${domInfo.bodyText.substring(0, 100)}"`);

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
      if (buttons.length > 0) {
        console.log(`  Button texts: ${buttons.map(b => b.text).join(', ')}`);
      }

      // Console errors
      const errors = consoleMessages.filter(m => m.type === 'error' || m.type === 'pageerror');
      console.log(`  Console errors: ${errors.length}`);
      for (const err of errors.slice(0, 5)) {
        console.log(`    - ${err.text.substring(0, 150)}`);
      }

      // Failed requests
      console.log(`  Failed requests: ${failedRequests.length}`);
      for (const req of failedRequests.slice(0, 5)) {
        console.log(`    - ${req.url} (${req.status || req.failure})`);
      }

      results.push({
        page: page.name,
        url: BASE + page.path,
        screenshot: ssPath,
        screenshotSize: ssSize,
        domInfo,
        buttons: buttons.length,
        buttonTexts: buttons.map(b => b.text),
        consoleErrors: errors.map(e => e.text),
        failedRequests,
        networkRequests: networkRequests.length,
        networkResponses: networkResponses.length,
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
  const reportPath = path.join(__dirname, 'debug-6pages-results.json');
  fs.writeFileSync(reportPath, JSON.stringify(results, null, 2));
  console.log(`\n=== Results written to ${reportPath} ===`);

  // Summary
  console.log('\n=== SUMMARY ===');
  for (const r of results) {
    console.log(`\n${r.page}:`);
    if (r.error) { console.log(`  ERROR: ${r.error}`); continue; }
    console.log(`  Screenshot: ${r.screenshotSize} bytes`);
    console.log(`  DOM: rootChildren=${r.domInfo?.rootChildCount}, allElements=${r.domInfo?.allElements}, textLen=${r.domInfo?.bodyTextLength}`);
    console.log(`  Dark theme: ${r.domInfo?.isDark || r.domInfo?.hasDarkClass ? 'YES' : 'NO'}`);
    console.log(`  Data: tables=${r.domInfo?.tables}, rows=${r.domInfo?.rows}, buttons=${r.domInfo?.buttons}`);
    console.log(`  Buttons: ${r.buttons} (${r.buttonTexts?.join(', ')})`);
    console.log(`  Console errors: ${r.consoleErrors?.length || 0}`);
    if (r.consoleErrors && r.consoleErrors.length > 0) {
      for (const err of r.consoleErrors) console.log(`    - ${err.substring(0, 100)}`);
    }
    console.log(`  Failed requests: ${r.failedRequests?.length || 0}`);
    if (r.failedRequests && r.failedRequests.length > 0) {
      for (const req of r.failedRequests) console.log(`    - ${req.url} (${req.status || req.failure})`);
    }
  }
})();
