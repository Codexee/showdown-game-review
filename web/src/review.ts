// Review screen (roadmap stage 4, vault ADR-0011): a DS-style pair of screens.
// Top screen: the battle at the start of the selected turn, with the eval bar beside it.
// Hinge: turn controls. Bottom screen: eval graph, turn list, and what happened.
import { api, type Analysis, type Mon, type Review, type SideReview, type SideView, type Step, type TurnReview } from './api'
import { errText, fmtDate, h, pct, s, say, sprite } from './dom'
import { formatBadge, icon, shortDate } from './list'
import { battleSprite, fieldOverlays, infoCard, moveStrip, sideOverlays, substituteSprite } from './battlefx'

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
  private readonly methodBox = h('details', { class: 'method' })
  // Pokemon details, docked in the review column (no floating tooltip): shows the Pokemon
  // under the pointer or keyboard focus; a click pins it; otherwise the opponent's active one.
  private readonly inspectPanel = h('section', { class: 'inspect-panel', 'aria-label': 'Pokémon details', 'aria-live': 'polite' })
  private pinned: string | null = null
  private hovered: { key: string; mon: Mon } | null = null
  private revealScores = false   // animate the scorecards once, when a review finishes while open
  private revealGraph = false    // and pop in the graph's mistake markers
  private analysis: Analysis | null = null
  private opened = false
  private openedAt = 0
  // Turn-change motion: only when stepping forward one turn, not when holding a key or jumping.
  private lastStepAt = 0
  private prevMons: Map<string, MonSnap> | null = null
  private lastStatus: string | undefined = undefined
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
  private get isRandom(): boolean { return teamIsRandom(this.review.format_id) }
  private get me(): 'p1' | 'p2' { return this.review.perspective }
  private get them(): 'p1' | 'p2' { return this.me === 'p1' ? 'p2' : 'p1' }

  private build() {
    const g = this.review.game
    const meName = this.steps[0]?.state.sides[this.me].name || this.me
    const themName = this.steps[0]?.state.sides[this.them].name || this.them
    const result = g.user_side === this.me ? g.result : null
    const swap = h('button', { type: 'button', class: 'link-btn', title: `View as ${themName}`, 'aria-label': `View as ${themName}` },
      h('span', { 'aria-hidden': 'true' }, '⇄ '), themName)
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
      h('h1', {}, h('span', { class: 'me' }, meName), this.elo(this.me), h('span', { class: 'vs' }, 'vs'),
        h('span', { class: 'them' }, themName), this.elo(this.them)),
      h('p', { class: 'meta' },
        result ? h('span', { class: `pip ${result}`, role: 'img', 'aria-label': result === 'win' ? 'Win' : result === 'loss' ? 'Loss' : 'Tie' },
          result[0].toUpperCase()) : null,
        formatBadge(g.format_id, g.format),
        h('span', { title: fmtDate(g.played_at ?? g.uploadtime) }, shortDate(g.played_at ?? g.uploadtime)),
        g.id.startsWith('upload-') ? null
          : h('a', { href: `https://replay.pokemonshowdown.com/${g.id}`, target: '_blank', rel: 'noopener', title: 'Replay on Showdown' }, 'Replay ↗'),
        swap))

    this.prevBtn.addEventListener('click', () => this.go(this.step - 1))
    this.nextBtn.addEventListener('click', () => this.go(this.step + 1))
    // Turn controls: between the two screens on phones; on a desktop they sit in the Turns
    // panel header, leaving a thin hinge, so the battle box has more height.
    const nav = h('div', { class: 'turn-nav' }, this.prevBtn, this.turnLabel, this.nextBtn)
    const hinge = h('div', { class: 'hinge' })
    const turnsHead = h('div', { class: 'turns-head' }, h('h2', {}, 'Turns'))
    const wide = window.matchMedia('(min-width: 1100px) and (min-height: 620px)')
    const placeNav = () => {
      ;(wide.matches ? turnsHead : hinge).append(nav)
      hinge.classList.toggle('thin', wide.matches)
    }
    placeNav()
    wide.addEventListener('change', () => { if (nav.isConnected || !this.root.isConnected) placeNav() })

    // Bottom screen: the Pokemon details, right under the battle box (fixed height, so the
    // battle box never moves). The graph sits in the review column above "What happened".
    const bottom = h('div', { class: 'screen bottom' }, this.inspectPanel)
    const graphPanel = h('section', { class: 'panel graph-panel frame', 'aria-label': 'Win chance over the game' }, this.graph, this.methodBox)

    const teamArea = h('textarea', { id: 'team-paste', rows: '8', spellcheck: 'false',
      placeholder: 'Paste the team you used (Showdown export format)' })
    teamArea.value = g.team_paste ?? ''
    const teamForm = h('form', { class: 'team-form' },
      h('label', { for: 'team-paste', class: 'sr-only' }, 'Your team (Showdown export)'),
      teamArea, h('button', { type: 'submit' }, 'Save team'))
    // Team paste for every format where players build their own team (VGC, OU, and any added
    // later); not where the game hands out teams (vault 2026-11-22-direction-codex-review).
    const ownTeam = !teamIsRandom(g.format_id)
    teamForm.addEventListener('submit', async e => {
      e.preventDefault()
      try { await api.saveTeam(g.id, teamArea.value); say('Team saved.') } catch (err) { say(errText(err), 'error') }
    })

    // Desktop: three columns that fit one screen (battle | turns | review); phones stack them.
    this.root.replaceChildren(
      header,
      h('div', { class: 'review-layout' },
        h('div', { class: 'ds col-battle' },
          h('div', { class: 'top-row' }, this.topScreen, this.evalBar),
          hinge,
          bottom),
        h('section', { class: 'panel col-turns frame', 'aria-label': 'Turns' },
          turnsHead, this.turnList,
          h('p', { class: 'keys', 'aria-label': 'Use the left and right arrow keys to step through turns' },
            h('kbd', {}, '←'), h('kbd', {}, '→'))),
        h('div', { class: 'col-review' },
          this.analysisBar,
          graphPanel,
          h('section', { class: 'panel events-panel frame', 'aria-label': 'What happened' },
            h('h2', {}, 'What happened'), this.eventsBox),
          ownTeam ? h('details', { class: 'team-details frame' }, h('summary', {}, 'Your team'), teamForm) : null)))

    this.renderMethod()
    this.buildGraph()
    this.buildTurnList()
    this.renderAnalysisBar()
    if (!this.opened) {   // match the games page: the screen rises in once when it opens
      this.opened = true
      this.root.querySelectorAll<HTMLElement>('.review-layout > *').forEach((el, i) => {
        el.classList.add('enter'); el.style.setProperty('--i', String(i))
      })
      this.openedAt = performance.now()
      this.markRowsEntering()
    }
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
      this.renderMethod()
      this.buildGraph()
      this.buildTurnList()
      this.go(this.step, false)
    } catch { /* keep the model's eval */ }
  }

  /** Short label for how the win chance is made; the full explanation opens below it. */
  /** A player's ladder rating for this game: before, and the change (green / red). */
  private elo(side: 'p1' | 'p2') {
    const r = this.review.game.summary?.[side]
    if (!r || r.rating_before == null) return null
    const d = r.rating_after != null ? r.rating_after - r.rating_before : null
    return h('span', { class: 'elo-tag', title: `Elo ${r.rating_before}${r.rating_after != null ? ` → ${r.rating_after}` : ''}` },
      h('span', { class: 'elo-n' }, String(r.rating_before)),
      d == null ? null : h('span', { class: `elo-d ${d >= 0 ? 'up' : 'down'}` }, `${d >= 0 ? '+' : '−'}${Math.abs(d)}`))
  }

  private renderMethod() {
    const m = this.review.eval_method
    const label = m === 'model+search' ? 'Model + search' : m === 'model' ? 'Model' : 'HP estimate'
    this.methodBox.replaceChildren(
      h('summary', {}, h('span', { class: 'method-tag' }, label), ' win chance'),
      h('p', {}, this.review.eval_method_text))
  }

  private afterAnalysis() {
    clearTimeout(this.pollTimer)
    const was = this.lastStatus
    const st = this.analysis?.status
    this.lastStatus = st
    if (st === 'done' && (was === 'queued' || was === 'running')) {
      this.revealScores = true
      // The graph may be rebuilt right after (the blended eval arrives), so keep the pop for a moment.
      this.revealGraph = true
      window.setTimeout(() => { this.revealGraph = false }, 1500)
    }
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
    const run = h('button', { type: 'button' }, a?.status === 'done' ? 'Analyze again' : 'Analyze')
    run.addEventListener('click', async () => {
      run.disabled = true
      try { this.analysis = await api.analyze(this.review.game.id) } catch (err) { say(errText(err), 'error') }
      this.afterAnalysis()
    })
    const parts: (Node | string)[] = []
    if (!a || a.status === 'none') {
      parts.push(h('p', {}, 'Grade every choice, about a minute.'), run)
    } else if (a.status === 'queued' || a.status === 'running') {
      const [done, total] = a.progress ?? [0, 0]
      parts.push(h('p', { class: 'analysis-progress' }, total ? `Analyzing turn ${done} / ${total}` : 'Starting…'),
        h('div', { class: 'progress-track' }, h('div', { class: 'progress-fill', style: `width:${total ? (done / total) * 100 : 3}%` })))
    } else if (a.status === 'unsupported' || a.status === 'error') {
      parts.push(h('p', { class: 'muted' }, a.error ?? 'This game can’t be analyzed.'))
      if (a.status === 'error') parts.push(run)
    } else if (a.status === 'done' && a.result) {
      const sum = a.result.summary
      const reveal = this.revealScores
      this.revealScores = false
      parts.push(h('div', { class: `scorecards${reveal ? ' enter' : ''}` }, this.scorecard(sum[this.me], 'mine'), this.scorecard(sum[this.them], 'theirs')))
      parts.push(h('details', { class: 'how small muted' }, h('summary', {}, 'How grading works'),
        h('p', {}, `Each choice is graded by the win chance it gave up against the best option: ?! inaccuracy 5, ? mistake 10, ?? blunder 20 points. ` +
          (a.result.mode === 'perfect' ? `Uses both teams' real sets. ` : `Uses only what that player could see: the opponent's hidden moves, item, ability and Tera are filled in from the Random Battle sets, ${a.result.seeds} ways. `) +
          `Luck (the dice icon) is what the dice did beyond what both choices made likely.`)))
      if (a.stale) parts.push(h('p', { class: 'small' }, 'New model installed.'), run)
    }
    this.analysisBar.replaceChildren(h('h2', {}, 'Move review'), ...parts)
  }

  private scorecard(p: { name: string; accuracy: number | null; counts: Record<string, number>; luck_points: number }, who: string) {
    const counts = (['blunder', 'mistake', 'inaccuracy'] as const).map(k => {
      const n = p.counts[k]
      return n ? h('span', { class: `vchip ${k}`, title: `${n} ${VERDICT_TEXT[k].toLowerCase()}${n > 1 ? 's' : ''}`.replace('inaccuracys', 'inaccuracies') },
        h('b', {}, VERDICT_MARK[k]), ` ${n}`) : null
    })
    const luck = Math.round(p.luck_points)
    return h('div', { class: `scorecard ${who}` },
      h('p', { class: 'sc-name' }, p.name),
      h('p', { class: 'sc-acc', title: 'Accuracy (100 = every choice was the best)' },
        h('span', { class: 'sc-num' }, p.accuracy == null ? '–' : p.accuracy.toFixed(1)), h('span', { class: 'small muted' }, ' acc')),
      h('p', { class: 'sc-counts' }, ...(counts.some(Boolean) ? counts : [h('span', { class: 'vchip good', title: 'No inaccuracies or worse' }, '✓')])),
      h('p', { class: `luck ${luck >= 0 ? 'up' : 'down'}`, title: 'Luck: what the dice did beyond what both choices made likely (win-chance points)' },
        icon('dice', 'Luck'), `${luck >= 0 ? '+' : '−'}${Math.abs(luck)}`))
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
      return h('li', { class: `rv ${who === this.me ? 'mine' : 'theirs'}`, 'aria-label': `${name}: ${VERDICT_TEXT[v] ?? v}` },
        h('span', { class: `vchip ${v.replace(' ', '-')}`, title: VERDICT_TEXT[v] ?? v }, VERDICT_MARK[v] ? h('b', {}, VERDICT_MARK[v] + ' ') : null, VERDICT_TEXT[v] ?? v),
        h('span', { class: 'rv-choice', title: name }, r.played_label,
          (r.regret ?? 0) >= 0.5 ? h('span', { class: 'muted', title: 'Win chance given up' }, ` −${(r.regret ?? 0).toFixed(1)}`) : null,
          showBest ? h('span', { class: 'rv-best', title: 'Best choice and its win chance' }, ` → ${r.best_label} ${Math.round(r.best_value * 100)}%`) : null,
          r.no_blame ? h('span', { class: 'muted' }, ` (${r.no_blame})`) : null))
    }
    const names = { p1: this.steps[0].state.sides.p1.name, p2: this.steps[0].state.sides.p2.name }
    const luck = tr.luck_p1 == null ? null : (this.me === 'p1' ? tr.luck_p1 : -tr.luck_p1)
    return h('div', { class: 'review-box' },
      h('ul', {}, line(this.me, tr.sides[this.me], names[this.me]), line(this.them, tr.sides[this.them], names[this.them])),
      luck != null && Math.abs(luck) >= 0.02
        ? h('p', { class: `luck ${luck >= 0 ? 'up' : 'down'}`, title: 'Luck this turn, for you (win-chance points)' },
          icon('dice', 'Luck this turn'), pts(luck))
        : null)
  }

  // ---------------------------------------------------------------- navigation
  go(step: number, focusList = true) {
    const from = this.step
    this.step = clampStep(step, this.steps.length)
    const now = performance.now()
    // Animate a single step forward unless steps come fast (a held key): then render instantly,
    // so motion never slows down scrubbing.
    const motion = this.opened && this.step === from + 1 && now - this.lastStepAt > 180
    this.lastStepAt = now
    this.prevMons = motion ? snapMons(this.steps[from]) : null
    this.root.classList.toggle('still', !motion)
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
    this.hovered = null
    this.topScreen.replaceChildren(...fieldOverlays(view.field), field, tags)
    this.renderInspect()
  }

  /** Hover, focus or click a Pokemon to see its details in the docked panel. */
  private inspectOn(el: HTMLElement, side: 'p1' | 'p2', mon: Mon) {
    const key = monKey(side, mon)
    el.addEventListener('pointerenter', () => { this.hovered = { key, mon }; this.renderInspect() })
    el.addEventListener('focus', () => { this.hovered = { key, mon }; this.renderInspect() })
    const leave = () => { if (this.hovered?.key === key) { this.hovered = null; this.renderInspect() } }
    el.addEventListener('pointerleave', leave)
    el.addEventListener('blur', leave)
    el.addEventListener('click', () => { this.pinned = this.pinned === key ? null : key; this.renderInspect() })
    el.setAttribute('aria-controls', 'inspect-panel')
  }

  private renderInspect() {
    const view = this.steps[this.step].state
    const keyOf = (m: Mon) => {
      for (const side of ['p1', 'p2'] as const) if (view.sides[side].team.includes(m)) return monKey(side, m)
      return null
    }
    const find = (key: string | null) => {
      if (!key) return null
      for (const side of ['p1', 'p2'] as const) {
        const m = view.sides[side].team.find(x => monKey(side, x) === key)
        if (m) return m
      }
      return null
    }
    const pinned = find(this.pinned)
    const theirs = view.sides[this.them].team.find(m => m.active && !m.fainted)
    const mon = this.hovered?.mon ?? pinned ?? theirs ?? null
    const key = mon ? (this.hovered?.key ?? keyOf(mon)) : null
    const isPinned = !!key && this.pinned === key
    // Pin as an icon button (icons over text labels: vault visual-style), pressed when pinned.
    const pin = h('button', { type: 'button', class: 'icon-btn pin-btn', 'aria-pressed': String(isPinned),
      'aria-label': isPinned ? 'Unpin this Pokémon' : 'Pin this Pokémon', title: isPinned ? 'Unpin' : 'Pin (keeps it here as you step)' },
    icon(isPinned ? 'pin' : 'pinoff', ''))
    pin.disabled = !key
    pin.addEventListener('click', () => { this.pinned = isPinned ? null : key; this.renderInspect() })
    this.inspectPanel.id = 'inspect-panel'
    this.inspectPanel.replaceChildren(
      h('div', { class: 'inspect-head' }, h('h2', {}, 'Pokémon'), pin),
      mon ? infoCard(mon, this.review.dex, this.isRandom) : h('p', { class: 'muted' }, '—'))
  }

  private sideArea(side: SideView, mine: boolean, doubles: boolean) {
    const slots = doubles ? [0, 1] : [0]
    const area = h('div', { class: `side ${mine ? 'mine' : 'theirs'}` })
    const sprites = h('div', { class: 'platform' })
    const boxes = h('div', { class: 'hp-boxes' })
    const sid = mine ? this.me : this.them
    for (const pos of slots) {
      const mon = side.team.find(m => m.active && m.position === pos)
      // The Pokemon that fainted in this slot during the turn: shown sinking out, before its
      // replacement slides in (the turn-start state already has the replacement, or nobody
      // at the end of the game).
      // Whoever stood in this slot last turn and has left it: fainted (sinks out) or was
      // withdrawn (recalled: flashes red and shrinks away). The new one then comes in.
      const left = this.prevMons ? [...this.prevMons.entries()].find(([k, p]) => p.active && p.position === pos
        && k.startsWith(`${sid}|`) && (!mon || k !== monKey(sid, mon))) : undefined
      const leftNow = left ? side.team.find(m => monKey(sid, m) === left[0]) : undefined
      const fell = left && leftNow?.fainted ? left : undefined
      const recalled = left && leftNow && !leftNow.fainted && !leftNow.active ? left : undefined
      if (fell) sprites.append(battleSprite(fell[1].sprite, mine, '', 'sprite faint-ghost'))
      if (recalled) sprites.append(battleSprite(recalled[1].sprite, mine, '', 'sprite recall-ghost'))
      if (mon) {
        const prev = this.prevMons?.get(monKey(mine ? this.me : this.them, mon))
        const frac = mon.fainted ? 0 : mon.hp / (mon.maxhp || 100)
        // A Pokemon seen for the first time came in at full HP; a switch-in that lost HP on
        // the way in (hazards, a pivot hit) slides in and then shudders.
        const before = prev ? prev.frac : 1
        const hurt = frac < before - 0.004
        const fx = !this.prevMons ? ''
          : mon.fainted && !(prev?.fainted) ? ' faint-now'
            : !prev || !prev.active ? ` switch-in${hurt ? ' hit' : ''}`
              : hurt ? ' hit' : ''
        const cls = `sprite${mon.fainted ? ' fainted' : ''}${fx}${fell ? ' after-faint' : recalled ? ' after-recall' : ''}`
        const spr = mon.volatiles.includes('substitute') && !mon.fainted
          ? substituteSprite(mine, cls) : battleSprite(mon.sprite, mine, mon.species, cls)
        spr.dataset.side = mine ? 'mine' : 'theirs'
        spr.dataset.pos = String(pos)
        this.inspectOn(spr, sid, mon)
        sprites.append(spr)
        const box = this.hpBox(mon, mine, prev)
        if (fell && leftNow) {
          // The fainted one's HP box drains to 0 on top, then gives way to the replacement's.
          box.classList.add('after-faint-box')
          boxes.append(h('div', { class: 'hp-slot' }, box, this.faintBox(leftNow, mine, fell[1])))
        } else {
          boxes.append(box)
        }
      } else {
        sprites.append(h('span', { class: 'sprite empty', 'aria-hidden': 'true' }))
        if (fell && leftNow) boxes.append(this.faintBox(leftNow, mine, fell[1], true))   // last one: stays at 0
      }
    }
    sprites.append(...sideOverlays(side))
    // No trainer name here (it's in the page header): more room for the Pokemon.
    area.append(h('div', { class: 'party-row' }, this.sideTags(side, mine), this.party(side)), boxes, sprites)
    return area
  }

  /** The HP box of a Pokemon that fainted this turn, starting from its HP last turn so the
   *  bar visibly drains to 0. `final`: no replacement (end of game), so it stays. */
  private faintBox(mon: Mon, mine: boolean, prev: MonSnap, final = false) {
    const box = this.hpBox(mon, mine, prev)
    box.classList.add('faint-box')
    if (final) box.classList.add('final')
    else { box.setAttribute('aria-hidden', 'true'); box.removeAttribute('tabindex') }
    return box
  }

  private hpBox(mon: Mon, mine: boolean, prev?: MonSnap) {
    const frac = mon.fainted ? 0 : mon.hp / (mon.maxhp || 100)
    // What changed since the previous turn: a "ghost" shows HP just lost (drains away) or
    // gained (flashes); new status and stat chips pop. The bar itself is already final.
    const before = !this.prevMons ? frac : prev ? prev.frac : 1   // first time seen: came in at full HP
    const lost = before - frac > 0.004 ? before - frac : 0
    const gained = prev && prev.active && frac - prev.frac > 0.004 ? frac - prev.frac : 0
    const ghost = lost ? h('div', { class: 'hp-ghost lost', style: `left:${(frac * 100).toFixed(1)}%;width:${(lost * 100).toFixed(1)}%` })
      : gained ? h('div', { class: 'hp-ghost gained', style: `left:${(prev!.frac * 100).toFixed(1)}%;width:${(gained * 100).toFixed(1)}%` })
        : null
    const newStatus = !!prev && prev.active && mon.status !== prev.status && !!mon.status
    const prevBoosts = prev?.active ? prev.boosts : null
    const tone = frac > 0.5 ? 'green' : frac > 0.2 ? 'yellow' : 'red'
    const hpText = mon.fainted ? 'Fainted' : mon.hp_exact ? `${mon.hp}/${mon.maxhp}` : `${Math.round(frac * 100)}%`
    const boosts = Object.entries(mon.boosts).map(([k, v]) =>
      h('span', { class: `chip ${v > 0 ? 'up' : 'down'}${prevBoosts && prevBoosts[k] !== v ? ' pop' : ''}` },
        `${v > 0 ? '+' : '−'}${Math.abs(v)} ${STAT_SHORT[k] ?? k}`))
    const extra = [
      mon.tera_type ? h('span', { class: 'chip tera' }, `Tera ${mon.tera_type}`) : null,
      ...mon.volatiles.filter(v => v === 'substitute' || v === 'confusion' || v === 'leechseed')
        .map(v => h('span', { class: 'chip' }, v === 'substitute' ? 'Substitute' : v === 'confusion' ? 'Confused' : 'Seeded')),
    ]
    const box = h('div', { class: `hp-box ${mine ? 'mine' : 'theirs'}`, tabindex: '0' },
      h('div', { class: 'hp-name' },
        h('span', { class: 'mon-name' }, mon.name !== mon.species && !mon.species.startsWith(mon.name) ? `${mon.name} (${mon.species})` : mon.species),
        h('span', { class: 'lv' }, `Lv${mon.level}`)),
      h('div', { class: 'hp-row' },
        h('span', { class: 'hp-tag', 'aria-hidden': 'true' }, 'HP'),
        h('div', { class: 'hp-track', role: 'meter', 'aria-label': `${mon.species} HP`, 'aria-valuemin': '0',
          'aria-valuemax': '100', 'aria-valuenow': String(Math.round(frac * 100)) },
          h('div', { class: `hp-fill ${tone}`, style: `width:${(frac * 100).toFixed(1)}%` }), ghost)),
      // One row for status, stat changes and the HP number: always there, so a boost never
      // makes the box taller.
      h('div', { class: 'hp-foot' },
        mon.status ? h('span', { class: `status-tag ${mon.status}${newStatus ? ' pop' : ''}` }, STATUS_LABEL[mon.status] ?? mon.status) : null,
        h('span', { class: 'chips' }, ...boosts, ...extra),
        h('span', { class: 'hp-num' }, hpText)),
      moveStrip(mon, this.review.dex))
    this.inspectOn(box, mine ? this.me : this.them, mon)
    return box
  }

  /** The team as mini sprites (like Showdown's party icons); a Pokeball outline for one not
   *  seen yet. Each seen one opens its details in the docked panel. */
  private party(side: SideView) {
    const size = side.team_size ?? Math.max(6, side.team.length)
    const row = h('span', { class: 'party', 'aria-label': `${side.name}'s team` })
    const seen = side.team.filter(m => m.seen)
    for (let i = 0; i < size; i++) {
      const m = seen[i]
      if (!m) {
        row.append(h('span', { class: 'pmini unknown', title: 'Not seen yet', role: 'img', 'aria-label': 'Not seen yet' },
          h('img', { class: 'pmini-ball', src: '/sprites/item/poke-ball.png', alt: '', width: '24', height: '24' })))
        continue
      }
      const state = m.fainted ? 'fainted' : m.status ? 'status' : m.active ? 'active' : ''
      const label = `${m.species}${m.fainted ? ', fainted' : m.status ? `, ${STATUS_LABEL[m.status] ?? m.status}` : ''}`
      const b = h('button', { type: 'button', class: `pmini ${state}`, 'aria-label': label },
        sprite(m.sprite, false, '', 'pmini-img'),
        m.status && !m.fainted ? h('span', { class: `pmini-status ${m.status}`, 'aria-hidden': 'true' }) : null)
      this.inspectOn(b, side.id, m)
      row.append(b)
    }
    return row
  }

  private fieldTags(st: Step) {
    const view = st.state
    const tags: HTMLElement[] = []
    if (view.field.weather) tags.push(h('span', { class: 'tag weather' }, WEATHER_NAMES[view.field.weather] ?? titleCase(view.field.weather)))
    if (view.field.terrain) tags.push(h('span', { class: 'tag terrain' }, titleCase(view.field.terrain.replace('terrain', ' Terrain'))))
    const ROOMS: Record<string, string> = { trickroom: 'Trick Room', magicroom: 'Magic Room', wonderroom: 'Wonder Room',
      gravity: 'Gravity', mudsport: 'Mud Sport', watersport: 'Water Sport', fairylock: 'Fairy Lock', iondeluge: 'Ion Deluge' }
    for (const p of view.field.pseudo_weather) tags.push(h('span', { class: 'tag' }, ROOMS[p] ?? titleCase(p)))
    // Whole-field effects only; each side's conditions sit in that side's own row.
    return h('div', { class: 'field-tags' }, ...tags)
  }

  /** A side's conditions (hazards, screens, Tailwind) as tags in its own colour, placed in
   *  its row by its party icons: where they sit says whose side, no "(your side)" text. */
  private sideTags(side: SideView, mine: boolean) {
    return h('span', { class: 'side-tags' }, ...Object.entries(side.conditions).map(([c, layers]) =>
      h('span', { class: `tag ${mine ? 'mine' : 'theirs'}`, title: `${CONDITION_NAMES[c] ?? titleCase(c)} on ${mine ? 'your' : 'their'} side` },
        `${CONDITION_NAMES[c] ?? titleCase(c)}${layers > 1 ? ` ×${layers}` : ''}`)))
  }

  // ---------------------------------------------------------------- eval
  private renderEval(st: Step) {
    const v = st.eval
    if (!this.evalBar.firstChild) {
      this.evalBar.append(h('div', { class: 'eval-them' }), h('div', { class: 'eval-me' }), h('span', { class: 'eval-num' }))
    }
    const [them, me, num] = [...this.evalBar.children] as HTMLElement[]
    them.style.height = `${((1 - v) * 100).toFixed(1)}%`   // kept in place: the HP-bar transition runs
    me.style.height = `${(v * 100).toFixed(1)}%`
    num.textContent = pct(v)
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
          class: `gmark ${v}${this.revealGraph ? ' pop' : ''}`, style: `--i:${i}` }))
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
  // The turn rows rise in when the screen opens. The list is often rebuilt a moment later (the
  // saved review arrives), so a rebuild in the first half second keeps the entrance going.
  private markRowsEntering() {
    const t = performance.now() - this.openedAt
    if (!this.openedAt || t > 500) return
    ;[...this.turnList.children].forEach((li, i) => {
      const el = li as HTMLElement
      el.classList.add('enter'); el.style.setProperty('--i', String(Math.min(i, 12)))
      el.style.animationDelay = `${Math.max(0, Math.min(i, 12) * 25 + 120 - t)}ms`
    })
  }

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
    this.markRowsEntering()
  }

  private renderEvents(st: Step) {
    // No "Turn N" heading here: the turn list and the Turns header already say which turn.
    const tr = this.reviewFor(this.eventTurn(this.step))
    this.eventsBox.replaceChildren(
      ...(tr ? [this.reviewBox(tr)] : []),
      st.events.length
        ? h('ul', { class: this.prevMons ? 'play' : '' }, ...st.events.map((e, i) =>
          h('li', { class: `ev ${e.kind} ${e.side === this.me ? 'mine' : e.side === this.them ? 'theirs' : ''}`, style: `--i:${Math.min(i, 8)}` }, e.text)))
        : h('p', { class: 'muted' }, 'Nothing happened.'))
  }
}

interface MonSnap { frac: number; active: boolean; fainted: boolean; status: string | null; boosts: Record<string, number>
  sprite: string; position: number | null }
const monKey = (side: string, m: Mon) => `${side}|${m.name}|${m.species.split('-')[0]}`
function snapMons(st: Step | undefined): Map<string, MonSnap> {
  const out = new Map<string, MonSnap>()
  if (!st) return out
  for (const side of ['p1', 'p2'] as const) {
    for (const m of st.state.sides[side].team) {
      out.set(monKey(side, m), { frac: m.fainted ? 0 : m.hp / (m.maxhp || 100), active: m.active, fainted: m.fainted,
        status: m.status ?? null, boosts: { ...m.boosts }, sprite: m.sprite, position: m.position })
    }
  }
  return out
}

/** Formats that hand out teams (no team to paste). Everything else, VGC, OU and formats added
 *  later, gets the team paste. */
export function teamIsRandom(formatId: string): boolean {
  return /random|hackmonscup|challengecup|factory/.test(formatId.toLowerCase())
}

function clampStep(i: number, n: number) { return Math.max(0, Math.min(n - 1, Number.isFinite(i) ? i : 0)) }

// The router keeps one live screen so the key handler can reach it.
let current: { handleKey(e: KeyboardEvent): void } | null = null
export function reviewKeyHandler(e: KeyboardEvent) { current?.handleKey(e) }
export function setCurrent(screen: { handleKey(e: KeyboardEvent): void } | null) { current = screen }
export { ReviewScreen }
