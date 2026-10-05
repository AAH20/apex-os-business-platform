import { chromium } from 'playwright'

const BASE = 'http://localhost:3000'
const UNIQ = Date.now()
const log = (...a) => console.log(...a)

const openModal = async (page, label) => {
  await page.evaluate((label) => {
    const b = [...document.querySelectorAll('button')].find(x => x.innerText.trim().startsWith(label))
    b?.click()
  }, label)
  await page.waitForTimeout(800)
}
// Scope to the DASHBOARD modal only (has an h3 heading), not Layout's sidebar overlays.
const modal = page => page.locator('div.fixed:has(h3)').last()

const fill = (page, fn, arg) => page.evaluate(fn, arg)

const run = async () => {
  const browser = await chromium.launch()
  const page = await browser.newPage()
  page.on('console', m => { if (m.type() === 'error') log('CONSOLE ERR: ' + m.text()) })
  page.on('response', async r => {
    if (r.request().method() !== 'GET') log('RESP ' + r.status() + ' ' + r.request().method() + ' ' + r.url().replace(BASE, ''))
  })

  await page.goto(BASE + '/dashboard', { waitUntil: 'networkidle' })
  await page.waitForSelector('text=Quick Actions')
  await page.waitForTimeout(1200)

  // ── Add User: VALID email → expect modal to close (success) ──
  const uniq = Date.now()
  await openModal(page, 'Add User')
  await fill(page, (uniq) => {
    const f = [...document.querySelectorAll('div.fixed')].pop()
    const set = (el, v) => { Object.getOwnPropertyDescriptor(el.constructor.prototype, 'value').set.call(el, v); el.dispatchEvent(new Event('input', { bubbles: true })) }
    const inp = [...f.querySelectorAll('input')]
    set(inp[0], 'QA Bot'); set(inp[1], 'qa.bot+' + uniq + '@apexos.io')
    const sels = [...f.querySelectorAll('select')]; set(sels[0], 'admin'); set(sels[1], 'active')
    f.querySelector('button[type=submit]').click()
  }, uniq)
  await page.waitForTimeout(2500)
  log('AddUser VALID -> modal closed: ' + (await modal(page).count() === 0))

  // ── Add User: INVALID email → expect visible error text inside modal ──
  await openModal(page, 'Add User')
  await fill(page, () => {
    const f = [...document.querySelectorAll('div.fixed')].pop()
    const set = (el, v) => { Object.getOwnPropertyDescriptor(el.constructor.prototype, 'value').set.call(el, v); el.dispatchEvent(new Event('input', { bubbles: true })) }
    const inp = [...f.querySelectorAll('input')]
    set(inp[0], 'QA Bad'); set(inp[1], 'bad@apex.test')
    f.querySelector('button[type=submit]').click()
  })
  await page.waitForTimeout(2500)
  log('AddUser INVALID -> still open: ' + (await modal(page).count() > 0))
  log('AddUser INVALID -> error text: ' + JSON.stringify(await modal(page).locator('p.text-red-400').innerText().catch(() => 'NONE SHOWN')))
  log('AddUser INVALID -> button re-enabled: ' + await modal(page).locator('button[type=submit]').isEnabled())
  await modal(page).locator('button', { hasText: 'Cancel' }).click()
  await page.waitForTimeout(500)

  // ── New Product: valid → close; invalid → error ──
  await openModal(page, 'New Product')
  await fill(page, (uniq) => {
    const f = [...document.querySelectorAll('div.fixed')].pop()
    const set = (el, v) => { Object.getOwnPropertyDescriptor(el.constructor.prototype, 'value').set.call(el, v); el.dispatchEvent(new Event('input', { bubbles: true })) }
    const t = [...f.querySelectorAll('input[type=text]')]; set(t[0], 'QA Widget'); set(t[1], 'QA-' + uniq)
    const n = [...f.querySelectorAll('input[type=number]')]
    set(n[0], '19.99'); set(n[1], '7.5'); set(n[2], '120'); set(n[3], '10')
    f.querySelector('button[type=submit]').click()
  }, uniq)
  await page.waitForTimeout(2500)
  log('NewProduct -> modal closed: ' + (await modal(page).count() === 0) +
      ' | err=' + JSON.stringify(await modal(page).locator('p.text-red-400').innerText().catch(() => 'none/closed')))

  // ── Every quick action opens a REAL modal (no stub anywhere) ──
  const labels = ['Generate Report', 'Add User', 'New Product', 'View Analytics', 'Settings', 'Notifications', 'Goals', 'New Lead', 'View all']
  log('\n=== full sweep ===')
  for (const l of labels) {
    await openModal(page, l)
    const res = await modal(page).evaluate(m => ({
      h: m.querySelector('h3')?.innerText,
      stub: m.innerText.includes('not yet implemented'),
      inputs: m.querySelectorAll('input,select').length,
      chars: m.innerText.length,
    })).catch(e => ({ err: e.message }))
    log(`${l.padEnd(17)} -> ${JSON.stringify(res)}`)
    if (l === 'View Analytics' || l === 'Notifications') log(await modal(page).innerText())
    if (await modal(page).count()) { await modal(page).locator('button').last().click(); await page.waitForTimeout(600) }
    // Settings auto-closes; make sure it is gone
    if (await modal(page).count()) { await page.evaluate(() => { const f = [...document.querySelectorAll('div.fixed')].pop(); [...f.querySelectorAll('button')].pop()?.click() }); await page.waitForTimeout(400) }
  }
  log('leftover modals at end: ' + await modal(page).count())
  await browser.close()
}
run().catch(e => { console.error('FATAL', e.message); process.exit(1) })
