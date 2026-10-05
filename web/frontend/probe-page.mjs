// Capture console errors + page exceptions + network failures for a page.
// Usage: node probe.mjs <path> [timeoutMs]
import { chromium } from 'playwright';

const target = process.argv[2] || '/iot';
const budget = Number(process.argv[3] || 12000);

const browser = await chromium.launch({ args: ['--no-sandbox'] });
const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });

const consoleErrors = [];
const pageErrors = [];
const failedRequests = [];
const pending = new Set();

page.on('console', (m) => {
  if (m.type() === 'error' || m.type() === 'warning') {
    consoleErrors.push(`[${m.type()}] ${m.text().slice(0, 300)}`);
  }
});
page.on('pageerror', (e) => pageErrors.push(String(e.message || e).slice(0, 500)));
page.on('request', (r) => pending.add(r.url()));
page.on('requestfinished', (r) => pending.delete(r.url()));
page.on('requestfailed', (r) => {
  failedRequests.push(`${r.url().slice(0, 120)} :: ${r.failure()?.errorText}`);
  pending.delete(r.url());
});

let timedOut = false;
try {
  await page.goto(`http://localhost:3000${target}`, {
    waitUntil: 'domcontentloaded',
    timeout: budget,
  });
  await page.waitForTimeout(budget);
} catch (e) {
  timedOut = true;
}

const domLen = await page.evaluate(() => document.getElementById('root')?.innerHTML.length ?? -1)
  .catch(() => -2);

const text = await page.evaluate(() => document.body.innerText.slice(0, 400))
  .catch(() => '<unavailable>');

console.log(JSON.stringify({
  target,
  gotoTimedOut: timedOut,
  rootHtmlLength: domLen,
  stuckRequests: [...pending].slice(0, 8),
  pageErrors: pageErrors.slice(0, 5),
  consoleErrors: consoleErrors.slice(0, 8),
  failedRequests: failedRequests.slice(0, 8),
  visibleText: text.replace(/\s+/g, ' ').slice(0, 220),
}, null, 2));

await browser.close();
