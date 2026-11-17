// The game in a frame, plus the list of what went wrong.
// The Play page and the Try page both use this.

// Where maps are read from when the game doesn't have one built in.
const MAPVIS = 'https://mapvis-atc.vercel.app'

// The room every practice island runs in.
export const PRACTICE_MAP = 'atc-1'

// A short plain hint for the mistakes that come up most.
const HINTS = [
  [/no anchor named|not an anchor|is not a spot/i,
    "That spot isn't on this map. Use a name from the Spots list."],
  [/IndentationError|unexpected indent|unindent/i,
    "The spaces at the start of that line don't match the lines around it."],
  [/SyntaxError|invalid syntax/i,
    'Python could not read that line. Look for a missing quote, bracket or colon, on that line or the one above.'],
  [/NameError|isn't defined|is not defined/i,
    "Python doesn't know that name. Check the spelling, and check it's in the import line at the top."],
  [/ImportError|no module named|cannot import/i,
    "The import line names something that doesn't exist. Check the spelling against the list of words."],
  [/no yield|forgot.*yield|not a generator/i,
    'A game word only happens with yield in front of it.'],
  [/answered 404|not in your island|could not reach/i,
    'The game could not find one of the island files.'],
  [/TypeError/i,
    'A word got the wrong kind of value, like a number where it wanted text.'],
]

function hintFor(text) {
  for (const [pattern, hint] of HINTS) if (pattern.test(text)) return hint
  return ''
}

// Pulls "island.py, line 12" out of a Python traceback, skipping the game's own files.
function whereIn(text) {
  const found = [...text.matchAll(/File "([^"]+)", line (\d+)/g)]
    .filter((m) => !/(^|\/)(vine|grape|driver)\.py$/.test(m[1]))
  const last = found[found.length - 1]
  if (last) return `${last[1].split('/').pop()}, line ${last[2]}`
  const plain = /([a-z_]+\.py), line (\d+)/.exec(text)
  return plain ? `${plain[1]}, line ${plain[2]}` : ''
}

// Some errors name the thing that is wrong but not the line it is on.
// This looks the name up in the island's own files.
export function findLine(text, files) {
  const names = []
  let m
  if ((m = /(\w+)\(\) has no yield/.exec(text))) names.push(['def ' + m[1], true])
  for (const hit of text.matchAll(/'([A-Za-z_]\w*)'/g)) names.push([hit[1], false])
  if ((m = /import name (\w+)/.exec(text))) names.push([m[1], false])
  for (const [name, exact] of names) {
    for (const [file, source] of Object.entries(files || {})) {
      if (!file.endsWith('.py')) continue
      const lines = String(source).split('\n')
      const word = new RegExp('\\b' + name + '\\b')
      const test = exact ? (l) => l.includes(name) : (l) => word.test(l)
      const at = lines.findIndex((l) => test(l) && !l.trim().startsWith('#'))
      if (at >= 0) return `${file}, line ${at + 1}`
    }
  }
  return ''
}

// Turns one thing the game printed into something a new member can act on.
// Returns null for the chatter nobody needs to see.
export function explain(level, raw) {
  const text = String(raw || '')
  let m

  if ((m = /^\[pmap\] [\w-]+: island did not load: ([\s\S]*)/.exec(text))) {
    return { kind: 'error', title: "Your island didn't load", detail: m[1], where: whereIn(m[1]), hint: hintFor(m[1]) }
  }
  if ((m = /^\[pmap\] [\w-]+: this island claims (.+?), which (?:is|are) not (?:an anchor|anchors) on this map\. It has: (.*)/.exec(text))) {
    return {
      kind: 'error',
      title: `There is no spot called ${m[1]} on this map`,
      detail: `The spots on this map are: ${m[2]}.`,
      hint: 'Fix the name in @on_talk("...") so it matches one of them.',
    }
  }
  if ((m = /^\[pmap\] [\w-]+: the island's opening stopped: ([\s\S]*)/.exec(text))) {
    return { kind: 'error', title: 'Your @on_start stopped', detail: m[1], where: whereIn(m[1]), hint: hintFor(m[1]) }
  }
  if ((m = /^\[pmap\] [\w-]+: the island's opening was refused: ([\s\S]*)/.exec(text))) {
    return { kind: 'warn', title: 'The game said no to something in @on_start', detail: m[1].split(' · ').join('\n'), hint: hintFor(m[1]) }
  }
  if ((m = /^\[pmap\] station ([\w-]+): ([\s\S]*)/.exec(text))) {
    return { kind: 'error', title: `Talking to "${m[1]}" stopped`, detail: m[2], where: whereIn(m[2]), hint: hintFor(m[2]) }
  }
  if (/^Traceback \(most recent call last\)/.test(text)) {
    return { kind: 'trace', detail: text, where: whereIn(text), hint: hintFor(text) }
  }
  if ((m = /^\[island\] (.*)/.exec(text))) {
    return { kind: 'warn', title: 'Fetching your island', detail: m[1], hint: hintFor(m[1]) }
  }
  if ((m = /^\[print\] ([\s\S]*)/.exec(text))) {
    return { kind: 'print', title: 'print', detail: m[1] }
  }
  if (/could not load .*map\.json|This place did not load/.test(text)) {
    return { kind: 'error', title: "The map didn't load", detail: text }
  }
  if (level === 'error') return { kind: 'quiet', detail: text }
  return null
}

function el(tag, cls, text) {
  const node = document.createElement(tag)
  if (cls) node.className = cls
  if (text !== undefined) node.textContent = text
  return node
}

// box:     where the game frame goes
// list:    where the messages go
// path:    the address the game is loaded from. The Try page uses its own, so
//          its service worker can swap the island in.
export function createStage({ box, list, path = '/', files = null }) {
  let frame = null
  let lastError = null
  let count = 0
  let quiet = null
  const listeners = []

  function empty() {
    list.replaceChildren()
    const none = el('p', 'msg-none', 'No problems so far. Walk up to someone and press E.')
    list.append(none)
    lastError = null
    count = 0
    quiet = null
    listeners.forEach((fn) => fn(null))
  }

  function card(info) {
    if (!count) list.replaceChildren()
    count++
    const item = el('div', `msg msg-${info.kind}`)
    if (info.title) item.append(el('div', 'msg-title', info.title))
    if (info.where) item.append(el('div', 'msg-where', info.where))
    if (info.detail) item.append(el('pre', 'msg-detail', info.detail))
    if (info.hint) item.append(el('div', 'msg-hint', info.hint))
    list.append(item)
    item.scrollIntoView({ block: 'nearest' })
    if (info.kind === 'error') listeners.forEach((fn) => fn(info))
    return item
  }

  function say(info) {
    // A traceback belongs to the error just before it, so it adds its line number there.
    if (info.kind === 'trace') {
      if (lastError && !lastError.querySelector('.msg-where') && info.where) {
        lastError.querySelector('.msg-title').after(el('div', 'msg-where', info.where))
      }
      if (lastError) {
        const more = el('details', 'msg-more')
        more.append(el('summary', '', 'the full Python error'), el('pre', 'msg-detail', info.detail))
        lastError.append(more)
        return
      }
      info = { kind: 'error', title: 'Python error', detail: info.detail, where: info.where, hint: info.hint }
    }
    // Errors that are the game's own business go in one folded box at the bottom.
    if (info.kind === 'quiet') {
      if (!quiet) {
        quiet = el('details', 'msg msg-quiet')
        quiet.append(el('summary', '', 'other things the game printed'))
      }
      quiet.append(el('pre', 'msg-detail', info.detail))
      if (count) list.append(quiet)
      return
    }
    const item = card(info)
    if (info.kind === 'error') lastError = item
    if (quiet) list.append(quiet)
  }

  window.addEventListener('message', (event) => {
    if (event.origin !== window.location.origin) return
    const data = event.data
    if (!data || data.from !== 'blhs-game') return
    if (frame && event.source !== frame.contentWindow) return
    const info = explain(data.level, data.text)
    if (!info) return
    if (info.kind === 'error' && !info.where && files) {
      // Look the line up before showing it, so the card arrives whole.
      Promise.resolve(files()).then((found) => {
        info.where = findLine(info.detail || '', found)
        say(info)
      }).catch(() => say(info))
      return
    }
    say(info)
  })

  // Starts the game over. `grape` is the address of the island's folder.
  function run({ grape, map, at, fresh = true, platform = false }) {
    empty()
    if (fresh) {
      // A new player every time, so @on_start runs again and old flags are gone.
      // The game only remembers flags and scores when a saved game exists, so
      // this writes a blank one: year 1, past the intro, nothing done yet.
      // It is marked graduated so the game's own "go do this next" line stays
      // quiet and the only objective on screen is the one your island sets.
      try {
        for (const key of Object.keys(localStorage)) if (key.startsWith('blhs_')) localStorage.removeItem(key)
        localStorage.setItem('blhs_save_v2', JSON.stringify({
          v: 2, id: 'practice', handle: 'Thor', pronouns: '', boatName: '', year: 1, season: 'Fall',
          beat: 'practice', introDone: true, graduated: true, plans: {}, flags: [],
          tokens: ['Fall', 'Winter', 'Spring'],
          ledger: [], ranks: {}, islands: {}, exposure: [], completions: [],
          stickers: [], facts: [], badges: [], savedAt: Date.now(),
        }))
      } catch (e) { /* storage is blocked, the game still runs */ }
    }
    const q = new URLSearchParams({ scene: 'pmap', map: map || PRACTICE_MAP, deep: '1' })
    if (at) q.set('at', at)
    if (grape) q.set('grape', grape)
    if (platform) q.set('src', 'platform')

    // A new frame each time. Setting the same address on the old one does not always reload it.
    const next = el('iframe', 'game')
    next.title = 'the game'
    next.allow = 'autoplay; fullscreen; gamepad'
    next.src = `${path}?${q}`
    box.replaceChildren(next)
    frame = next
    return next
  }

  function focus() {
    if (frame) frame.focus()
  }

  empty()
  // onError(fn): fn gets each error as it shows up, and null when the list is cleared.
  return { run, say, empty, focus, onError: (fn) => listeners.push(fn) }
}

// The spots on a map, as [{name, label, kind}]. Empty if the map can't be read.
export async function spotsOf(map) {
  for (const base of ['/maps-vendored', '/maps-painted']) {
    try {
      const res = await fetch(`${base}/${map}/map.json`, { cache: 'no-store' })
      if (!res.ok) continue
      const data = await res.json()
      if (Array.isArray(data.anchors)) {
        return data.anchors.map((a) => ({ name: a.name, label: a.label || a.name, kind: a.kind }))
      }
    } catch (e) { /* not there, or not JSON. Try the next place. */ }
  }
  return []
}

// Where to find a map: 'built-in', 'mapvis' (published but not in the game yet) or 'missing'.
export async function whereIsMap(map) {
  for (const base of ['/maps-vendored', '/maps-painted']) {
    try {
      const res = await fetch(`${base}/${map}/map.json`, { cache: 'no-store' })
      if (res.ok && /json/.test(res.headers.get('content-type') || '')) return 'built-in'
    } catch (e) { /* keep looking */ }
  }
  try {
    const res = await fetch(`${MAPVIS}/api/v1/maps/${encodeURIComponent(map)}`, { cache: 'no-store' })
    if (res.ok) return 'mapvis'
  } catch (e) { /* offline, or MAPVIS is down */ }
  return 'missing'
}

// Fills a <select> with the spots on a map and remembers the last pick.
export async function fillSpots(select, map, key) {
  const spots = await spotsOf(map)
  select.replaceChildren()
  const door = el('option', '', 'where the map starts')
  door.value = ''
  select.append(door)
  for (const s of spots) {
    const opt = el('option', '', s.label === s.name ? s.name : `${s.name}  (${s.label})`)
    opt.value = s.name
    select.append(opt)
  }
  let saved = ''
  try { saved = localStorage.getItem(key) || '' } catch (e) { /* fine */ }
  if (spots.some((s) => s.name === saved)) select.value = saved
  select.onchange = () => {
    try { localStorage.setItem(key, select.value) } catch (e) { /* fine */ }
    select.dispatchEvent(new CustomEvent('picked'))
  }
  return spots
}
