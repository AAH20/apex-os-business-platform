import { chromium } from 'playwright'

const BASE = 'http://localhost:3000'
const log = (...a) => { console.log(...a) }
const seenRequests = []

/** Click a button by exact trimmed label inside the open modal (DOM-level, resilient to whitespace). */
const clickByText = (page, texts) => page.evaluate((texts) => {
  const fixed = [...document.querySelectorAll('div.fixed')].pop()
  if (!fixed) return 'NO_MODAL'
  const btn = [...fixed.querySelectorAll('button')].find(b => texts.includes(b.innerText.trim()))
  if (!btn) return 'NO_BUTTON:' + [...fixed.querySelectorAll('button')].map(b => b.innerText.trim()).join('|')
  btn.click()
  return 'OK:' + btn.innerText.trim()
}, texts)

const openAction = async (page, label) => {
  const clicked = await page.evaluate((label) => {
    const b = [...document.querySelectorAll('button')].find(x => x.innerText.trim().startsWith(label))
    if (!b) return 'NOT_FOUND'
    b.click(); return 'OK'
  }, label)
  await page.waitForTimeout(900)
  const info = await page.evaluate(() => {
    const fixed = [...document.querySelectorAll('div.fixed')].pop()
    if (!fixed) return { open: false }
    return {
      open: true,
      heading: fixed.querySelector('h3')?.innerText ?? 'NONE',
      stub: fixed.innerText.includes('not yet implemented'),
      body: fixed.innerText.replace(/\n{2,}/g, '\n').slice(0, 800),
      buttons: [...fixed.querySelectorAll('button')].map(b => b.innerText.trim() || '[icon]'),
    }
  })
  log(`\n=== ${label} (click=${clicked}) === modal="${info.heading}" STUB=${info.stub}`)
  log('buttons: ' + (info.buttons || []).join(' | '))
  if (info.body) log(info.body)
  return info
}

const closeModal = async (page) => {
  const r = await clickByText(page, ['Close', 'Cancel', 'Done'])
  await page.waitForTimeout(600)
  let stillOpen = await page.evaluate(() => document.querySelectorAll('div.fixed').length > 0)
  if (stillOpen) {
    await page.evaluate(() => { const f = [...document.querySelectorAll('div.fixed')].pop(); [...f.querySelectorAll('button')].pop()?.click() })
    await page.waitForTimeout(500)
    stillOpen = await page.evaluate(() => document.querySelectorAll('div.fixed').length > 0)
  }
  return r + ' stillOpen=' + stillOpen
}

const setVal = (el, v) => { const s = Object.getOwnPropertyDescriptor(el.constructor.prototype, 'value').set; s.call(el, v); el.dispatchEvent(new Event('input', { bubbles: true })) }

const run = async () => {
  const browser = await chromium.launch()
  const ctx = await browser.newContext({ acceptDownloads: true })
  const page = await ctx.newPage()
  page.on('console', m => { if (m.type() === 'error') log('CONSOLE ERROR: ' + m.text()) })
  page.on('pageerror', e => log('PAGE ERROR: ' + e.message))
  page.on('request', r => { if (r.method() !== 'GET') seenRequests.push(r.method() + ' ' + r.url().replace(BASE, '') + ' :: ' + (r.postData() || '').slice(0, 240)) })
  page.on('download', async d => {
    const fs = await import('node:fs')
    log('DOWNLOAD EVENT: ' + d.suggestedFilename())
    log('CSV CONTENT:\n' + fs.readFileSync(await d.path(), 'utf8'))
  })

  await page.goto(BASE + '/dashboard', { waitUntil: 'networkidle' })
  await page.waitForSelector('text=Quick Actions', { timeout: 20000 })
  await page.waitForTimeout(1500)

  let i = await openAction(page, 'Generate Report')
  if (!i.stub) {
    log('download click -> ' + await clickByText(page, ['Download CSV']))
    await page.waitForTimeout(2500)
    log('post-download: ' + JSON.stringify(await page.evaluate(() => {
      const f = [...document.querySelectorAll('div.fixed')].pop()
      return { open: !!f, text: f?.innerText.replace(/\n{2,}/g, '\n').slice(0, 300) }
    })))
    log('close -> ' + await closeModal(page))
  }

  i = await openAction(page, 'Add User')
  if (!i.stub) {
    await page.evaluate(() => {
      const f = [...document.querySelectorAll('div.fixed')].pop()
      const set = (el, v) => { const s = Object.getOwnPropertyDescriptor(el.constructor.prototype, 'value').set; s.call(el, v); el.dispatchEvent(new Event('input', { bubbles: true })) }
      const inputs = [...f.querySelectorAll('input')]
      set(inputs[0], 'QA Bot'); set(inputs[1], 'qa.bot@apex.test')
      const sels = [...f.querySelectorAll('select')]
      set(sels[0], 'admin'); set(sels[1], 'active')
      f.querySelector('button[type=submit]').click()
    })
    await page.waitForTimeout(2500)
    log('AddUser result: ' + JSON.stringify(await page.evaluate(() => {
      const f = [...document.querySelectorAll('div.fixed')].pop()
      return f ? { open: true, err: f.querySelector('.text-red-400')?.innerText || 'none' } : { open: false }
    })))
    log('close -> ' + await closeModal(page))
  }

  i = await openAction(page, 'New Product')
  if (!i.stub) {
    await page.evaluate(() => {
      const f = [...document.querySelectorAll('div.fixed')].pop()
      const set = (el, v) => { const s = Object.getOwnPropertyDescriptor(el.constructor.prototype, 'value').set; s.call(el, v); el.dispatchEvent(new Event('input', { bubbles: true })) }
      const t = [...f.querySelectorAll('input[type=text]')]
      set(t[0], 'QA Widget'); set(t[1], 'QA-001')
      const n = [...f.querySelectorAll('input[type=number]')]
      set(n[0], '19.99'); set(n[1], '7.50'); set(n[2], '120'); set(n[3], '10')
      f.querySelector('button[type=submit]').click()
    })
    await page.waitForTimeout(2500)
    log('NewProduct result: ' + JSON.stringify(await page.evaluate(() => {
      const f = [...document.querySelectorAll('div.fixed')].pop()
      return f ? { open: true, err: f.querySelector('.text-red-400')?.innerText || 'none' } : { open: false }
    })))
    log('close -> ' + await closeModal(page))
  }

  i = await openAction(page, 'View Analytics')
  if (!i.stub) { await page.waitForTimeout(2500); log('ANALYTICS FINAL: ' + await page.evaluate(() => [...document.querySelectorAll('div.fixed')].pop()?.innerText.replace(/\n{2,}/g, '\n').slice(0, 900))); log('close -> ' + await closeModal(page)) }

  i = await openAction(page, 'Settings')
  if (!i.stub) {
    await page.evaluate(() => {
      const f = [...document.querySelectorAll('div.fixed')].pop()
      const set = (el, v) => { const s = Object.getOwnPropertyDescriptor(el.constructor.prototype, 'value').set; s.call(el, v); el.dispatchEvent(new Event('input', { bubbles: true })) }
      set(f.querySelector('input[type=text]'), 'APEX QA Corp')
      const sels = [...f.querySelectorAll('select')]
      set(sels[1], 'EUR'); set(sels[2], 'DD/MM/YYYY')
      const cbs = [...f.querySelectorAll('input[type=checkbox]')]
      cbs[1].click(); cbs[2].click()
      f.querySelector('button[type=submit]').click()
    })
    await page.waitForTimeout(2000)
    log('PERSISTED: ' + await page.evaluate(() => localStorage.getItem('apex-dashboard-settings')))
    log('auto-closed: ' + await page.evaluate(() => document.querySelectorAll('div.fixed').length === 0))
  }

  i = await openAction(page, 'Notifications')
  if (!i.stub) { await page.waitForTimeout(2500); log('NOTIFICATIONS FINAL: ' + await page.evaluate(() => [...document.querySelectorAll('div.fixed')].pop()?.innerText.replace(/\n{2,}/g, '\n').slice(0, 900))); log('close -> ' + await closeModal(page)) }

  i = await openAction(page, 'View all')
  if (!i.stub) log('close -> ' + await closeModal(page))

  i = await openAction(page, 'Goals'); if (!i.stub) log('close -> ' + await closeModal(page))
  i = await openAction(page, 'New Lead'); if (!i.stub) log('close -> ' + await closeModal(page))

  log('\n=== NON-GET REQUESTS ===')
  log(seenRequests.length ? seenRequests.join('\n') : '(none)')
  await browser.close()
}
run().catch(e => { console.error('FATAL', e.message); process.exit(1) })
