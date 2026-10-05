// Exercise every tab + search + pagination on a page, report errors and timings.
// Usage: node probe-iot-tabs.mjs [path] [timeoutMs]
import { chromium } from 'playwright';

const target = process.argv[2] || '/iot';
const budget = Number(process.argv[3] || 12000);

const browser = await chromium.launch({ args: ['--no-sandbox'] });
const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });

const pageErrors = [];
const consoleErrors = [];
page.on('pageerror', (e) => pageErrors.push(String(e.message || e).slice(0, 400)));
page.on('console', (m) => {
  if (m.type() === 'error') consoleErrors.push(m.text().slice(0, 300));
});

const t0 = Date.now();
await page.goto(`http://localhost:3000${target}`, { waitUntil: 'domcontentloaded', timeout: budget });
await page.waitForSelector('#root', { timeout: budget });
const domReadyMs = Date.now() - t0;

// Confirm the main thread is actually responsive: a synchronous eval must answer fast.
const mainThreadMs = await page.evaluate(() => {
  const s = performance.now();
  let x = 0;
  for (let i = 0; i < 5e6; i++) x += i;
  return { busyMs: Math.round(performance.now() - s), x };
});

const tabLabels = ['Devices', 'Sensors', 'Telemetry', 'Alerts', 'Groups'];
const tabResults = [];
for (const label of tabLabels) {
  const started = Date.now();
  try {
    await page.getByRole('button', { name: label, exact: true }).click({ timeout: 5000 });
    await page.waitForTimeout(600);
    tabResults.push({
      tab: label,
      ms: Date.now() - started,
      rootLen: await page.evaluate(() => document.getElementById('root')?.innerHTML.length ?? -1),
      hasTable: await page.evaluate(() => !!document.querySelector('table')),
      rows: await page.evaluate(() => document.querySelectorAll('tbody tr').length),
      text: await page.evaluate(() => {
        const t = document.querySelector('table')?.parentElement?.innerText ?? document.body.innerText;
        return t.replace(/\s+/g, ' ').slice(0, 70);
      }),
    });
  } catch (e) {
    tabResults.push({ tab: label, error: String(e.message || e).slice(0, 200) });
  }
}

// Search interaction on the last tab, then confirm the main thread still answers.
const searchMs = await page.evaluate(async () => {
  const inp = document.querySelector('input[placeholder^="Search"]');
  if (!inp) return { error: 'no search input' };
  const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
  const start = performance.now();
  setter.call(inp, 'zzz-no-match');
  inp.dispatchEvent(new Event('input', { bubbles: true }));
  await new Promise((r) => setTimeout(r, 500));
  return { busyMs: Math.round(performance.now() - start), value: inp.value };
});

const finalRootLen = await page.evaluate(() => document.getElementById('root')?.innerHTML.length ?? -1);

console.log(JSON.stringify({
  target,
  domReadyMs,
  mainThread: mainThreadMs,
  tabResults,
  search: searchMs,
  finalRootLen,
  pageErrors,
  consoleErrors,
}, null, 2));

await browser.close();