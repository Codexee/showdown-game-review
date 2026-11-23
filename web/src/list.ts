// Games page: trainer card (username, sync, ratings), adding games, and the game list.
import { api, type Game, type Profile, type Settings } from './api'
import { errText, fmtAgo, fmtDate, h, say, sprite } from './dom'
import { toggle } from './switch'

// 8×8 pixel icons ('#' = filled). Each has a title for its meaning.
const ICONS: Record<string, string[]> = {
  lock: ['..####..', '.#....#.', '.#....#.', '########', '###..###', '###..###', '########', '########'],
  disk: ['#######.', '#.###.##', '#.###..#', '#......#', '#.####.#', '#.#..#.#', '#.####.#', '########'],
  scroll: ['######..', '#....##.', '#.##..#.', '#.....#.', '#.###.#.', '#.....#.', '#.###.#.', '#######.'],
  // 14×14 so it draws 1:1 at 14 px (matches the text) and the five pips stay sharp.
  dice: ['##############', '#............#', '#.##......##.#', '#.##......##.#', '#............#', '#............#', '#.....##.....#', '#.....##.....#', '#............#', '#............#', '#.##......##.#', '#.##......##.#', '#............#', '##############'],
  pin: ['..####..', '..####..', '..####..', '.######.', '...##...', '...##...', '...#....', '...#....'],
  pinoff: ['..####..', '..#..#..', '..#..#..', '.######.', '...##...', '...##...', '...#....', '...#....'],
  sun: ['...##...', '.#....#.', '..####..', '#.####.#', '#.####.#', '..####..', '.#....#.', '...##...'],
  moon: ['..###...', '.###....', '###.....', '###.....', '####....', '#####..#', '.######.', '..####..'],
  motion: ['........', '.####...', '........', '..#####.', '........', '.####...', '........', '........'],
  drop: ['...##...', '...##...', '.######.', '..####..', '...##...', '#......#', '#......#', '########'],
  sync: ['..###.#.', '.#...##.', '#...###.', '#.......', '#......#', '.......#', '.#....#.', '..####..'],
  lens: ['.###....', '#...#...', '#...#...', '#...#...', '.####...', '....##..', '.....##.', '......##'],
}
let profileShown = false            // animate the ladder bars once per page load
const seenGames = new Set<string>()  // rows already shown: only new games animate in

const state = {
  settings: null as Settings | null,
  filters: { format: '', result: '', opponent: '' },
}

const userInput = h('input', { id: 'username', autocomplete: 'off', spellcheck: 'false', maxlength: '18' })
const syncInfo = h('p', { class: 'sync-info' })
const syncIcon = icon('sync', '')   // square pixel icon: centred, and spins about its middle
const syncLabel = h('span', {}, 'Sync')
const syncBtn = h('button', { type: 'button', class: 'sync-btn' }, syncIcon, syncLabel)
const profileBox = h('div', { class: 'ratings-box' })
const list = h('ol', { class: 'games', 'aria-label': 'Your games' })
const formatSel = h('select', { id: 'f-format' }, h('option', { value: '' }, 'All formats'))
const resultSel = h('select', { id: 'f-result' },
  h('option', { value: '' }, 'Any result'), h('option', { value: 'win' }, 'Wins'),
  h('option', { value: 'loss' }, 'Losses'), h('option', { value: 'tie' }, 'Ties'))
const oppInput = h('input', { id: 'f-opp', type: 'search', placeholder: 'Opponent' })
const urlInput = h('input', { id: 'replay-url', type: 'url', placeholder: 'https://replay.pokemonshowdown.com/…', required: '' })
const fileInput = h('input', { id: 'replay-file', type: 'file', class: 'sr-only', accept: '.log,.html,.htm,.json,.txt' })
const scriptStatus = h('p', { class: 'small muted' })
const scriptBox = h('details', { class: 'userscript' },
  h('summary', {}, 'Auto-save every battle'),
  h('ol', {},
    h('li', {}, 'Install ', h('a', { href: 'https://www.tampermonkey.net/', target: '_blank', rel: 'noopener' }, 'Tampermonkey'), '.'),
    h('li', {}, h('a', { href: '/userscript/showdown-review.user.js' }, 'Install the userscript'), '.'),
    h('li', {}, 'Play with this app running.')),
  h('p', { class: 'small muted' }, 'Sends only battle logs to this app. Your login stays in your browser.'),
  scriptStatus)

let wired = false
function wire() {
  if (wired) return
  wired = true
  userForm.addEventListener('submit', async e => {
    e.preventDefault()
    try {
      state.settings = await api.saveSettings({ username: userInput.value })
      say(`Saved: ${state.settings.username}`)
      await Promise.all([loadSettings(), loadProfile(true), loadGames()])
    } catch (err) { say(errText(err), 'error') }
  })
  syncBtn.addEventListener('click', async () => {
    syncBtn.disabled = true
    syncBtn.classList.add('busy')
    syncLabel.textContent = 'Syncing'
    try {
      const r = await api.sync()
      let msg = r.added.length ? `Saved ${r.added.length} new game${r.added.length === 1 ? '' : 's'}.` : 'No new games.'
      if (r.first_sync) msg += ' From now on, every game you upload is saved automatically.'
      if (r.errors.length) msg += ` ${r.errors.length} couldn't be saved: ${r.errors[0]}`
      say(msg, r.errors.length ? 'error' : 'ok')
      await Promise.all([loadSettings(), loadProfile(), loadGames()])
    } catch (err) { say(errText(err), 'error') }
    finally { syncBtn.disabled = false; syncBtn.classList.remove('busy'); syncLabel.textContent = 'Sync' }
  })
  urlForm.addEventListener('submit', async e => {
    e.preventDefault()
    try {
      const r = await api.importUrl(urlInput.value)
      say(r.added ? 'Game added.' : 'That game is already saved.')
      urlInput.value = ''
      await loadGames()
    } catch (err) { say(errText(err), 'error') }
  })
  const upload = async (f: File | undefined) => {
    if (!f) return
    try {
      const r = await api.importFile(f)
      say(r.added ? 'Game added.' : 'That game is already saved.')
      await loadGames()
    } catch (err) { say(errText(err), 'error') }
    finally { fileInput.value = '' }
  }
  fileInput.addEventListener('change', () => void upload(fileInput.files?.[0]))
  // The drop zone also takes a file dragged onto it.
  fileDrop.addEventListener('dragover', e => { e.preventDefault(); fileDrop.classList.add('over') })
  fileDrop.addEventListener('dragleave', () => fileDrop.classList.remove('over'))
  fileDrop.addEventListener('drop', e => {
    e.preventDefault()
    fileDrop.classList.remove('over')
    void upload(e.dataTransfer?.files?.[0])
  })
  formatSel.addEventListener('change', () => { state.filters.format = formatSel.value; loadGames() })
  resultSel.addEventListener('change', () => { state.filters.result = resultSel.value; loadGames() })
  let t = 0
  oppInput.addEventListener('input', () => {
    clearTimeout(t)
    t = window.setTimeout(() => { state.filters.opponent = oppInput.value; loadGames() }, 250)
  })
  // The server's poller adds games in the background.
  setInterval(() => {
    if (document.hidden || !list.isConnected) return
    void loadSettings().then(() => loadGames()).catch(() => {})
  }, 60_000)
}

// Auto-analysis: the server reviews each newly saved game (setting kept on the server, so it
// works while this page is closed). Optimistic: flips at once, reverts if the save fails.
const autoSwitch = toggle('Auto-analyze new games', () => state.settings?.auto_analyze ?? true, on => {
  if (state.settings) state.settings.auto_analyze = on
  api.saveSettings({ auto_analyze: on })
    .then(s => { state.settings = s; say(on ? 'New games will be analyzed.' : 'Auto-analysis off.') })
    .catch(err => { if (state.settings) state.settings.auto_analyze = !on; autoSwitch.sync(); say(errText(err), 'error') })
}, h('span', { class: 'switch-text' }, 'Auto-analyze'))
const autoRow = h('div', { class: 'auto-row', title: 'Review every new Random Battle game in the background (about a minute each)' }, autoSwitch.el)

const userForm = h('form', { class: 'user-form' },
  h('label', { for: 'username' }, 'Username'),
  h('div', { class: 'row' }, userInput, h('button', { type: 'submit', class: 'quiet' }, 'Save'), syncBtn))
const fileDrop = h('label', { for: 'replay-file', class: 'file-drop', title: 'A saved .log, .html or .json replay' },
  icon('drop', ''), h('span', {}, 'Drop or choose a file'))
const urlForm = h('form', { class: 'url-form' },
  h('label', { for: 'replay-url', class: 'sr-only' }, 'Replay URL'), urlInput, h('button', { type: 'submit' }, 'Add'))

export async function renderList(root: HTMLElement) {
  wire()
  // One block: profile, sync and adding games beside the games list. On a desktop it fits
  // the window and the list scrolls inside it (user request 2026-11-23); phones stack it.
  root.replaceChildren(
    h('header', { class: 'app-head' }, h('h1', {}, 'Showdown Review')),
    h('section', { class: 'home frame', 'aria-label': 'Your profile and games' },
      h('div', { class: 'home-side' },
        h('div', { class: 'home-profile', 'aria-label': 'Your profile' }, userForm, syncInfo, autoRow, profileBox),
        h('div', { class: 'add', 'aria-label': 'Add games' },
          h('h2', {}, 'Add a game'),
          // One grid, so the drop zone lines up with the link box (the Add button sits beside the link).
          h('div', { class: 'add-grid' }, urlForm, fileInput, fileDrop),
          scriptBox)),
      h('div', { class: 'home-games game-list', 'aria-label': 'Your games' },
        h('div', { class: 'list-head' },
          h('h2', {}, 'Games'),
          h('div', { class: 'row filters' },
            h('label', { for: 'f-format', class: 'sr-only' }, 'Format'), formatSel,
            h('label', { for: 'f-result', class: 'sr-only' }, 'Result'), resultSel,
            h('label', { for: 'f-opp', class: 'sr-only' }, 'Opponent'), oppInput)),
        list)))
  await loadSettings().catch(err => say(errText(err), 'error'))
  await Promise.all([loadProfile(), loadGames()])
}

async function loadSettings() {
  state.settings = await api.settings()
  const s = state.settings
  if (document.activeElement !== userInput) userInput.value = s.username
  autoSwitch.sync()
  syncInfo.textContent = `Synced ${fmtAgo(s.last_sync)}`
  syncInfo.title = s.poller_enabled ? `Checks for new games every ${s.poll_minutes} minutes` : ''
  scriptStatus.textContent = s.last_ingest || s.last_ingest_private
    ? `Last battle ${fmtAgo(s.last_ingest)}. Private replays checked ${fmtAgo(s.last_ingest_private)}.`
    : 'Nothing received yet.'
}

async function loadProfile(refresh = false) {
  let p: Profile
  try { p = await api.profile(refresh) } catch (err) {
    profileBox.replaceChildren(h('p', { class: 'muted' }, `Couldn't load ratings: ${errText(err)}`))
    return
  }
  const rows = Object.entries(p.ratings ?? {}).sort((a, b) => b[1].w + b[1].l - (a[1].w + a[1].l)).slice(0, 4)
  const animate = !profileShown
  profileShown = true
  profileBox.replaceChildren(
    h('h2', { class: 'ladders-head' }, 'Ladders'),
    rows.length
      ? h('ul', { class: `ladders${animate ? ' enter' : ''}` }, ...rows.map(([fmt, r], i) => ladderRow(fmt, r, i)))
      : h('p', { class: 'muted' }, 'No ladder games yet.'))
}

/** One ladder: format badge, Elo, and a wins-vs-losses bar (green vs red, like HP). */
function ladderRow(fmt: string, r: { elo: number; gxe: number; w: number; l: number }, i: number) {
  const n = r.w + r.l
  const winPct = n ? Math.round((r.w / n) * 100) : 50
  return h('li', { class: 'ladder', style: `--i:${i}` },
    formatBadge(fmt, ''),
    h('span', { class: 'elo', title: 'Elo' }, Math.round(r.elo)),
    h('span', { class: 'gxe small muted', title: 'GXE: chance to beat an average player' }, `GXE ${Math.round(r.gxe)}`),
    h('span', { class: 'wl', role: 'img', 'aria-label': `${r.w} wins, ${r.l} losses (${winPct}% won)`, title: `${r.w} wins, ${r.l} losses` },
      h('span', { class: 'wl-w', style: `flex-grow:${r.w || (n ? 0 : 1)}` }),
      h('span', { class: 'wl-l', style: `flex-grow:${r.l || (n ? 0 : 1)}` })),
    h('span', { class: 'wl-nums small', 'aria-hidden': 'true' },
      h('span', { class: 'w' }, r.w), h('span', { class: 'muted' }, '–'), h('span', { class: 'l' }, r.l)))
}

async function loadFormats() {
  const fmts = await api.formats()
  const keep = formatSel.value
  formatSel.replaceChildren(h('option', { value: '' }, 'All formats'),
    ...fmts.map(f => h('option', { value: f.format_id }, `${f.format} (${f.n})`)))
  formatSel.value = keep
}

async function loadGames() {
  try {
    const [games] = await Promise.all([api.games(state.filters), loadFormats()])
    const first = seenGames.size === 0
    let k = 0
    list.replaceChildren(...games.map(g => {
      const row = gameRow(g)
      if (!seenGames.has(g.id)) {
        row.classList.add('enter')
        row.style.setProperty('--i', String(first ? Math.min(k++, 10) : 0))
        seenGames.add(g.id)
      }
      return row
    }))
    if (!games.length) {
      const s = state.settings
      const filtered = state.filters.format || state.filters.result || state.filters.opponent
      list.append(h('li', { class: 'empty' },
        filtered ? 'No games match these filters.'
          : s?.sync_start ? `No games since ${fmtDate(s.sync_start)}. Add an older one by URL.`
            : 'No games yet. Press Sync, or add one by URL.'))
    }
  } catch (err) { say(errText(err), 'error') }
}

function gameRow(g: Game) {
  const mine = g.user_side ?? 'p1'
  const theirs = mine === 'p1' ? 'p2' : 'p1'
  const r = g.result
  const ratingDelta = g.rating_before != null && g.rating_after != null ? g.rating_after - g.rating_before : null
  const when = g.played_at ?? g.uploadtime
  const marks = [
    g.private ? icon('lock', 'Private replay') : null,
    g.source === 'userscript' ? icon('disk', 'Saved by the userscript, not uploaded') : null,
    g.has_inputlog ? icon('scroll', 'Full battle data: move review available') : null,
    g.analyzed ? icon('lens', 'Reviewed') : null,
  ].filter(Boolean) as Element[]
  const link = h('a', { href: `#/game/${encodeURIComponent(g.id)}`, class: 'game' },
    h('span', { class: `pip ${r ?? 'none'}`, role: 'img', 'aria-label': r ? r[0].toUpperCase() + r.slice(1) : 'No result' }, r ? r[0].toUpperCase() : '·'),
    h('span', { class: 'who' },
      h('span', { class: 'opp' }, g.user_side ? (g.opponent ?? 'Unknown') : `${g.p1} vs ${g.p2}`),
      formatBadge(g.format_id, g.format)),
    h('span', { class: 'when small muted', title: fmtDate(when) },
      shortDate(when), ' ', h('span', { class: 'turns', title: `${g.turns} turns` }, `T${g.turns}`)),
    h('span', { class: `delta ${ratingDelta == null ? '' : ratingDelta >= 0 ? 'up' : 'down'}`, title: ratingDelta == null ? '' : 'Rating change' },
      ratingDelta == null ? '' : `${ratingDelta >= 0 ? '+' : '−'}${Math.abs(ratingDelta)}`),
    h('span', { class: 'mini-team mine', 'aria-label': `Your team: ${g.teams[mine].join(', ')}` },
      ...g.teams[mine].slice(0, 6).map(sp => sprite(spriteIdFromSpecies(sp), false, '', 'mini'))),
    h('span', { class: 'mini-team theirs', 'aria-label': `Their team: ${g.teams[theirs].join(', ')}` },
      ...g.teams[theirs].slice(0, 6).map(sp => sprite(spriteIdFromSpecies(sp), false, '', 'mini'))),
    marks.length ? h('span', { class: 'marks' }, ...marks) : null)
  return h('li', {}, link)
}

/** "3 h ago" today, "Nov 22" this year, else "Nov 22, 2025". The full date is the title. */
export function shortDate(t: number | null): string {
  if (!t) return ''
  if (Date.now() / 1000 - t < 86400) return fmtAgo(t)
  const d = new Date(t * 1000)
  const sameYear = d.getFullYear() === new Date().getFullYear()
  return new Intl.DateTimeFormat(undefined, sameYear ? { month: 'short', day: 'numeric' } : { dateStyle: 'medium' }).format(d)
}

/** Short format badge: a generation tile plus a short name, coloured by format family. */
export function formatBadge(formatId: string, formatName: string) {
  const id = formatId.toLowerCase()
  const gen = id.match(/^gen(\d+)/)?.[1] ?? ''
  const rest = id.replace(/^gen\d+/, '')
  const family = rest.includes('vgc') ? 'vgc' : rest.includes('random') ? 'rand' : 'other'
  const reg = rest.match(/reg([a-z])([a-z])?$/)
  const NAMES: Record<string, string> = { randombattle: 'Random', ou: 'OU', ubers: 'Ubers', uu: 'UU', championsou: 'Champions OU',
    randomdoublesbattle: 'Random Doubles', firstbloodrandombattle: 'First Blood' }
  const name = family === 'vgc'
    ? `VGC${reg ? ` ${reg[1].toUpperCase()}${reg[2] ? `-${reg[2].toUpperCase()}` : ''}` : ''}`
    : NAMES[rest] ?? (formatName.replace(/^\[[^\]]*\]\s*/, '') || rest)
  return h('span', { class: `fmt-badge ${family}`, title: formatName || formatId },
    gen ? h('span', { class: 'fmt-gen' }, gen) : null, h('span', { class: 'fmt-name' }, name))
}

export function icon(name: string, label: string): Element {
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg')
  const rows = ICONS[name]
  svg.setAttribute('viewBox', `0 0 ${rows[0].length} ${rows.length}`)
  svg.setAttribute('class', `pxicon ${name}`)
  if (label) {
    svg.setAttribute('role', 'img')
    svg.setAttribute('aria-label', label)
    const title = document.createElementNS('http://www.w3.org/2000/svg', 'title')
    title.textContent = label
    svg.append(title)
  } else {
    svg.setAttribute('aria-hidden', 'true')   // decorative: the button's text names the action
  }
  ICONS[name].forEach((row, y) => [...row].forEach((c, x) => {
    if (c !== '#') return
    const r = document.createElementNS('http://www.w3.org/2000/svg', 'rect')
    r.setAttribute('x', String(x)); r.setAttribute('y', String(y)); r.setAttribute('width', '1'); r.setAttribute('height', '1')
    svg.append(r)
  }))
  return svg
}

// Same rule as server/sprites.py sprite_id (kept short: the list only needs a guess;
// a missing sprite just shows the fallback).
const HYPHENATED = new Set(['hooh', 'porygonz', 'jangmoo', 'hakamoo', 'kommoo', 'chiyu', 'tinglu', 'wochien', 'chienpao', 'nidoranf', 'nidoranm'])
const id = (x: string) => x.toLowerCase().replace(/[^a-z0-9]/g, '')
export function spriteIdFromSpecies(species: string): string {
  const parts = species.split('-')
  let base: string, formes: string[]
  if (parts.length >= 2 && HYPHENATED.has(id(parts[0] + parts[1]))) { base = id(parts[0] + parts[1]); formes = parts.slice(2) }
  else { base = id(parts[0]); formes = parts.slice(1) }
  const forme = id(formes.join(''))
  return forme ? `${base}-${forme}` : base
}
