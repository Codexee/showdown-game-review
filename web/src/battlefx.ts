// Battle-screen extras (2026-11-23): animated sprites that step slowly, the substitute doll,
// field and side-condition overlays, move effects by type and category, move strips and
// info cards with everything Showdown's own tooltips show.
import type { BattleEvent, Dex, DexRole, Mon, SideView } from './api'
import { h } from './dom'

export const TYPE_COLORS: Record<string, string> = {
  Normal: '#a8a77a', Fire: '#ee8130', Water: '#6390f0', Electric: '#f7d02c', Grass: '#7ac74c', Ice: '#96d9d6',
  Fighting: '#c22e28', Poison: '#a33ea1', Ground: '#e2bf65', Flying: '#a98ff3', Psychic: '#f95587', Bug: '#a6b91a',
  Rock: '#b6a136', Ghost: '#735797', Dragon: '#6f35fc', Dark: '#705746', Steel: '#b7b7ce', Fairy: '#d685ad',
  Stellar: '#40b5a5',
}
const typeColor = (t: string | undefined) => TYPE_COLORS[t ?? ''] ?? '#9aa4b2'
const motionOff = () => document.documentElement.dataset.motion === 'off'
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

/** Side conditions drawn on that side's platform: screens, hazards, Tailwind. */
export function sideOverlays(side: SideView): HTMLElement[] {
  const out: HTMLElement[] = []
  for (const [c, layers] of Object.entries(side.conditions)) {
    if (['reflect', 'lightscreen', 'auroraveil', 'stealthrock', 'spikes', 'toxicspikes', 'stickyweb', 'tailwind', 'safeguard', 'mist'].includes(c)) {
      out.push(h('span', { class: `cond ${c}`, style: `--layers:${layers}`, 'aria-hidden': 'true' }))
    }
  }
  return out
}

// ---------------------------------------------------------------- move effects
/** Small effects for the moves just used: physical = impact on the target, special = an orb
 *  from user to target, status = a ring on the target (or the user). Coloured by type. Pure
 *  decoration over the final state: it never delays stepping. */
export function playMoves(screen: HTMLElement, events: BattleEvent[], dex: Dex | undefined, me: string) {
  if (!dex || motionOff()) return
  const moves = events.filter(e => e.kind === 'move' && e.move && dex.moves[e.move]).slice(0, 3)
  const box = screen.getBoundingClientRect()
  const spriteAt = (side: string | null | undefined, pos: number | undefined) =>
    screen.querySelector<HTMLElement>(`[data-side="${side === me ? 'mine' : 'theirs'}"][data-pos="${pos ?? 0}"]`)
  const centre = (el: HTMLElement) => {
    const r = el.getBoundingClientRect()
    return { x: r.left - box.left + r.width / 2, y: r.top - box.top + r.height * 0.55 }
  }
  moves.forEach((e, i) => {
    const mv = dex.moves[e.move!]
    const user = spriteAt(e.side, e.pos)
    const target = e.target ? spriteAt(e.target, e.target_pos) : user
    if (!user || !target) return
    const color = typeColor(mv.type)
    const delay = i * 300
    const a = centre(user), b = centre(target)
    const spark = (x: number, y: number, cls: string) => {
      const el = h('span', { class: `move-fx ${cls}`, style: `left:${x}px;top:${y}px;--c:${color}`, 'aria-hidden': 'true' })
      screen.append(el)
      return el
    }
    if (reducedMotion()) {                       // gentle: one soft flash on the target, no travel
      const f = spark(b.x, b.y, 'burst')
      f.animate([{ opacity: 0.7 }, { opacity: 0 }], { duration: 320, delay, fill: 'both' }).finished.then(() => f.remove())
      return
    }
    if (mv.cat === 'Special' && user !== target) {
      const orb = spark(a.x, a.y, 'orb')
      orb.animate([{ transform: 'translate(-50%, -50%) scale(0.6)', opacity: 0 },
        { transform: 'translate(-50%, -50%) scale(1)', opacity: 1, offset: 0.2 },
        { transform: `translate(calc(-50% + ${b.x - a.x}px), calc(-50% + ${b.y - a.y}px)) scale(1)`, opacity: 1 }],
      { duration: 260, delay, easing: 'cubic-bezier(0.77, 0, 0.175, 1)', fill: 'both' }).finished.then(() => orb.remove())
    }
    const hitDelay = delay + (mv.cat === 'Special' && user !== target ? 220 : mv.cat === 'Physical' ? 60 : 0)
    const f = spark(b.x, b.y, mv.cat === 'Status' ? 'ring' : 'burst')
    f.animate([{ transform: 'translate(-50%, -50%) scale(0.6)', opacity: 0.9 },
      { transform: 'translate(-50%, -50%) scale(1.25)', opacity: 0 }],
    { duration: mv.cat === 'Status' ? 420 : 300, delay: hitDelay, easing: 'cubic-bezier(0.23, 1, 0.32, 1)', fill: 'both' })
      .finished.then(() => f.remove())
  })
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
const pctTxt = (p: number) => (p >= 0.995 ? '' : ` ${Math.round(p * 100)}%`)

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

/** Everything Showdown's tooltip shows, from what this replay revealed plus (Random Battle)
 *  the set odds: types, HP, status, ability, item, Tera, revealed and possible moves, stats. */
export function infoCard(mon: Mon, dex: Dex | undefined, random: boolean): HTMLElement {
  const sp = dex?.species[mon.species]
  const set = dex?.sets[mon.species]
  const roles = set ? rolesFor(set.roles, mon) : []
  const frac = mon.fainted ? 0 : mon.hp / (mon.maxhp || 100)
  const row = (label: string, ...value: (Node | string | null)[]) => h('div', { class: 'tip-row' }, h('span', { class: 'tip-k' }, label), h('span', {}, ...value))
  // Guesses from the set data are italic and say so; revealed facts are plain.
  const possible = (pairs: [string, number][], fmt: (k: string) => string) =>
    pairs.length ? h('span', { class: 'tip-guess', title: 'Not revealed: from the Random Battle set data' },
      pairs.length === 1 && pairs[0][1] >= 0.995 ? `${fmt(pairs[0][0])} (always)` : pairs.slice(0, 5).map(([k, p]) => fmt(k) + pctTxt(p)).join(', ')) : null
  const parts: (Node | null)[] = [
    h('div', { class: 'tip-head' }, h('b', {}, mon.species), h('span', { class: 'muted' }, ` Lv${mon.level}`),
      ...(sp?.types ?? []).map(t => h('span', { class: 'tchip', style: `--c:${typeColor(t)}` }, t)),
      mon.tera_type ? h('span', { class: 'tchip tera', style: `--c:${typeColor(mon.tera_type)}` }, `Tera ${mon.tera_type}`) : null),
    row('HP', mon.fainted ? 'Fainted' : mon.hp_exact ? `${mon.hp}/${mon.maxhp} (${Math.round(frac * 100)}%)` : `${Math.round(frac * 100)}%`,
      mon.status ? h('span', { class: `status-tag ${mon.status}` }, mon.status.toUpperCase()) : null),
    row('Ability', mon.ability ? titleCase(mon.ability) : possible(odds(roles, r => r.abilities), k => k) ?? h('span', { class: 'muted' }, 'unknown')),
    row('Item', mon.item !== null ? (mon.item ? titleCase(mon.item) : 'none') : possible(odds(roles, r => r.items), k => k) ?? h('span', { class: 'muted' }, 'unknown')),
    random && !mon.tera_type && roles.length ? row('Tera', possible(odds(roles, r => r.tera), k => k)) : null,
    mon.moves.length ? row('Moves', h('span', { class: 'tip-moves' }, ...mon.moves.map(id => moveChip(id, dex)))) : null,
  ]
  if (roles.length) {
    const left = odds(roles, r => r.moves).filter(([id]) => !mon.moves.includes(id))
    if (left.length && mon.moves.length < 4) {
      parts.push(row(mon.moves.length ? 'Could have' : 'Possible', h('span', { class: 'tip-guess' },
        left.slice(0, 8).map(([id, p]) => (dex?.moves[id]?.name ?? titleCase(id)) + pctTxt(p)).join(', '))))
    }
  }
  if (sp?.bs && Object.keys(sp.bs).length) {
    // Random Battle sets use 31 IVs and 84 EVs with a neutral nature, so stats are exact.
    const lv = mon.level || 100
    const stat = (k: string) => {
      const b = sp.bs[k]
      if (!random) return b
      return k === 'hp' ? Math.floor(((2 * b + 31 + 21) * lv) / 100) + lv + 10 : Math.floor(((2 * b + 31 + 21) * lv) / 100) + 5
    }
    parts.push(row(random ? 'Stats' : 'Base', h('span', { class: 'tip-stats' }, ...STAT_ORDER.map(k => {
      const v = stat(k), b = k === 'hp' ? 0 : (mon.boosts[k] ?? 0)
      const shown = b ? Math.floor(v * boostMul(b)) : v
      return h('span', { class: b > 0 ? 'up' : b < 0 ? 'down' : '' }, `${STAT_SHORT[k]} ${shown}`)
    }))))
  }
  return h('div', { class: 'tip-body' }, ...parts)
}

// One floating card for the whole screen, shown on hover or keyboard focus.
let tipEl: HTMLElement | null = null
function tip(): HTMLElement {
  if (!tipEl) {
    tipEl = h('div', { class: 'mon-tip frame', role: 'tooltip', id: 'mon-tip' })
    document.body.append(tipEl)
  }
  return tipEl
}
export function hideTip() { tipEl?.classList.remove('show') }
export function attachTip(el: HTMLElement, content: () => HTMLElement) {
  const show = () => {
    const t = tip()
    t.replaceChildren(content())
    t.classList.add('show')
    const r = el.getBoundingClientRect(), tr = t.getBoundingClientRect()
    let x = r.right + 8, y = r.top
    if (x + tr.width > innerWidth - 8) x = Math.max(8, r.left - tr.width - 8)
    if (y + tr.height > innerHeight - 8) y = Math.max(8, innerHeight - tr.height - 8)
    t.style.left = `${x}px`
    t.style.top = `${y}px`
  }
  el.addEventListener('pointerenter', show)
  el.addEventListener('pointerleave', hideTip)
  el.addEventListener('focus', show)
  el.addEventListener('blur', hideTip)
  el.setAttribute('aria-describedby', 'mon-tip')
}
