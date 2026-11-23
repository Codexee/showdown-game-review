// Games page: trainer card (username, sync, ratings), adding games, and the game list.
import { api, type Game, type Profile, type Settings } from './api'
import { errText, fmtAgo, fmtDate, h, say, sprite } from './dom'

const state = {
  settings: null as Settings | null,
  filters: { format: '', result: '', opponent: '' },
}

const userInput = h('input', { id: 'username', autocomplete: 'off', spellcheck: 'false', maxlength: '18' })
const syncInfo = h('p', { class: 'sync-info' })
const syncBtn = h('button', { type: 'button' }, 'Sync now')
const profileBox = h('div', { class: 'ratings-box' })
const list = h('ol', { class: 'games', 'aria-label': 'Your games' })
const formatSel = h('select', { id: 'f-format' }, h('option', { value: '' }, 'All formats'))
const resultSel = h('select', { id: 'f-result' },
  h('option', { value: '' }, 'Any result'), h('option', { value: 'win' }, 'Wins'),
  h('option', { value: 'loss' }, 'Losses'), h('option', { value: 'tie' }, 'Ties'))
const oppInput = h('input', { id: 'f-opp', type: 'search', placeholder: 'Opponent' })
const urlInput = h('input', { id: 'replay-url', type: 'url', placeholder: 'https://replay.pokemonshowdown.com/…', required: '' })
const fileInput = h('input', { id: 'replay-file', type: 'file', accept: '.log,.html,.htm,.json,.txt' })
const scriptStatus = h('p', { class: 'small muted' })
const scriptBox = h('details', { class: 'userscript' },
  h('summary', {}, 'Save every game, even ones you don\'t upload'),
  h('ol', {},
    h('li', {}, 'Install the ', h('a', { href: 'https://www.tampermonkey.net/', target: '_blank', rel: 'noopener' }, 'Tampermonkey'), ' browser extension.'),
    h('li', {}, h('a', { href: '/userscript/showdown-review.user.js' }, 'Install the Showdown Review userscript'), '. Tampermonkey opens an install page.'),
    h('li', {}, 'Play on play.pokemonshowdown.com with this app running. Each battle is saved here a few seconds after it ends. Private replays you upload are picked up every 15 minutes.')),
  h('p', { class: 'small muted' }, 'The script only sends battle logs and private replay ids to this app on your computer. Your Showdown password and login stay in your browser.'),
  scriptStatus)

let wired = false
function wire() {
  if (wired) return
  wired = true
  userForm.addEventListener('submit', async e => {
    e.preventDefault()
    try {
      state.settings = await api.saveSettings({ username: userInput.value })
      say(`Username set to ${state.settings.username}.`)
      await Promise.all([loadSettings(), loadProfile(true), loadGames()])
    } catch (err) { say(errText(err), 'error') }
  })
  syncBtn.addEventListener('click', async () => {
    syncBtn.disabled = true
    syncBtn.textContent = 'Syncing…'
    try {
      const r = await api.sync()
      let msg = r.added.length ? `Saved ${r.added.length} new game${r.added.length === 1 ? '' : 's'}.` : 'No new games.'
      if (r.first_sync) msg += ' From now on, every game you upload is saved automatically.'
      if (r.errors.length) msg += ` ${r.errors.length} couldn't be saved: ${r.errors[0]}`
      say(msg, r.errors.length ? 'error' : 'ok')
      await Promise.all([loadSettings(), loadProfile(), loadGames()])
    } catch (err) { say(errText(err), 'error') }
    finally { syncBtn.disabled = false; syncBtn.textContent = 'Sync now' }
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
  fileInput.addEventListener('change', async () => {
    const f = fileInput.files?.[0]
    if (!f) return
    try {
      const r = await api.importFile(f)
      say(r.added ? 'Game added.' : 'That game is already saved.')
      await loadGames()
    } catch (err) { say(errText(err), 'error') }
    finally { fileInput.value = '' }
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

const userForm = h('form', { class: 'user-form' },
  h('label', { for: 'username' }, 'Showdown username'),
  h('div', { class: 'row' }, userInput, h('button', { type: 'submit', class: 'quiet' }, 'Save'), syncBtn))
const urlForm = h('form', { class: 'row' },
  h('label', { for: 'replay-url', class: 'sr-only' }, 'Replay URL'), urlInput, h('button', { type: 'submit' }, 'Add game'))

export async function renderList(root: HTMLElement) {
  wire()
  // One block: profile, sync and adding games beside the games list. On a desktop it fits
  // the window and the list scrolls inside it (user request 2026-11-23); phones stack it.
  root.replaceChildren(
    h('header', { class: 'app-head' }, h('h1', {}, 'Showdown Review')),
    h('section', { class: 'home frame', 'aria-label': 'Your profile and games' },
      h('div', { class: 'home-side' },
        h('div', { class: 'home-profile', 'aria-label': 'Your profile' }, userForm, syncInfo, profileBox),
        h('div', { class: 'add', 'aria-label': 'Add games' },
          h('h2', {}, 'Add a game'),
          urlForm,
          h('div', { class: 'row' }, h('label', { for: 'replay-file' }, 'Or upload a saved log or replay file'), fileInput),
          scriptBox)),
      h('div', { class: 'home-games game-list', 'aria-label': 'Your games' },
        h('div', { class: 'list-head' },
          h('h2', {}, 'Your games'),
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
  syncInfo.textContent = `Last synced ${fmtAgo(s.last_sync)}.` + (s.poller_enabled ? ` Checks again every ${s.poll_minutes} minutes.` : '')
  scriptStatus.textContent = s.last_ingest || s.last_ingest_private
    ? `Last game from the script: ${fmtAgo(s.last_ingest)}. Last private replay check: ${fmtAgo(s.last_ingest_private)}.`
    : 'The script hasn\'t sent anything yet.'
}

async function loadProfile(refresh = false) {
  let p: Profile
  try { p = await api.profile(refresh) } catch (err) {
    profileBox.replaceChildren(h('p', { class: 'muted' }, `Couldn't load ratings: ${errText(err)}`))
    return
  }
  const rows = Object.entries(p.ratings ?? {}).sort((a, b) => b[1].w + b[1].l - (a[1].w + a[1].l)).slice(0, 4)
  profileBox.replaceChildren(
    h('p', { class: 'small muted' }, 'Your most-played ladders'),
    rows.length
      ? h('dl', { class: 'ratings' }, ...rows.flatMap(([fmt, r]) => [
        h('dt', {}, fmt),
        h('dd', {}, h('span', { class: 'elo' }, Math.round(r.elo)), h('span', { class: 'small muted' }, `GXE ${r.gxe}, ${r.w} wins, ${r.l} losses`)),
      ]))
      : h('p', { class: 'muted' }, 'No ladder ratings yet.'))
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
    list.replaceChildren(...games.map(gameRow))
    if (!games.length) {
      const s = state.settings
      const filtered = state.filters.format || state.filters.result || state.filters.opponent
      list.append(h('li', { class: 'empty' },
        filtered ? 'No games match these filters.'
          : s?.sync_start ? `No games yet. Games you upload after ${fmtDate(s.sync_start)} appear here. To review an older game, add it by URL above.`
            : 'No games yet. Press "Sync now" to start saving your games, or add one by URL above.'))
    }
  } catch (err) { say(errText(err), 'error') }
}

function gameRow(g: Game) {
  const mine = g.user_side ?? 'p1'
  const theirs = mine === 'p1' ? 'p2' : 'p1'
  const r = g.result
  const ratingDelta = g.rating_before != null && g.rating_after != null ? g.rating_after - g.rating_before : null
  const link = h('a', { href: `#/game/${encodeURIComponent(g.id)}`, class: 'game' },
    h('span', { class: `pip ${r ?? 'none'}`, 'aria-label': r ? r[0].toUpperCase() + r.slice(1) : 'No result' }, r ? r[0].toUpperCase() : '·'),
    h('span', { class: 'who' },
      h('span', { class: 'opp' }, g.user_side ? (g.opponent ?? 'Unknown') : `${g.p1} vs ${g.p2}`),
      h('span', { class: 'fmt small' }, g.format)),
    h('span', { class: 'when small muted' }, fmtDate(g.played_at ?? g.uploadtime), h('br', {}), `${g.turns} turns`),
    h('span', { class: `delta ${ratingDelta == null ? '' : ratingDelta >= 0 ? 'up' : 'down'}` },
      ratingDelta == null ? '' : `${ratingDelta >= 0 ? '+' : '−'}${Math.abs(ratingDelta)}`),
    h('span', { class: 'mini-team mine', 'aria-label': `Your team: ${g.teams[mine].join(', ')}` },
      ...g.teams[mine].slice(0, 6).map(sp => sprite(spriteIdFromSpecies(sp), false, '', 'mini'))),
    h('span', { class: 'mini-team theirs', 'aria-label': `Their team: ${g.teams[theirs].join(', ')}` },
      ...g.teams[theirs].slice(0, 6).map(sp => sprite(spriteIdFromSpecies(sp), false, '', 'mini'))),
    g.private || g.source === 'userscript' || g.has_inputlog
      ? h('span', { class: 'tags' },
        g.private ? h('span', { class: 'tag' }, 'Private') : null,
        g.source === 'userscript' ? h('span', { class: 'tag' }, 'Not uploaded') : null,
        g.has_inputlog ? h('span', { class: 'tag', title: 'Full battle data saved' }, 'Full data') : null)
      : null)
  return h('li', {}, link)
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
