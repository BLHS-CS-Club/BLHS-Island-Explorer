// Records the short video for each guide, from the real game.
//
//   python play.py --no-open           (leave it running in another window)
//   node tools/clips.mjs               records every guide
//   node tools/clips.mjs 02-choice     records one
//
// Each guide's guide.json has a "clip" list that says what happens in its video:
//   "say:words"          the caption along the bottom
//   "hl:6-9"             light up lines 6 to 9 of the code (0-0 turns it off)
//   a number             wait that many milliseconds
//   "e", "space"         keys pressed in the game
//   "pick:1"             click the second choice button
//   "button:Keep going"  click a button in the game by its words
//   "list"               click the line at the top of the screen
//   "edit:old=>new"      type a change into the code
//   "run"                press Run and wait for the game to start over
//
// The videos land in out/videos as mp4. This needs Node, Playwright and ffmpeg.
// Playwright is borrowed from the engine checkout next door. Set FFMPEG to the
// ffmpeg program if it isn't on your PATH.
import { createRequire } from 'node:module'
import { execFileSync } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const engine = process.env.BLHS_ENGINE || path.resolve(repo, '..', 'AdventureGame')
const { chromium } = createRequire(path.join(engine, 'package.json'))('playwright')
const ffmpeg = process.env.FFMPEG || 'ffmpeg'
const base = process.env.BLHS_PLAY || 'http://localhost:5290'
const out = path.join(repo, 'out', 'videos')
const raw = path.join(repo, 'out', 'raw')
const only = process.argv[2]
const W = 1280
const H = 720

fs.mkdirSync(out, { recursive: true })
fs.mkdirSync(raw, { recursive: true })

const guides = fs.readdirSync(path.join(repo, 'learn'))
  .filter((name) => fs.existsSync(path.join(repo, 'learn', name, 'guide.json')))
  .filter((name) => !only || name === only)
  .sort()

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

async function record(id, n) {
  const guide = JSON.parse(fs.readFileSync(path.join(repo, 'learn', id, 'guide.json'), 'utf8'))
  if (!Array.isArray(guide.clip)) return console.log(`${id}: no clip list, skipped`)

  const browser = await chromium.launch()
  const context = await browser.newContext({
    viewport: { width: W, height: H },
    recordVideo: { dir: raw, size: { width: W, height: H } },
  })
  const page = await context.newPage()
  const began = Date.now()

  // The game says this line once the map is up and the player can move.
  let loaded = 0
  page.on('console', (m) => { if (/\[pmap\] loaded "/.test(m.text())) loaded++ })
  const gameReady = async (count) => {
    const stop = Date.now() + 40000
    while (loaded < count && Date.now() < stop) await sleep(150)
    await sleep(1600)
  }

  await page.goto(`${base}/club/try/?g=${id}&clip=1`, { waitUntil: 'load' })
  await gameReady(1)
  const frame = () => page.frames().find((f) => /scene=pmap/.test(f.url()))
  const focusGame = () => frame().locator('canvas').first().click({ position: { x: 4, y: 4 } }).catch(() => {})
  await focusGame()

  let runs = 1
  const started = Date.now()
  for (const step of guide.clip) {
    if (typeof step === 'number') { await sleep(step); continue }
    const [what, ...rest] = step.split(':')
    const value = rest.join(':')
    if (what === 'say') {
      await page.evaluate((t) => { document.getElementById('caption').textContent = t }, value)
    } else if (what === 'hl') {
      const [from, to] = value.split('-').map(Number)
      await page.evaluate(([a, b]) => {
        const cm = document.querySelector('.CodeMirror').CodeMirror
        for (let i = 0; i < cm.lineCount(); i++) cm.removeLineClass(i, 'background', 'hl-line')
        for (let i = a; i <= b && a > 0; i++) cm.addLineClass(i - 1, 'background', 'hl-line')
        if (a > 0) cm.scrollIntoView({ line: Math.max(0, a - 3), ch: 0 }, 40)
      }, [from, to])
    } else if (what === 'e') {
      await focusGame(); await page.keyboard.press('e')
    } else if (what === 'space') {
      await page.keyboard.press('Space')
    } else if (what === 'pick') {
      const buttons = frame().locator('button:visible')
      const texts = await buttons.allInnerTexts()
      const real = texts.map((t, i) => [t, i]).filter(([t]) => !/^(Wide|Chart|\?|Leave this for now)$/.test(t.trim()))
      const hit = real[Number(value)]
      if (hit) await buttons.nth(hit[1]).click().catch(() => {})
    } else if (what === 'button') {
      await frame().locator('button:visible', { hasText: value }).first().click().catch(() => {})
    } else if (what === 'list') {
      await frame().locator('.ob-panel').first().click().catch(() => {})
    } else if (what === 'edit') {
      const [find, to] = value.split('=>')
      await page.evaluate(async ([a, b]) => {
        const cm = document.querySelector('.CodeMirror').CodeMirror
        const wait = (ms) => new Promise((r) => setTimeout(r, ms))
        const at = cm.getValue().indexOf(a)
        if (at < 0) return
        cm.focus()
        cm.setSelection(cm.posFromIndex(at), cm.posFromIndex(at + a.length))
        await wait(900)
        cm.replaceSelection('')
        await wait(350)
        for (const ch of b) { cm.replaceSelection(ch); await wait(45) }
      }, [find, to])
    } else if (what === 'run') {
      runs++
      await page.click('#run')
      await gameReady(runs)
      await focusGame()
    } else {
      console.log(`${id}: don't know the step "${step}"`)
    }
  }
  await sleep(1200)
  const skip = (started - began) / 1000
  const video = page.video()
  await context.close()
  const webm = await video.path()
  await browser.close()

  const title = `Guide ${String(n).padStart(2, '0')} - ${guide.title}`
  const mp4 = path.join(out, `${title}.mp4`)
  // Cut off the part before the game was ready, and save as an mp4 that plays everywhere.
  execFileSync(ffmpeg, ['-y', '-loglevel', 'error', '-ss', skip.toFixed(2), '-i', webm,
    '-c:v', 'libx264', '-preset', 'slow', '-crf', '21', '-pix_fmt', 'yuv420p', '-r', '30',
    '-movflags', '+faststart', '-an', mp4])
  fs.rmSync(webm, { force: true })
  const size = (fs.statSync(mp4).size / 1e6).toFixed(1)
  console.log(`${title}.mp4  ${size} MB  ${((Date.now() - started) / 1000).toFixed(0)} s`)
}

const all = fs.readdirSync(path.join(repo, 'learn'))
  .filter((name) => fs.existsSync(path.join(repo, 'learn', name, 'guide.json'))).sort()
for (const id of guides) await record(id, all.indexOf(id) + 1)
