import { chromium } from 'playwright';

const PAGES = [
  { name: 'iot',               url: 'http://localhost:3000/iot',            expect: ['Temp Sensor', 'Warehouse'] },
  { name: 'compliance',        url: 'http://localhost:3000/compliance',     expect: ['GDPR', 'SOC', 'ISO'] },
  { name: 'budgeting',         url: 'http://localhost:3000/budgeting',      expect: ['FY2026', 'Budget'] },
  { name: 'capacity-planning', url: 'http://localhost:3000/capacity-planning', expect: ['Q4 2026', 'Capacity'] },
];

const browser = await chromium.launch();
const out = [];
for (const p of PAGES) {
  const ctx = await browser.newContext();
  const page = await ctx.newPage();
  const bad = [];
  page.on('response', r => { if (r.url().includes('/api/') && r.status() >= 400) bad.push(`${r.status()} ${r.url()}`); });
  await page.goto(p.url, { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForTimeout(2000);
  const main = await page.evaluate(() => {
    const m = document.querySelector('main') || document.body;
    return m.innerText;
  });
  out.push({
    page: p.name,
    mainLen: main.length,
    foundExpected: p.expect.filter(e => main.toLowerCase().includes(e.toLowerCase())),
    hasFailed: /Failed to fetch|API error/i.test(main),
    badApi: bad,
    main: main.replace(/\s+/g, ' ').slice(0, 400),
  });
  await ctx.close();
}
await browser.close();
console.log(JSON.stringify(out, null, 2));
