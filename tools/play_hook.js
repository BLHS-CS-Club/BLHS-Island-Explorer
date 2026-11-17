// play.py adds this file to the game's page, and it does four things:
//   1. starts every run as a new player, so flags and tasks from last time are gone
//   2. reloads the game when you save a file
//   3. sends what the game prints back to play.py, so errors show up in the terminal
//   4. shows the error on top of the game, like a dev server does
(function () {
  if (window.__blhsPlay) return
  window.__blhsPlay = true

  // 1. the game only keeps flags, tasks and scores when a saved game exists, so write a
  // blank one every time (marked graduated, which keeps the game's own "do this next" line
  // from showing over the island's)
  try {
    for (const key of Object.keys(localStorage)) if (key.startsWith('blhs_')) localStorage.removeItem(key)
    localStorage.setItem('blhs_save_v2', JSON.stringify({
      v: 2, id: 'practice', handle: 'Thor', pronouns: '', boatName: '', year: 1, season: 'Fall',
      beat: 'practice', introDone: true, graduated: true, plans: {}, flags: [],
      tokens: ['Fall', 'Winter', 'Spring'], ledger: [], ranks: {}, islands: {}, exposure: [],
      completions: [], stickers: [], facts: [], badges: [], savedAt: Date.now(),
    }))
  } catch (e) { /* storage is blocked, and the game still runs without it */ }

  // 4. the box that shows errors over the game
  let box = null
  function show(errors) {
    if (!errors || !errors.length) { if (box) box.remove(); box = null; return }
    if (!box) {
      box = document.createElement('div')
      box.style.cssText = 'position:fixed;left:12px;right:12px;top:12px;z-index:99999;max-height:60vh;overflow:auto;' +
        'background:rgba(20,20,24,.94);color:#eee;border:1px solid #c0392b;border-left:6px solid #c0392b;border-radius:6px;' +
        'padding:12px 16px;font:14px/1.5 Consolas,Menlo,monospace;white-space:pre-wrap;box-shadow:0 8px 30px rgba(0,0,0,.5)'
      const attach = () => document.body ? document.body.append(box) : setTimeout(attach, 50)
      attach()
    }
    box.textContent = ''
    for (const e of errors) {
      const where = document.createElement('div')
      where.style.cssText = 'color:#ff8a80;font-weight:bold'
      where.textContent = e.where ? `${e.where}  ${e.title}` : e.title
      const detail = document.createElement('div')
      detail.textContent = e.detail || ''
      const hint = document.createElement('div')
      hint.style.cssText = 'color:#9ecbff;margin-bottom:10px'
      hint.textContent = e.hint || ''
      box.append(where, detail, hint)
    }
  }

  // 3. send what the game prints to play.py, which answers with every error so far
  function tell(level, parts) {
    const text = parts.map((v) => (typeof v === 'string' ? v : v instanceof Error ? v.message : safe(v))).join(' ')
    if (!/^\[(pmap|island|print)\]|Traceback \(most recent call last\)/.test(text) && level !== 'error') return
    fetch('/_play/log', { method: 'POST', body: JSON.stringify({ level, text }) })
      .then((r) => r.json())
      .then((got) => show(got.errors))
      .catch(() => {})
  }
  function safe(v) { try { return JSON.stringify(v) } catch (e) { return String(v) } }
  for (const level of ['log', 'info', 'warn', 'error']) {
    const real = console[level]
    console[level] = function () { tell(level, Array.prototype.slice.call(arguments)); return real.apply(console, arguments) }
  }

  // 2. ask play.py a few times a second whether a file was saved, and reload if one was
  let stamp = null
  async function check() {
    try {
      const first = stamp === null
      const state = await (await fetch(first ? '/_play/state?fresh=1' : '/_play/state', { cache: 'no-store' })).json()
      if (first) {
        stamp = state.stamp
        show(state.errors)
      } else if (state.stamp !== stamp) {
        window.location.replace('/')
        return
      }
    } catch (e) { /* play.py isn't running, so there's nothing to do until it's back */ }
    setTimeout(check, 700)
  }
  check()
})()
