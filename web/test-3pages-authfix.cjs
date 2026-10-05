const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const BASE = 'http://localhost:3000';
const PAGES = [
  { name: 'data-warehouse', path: '/data-warehouse' },
  { name: 'knowledge-base', path: '/knowledge-base' },
  { name: 'monitoring', path: '/monitoring' },
];

const SCREENSHOT_DIR = path.join(__dirname, 'screenshots', 'retest-3pages-authfix');
fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });

const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';

const results = [];

async function testPage(browser, pageInfo) {
  const { name, path: pagePath } = pageInfo;
  const page = await browser.newPage();
  const pageResult = { page: name, render: null, data: null, buttons: {}, issues: [] };

  try {
    // 1. Navigate and check render
    const response = await page.goto(`${BASE}${pagePath}`, { waitUntil: 'networkidle', timeout: 20000 });
    await page.waitForTimeout(2500);

    const title = await page.title();
    const h1 = await page.locator('h1').first().textContent().catch(() => null);
    const bodyText = await page.locator('body').textContent().catch(() => '');
    const hasContent = bodyText && bodyText.trim().length > 50;
    pageResult.render = {
      status: response ? response.status() : 'unknown',
      title,
      h1,
      hasContent,
      ok: response && response.status() === 200 && hasContent
    };

    // 2. Screenshot with Chrome headless
    const screenshotPath = path.join(SCREENSHOT_DIR, `${name}.png`);
    try {
      execSync(`"${CHROME}" --headless --disable-gpu --no-sandbox --disable-dev-shm-usage --window-size=1920,1080 --screenshot="${screenshotPath}" --virtual-time-budget=5000 "${BASE}${pagePath}" 2>/dev/null`, { timeout: 30000 });
      pageResult.screenshot = screenshotPath;
      pageResult.screenshotSize = fs.existsSync(screenshotPath) ? fs.statSync(screenshotPath).size : 0;
    } catch (e) {
      pageResult.issues.push(`Screenshot failed: ${e.message}`);
    }

    // 3. Check data loaded
    const tableRows = await page.locator('tbody tr').count();
    const cards = await page.locator('.card, [class*="card"]').count();
    const sections = await page.locator('section, .section, [class*="section"]').count();
    const listItems = await page.locator('li, [class*="list-item"], [class*="listItem"]').count();
    pageResult.data = { tableRows, cards, sections, listItems, loaded: tableRows > 0 || cards > 0 || sections > 0 || listItems > 0 };

    // 4. Test all buttons on the page
    const allButtons = await page.locator('button').all();
    const buttonTexts = [];
    for (const btn of allButtons) {
      const text = await btn.textContent().catch(() => '');
      const visible = await btn.isVisible().catch(() => false);
      if (visible && text.trim()) {
        buttonTexts.push(text.trim());
      }
    }
    pageResult.buttonsFound = buttonTexts;

    // Test each unique button
    const uniqueButtons = [...new Set(buttonTexts)];
    for (const btnText of uniqueButtons.slice(0, 10)) {
      try {
        const btn = page.locator(`button:has-text("${btnText}")`).first();
        if (await btn.count() > 0 && await btn.isVisible()) {
          await btn.click();
          await page.waitForTimeout(1000);
          // Check if modal/dialog appeared
          const modal = await page.locator('[role="dialog"], .modal, form, [class*="modal"], [class*="dialog"]').first().isVisible().catch(() => false);
          // Check if page content changed
          const newBodyLen = await page.locator('body').textContent().then(t => t.length).catch(() => 0);
          pageResult.buttons[btnText] = { clicked: true, modalAppeared: modal, contentChanged: newBodyLen !== bodyText.length };
          // Close modal if opened
          await page.keyboard.press('Escape');
          await page.waitForTimeout(500);
        }
      } catch (e) {
        pageResult.buttons[btnText] = { clicked: false, error: e.message };
      }
    }

    // 5. Test links/navigation
    const links = await page.locator('a[href]').all();
    const linkHrefs = [];
    for (const link of links.slice(0, 10)) {
      const href = await link.getAttribute('href').catch(() => '');
      if (href && href.startsWith('/')) linkHrefs.push(href);
    }
    pageResult.internalLinks = [...new Set(linkHrefs)];

  } catch (e) {
    pageResult.issues.push(e.message);
  } finally {
    await page.close();
  }

  return pageResult;
}

(async () => {
  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-dev-shm-usage']
  });

  for (const pageInfo of PAGES) {
    console.log(`Testing ${pageInfo.name}...`);
    const result = await testPage(browser, pageInfo);
    results.push(result);
    console.log(JSON.stringify(result, null, 2));
  }

  await browser.close();

  console.log('\n=== SUMMARY ===');
  for (const r of results) {
    const renderOk = r.render && r.render.ok;
    const dataOk = r.data && r.data.loaded;
    const btnCount = Object.keys(r.buttons || {}).length;
    const btnWorking = Object.values(r.buttons || {}).filter(b => b.clicked).length;
    console.log(`${r.page}: render=${renderOk ? 'OK' : 'FAIL'}, data=${dataOk ? 'OK' : 'FAIL'}, buttons=${btnWorking}/${btnCount} working`);
    if (r.issues.length > 0) {
      console.log(`  ISSUES: ${r.issues.join('; ')}`);
    }
  }

  fs.writeFileSync(path.join(SCREENSHOT_DIR, 'results.json'), JSON.stringify(results, null, 2));
  console.log(`\nResults saved to ${path.join(SCREENSHOT_DIR, 'results.json')}`);
})();
