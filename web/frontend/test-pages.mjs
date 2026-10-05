import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';

const BASE_URL = 'http://localhost:3000';
const SCREENSHOT_DIR = '/Users/ahmedhassan/.hermes/cache/scratch/screenshots';

const pages = [
  { name: 'datascience', route: '/datascience' },
  { name: 'continuous-bi', route: '/continuous-bi' },
  { name: 'hr-management', route: '/hr-management' },
  { name: 'inventory-management', route: '/inventory-management' },
  { name: 'supply-chain', route: '/supply-chain' },
  { name: 'manufacturing', route: '/manufacturing' },
];

if (!fs.existsSync(SCREENSHOT_DIR)) fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });

const results = [];

async function testPage(browser, page) {
  const context = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  const p = await context.newPage();
  
  const consoleErrors = [];
  p.on('console', msg => {
    if (msg.type() === 'error') consoleErrors.push(msg.text());
  });
  p.on('pageerror', err => consoleErrors.push(err.message));

  const url = `${BASE_URL}${page.route}`;
  console.log(`Testing: ${page.name} (${url})`);
  
  try {
    await p.goto(url, { waitUntil: 'networkidle', timeout: 15000 });
    await p.waitForTimeout(2000); // extra wait for dynamic content

    // Screenshot
    const screenshotPath = path.join(SCREENSHOT_DIR, `${page.name}.png`);
    await p.screenshot({ path: screenshotPath, fullPage: true });

    // Check dark theme
    const darkTheme = await p.evaluate(() => {
      const body = document.body;
      const html = document.documentElement;
      const bodyBg = getComputedStyle(body).backgroundColor;
      const htmlBg = getComputedStyle(html).backgroundColor;
      const bodyColor = getComputedStyle(body).color;
      // Check for dark background (low luminance)
      const isDark = (color) => {
        const match = color.match(/(\d+),\s*(\d+),\s*(\d+)/);
        if (!match) return false;
        const [_, r, g, b] = match.map(Number);
        const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
        return luminance < 0.3;
      };
      return { bodyBg, htmlBg, bodyColor, isDark: isDark(bodyBg) || isDark(htmlBg) };
    });

    // Check data loaded (look for tables, cards, lists, or data containers)
    const dataLoaded = await p.evaluate(() => {
      const tables = document.querySelectorAll('table').length;
      const cards = document.querySelectorAll('[class*="card"], [class*="Card"]').length;
      const rows = document.querySelectorAll('tr, [class*="row"], [class*="Row"]').length;
      const lists = document.querySelectorAll('ul, ol, [class*="list"], [class*="List"]').length;
      const charts = document.querySelectorAll('svg, canvas, [class*="chart"], [class*="Chart"]').length;
      const text = document.body.innerText.trim();
      const hasContent = text.length > 100;
      return { tables, cards, rows, lists, charts, hasContent, textLength: text.length };
    });

    // Check buttons
    const buttons = await p.evaluate(() => {
      const btns = document.querySelectorAll('button, [role="button"], input[type="submit"], input[type="button"]');
      const btnTexts = Array.from(btns).map(b => b.textContent?.trim() || b.getAttribute('aria-label') || '').filter(Boolean);
      return { count: btns.length, texts: btnTexts.slice(0, 10) };
    });

    // Page dimensions
    const dimensions = await p.evaluate(() => ({
      width: document.documentElement.scrollWidth,
      height: document.documentElement.scrollHeight,
    }));

    const result = {
      page: page.name,
      url,
      screenshot: screenshotPath,
      size: `${dimensions.width}x${dimensions.height}`,
      dark_theme: darkTheme.isDark,
      dark_theme_detail: darkTheme,
      data_loaded: dataLoaded.hasContent && (dataLoaded.tables > 0 || dataLoaded.cards > 0 || dataLoaded.rows > 0 || dataLoaded.lists > 0 || dataLoaded.charts > 0),
      data_detail: dataLoaded,
      buttons: buttons.count,
      button_texts: buttons.texts,
      console_errors: consoleErrors,
      issues: [],
    };

    if (!result.dark_theme) result.issues.push('Dark theme not detected');
    if (!result.data_loaded) result.issues.push('No data content loaded');
    if (buttons.count === 0) result.issues.push('No buttons found');
    if (consoleErrors.length > 0) result.issues.push(`${consoleErrors.length} console error(s)`);

    results.push(result);
    console.log(`  ✓ Screenshot: ${screenshotPath}`);
    console.log(`  Dark: ${result.dark_theme}, Data: ${result.data_loaded}, Buttons: ${buttons.count}, Errors: ${consoleErrors.length}`);
    
  } catch (err) {
    console.log(`  ✗ Error: ${err.message}`);
    results.push({
      page: page.name,
      url,
      screenshot: null,
      size: 'N/A',
      dark_theme: false,
      data_loaded: false,
      buttons: 0,
      console_errors: consoleErrors,
      issues: [err.message],
    });
  } finally {
    await context.close();
  }
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  console.log('Browser launched\n');
  
  for (const page of pages) {
    await testPage(browser, page);
  }
  
  await browser.close();
  
  // Write results
  const reportPath = path.join(SCREENSHOT_DIR, 'test-results.json');
  fs.writeFileSync(reportPath, JSON.stringify(results, null, 2));
  console.log(`\nResults saved to: ${reportPath}`);
  
  // Summary
  console.log('\n=== SUMMARY ===');
  for (const r of results) {
    const status = r.issues.length === 0 ? 'PASS' : 'FAIL';
    console.log(`${status} | ${r.page} | Dark:${r.dark_theme} | Data:${r.data_loaded} | Buttons:${r.buttons} | Errors:${r.console_errors.length} | ${r.issues.join('; ')}`);
  }
})();
