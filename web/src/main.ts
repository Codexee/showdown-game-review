// Game list page (roadmap stage 2a). Plain and functional on purpose:
// the Gen 4-5 pixel-art design comes in stage 4 (vault: visual-style).
import './style.css'
import { api, type Game, type GameDetail, type Profile, type Settings } from './api'

// Build elements with textContent only: player names come from other people.
function h<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  props: Partial<Record<string, string>> = {},
  ...children: (Node | string | null | false)[]
): HTMLElementTagNameMap[K] {
  const el = document.createElement(tag)
  for (const [k, v] of Object.entries(props)) if (v !== undefined) el.setAttribute(k, v)
  for (const c of children) if (c) el.append(c)
  return el
}

const fmtDate = (t: number | null) =>
  t ? new Date(t * 1000).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' }) : '—'
const fmtAgo = (t: number | null) => {
  if (!t) return 'never'
  const s = Math.round(Date.now() / 1000 - t)
  if (s < 60) return 'just now'
  if (s < 3600) return `${Math.round(s / 60)} min ago`
  if (s < 86400) return `${Math.round(s / 3600)} h ago`
  return fmtDate(t)
}

const state = {
  settings: null as Settings | null,
  filters: { format: '', result: '', opponent: '' },
  selected: null as string | null,
}

const app = document.querySelector<HTMLDivElement>('#app')!
const status = h('p', { class: 'status', role: 'status', 'aria-live': 'polite' })
const say = (msg: string, kind: 'ok' | 'error' = 'ok') => {
  status.textContent = msg
  status.dataset.kind = kind
}

// ---- header: user, sync -------------------------------------------------------
const userInput = h('input', { id: 'username', autocomplete: 'off', spellcheck: 'false', maxlength: '18' })
const syncInfo = h('span', { class: 'muted' })
const syncBtn = h('button', { type: 'button' }, 'Sync now')
const userForm = h('form', { class: 'row' },
  h('label', { for: 'username' }, 'Showdown username'), userInput,
  h('button', { type: 'submit', class: 'secondary' }, 'Save'), syncBtn, syncInfo)

userForm.addEventListener('submit', async e => {
  e.preventDefault()
  try {
    state.settings = await api.saveSettings({ username: userInput.value })
    say(`Username set to ${state.settings.username}.`)
    await Promise.all([loadProfile(true), loadGames()])
  } catch (err) { say(String((err as Error).message), 'error') }
})

syncBtn.addEventListener('click', async () => {
  syncBtn.disabled = true
  syncBtn.textContent = 'Syncing…'
  try {
    const r = await api.sync()
    const parts = [`${r.added.length} new game${r.added.length === 1 ? '' : 's'}`]
    if (r.first_sync) parts.push('first sync: only games uploaded from now on are saved automatically')
    if (r.errors.length) parts.push(`${r.errors.length} error(s): ${r.errors[0]}`)
    say(parts.join(' · '), r.errors.length ? 'error' : 'ok')
    await Promise.all([loadSettings(), loadProfile(), loadGames()])
  } catch (err) { say(String((err as Error).message), 'error') }
  finally { syncBtn.disabled = false; syncBtn.textContent = 'Sync now' }
})

// ---- profile -------------------------------------------------------------------
const profileBox = h('section', { class: 'profile', 'aria-label': 'Ratings' })

async function loadProfile(refresh = false) {
  profileBox.replaceChildren()
  let p: Profile
  try { p = await api.profile(refresh) } catch (err) {
    profileBox.append(h('p', { class: 'muted' }, `Couldn't load ratings: ${(err as Error).message}`))
    return
  }
  const rows = Object.entries(p.ratings ?? {})
    .sort((a, b) => b[1].w + b[1].l - (a[1].w + a[1].l))
    .slice(0, 6)
  profileBox.append(h('h2', {}, `${p.username}'s ladder ratings`))
  if (!rows.length) { profileBox.append(h('p', { class: 'muted' }, 'No ladder ratings.')); return }
  const list = h('ul', { class: 'ratings' })
  for (const [fmt, r] of rows) {
    list.append(h('li', {},
      h('span', { class: 'fmt' }, fmt),
      h('strong', {}, String(Math.round(r.elo))),
      h('span', { class: 'muted' }, ` GXE ${r.gxe} · ${r.w}–${r.l}`)))
  }
  profileBox.append(list, h('p', { class: 'muted small' }, 'Most-played formats. Elo is the current ladder rating.'))
}

// ---- import --------------------------------------------------------------------
const urlInput = h('input', { id: 'replay-url', type: 'url', placeholder: 'https://replay.pokemonshowdown.com/…', required: '' })
const urlForm = h('form', { class: 'row' },
  h('label', { for: 'replay-url' }, 'Add a replay by URL'), urlInput, h('button', { type: 'submit' }, 'Add'))
urlForm.addEventListener('submit', async e => {
  e.preventDefault()
  try {
    const r = await api.importUrl(urlInput.value)
    say(r.added ? `Added ${r.id}.` : `${r.id} is already saved.`)
    urlInput.value = ''
    await loadGames(r.id)
  } catch (err) { say(String((err as Error).message), 'error') }
})

const fileInput = h('input', { id: 'replay-file', type: 'file', accept: '.log,.html,.htm,.json,.txt' })
const fileRow = h('div', { class: 'row' }, h('label', { for: 'replay-file' }, 'Or upload a saved log or replay file'), fileInput)
fileInput.addEventListener('change', async () => {
  const f = fileInput.files?.[0]
  if (!f) return
  try {
    const r = await api.importFile(f)
    say(r.added ? `Added ${r.id}.` : `${r.id} is already saved.`)
    await loadGames(r.id)
  } catch (err) { say(String((err as Error).message), 'error') }
  finally { fileInput.value = '' }
})

// ---- filters and list ------------------------------------------------------------
const formatSel = h('select', { id: 'f-format' }, h('option', { value: '' }, 'All formats'))
const resultSel = h('select', { id: 'f-result' },
  h('option', { value: '' }, 'Any result'), h('option', { value: 'win' }, 'Wins'),
  h('option', { value: 'loss' }, 'Losses'), h('option', { value: 'tie' }, 'Ties'))
const oppInput = h('input', { id: 'f-opp', type: 'search', placeholder: 'Opponent' })
const filters = h('div', { class: 'row filters' },
  h('label', { for: 'f-format', class: 'sr-only' }, 'Format'), formatSel,
  h('label', { for: 'f-result', class: 'sr-only' }, 'Result'), resultSel,
  h('label', { for: 'f-opp', class: 'sr-only' }, 'Opponent'), oppInput)
formatSel.addEventListener('change', () => { state.filters.format = formatSel.value; loadGames() })
resultSel.addEventListener('change', () => { state.filters.result = resultSel.value; loadGames() })
let oppTimer = 0
oppInput.addEventListener('input', () => {
  clearTimeout(oppTimer)
  oppTimer = window.setTimeout(() => { state.filters.opponent = oppInput.value; loadGames() }, 250)
})

const list = h('ol', { class: 'games', 'aria-label': 'Games' })
const detail = h('section', { class: 'detail', 'aria-label': 'Selected game' })

function resultBadge(g: Game) {
  const label = g.result === 'win' ? 'Win' : g.result === 'loss' ? 'Loss' : g.result === 'tie' ? 'Tie' : '—'
  return h('span', { class: `badge result-${g.result ?? 'none'}` }, label)
}

function ratingText(g: Game) {
  if (g.rating_before == null) return ''
  if (g.rating_after == null) return String(g.rating_before)
  const d = g.rating_after - g.rating_before
  return `${g.rating_before} → ${g.rating_after} (${d >= 0 ? '+' : ''}${d})`
}

function gameRow(g: Game) {
  const mine = g.user_side ? g.teams[g.user_side] : g.teams.p1
  const theirs = g.user_side ? g.teams[g.user_side === 'p1' ? 'p2' : 'p1'] : g.teams.p2
  const btn = h('button', { type: 'button', class: 'game', 'data-id': g.id, 'aria-pressed': String(state.selected === g.id) },
    h('span', { class: 'when' }, fmtDate(g.played_at ?? g.uploadtime)),
    h('span', { class: 'fmt' }, g.format),
    resultBadge(g),
    h('span', { class: 'vs' }, g.user_side ? `vs ${g.opponent ?? '?'}` : `${g.p1} vs ${g.p2}`),
    h('span', { class: 'rating' }, ratingText(g)),
    h('span', { class: 'turns muted' }, `${g.turns} turns`),
    h('span', { class: 'teams muted' }, `${mine.join(', ')}  ·  ${theirs.join(', ')}`),
    h('span', { class: 'tags' },
      g.private ? h('span', { class: 'tag' }, 'private') : null,
      g.source !== 'poller' ? h('span', { class: 'tag' }, g.source) : null,
      g.has_inputlog ? h('span', { class: 'tag', title: 'Full inputlog saved (random formats)' }, 'inputlog') : null,
      g.has_team_paste ? h('span', { class: 'tag' }, 'team') : null))
  btn.addEventListener('click', () => select(g.id))
  return h('li', {}, btn)
}

async function loadFormats() {
  const fmts = await api.formats()
  const keep = formatSel.value
  formatSel.replaceChildren(h('option', { value: '' }, 'All formats'),
    ...fmts.map(f => h('option', { value: f.format_id }, `${f.format} (${f.n})`)))
  formatSel.value = keep
}

async function loadGames(selectId?: string) {
  try {
    const [games] = await Promise.all([api.games(state.filters), loadFormats()])
    list.replaceChildren(...games.map(gameRow))
    if (!games.length) {
      const s = state.settings
      list.append(h('li', { class: 'empty' },
        s?.sync_start
          ? `No games yet. Games ${s.username} uploads after ${fmtDate(s.sync_start)} appear here after a sync. Older games can be added by URL.`
          : 'No games yet. Press "Sync now" to start saving your games, or add a replay by URL.'))
    }
    if (selectId) await select(selectId)
  } catch (err) { say(String((err as Error).message), 'error') }
}

async function select(id: string) {
  state.selected = id
  for (const b of list.querySelectorAll<HTMLButtonElement>('button.game')) {
    b.setAttribute('aria-pressed', String(b.dataset.id === id))
  }
  let g: GameDetail
  try { g = await api.game(id) } catch (err) { say(String((err as Error).message), 'error'); return }
  const team = h('textarea', { id: 'team-paste', rows: '8', spellcheck: 'false',
    placeholder: 'Paste your team here (Showdown export format)' })
  team.value = g.team_paste ?? ''
  const save = h('button', { type: 'submit' }, 'Save team')
  const teamForm = h('form', {}, h('label', { for: 'team-paste' }, 'Your team for this game'), team, save)
  teamForm.addEventListener('submit', async e => {
    e.preventDefault()
    try { await api.saveTeam(g.id, team.value); say('Team saved.'); loadGames() }
    catch (err) { say(String((err as Error).message), 'error') }
  })
  const link = g.id.startsWith('upload-') ? null
    : h('a', { href: `https://replay.pokemonshowdown.com/${g.id}`, target: '_blank', rel: 'noopener' }, 'Open on Showdown')
  detail.replaceChildren(
    h('h2', {}, `${g.p1} vs ${g.p2}`),
    h('p', {}, `${g.format} · ${fmtDate(g.played_at)} · ${g.turns} turns · `, resultBadge(g), ' ', link),
    h('p', { class: 'muted small' }, 'The replay viewer and eval bar come in a later stage.'),
    teamForm,
    h('details', {}, h('summary', {}, 'Battle log'), h('pre', {}, g.log)))
}

async function loadSettings() {
  state.settings = await api.settings()
  if (document.activeElement !== userInput) userInput.value = state.settings.username
  syncInfo.textContent = `Last sync ${fmtAgo(state.settings.last_sync)}` +
    (state.settings.poller_enabled ? ` · auto every ${state.settings.poll_minutes} min` : '')
}

app.append(
  h('header', {}, h('h1', {}, 'Showdown Review'), userForm),
  status,
  h('main', {},
    h('div', { class: 'col' },
      profileBox,
      h('section', { class: 'import', 'aria-label': 'Add games' }, urlForm, fileRow),
      h('section', { 'aria-label': 'Your games' }, h('h2', {}, 'Games'), filters, list)),
    detail),
)

await loadSettings()
await Promise.all([loadProfile(), loadGames()])

// The server's poller adds games in the background; pick them up while the page is open.
setInterval(() => {
  if (document.hidden) return
  void loadSettings().then(() => loadGames()).catch(() => {})
}, 60_000)
