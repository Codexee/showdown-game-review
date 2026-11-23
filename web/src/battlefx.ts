// Battle-screen extras (2026-11-23): animated sprites that step slowly, the substitute doll,
// field and side-condition overlays, move strips, and Pokemon details laid out like
// Showdown's tooltip (with the Random Battle set odds, as in Showdown's randbats tooltip).
import type { Dex, DexRole, Mon } from './api'
import { h } from './dom'

export const TYPE_COLORS: Record<string, string> = {
  Normal: '#a8a77a', Fire: '#ee8130', Water: '#6390f0', Electric: '#f7d02c', Grass: '#7ac74c', Ice: '#96d9d6',
  Fighting: '#c22e28', Poison: '#a33ea1', Ground: '#e2bf65', Flying: '#a98ff3', Psychic: '#f95587', Bug: '#a6b91a',
  Rock: '#b6a136', Ghost: '#735797', Dragon: '#6f35fc', Dark: '#705746', Steel: '#b7b7ce', Fairy: '#d685ad',
  Stellar: '#40b5a5',
}
const typeColor = (t: string | undefined) => TYPE_COLORS[t ?? ''] ?? '#9aa4b2'
const reducedMotion = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches
const titleCase = (id: string) => id.replace(/(^|[^a-z])([a-z])/g, (_, a, b) => a + b.toUpperCase())

// ---------------------------------------------------------------- sprites
interface AniMeta { w: number; h: number; frames: number; ms: number[] }
const aniMeta = new Map<string, AniMeta | null>()       // known: meta, or null = no animated sprite
const aniPending = new Map<string, Promise<AniMeta | null>>()

function loadMeta(key: string): Promise<AniMeta | null> {
  let p = aniPending.get(key)
  if (!p) {
    p = fetch(`/sprites/${key}.json`).then(r => (r.ok ? r.json() as Promise<AniMeta> : null)).catch(() => null)
      .then(m => { aniMeta.set(key, m); return m })
    aniPending.set(key, p)
  }
  return p
}

function aniInner(key: string, m: AniMeta): HTMLElement {
  // Step slowly: each frame shown twice as long as in the game's GIF, three times with the
  // system's reduced-motion setting. The app's Motion switch (off) freezes the first frame.
  const total = m.ms.reduce((a, b) => a + b, 0) * (reducedMotion() ? 3 : 2)
  return h('span', { class: 'ani-win', style: `--fw:${m.w};--fh:${m.h};--n:${m.frames};--dur:${total}ms` },
    h('img', { class: 'ani-strip', alt: '', src: `/sprites/${key}.png`, decoding: 'async' }))
}

/** A battle sprite: a stable wrapper (classes, data and the info card stay on it) holding
 *  the animated sprite when Showdown has one, else the still one until it loads. */
export function battleSprite(id: string, back: boolean, alt: string, cls: string): HTMLElement {
  const key = `gen5ani${back ? '-back' : ''}/${encodeURIComponent(id)}`
  const wrap = h('span', { class: `${cls} spr`, role: 'img', 'aria-label': alt, tabindex: '0' })
  const known = aniMeta.get(key)
  if (known) {
    wrap.classList.add('ani')
    wrap.append(aniInner(key, known))
    return wrap
  }
  const img = h('img', { class: 'still', alt: '', decoding: 'async', width: '96', height: '96',
    src: `/sprites/${back ? 'gen5-back' : 'gen5'}/${encodeURIComponent(id)}.png` })
  img.addEventListener('error', () => wrap.classList.add('missing'), { once: true })
  wrap.append(img)
  if (known === undefined) {
    void loadMeta(key).then(m => {
      if (m && wrap.isConnected) { wrap.classList.add('ani'); wrap.replaceChildren(aniInner(key, m)) }
    })
  }
  return wrap
}

export function substituteSprite(back: boolean, cls: string): HTMLElement {
  return h('img', { class: `${cls} sub`, alt: 'Substitute', decoding: 'async', width: '96', height: '96',
    src: `/sprites/${back ? 'sub-back' : 'sub'}/substitute.png` })
}

// ---------------------------------------------------------------- field effects
const WEATHER_FX: Record<string, string> = {
  raindance: 'rain', primordialsea: 'rain', sunnyday: 'sun', desolateland: 'sun', sandstorm: 'sand',
  snowscape: 'snow', hail: 'snow', deltastream: 'wind',
}
/** Quiet overlays for weather, terrain and room effects (labels stay in the tags below). */
export function fieldOverlays(field: { weather: string; terrain: string; pseudo_weather: string[] }): HTMLElement[] {
  const out: HTMLElement[] = []
  const wx = WEATHER_FX[field.weather]
  if (wx) out.push(h('div', { class: `fx-layer wx ${wx}`, 'aria-hidden': 'true' }))
  if (field.terrain) out.push(h('div', { class: `fx-layer terrain ${field.terrain.replace('terrain', '')}`, 'aria-hidden': 'true' }))
  for (const p of field.pseudo_weather) {
    if (['trickroom', 'gravity', 'magicroom', 'wonderroom'].includes(p)) out.push(h('div', { class: `fx-layer room ${p}`, 'aria-hidden': 'true' }))
  }
  return out
}

// ---------------------------------------------------------------- moves and info cards
/** Role weights given what has been revealed: roles that can't have a revealed move drop out. */
function rolesFor(roles: DexRole[], mon: Mon): DexRole[] {
  const fit = roles.filter(r => mon.moves.every(m => m in r.moves))
  return fit.length ? fit : roles
}
function odds(roles: DexRole[], pick: (r: DexRole) => Record<string, number>): [string, number][] {
  const total = roles.reduce((a, r) => a + r.weight, 0) || 1
  const acc: Record<string, number> = {}
  for (const r of roles) for (const [k, p] of Object.entries(pick(r))) acc[k] = (acc[k] ?? 0) + (p * r.weight) / total
  return Object.entries(acc).sort((a, b) => b[1] - a[1])
}

function moveChip(id: string | null, dex: Dex | undefined, cls = '') {
  if (!id) return h('span', { class: `mchip unknown ${cls}`, title: 'Not revealed yet' }, '?')
  const m = dex?.moves[id]
  const label = m?.name ?? titleCase(id)
  return h('span', { class: `mchip ${cls}`, style: `--c:${typeColor(m?.type)}`,
    title: m ? `${m.name}: ${m.type} ${m.cat}${m.bp ? `, ${m.bp} power` : ''}${m.acc <= 100 ? `, ${m.acc}% accuracy` : ''}${m.pri ? `, priority ${m.pri > 0 ? '+' : ''}${m.pri}` : ''}` : label },
  h('span', { class: `mcat ${m?.cat?.toLowerCase() ?? ''}`, 'aria-hidden': 'true' }), label)
}

/** The four move slots: revealed moves, then "?" for slots not seen yet. */
export function moveStrip(mon: Mon, dex: Dex | undefined) {
  const slots: (string | null)[] = [...mon.moves.slice(0, 4)]
  while (slots.length < 4) slots.push(null)
  return h('div', { class: 'mstrip', 'aria-label': `${mon.species}'s moves` }, ...slots.map(id => moveChip(id, dex)))
}

const STAT_ORDER = ['hp', 'atk', 'def', 'spa', 'spd', 'spe'] as const
const STAT_SHORT: Record<string, string> = { hp: 'HP', atk: 'Atk', def: 'Def', spa: 'SpA', spd: 'SpD', spe: 'Spe' }
const boostMul = (b: number) => (b >= 0 ? (2 + b) / 2 : 2 / (2 - b))
const pctP = (p: number) => ` (${Math.round(p * 100)}%)`

export function typeChip(t: string, cls = '') {
  return h('span', { class: `tchip ${cls}`, style: `--c:${typeColor(t)}` }, t)
}

/** A Pokemon's details in the order and wording of Showdown's tooltip: name, level and
 *  types; HP and status; ability; item; Tera; stats; moves. Revealed facts are bold;
 *  anything from the Random Battle set data says "Possible" and gives its odds. */
export function infoCard(mon: Mon, dex: Dex | undefined, random: boolean): HTMLElement {
  const sp = dex?.species[mon.species]
  const set = dex?.sets[mon.species]
  const roles = set ? rolesFor(set.roles, mon) : []
  const frac = mon.fainted ? 0 : mon.hp / (mon.maxhp || 100)
  const line = (...kids: (Node | string | null)[]) => h('p', { class: 'tip-line' }, ...kids)
  const label = (t: string) => h('span', { class: 'tip-k' }, t)
  const shown = (t: string) => h('b', {}, t)
  const guesses = (pairs: [string, number][], fmt: (k: string) => string) =>
    h('span', { class: 'tip-guess' }, pairs.slice(0, 6).map(([k, p]) => fmt(k) + (pairs.length === 1 && p >= 0.995 ? '' : pctP(p))).join(', '))
  const fact = (one: string, many: string, value: string | null, pairs: [string, number][], fmt = (k: string) => k) =>
    value ? line(label(`${one}: `), shown(value))
      : pairs.length ? line(label(`${pairs.length > 1 ? many : `Possible ${one === 'Tera Type' ? one : one.toLowerCase()}`}: `), guesses(pairs, fmt)) : null

  const parts: (Node | null)[] = [
    h('p', { class: 'tip-head' }, h('b', {}, mon.species), h('span', { class: 'tip-lv' }, ` L${mon.level}`),
      ...(sp?.types ?? []).map(t => typeChip(t)),
      mon.tera_type ? typeChip(`Tera ${mon.tera_type}`, 'tera') : null),
    line(label('HP: '), shown(mon.fainted ? 'fainted' : mon.hp_exact ? `${mon.hp}/${mon.maxhp} (${Math.round(frac * 100)}%)` : `${Math.round(frac * 100)}%`),
      mon.status ? h('span', { class: `status-tag ${mon.status}` }, mon.status.toUpperCase()) : null),
    fact('Ability', 'Possible abilities', mon.ability ? titleCase(mon.ability) : null, odds(roles, r => r.abilities)),
    fact('Item', 'Possible items', mon.item !== null ? (mon.item ? titleCase(mon.item) : '(none)') : null, odds(roles, r => r.items)),
    random || mon.tera_type ? fact('Tera Type', 'Possible Tera Types', mon.tera_type || null, odds(roles, r => r.tera)) : null,
    roles.length ? line(label(roles.length > 1 ? 'Possible roles: ' : 'Role: '),
      h('span', { class: 'tip-guess' }, roles.map(r => r.name + (roles.length > 1 ? pctP(r.weight / roles.reduce((a, x) => a + x.weight, 0)) : '')).join(', '))) : null,
  ]
  if (sp?.bs && Object.keys(sp.bs).length) {
    // Random Battle sets use 31 IVs and 84 EVs with a neutral nature, so stats are exact.
    const lv = mon.level || 100
    const stat = (k: string) => {
      const b = sp.bs[k]
      if (!random) return b
      return k === 'hp' ? Math.floor(((2 * b + 31 + 21) * lv) / 100) + lv + 10 : Math.floor(((2 * b + 31 + 21) * lv) / 100) + 5
    }
    const cells: (Node | string)[] = []
    STAT_ORDER.forEach((k, i) => {
      const v = stat(k), b = k === 'hp' ? 0 : (mon.boosts[k] ?? 0)
      if (i) cells.push(h('span', { class: 'tip-sep' }, ' / '))
      cells.push(h('span', { class: b > 0 ? 'up' : b < 0 ? 'down' : '' }, `${STAT_SHORT[k]} ${b ? Math.floor(v * boostMul(b)) : v}`))
    })
    parts.push(line(random ? null : label('Base: '), h('span', { class: 'tip-stats' }, ...cells)))
  }
  const moves = h('ul', { class: 'tip-moves' }, ...mon.moves.map(id => {
    const m = dex?.moves[id]
    return h('li', { style: `--c:${typeColor(m?.type)}` }, h('b', {}, m?.name ?? titleCase(id)))
  }))
  if (roles.length && mon.moves.length < 4) {
    for (const [id, p] of odds(roles, r => r.moves).filter(([id]) => !mon.moves.includes(id)).slice(0, 8)) {
      const m = dex?.moves[id]
      moves.append(h('li', { class: 'tip-guess', style: `--c:${typeColor(m?.type)}` }, (m?.name ?? titleCase(id)) + pctP(p)))
    }
  }
  if (moves.children.length) parts.push(moves)
  return h('div', { class: 'tip-body' }, ...parts)
}
