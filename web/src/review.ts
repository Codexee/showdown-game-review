// Review screen (roadmap stage 4, vault ADR-0011): a DS-style pair of screens.
// Top screen: the battle at the start of the selected turn, with the eval bar beside it.
// Hinge: turn controls. Bottom screen: eval graph, turn list, and what happened.
import { api, type Analysis, type Mon, type Review, type SideReview, type SideView, type Step, type TurnReview } from './api'
import { errText, fmtDate, h, pct, s, say, sprite } from './dom'

const STAT_SHORT: Record<string, string> = { atk: 'Atk', def: 'Def', spa: 'SpA', spd: 'SpD', spe: 'Spe', accuracy: 'Acc', evasion: 'Eva' }
const STATUS_LABEL: Record<string, string> = { brn: 'BRN', par: 'PAR', slp: 'SLP', frz: 'FRZ', psn: 'PSN', tox: 'TOX' }
const CONDITION_NAMES: Record<string, string> = {
  stealthrock: 'Stealth Rock', spikes: 'Spikes', toxicspikes: 'Toxic Spikes', stickyweb: 'Sticky Web',
  reflect: 'Reflect', lightscreen: 'Light Screen', auroraveil: 'Aurora Veil', tailwind: 'Tailwind',
  safeguard: 'Safeguard', mist: 'Mist',
}
const WEATHER_NAMES: Record<string, string> = {
  raindance: 'Rain', sunnyday: 'Harsh sun', sandstorm: 'Sandstorm', snowscape: 'Snow',
  desolateland: 'Extreme sun', primordialsea: 'Heavy rain', deltastream: 'Strong winds',
}
const VERDICT_MARK: Record<string, string> = { inaccuracy: '?!', mistake: '?', blunder: '??', 'no blame': '–' }
const VERDICT_TEXT: Record<string, string> = {
  best: 'Best choice', good: 'Good', inaccuracy: 'Inaccuracy', mistake: 'Mistake', blunder: 'Blunder',
  forced: 'Only one option', 'no blame': 'No blame',
}
const pts = (x: number) => `${x >= 0 ? '+' : '−'}${Math.abs(Math.round(x * 100))}`
const titleCase = (id: string) => id.replace(/(^|[^a-z])([a-z])/g, (_, a, b) => a + b.toUpperCase())

export async function renderReview(root: HTMLElement, id: string, initialStep: number | null) {
  root.replaceChildren(h('p', { class: 'loading' }, 'Loading game…'))
  let review: Review
  try {
    review = await api.review(id)
  } catch (err) {
    root.replaceChildren(h('p', { class: 'error' }, `Couldn't open this game: ${errText(err)}`),
      h('a', { href: '#/' }, 'Back to games'))
    return
  }
  setCurrent(new ReviewScreen(root, review, initialStep))
}

class ReviewScreen {
  private step = 0
  private review: Review
  private readonly topScreen = h('div', { class: 'screen top', 'aria-label': 'Battle' })
  private readonly evalBar = h('div', { class: 'evalbar', role: 'meter', 'aria-valuemin': '0', 'aria-valuemax': '100' })
  private readonly turnLabel = h('span', { class: 'turn-label' })
  private readonly prevBtn = h('button', { type: 'button', class: 'hinge-btn', 'aria-label': 'Previous turn' }, '◀')
  private readonly nextBtn = h('button', { type: 'button', class: 'hinge-btn', 'aria-label': 'Next turn' }, '▶')
  private readonly graph = h('div', { class: 'graph' })
  private readonly turnList = h('ol', { class: 'turn-list', 'aria-label': 'Turns' })
  private readonly eventsBox = h('div', { class: 'events', 'aria-live': 'polite' })
  private readonly analysisBar = h('section', { class: 'analysis-bar frame', 'aria-label': 'Move review' })
  private readonly methodText = h('p', { class: 'method' })
  private analysis: Analysis | null = null
  private pollTimer = 0

  private readonly root: HTMLElement

  constructor(root: HTMLElement, review: Review, initialStep: number | null) {
    this.root = root
    this.review = review
    this.step = clampStep(initialStep ?? 0, review.steps.length)
    this.build()
    this.go(this.step, false)
  }

  private get steps(): Step[] { return this.review.steps }
  private get me(): 'p1' | 'p2' { return this.review.perspective }
  private get them(): 'p1' | 'p2' { return this.me === 'p1' ? 'p2' : 'p1' }

  private build() {
    const g = this.review.game
    const meName = this.steps[0]?.state.sides[this.me].name || this.me
    const themName = this.steps[0]?.state.sides[this.them].name || this.them
    const result = g.user_side === this.me ? g.result : null
    const swap = h('button', { type: 'button', class: 'link-btn' }, `View as ${themName}`)
    swap.addEventListener('click', async () => {
      try {
        this.review = await api.review(g.id, this.them)
        this.root.replaceChildren()
        this.build()
        this.go(this.step, false)
      } catch (err) { say(errText(err), 'error') }
    })

    const header = h('header', { class: 'review-head' },
      h('a', { href: '#/', class: 'back' }, 'Games'),
      h('h1', {}, h('span', { class: 'me' }, meName), h('span', { class: 'vs' }, 'vs'), h('span', { class: 'them' }, themName)),
      h('p', { class: 'meta' },
        h('span', {}, g.format),
        h('span', {}, fmtDate(g.played_at ?? g.uploadtime)),
        result ? h('span', { class: `result result-${result}` }, result === 'win' ? 'Win' : result === 'loss' ? 'Loss' : 'Tie') : null,
        g.id.startsWith('upload-') ? null
          : h('a', { href: `https://replay.pokemonshowdown.com/${g.id}`, target: '_blank', rel: 'noopener' }, 'Replay on Showdown'),
        swap))

    this.prevBtn.addEventListener('click', () => this.go(this.step - 1))
    this.nextBtn.addEventListener('click', () => this.go(this.step + 1))
    const hinge = h('div', { class: 'hinge' }, this.prevBtn, this.turnLabel, this.nextBtn)

    const bottom = h('div', { class: 'screen bottom' },
      this.graph,
      this.methodText,
      h('div', { class: 'bottom-grid' },
        h('section', { 'aria-label': 'Turns' }, h('h2', {}, 'Turns'), this.turnList),
        h('section', { 'aria-label': 'What happened' }, h('h2', {}, 'What happened'), this.eventsBox)))

    const teamArea = h('textarea', { id: 'team-paste', rows: '8', spellcheck: 'false',
      placeholder: 'Paste the team you used (Showdown export format)' })
    teamArea.value = g.team_paste ?? ''
    const teamForm = h('form', { class: 'team-form' },
      h('label', { for: 'team-paste' }, 'Your team for this game'),
      h('p', { class: 'small muted' }, 'The model will use your exact sets instead of guessing them.'),
      teamArea, h('button', { type: 'submit' }, 'Save team'))
    teamForm.addEventListener('submit', async e => {
      e.preventDefault()
      try { await api.saveTeam(g.id, teamArea.value); say('Team saved.') } catch (err) { say(errText(err), 'error') }
    })

    this.root.replaceChildren(
      header,
      this.analysisBar,
      h('div', { class: 'ds' },
        h('div', { class: 'top-row' }, this.topScreen, this.evalBar),
        hinge,
        bottom),
      h('p', { class: 'keys' }, 'Use the ← and → keys to step through turns.'),
      h('details', { class: 'team-details frame' }, h('summary', {}, 'Your team for this game'), teamForm))

    this.methodText.textContent = this.review.eval_method_text
    this.buildGraph()
    this.buildTurnList()
    this.renderAnalysisBar()
    void this.loadAnalysis()
  }

  // ---------------------------------------------------------------- move review
  private async loadAnalysis() {
    try { this.analysis = await api.analysis(this.review.game.id) } catch { this.analysis = null }
    this.afterAnalysis()
  }

  private async refreshEval() {
    try {
      const r = await api.review(this.review.game.id, this.me)
      if (r.eval_method !== 'model+search') return
      this.review = r
      this.methodText.textContent = r.eval_method_text
      this.buildGraph()
      this.buildTurnList()
      this.go(this.step, false)
    } catch { /* keep the model's eval */ }
  }

  private afterAnalysis() {
    clearTimeout(this.pollTimer)
    const st = this.analysis?.status
    if ((st === 'queued' || st === 'running') && this.root.isConnected) {
      this.pollTimer = window.setTimeout(() => void this.loadAnalysis(), 2000)
    }
    this.renderAnalysisBar()
    // A current move review lets the server blend its one-turn search into the eval bar.
    if (st === 'done' && !this.analysis?.stale && this.analysis?.result?.mode !== 'perfect'
        && this.review.eval_method === 'model') void this.refreshEval()
    if (st === 'done') {
      this.buildTurnList()
      this.buildGraph()
      this.go(this.step, false)
    }
  }

  private renderAnalysisBar() {
    const a = this.analysis
    const run = h('button', { type: 'button' }, a?.status === 'done' ? 'Analyze again' : 'Analyze game')
    run.addEventListener('click', async () => {
      run.disabled = true
      try { this.analysis = await api.analyze(this.review.game.id) } catch (err) { say(errText(err), 'error') }
      this.afterAnalysis()
    })
    const parts: (Node | string)[] = []
    if (!a || a.status === 'none') {
      parts.push(h('p', {}, 'Grade every choice in this game: the engine plays each option on the simulator and shows how much win chance each choice gave up.'), run)
    } else if (a.status === 'queued' || a.status === 'running') {
      const [done, total] = a.progress ?? [0, 0]
      parts.push(h('p', { class: 'analysis-progress' }, total ? `Analyzing: turn ${done} of ${total}` : 'Starting the analysis…'),
        h('div', { class: 'progress-track' }, h('div', { class: 'progress-fill', style: `width:${total ? (done / total) * 100 : 3}%` })))
    } else if (a.status === 'unsupported' || a.status === 'error') {
      parts.push(h('p', { class: 'muted' }, a.error ?? 'This game can’t be analyzed.'))
      if (a.status === 'error') parts.push(run)
    } else if (a.status === 'done' && a.result) {
      const sum = a.result.summary
      parts.push(h('div', { class: 'scorecards' }, this.scorecard(sum[this.me], 'mine'), this.scorecard(sum[this.them], 'theirs')))
      parts.push(h('p', { class: 'small muted' },
        `Each choice is graded by the win chance it gave up against the best option (inaccuracy 5, mistake 10, blunder 20 points), ` +
        (a.result.mode === 'perfect' ? `using both teams' real sets. ` : `using only what that player could see: the opponent's unrevealed moves, item, ability and Tera type are filled in from the Random Battle sets, ${a.result.seeds} different ways. `) +
        `Luck is what the dice did beyond what both choices made likely.` + (a.stale ? ' A newer model is installed: analyze again to update.' : '')))
      if (a.stale) parts.push(run)
    }
    this.analysisBar.replaceChildren(h('h2', {}, 'Move review'), ...parts)
  }

  private scorecard(p: { name: string; accuracy: number | null; counts: Record<string, number>; luck_points: number }, who: string) {
    const counts = (['blunder', 'mistake', 'inaccuracy'] as const)
      .map(k => p.counts[k] ? h('span', { class: `vchip ${k}` }, `${p.counts[k]} ${k}${p.counts[k] > 1 ? (k === 'inaccuracy' ? '' : 's') : ''}`.replace('inaccuracys', 'inaccuracies')) : null)
    return h('div', { class: `scorecard ${who}` },
      h('p', { class: 'sc-name' }, p.name),
      h('p', { class: 'sc-acc' }, h('span', { class: 'sc-num' }, p.accuracy == null ? '–' : p.accuracy.toFixed(1)), h('span', { class: 'small' }, ' accuracy')),
      h('p', { class: 'sc-counts' }, ...(counts.some(Boolean) ? counts : [h('span', { class: 'small muted' }, 'No mistakes')])),
      h('p', { class: 'small' }, `Luck ${p.luck_points >= 0 ? '+' : '−'}${Math.abs(p.luck_points).toFixed(0)} points`))
  }

  /** The turn whose events (and choices) row i of the turn list describes. */
  private eventTurn(i: number): number | null {
    const st = this.steps[i]
    if (i === 0 || !st) return null
    return st.ended ? st.turn : st.turn - 1
  }

  private reviewFor(turn: number | null): TurnReview | null {
    if (turn == null || this.analysis?.status !== 'done') return null
    return this.analysis.result?.turns.find(t => t.turn === turn) ?? null
  }

  private reviewBox(tr: TurnReview) {
    const line = (who: 'p1' | 'p2', r: SideReview | undefined, name: string) => {
      if (!r || !r.played) return null
      const v = r.verdict ?? 'good'
      const showBest = r.best !== r.played && (r.regret ?? 0) >= 0.5
      return h('li', { class: `rv ${who === this.me ? 'mine' : 'theirs'}` },
        h('span', { class: `vchip ${v.replace(' ', '-')}` }, VERDICT_TEXT[v] ?? v),
        h('span', {}, `${name}: ${r.played_label}`,
          (r.regret ?? 0) >= 0.5 ? h('span', { class: 'muted' }, ` (−${(r.regret ?? 0).toFixed(1)} points)`) : null,
          showBest ? h('span', {}, `. Best: ${r.best_label} (${Math.round(r.best_value * 100)}%)`) : null,
          r.no_blame ? h('span', { class: 'muted' }, ` (${r.no_blame})`) : null))
    }
    const names = { p1: this.steps[0].state.sides.p1.name, p2: this.steps[0].state.sides.p2.name }
    const luck = tr.luck_p1 == null ? null : (this.me === 'p1' ? tr.luck_p1 : -tr.luck_p1)
    return h('div', { class: 'review-box' },
      h('ul', {}, line(this.me, tr.sides[this.me], names[this.me]), line(this.them, tr.sides[this.them], names[this.them])),
      luck != null && Math.abs(luck) >= 0.02
        ? h('p', { class: `luck ${luck >= 0 ? 'up' : 'down'}` }, `Luck this turn: ${pts(luck)} points for you`)
        : null)
  }

  // ---------------------------------------------------------------- navigation
  go(step: number, focusList = true) {
    this.step = clampStep(step, this.steps.length)
    const st = this.steps[this.step]
    this.turnLabel.textContent = st.ended ? `End of turn ${st.turn}` : `Turn ${st.turn} of ${this.lastTurn()}`
    this.prevBtn.disabled = this.step === 0
    this.nextBtn.disabled = this.step === this.steps.length - 1
    this.renderTop(st)
    this.renderEval(st)
    this.renderEvents(st)
    this.markGraph()
    for (const [i, li] of [...this.turnList.children].entries()) {
      const btn = li.querySelector('button')!
      btn.setAttribute('aria-current', i === this.step ? 'step' : 'false')
      if (i === this.step && focusList) this.keepInList(li as HTMLElement)
    }
    history.replaceState(null, '', `#/game/${encodeURIComponent(this.review.game.id)}/${this.step}`)
  }

  private lastTurn() { return this.steps[this.steps.length - 1]?.turn ?? 0 }

  // Keep the current turn visible inside the turn list without moving the page.
  // (scrollIntoView would also scroll the window, which made the page jump on every step.)
  private keepInList(li: HTMLElement) {
    const list = this.turnList
    const top = li.offsetTop - list.offsetTop
    const bottom = top + li.offsetHeight
    if (top < list.scrollTop) list.scrollTop = top
    else if (bottom > list.scrollTop + list.clientHeight) list.scrollTop = bottom - list.clientHeight
  }

  handleKey(e: KeyboardEvent) {
    if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return
    if (e.key === 'ArrowLeft') { this.go(this.step - 1); e.preventDefault() }
    else if (e.key === 'ArrowRight') { this.go(this.step + 1); e.preventDefault() }
    else if (e.key === 'Home') { this.go(0); e.preventDefault() }
    else if (e.key === 'End') { this.go(this.steps.length - 1); e.preventDefault() }
  }

  // ---------------------------------------------------------------- top screen
  private renderTop(st: Step) {
    const view = st.state
    const doubles = view.gametype === 'doubles'
    const field = h('div', { class: `field${doubles ? ' doubles' : ''}` })
    field.append(this.sideArea(view.sides[this.them], false, doubles), this.sideArea(view.sides[this.me], true, doubles))
    const tags = this.fieldTags(st)
    this.topScreen.replaceChildren(field, tags)
  }

  private sideArea(side: SideView, mine: boolean, doubles: boolean) {
    const slots = doubles ? [0, 1] : [0]
    const area = h('div', { class: `side ${mine ? 'mine' : 'theirs'}` })
    const sprites = h('div', { class: 'platform' })
    const boxes = h('div', { class: 'hp-boxes' })
    for (const pos of slots) {
      const mon = side.team.find(m => m.active && m.position === pos)
      if (mon) {
        sprites.append(sprite(mon.sprite, mine, mon.species, `sprite${mon.fainted ? ' fainted' : ''}`))
        boxes.append(this.hpBox(mon, mine))
      } else {
        sprites.append(h('span', { class: 'sprite empty', 'aria-hidden': 'true' }))
      }
    }
    area.append(h('div', { class: 'party-row' }, h('span', { class: 'trainer' }, side.name), this.party(side)), boxes, sprites)
    return area
  }

  private hpBox(mon: Mon, mine: boolean) {
    const frac = mon.fainted ? 0 : mon.hp / (mon.maxhp || 100)
    const tone = frac > 0.5 ? 'green' : frac > 0.2 ? 'yellow' : 'red'
    const hpText = mon.fainted ? 'Fainted' : mon.hp_exact ? `${mon.hp}/${mon.maxhp}` : `${Math.round(frac * 100)}%`
    const boosts = Object.entries(mon.boosts).map(([k, v]) =>
      h('span', { class: `chip ${v > 0 ? 'up' : 'down'}` }, `${v > 0 ? '+' : '−'}${Math.abs(v)} ${STAT_SHORT[k] ?? k}`))
    const extra = [
      mon.tera_type ? h('span', { class: 'chip tera' }, `Tera ${mon.tera_type}`) : null,
      ...mon.volatiles.filter(v => v === 'substitute' || v === 'confusion' || v === 'leechseed')
        .map(v => h('span', { class: 'chip' }, v === 'substitute' ? 'Substitute' : v === 'confusion' ? 'Confused' : 'Seeded')),
    ]
    const details = [
      mon.item !== null ? `Item: ${mon.item ? titleCase(mon.item) : 'none'}` : null,
      mon.ability ? `Ability: ${titleCase(mon.ability)}` : null,
      mon.moves.length ? `Moves: ${mon.moves.map(titleCase).join(', ')}` : null,
    ].filter(Boolean).join('\n')
    return h('div', { class: `hp-box ${mine ? 'mine' : 'theirs'}`, title: details || undefined },
      h('div', { class: 'hp-name' },
        h('span', { class: 'mon-name' }, mon.name !== mon.species && !mon.species.startsWith(mon.name) ? `${mon.name} (${mon.species})` : mon.species),
        h('span', { class: 'lv' }, `Lv${mon.level}`)),
      h('div', { class: 'hp-row' },
        h('span', { class: 'hp-tag', 'aria-hidden': 'true' }, 'HP'),
        h('div', { class: 'hp-track', role: 'meter', 'aria-label': `${mon.species} HP`, 'aria-valuemin': '0',
          'aria-valuemax': '100', 'aria-valuenow': String(Math.round(frac * 100)) },
          h('div', { class: `hp-fill ${tone}`, style: `width:${(frac * 100).toFixed(1)}%` }))),
      h('div', { class: 'hp-foot' },
        mon.status ? h('span', { class: `status-tag ${mon.status}` }, STATUS_LABEL[mon.status] ?? mon.status) : null,
        h('span', { class: 'hp-num' }, hpText)),
      boosts.length || extra.some(Boolean) ? h('div', { class: 'chips' }, ...boosts, ...extra) : null)
  }

  private party(side: SideView) {
    const size = side.team_size ?? Math.max(6, side.team.length)
    const balls = h('span', { class: 'party', 'aria-label': `${side.name}'s team` })
    const seen = side.team.filter(m => m.seen)
    for (let i = 0; i < size; i++) {
      const m = seen[i]
      const state = !m ? 'unknown' : m.fainted ? 'fainted' : m.status ? 'status' : 'ok'
      const label = !m ? 'Not seen yet' : `${m.species}${m.fainted ? ', fainted' : m.status ? `, ${STATUS_LABEL[m.status] ?? m.status}` : ''}`
      balls.append(h('span', { class: `ball ${state}`, title: label, role: 'img', 'aria-label': label }))
    }
    return balls
  }

  private fieldTags(st: Step) {
    const view = st.state
    const tags: HTMLElement[] = []
    if (view.field.weather) tags.push(h('span', { class: 'tag weather' }, WEATHER_NAMES[view.field.weather] ?? titleCase(view.field.weather)))
    if (view.field.terrain) tags.push(h('span', { class: 'tag terrain' }, titleCase(view.field.terrain.replace('terrain', ' Terrain'))))
    for (const p of view.field.pseudo_weather) tags.push(h('span', { class: 'tag' }, titleCase(p)))
    for (const sid of [this.them, this.me] as const) {
      for (const [c, layers] of Object.entries(view.sides[sid].conditions)) {
        const name = CONDITION_NAMES[c] ?? titleCase(c)
        tags.push(h('span', { class: `tag ${sid === this.me ? 'mine' : 'theirs'}` },
          `${name}${layers > 1 ? ` ×${layers}` : ''} (${sid === this.me ? 'your side' : 'their side'})`))
      }
    }
    return h('div', { class: 'field-tags' }, ...tags)
  }

  // ---------------------------------------------------------------- eval
  private renderEval(st: Step) {
    const v = st.eval
    this.evalBar.replaceChildren(
      h('div', { class: 'eval-them', style: `height:${((1 - v) * 100).toFixed(1)}%` }),
      h('div', { class: 'eval-me', style: `height:${(v * 100).toFixed(1)}%` }),
      h('span', { class: 'eval-num' }, pct(v)))
    this.evalBar.setAttribute('aria-valuenow', String(Math.round(v * 100)))
    this.evalBar.setAttribute('aria-label', `Estimated chance that ${st.state.sides[this.me].name} wins`)
    this.evalBar.title = `${st.state.sides[this.me].name}: ${pct(v)} to win (rough estimate)`
  }

  private graphMarker: SVGLineElement | null = null
  private graphDot: SVGRectElement | null = null
  private buildGraph() {
    const W = 600, H = 120, n = this.steps.length
    const x = (i: number) => (n <= 1 ? W / 2 : (i / (n - 1)) * W)
    const y = (v: number) => H - v * H
    // A stepped line suits the pixel look and the fact that eval changes per turn.
    let d = `M0 ${y(this.steps[0]?.eval ?? 0.5)}`
    this.steps.forEach((st, i) => { if (i > 0) d += ` H${x(i)} V${y(st.eval)}` })
    const area = `${d} H${W} V${H / 2} H0 Z`
    const svg = s('svg', { viewBox: `0 0 ${W} ${H}`, preserveAspectRatio: 'none', class: 'graph-svg', role: 'img',
      'aria-label': `Estimated win chance for ${this.steps[0]?.state.sides[this.me].name ?? 'you'} over the game` },
      s('defs', {},
        s('clipPath', { id: 'above' }, s('rect', { x: 0, y: 0, width: W, height: H / 2 })),
        s('clipPath', { id: 'below' }, s('rect', { x: 0, y: H / 2, width: W, height: H / 2 }))),
      s('path', { d: area, class: 'area-me', 'clip-path': 'url(#above)' }),
      s('path', { d: area, class: 'area-them', 'clip-path': 'url(#below)' }),
      s('line', { x1: 0, x2: W, y1: H / 2, y2: H / 2, class: 'mid' }),
      s('path', { d, class: 'line' }))
    this.graphMarker = s('line', { y1: 0, y2: H, class: 'marker' })
    this.graphDot = s('rect', { width: 8, height: 8, class: 'dot' })
    this.steps.forEach((_st, i) => {
      const v = this.reviewFor(this.eventTurn(i))?.sides[this.me]?.verdict
      if (v === 'mistake' || v === 'blunder') {
        svg.append(s('rect', { x: x(i) - 3, y: v === 'blunder' ? 2 : 4, width: 6, height: v === 'blunder' ? 10 : 6,
          class: `gmark ${v}` }))
      }
    })
    svg.append(this.graphMarker, this.graphDot)
    const pick = (ev: PointerEvent) => {
      const r = svg.getBoundingClientRect()
      const i = Math.round(((ev.clientX - r.left) / r.width) * (n - 1))
      this.go(i)
    }
    svg.addEventListener('pointerdown', pick)
    this.graph.replaceChildren(svg)
  }

  private markGraph() {
    const W = 600, H = 120, n = this.steps.length
    const xi = n <= 1 ? W / 2 : (this.step / (n - 1)) * W
    const v = this.steps[this.step].eval
    this.graphMarker?.setAttribute('x1', String(xi))
    this.graphMarker?.setAttribute('x2', String(xi))
    this.graphDot?.setAttribute('x', String(xi - 4))
    this.graphDot?.setAttribute('y', String(H - v * H - 4))
  }

  // ---------------------------------------------------------------- bottom screen
  private buildTurnList() {
    this.turnList.replaceChildren(...this.steps.map((st, i) => {
      const prev = i > 0 ? this.steps[i - 1].eval : st.eval
      const delta = Math.round((st.eval - prev) * 100) / 100 // whole points, so no "−0"
      const moves = st.events.filter(e => e.kind === 'move').map(e => e.text.replace(/\.$/, '').replace(/ on .*/, ''))
      const tr = this.reviewFor(this.eventTurn(i))
      const chip = (side: 'p1' | 'p2') => {
        const v = tr?.sides[side]?.verdict
        return v && VERDICT_MARK[v] ? h('span', { class: `vmark ${v.replace(' ', '-')} ${side === this.me ? 'mine' : 'theirs'}`,
          title: `${side === this.me ? 'You' : 'Opponent'}: ${VERDICT_TEXT[v]}` }, VERDICT_MARK[v]) : null
      }
      const btn = h('button', { type: 'button', class: 'turn-btn' },
        h('span', { class: 'turn-n' }, st.ended ? 'End' : i === 0 ? 'Leads' : `T${st.turn - 1}`, chip(this.me), chip(this.them)),
        h('span', { class: 'turn-moves' }, moves.length ? moves.join(', ') : st.events[0]?.text ?? ''),
        h('span', { class: `turn-eval ${Math.abs(delta) < 0.005 ? 'flat' : delta > 0 ? 'up' : 'down'}` },
          i === 0 ? pct(st.eval) : `${delta >= 0 ? '+' : '−'}${Math.abs(Math.round(delta * 100))}`))
      btn.addEventListener('click', () => this.go(i, false))
      return h('li', {}, btn)
    }))
  }

  private renderEvents(st: Step) {
    const heading = this.step === 0 ? 'Leads' : st.ended ? `Turn ${st.turn}, the last` : `Turn ${st.turn - 1}`
    const tr = this.reviewFor(this.eventTurn(this.step))
    this.eventsBox.replaceChildren(
      h('p', { class: 'events-when' }, heading),
      ...(tr ? [this.reviewBox(tr)] : []),
      st.events.length
        ? h('ul', {}, ...st.events.map(e =>
          h('li', { class: `ev ${e.kind} ${e.side === this.me ? 'mine' : e.side === this.them ? 'theirs' : ''}` }, e.text)))
        : h('p', { class: 'muted' }, 'Nothing happened.'))
  }
}

function clampStep(i: number, n: number) { return Math.max(0, Math.min(n - 1, Number.isFinite(i) ? i : 0)) }

// The router keeps one live screen so the key handler can reach it.
let current: { handleKey(e: KeyboardEvent): void } | null = null
export function reviewKeyHandler(e: KeyboardEvent) { current?.handleKey(e) }
export function setCurrent(screen: { handleKey(e: KeyboardEvent): void } | null) { current = screen }
export { ReviewScreen }
