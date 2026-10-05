const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const BASE_URL = 'http://localhost:5173';
const SCREENSHOT_DIR = '/tmp/apex_screenshots';

// Read routes from file
const routes = fs.readFileSync('/tmp/apex_routes.txt', 'utf8').trim().split('\n');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 1
  });

  const results = [];

  for (let i = 0; i < routes.length; i++) {
    const route = routes[i];
    const url = `${BASE_URL}${route.startsWith('/') ? route : '/' + route}`;
    const page = await context.newPage();
    
    const consoleErrors = [];
    page.on('console', msg => {
      if (msg.type() === 'error') consoleErrors.push(msg.text());
    });
    page.on('pageerror', err => {
      consoleErrors.push(`PAGEERROR: ${err.message}`);
    });

    const result = {
      route,
      url,
      status: 'unknown',
      title: '',
      hasContent: false,
      contentLength: 0,
      bgColor: '',
      textColor: '',
      isDarkTheme: false,
      consoleErrors: [],
      screenshot: ''
    };

    try {
      const response = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 10000 });
      result.status = response ? response.status() : 'no-response';
      
      // Wait for React to render
      await page.waitForTimeout(2000);
      
      // Check content
      result.title = await page.title();
      const bodyText = await page.evaluate(() => document.body?.innerText || '');
      result.contentLength = bodyText.length;
      result.hasContent = bodyText.trim().length > 50;
      
      // Check theme
      const theme = await page.evaluate(() => {
        const body = document.body;
        const styles = window.getComputedStyle(body);
        const bg = styles.backgroundColor;
        const color = styles.color;
        // Check for dark background (low luminance)
        const isDark = bg.includes('0, 0, 0') || 
                       bg.includes('13, 13, 13') || 
                       bg.includes('18, 18, 18') ||
                       bg.includes('26, 26, 26') ||
                       bg.includes('30, 30, 30') ||
                       bg.includes('15, 23, 42') ||
                       bg.includes('12, 17, 28') ||
                       bg.includes('20, 20, 20') ||
                       bg.includes('2, 6, 23') ||
                       bg.includes('17, 24, 39') ||
                       bg.includes('24, 24, 24') ||
                       bg.includes('40, 40, 40') ||
                       (bg.match(/\d+/g) && parseInt(bg.match(/\d+/g)[0]) < 80);
        return { bg, color, isDark };
      });
      result.bgColor = theme.bg;
      result.textColor = theme.color;
      result.isDarkTheme = theme.isDark;
      
      // Screenshot
      const screenshotName = `page_${String(i).padStart(2, '0')}${route === '/' ? '_root' : route.replace(/\//g, '_')}.png`;
      const screenshotPath = path.join(SCREENSHOT_DIR, screenshotName);
      await page.screenshot({ path: screenshotPath, fullPage: false });
      result.screenshot = screenshotPath;
      
      result.consoleErrors = consoleErrors;
      
      const statusIcon = result.hasContent ? '✓' : '⚠';
      console.log(`${statusIcon} [${i+1}/${routes.length}] ${route} - ${result.status} - content:${result.contentLength}chars - dark:${result.isDarkTheme} - errors:${consoleErrors.length}`);
      
    } catch (err) {
      result.status = 'error';
      result.consoleErrors.push(err.message);
      console.log(`✗ [${i+1}/${routes.length}] ${route} - ERROR: ${err.message}`);
    }

    results.push(result);
    await page.close();
  }

  await browser.close();

  // Write results
  fs.writeFileSync('/tmp/apex_results.json', JSON.stringify(results, null, 2));
  
  // Summary
  const ok = results.filter(r => r.hasContent && r.consoleErrors.length === 0);
  const withErrors = results.filter(r => r.consoleErrors.length > 0);
  const empty = results.filter(r => !r.hasContent);
  const dark = results.filter(r => r.isDarkTheme);
  
  console.log('\n=== SUMMARY ===');
  console.log(`Total routes: ${results.length}`);
  console.log(`Rendered OK: ${ok.length}`);
  console.log(`Empty/minimal: ${empty.length}`);
  console.log(`Console errors: ${withErrors.length}`);
  console.log(`Dark theme: ${dark.length}`);
  console.log(`Screenshots: ${SCREENSHOT_DIR}/`);
  
  if (withErrors.length > 0) {
    console.log('\nErrors:');
    withErrors.forEach(r => console.log(`  ${r.route}: ${r.consoleErrors.join(', ')}`));
  }
})();
