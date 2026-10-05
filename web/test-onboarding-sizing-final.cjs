const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const BASE = 'http://localhost:3000';
const PAGES = [
  { name: 'onboarding', path: '/onboarding' },
  { name: 'sizing', path: '/sizing' },
];
const SCREENSHOT_DIR = path.join(__dirname, 'screenshots');

if (!fs.existsSync(SCREENSHOT_DIR)) fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });

const results = [];

(async () => {
  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-dev-shm-usage'],
  });

  for (const pageInfo of PAGES) {
    const { name, path: route } = pageInfo;
    const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
    const consoleErrors = [];
    const pageErrors = [];

    page.on('console', (msg) => {
      if (msg.type() === 'error') consoleErrors.push(msg.text());
    });
    page.on('pageerror', (err) => pageErrors.push(err.message));

    const result = { page: name, size: '1280x800', dark_theme: false, data_loaded: false, buttons: [], console_errors: [], issues: [] };

    try {
      await page.goto(`${BASE}${route}`, { waitUntil: 'networkidle', timeout: 15000 });
      await page.waitForTimeout(2000);

      // Screenshot
      const ssPath = path.join(SCREENSHOT_DIR, `${name}-final.png`);
      await page.screenshot({ path: ssPath, fullPage: true });
      result.screenshot = ssPath;

      // Dark theme check
      const bgColor = await page.evaluate(() => {
        const el = document.body;
        const style = window.getComputedStyle(el);
        return style.backgroundColor;
      });
      const isDark = bgColor.includes('0, 0, 0') || bgColor.includes('15, 15, 26') || bgColor.includes('17, 24, 39') || bgColor.includes('31, 41, 55') || bgColor.includes('15, 23, 42') || bgColor.includes('26, 26, 46') || bgColor.includes('22, 33, 62') || bgColor.includes('0f0f1a') || bgColor.includes('0f172a') || bgColor.includes('1e293b') || bgColor.includes('111827') || bgColor.includes('0f0f1a') || bgColor.includes('1a1a2e') || bgColor.includes('16213e') || bgColor.includes('0f3460');
      result.dark_theme = isDark;
      result.bg_color = bgColor;
      if (!isDark) result.issues.push(`Dark theme not detected (bg: ${bgColor})`);

      // Data loaded check
      const bodyText = await page.evaluate(() => document.body.innerText);
      const hasContent = bodyText.length > 100;
      result.data_loaded = hasContent;
      if (!hasContent) result.issues.push('Page appears empty');

      // Buttons check
      const buttons = await page.evaluate(() => {
        return Array.from(document.querySelectorAll('button')).map((b) => ({
          text: b.textContent?.trim().substring(0, 50),
          visible: b.offsetParent !== null,
          disabled: b.disabled,
        }));
      });
      result.buttons = buttons;
      if (buttons.length === 0) result.issues.push('No buttons found');

      // Page-specific checks
      if (name === 'onboarding') {
        const hasWelcome = bodyText.includes('Welcome') || bodyText.includes('APEX-OS');
        const hasContinue = buttons.some((b) => b.text.includes('Continue') || b.text.includes('Next'));
        const hasStep = bodyText.includes('Step') || bodyText.includes('Organization');
        if (!hasWelcome) result.issues.push('Missing welcome content');
        if (!hasContinue) result.issues.push('Missing Continue button');
        if (!hasStep) result.issues.push('Missing step indicator');
      }

      if (name === 'sizing') {
        const hasTitle = bodyText.includes('Sizing') || bodyText.includes('Calculator');
        const hasInputs = bodyText.includes('Employees') || bodyText.includes('Transactions');
        const hasExport = buttons.some((b) => b.text.includes('Export'));
        const hasResult = bodyText.includes('Tier') || bodyText.includes('Infrastructure') || bodyText.includes('Cost');
        if (!hasTitle) result.issues.push('Missing title');
        if (!hasInputs) result.issues.push('Missing input fields');
        if (!hasExport) result.issues.push('Missing export buttons');
        if (!hasResult) result.issues.push('Missing results section');
      }

    } catch (e) {
      result.issues.push(`Error: ${e.message.split('\n')[0]}`);
    }

    result.console_errors = [...consoleErrors, ...pageErrors];
    if (consoleErrors.length > 0) result.issues.push(`${consoleErrors.length} console error(s)`);
    if (pageErrors.length > 0) result.issues.push(`${pageErrors.length} page error(s)`);

    results.push(result);
    await page.close();
  }

  await browser.close();

  // Output
  console.log('\n=== FINAL TEST RESULTS ===\n');
  for (const r of results) {
    console.log(`Page: ${r.page}`);
    console.log(`  Size: ${r.size}`);
    console.log(`  Dark Theme: ${r.dark_theme ? 'PASS' : 'FAIL'} (bg: ${r.bg_color || 'N/A'})`);
    console.log(`  Data Loaded: ${r.data_loaded ? 'PASS' : 'FAIL'}`);
    console.log(`  Buttons: ${r.buttons.length} found`);
    for (const b of r.buttons) {
      console.log(`    - "${b.text}" ${b.visible ? '(visible)' : '(hidden)'} ${b.disabled ? '(disabled)' : ''}`);
    }
    console.log(`  Console Errors: ${r.console_errors.length}`);
    if (r.console_errors.length > 0) {
      for (const e of r.console_errors) console.log(`    ! ${e.substring(0, 120)}`);
    }
    console.log(`  Issues: ${r.issues.length === 0 ? 'NONE' : r.issues.join('; ')}`);
    console.log('');
  }

  // Save JSON
  const reportPath = path.join(__dirname, 'onboarding-sizing-final-results.json');
  fs.writeFileSync(reportPath, JSON.stringify(results, null, 2));
  console.log(`Report saved: ${reportPath}`);
})();
