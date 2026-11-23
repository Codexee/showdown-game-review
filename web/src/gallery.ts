// Gallery (#/gallery): every battle-screen element on the real review screen, one example per
// "turn", built from a real game's turn so the sprites, cards and data are real. Step with ← →
// like any game; stepping forward one at a time plays the hit / faint / switch animations.
import { api, type Mon, type Review, type Step } from './api'
import { errText, h } from './dom'
import { ReviewScreen, setCurrent } from './review'

const clone = <T,>(x: T): T => JSON.parse(JSON.stringify(x))
export const GALLERY_ID = 'upload-gallery'

export async function renderGallery(root: HTMLElement) {
  root.replaceChildren(h('p', { class: 'loading' }, 'Building the gallery…'))
  let base: Review
  try {
    const games = await api.games({})
    const g = games.find(x => x.format_id.includes('randombattle') && x.gametype === 'singles') ?? games[0]
    if (!g) throw new Error('No saved games to build examples from.')
    base = await api.review(g.id)
  } catch (err) {
    root.replaceChildren(h('p', { class: 'error' }, `Couldn't build the gallery: ${errText(err)}`), h('a', { href: '#/' }, 'Back to games'))
    return
  }
  // A turn where both sides have a Pokemon out and the opponent has someone on the bench.
  const found = base.steps.findIndex((s, i) => i > 0 && !s.ended
    && s.state.sides[base.perspective === 'p1' ? 'p2' : 'p1'].team.filter(m => m.seen && !m.fainted).length >= 2)
  const start = found > 0 ? found : Math.min(1, base.steps.length - 1)
  const me = base.perspective, them = me === 'p1' ? 'p2' : 'p1'
  const seed = base.steps[start]
  const steps: Step[] = []
  const add = (label: string, edit: (s: Step) => void = () => {}) => {
    const s = clone(seed)
    s.events = [{ text: label, side: null, kind: 'info' }]
    s.eval = 0.5
    edit(s)
    steps.push(s)
  }
  const active = (s: Step, side: 'p1' | 'p2') => s.state.sides[side].team.find(m => m.active) as Mon
  const bench = (s: Step, side: 'p1' | 'p2') => s.state.sides[side].team.find(m => m.seen && !m.active && !m.fainted)

  add('Plain turn (no effects)')
  for (const st of ['brn', 'par', 'slp', 'frz', 'psn', 'tox']) add(`Status: ${st.toUpperCase()}`, s => { active(s, them).status = st })
  add('Stat changes: +2 Atk, −1 Spe, +1 Def', s => { Object.assign(active(s, them).boosts, { atk: 2, spe: -1, def: 1 }) })
  add('Substitute (the doll stands in)', s => { active(s, them).volatiles.push('substitute') })
  add('Terastallized (Tera Fairy)', s => { active(s, them).tera_type = 'Fairy' })
  add('Confused + Leech Seed', s => { active(s, them).volatiles.push('confusion', 'leechseed') })
  for (const [w, label] of [['raindance', 'Rain'], ['sunnyday', 'Harsh sun'], ['sandstorm', 'Sandstorm'], ['snowscape', 'Snow']] as const) {
    add(`Weather: ${label}`, s => { s.state.field.weather = w })
  }
  for (const t of ['electric', 'grassy', 'misty', 'psychic']) add(`Terrain: ${t}`, s => { s.state.field.terrain = `${t}terrain` })
  for (const [p, label] of [['trickroom', 'Trick Room'], ['gravity', 'Gravity'], ['magicroom', 'Magic Room']] as const) {
    add(`Room: ${label}`, s => { s.state.field.pseudo_weather = [p] })
  }
  add('Their side: Stealth Rock, Spikes ×3, Toxic Spikes ×2, Sticky Web', s => {
    Object.assign(s.state.sides[them].conditions, { stealthrock: 1, spikes: 3, toxicspikes: 2, stickyweb: 1 })
  })
  add('Your side: Reflect, Light Screen, Tailwind', s => {
    Object.assign(s.state.sides[me].conditions, { reflect: 1, lightscreen: 1, tailwind: 1 })
  })
  add('Before a hit (step → to see the HP drain and shudder)')
  add('Hit: lost 45% HP', s => { const m = active(s, them); m.hp = Math.max(1, Math.round(m.hp - 0.45 * m.maxhp)) })
  add('Before a switch (step →)')
  add('Switch: recalled, the next one sent out', s => {
    const out = active(s, them), next = bench(s, them)
    if (!next) return
    next.active = true; next.position = out.position; out.active = false; out.position = null
  })
  add('Before a faint (step →)')
  add('Faint: HP drains to 0, then the replacement comes in', s => {
    const out = active(s, them), next = bench(s, them)
    out.hp = 0; out.fainted = true
    if (!next) return
    next.active = true; next.position = out.position; out.active = false; out.position = null
  })
  steps.forEach((s, i) => { s.turn = i + 1; s.ended = false })

  const review: Review = { ...base, steps, game: { ...base.game, id: GALLERY_ID }, eval_method: 'placeholder',
    eval_method_text: 'Gallery: each "turn" is one example built from a real turn.' }
  setCurrent(new ReviewScreen(root, review, 0))
}
