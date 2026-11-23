// Typed calls to the local FastAPI server (server/app.py).

export type Result = 'win' | 'loss' | 'tie' | null

export interface Game {
  id: string
  format_id: string
  format: string
  p1: string
  p2: string
  played_at: number | null
  uploadtime: number | null
  private: boolean
  has_inputlog: boolean
  source: 'poller' | 'url' | 'upload' | 'userscript'
  has_team_paste: boolean
  turns: number
  gametype: string
  user_side: 'p1' | 'p2' | null
  opponent: string | null
  result: Result
  rating_before: number | null
  rating_after: number | null
  teams: { p1: string[]; p2: string[] }
  analyzed: boolean
}

export interface GameDetail extends Game {
  log: string
  inputlog: string | null
  team_paste: string | null
}

export interface Settings {
  username: string
  poll_minutes: number
  sync_start: number | null
  last_sync: number | null
  last_ingest: number | null
  last_ingest_private: number | null
  poller_enabled: boolean
}

export interface SyncResult {
  username: string
  started_at: number
  first_sync: boolean
  seen: number
  added: string[]
  errors: string[]
  profile_ok: boolean
}

export interface Rating {
  elo: number
  gxe: number
  w: number
  l: number
}

export interface Profile {
  username: string
  ratings: Record<string, Rating>
}

export interface Mon {
  name: string
  species: string
  sprite: string
  level: number
  hp: number
  maxhp: number
  hp_exact: boolean
  status: string
  fainted: boolean
  active: boolean
  position: number | null
  seen: boolean
  boosts: Record<string, number>
  volatiles: string[]
  item: string | null
  ability: string | null
  moves: string[]
  tera_type: string
}

export interface SideView {
  id: 'p1' | 'p2'
  name: string
  team_size: number | null
  team: Mon[]
  conditions: Record<string, number>
}

export interface BattleView {
  turn: number
  gametype: string
  sides: { p1: SideView; p2: SideView }
  field: { weather: string; terrain: string; pseudo_weather: string[] }
  ended: boolean
  winner: string | null
  perspective: 'p1' | 'p2'
}

export interface BattleEvent {
  text: string
  side: 'p1' | 'p2' | null
  kind: string
}

export interface Step {
  turn: number
  ended: boolean
  state: BattleView
  events: BattleEvent[]
  eval: number
  eval_model?: number   // when eval blends in the move review's search (eval_method 'model+search')
  eval_search?: number
}

export interface Review {
  game: Game & { team_paste: string | null }
  perspective: 'p1' | 'p2'
  format_id: string
  eval_method: string
  eval_method_text: string
  steps: Step[]
  warnings: string[]
}

export type Verdict = 'best' | 'good' | 'inaccuracy' | 'mistake' | 'blunder' | 'forced' | 'no blame'

export interface SideReview {
  options: { choice: string; label: string; value: number; mix: number }[]
  best: string
  best_label: string
  best_value: number
  played?: string
  played_label?: string
  played_value?: number
  regret?: number
  verdict?: Verdict
  no_blame?: string
}

export interface TurnReview {
  turn: number
  value_before: number
  value_after: number
  equilibrium: number
  expected_after?: number
  luck_p1?: number
  sides: { p1?: SideReview; p2?: SideReview }
}

export interface PlayerSummary {
  name: string
  graded_turns: number
  counts: Record<'best' | 'good' | 'inaccuracy' | 'mistake' | 'blunder', number>
  accuracy: number | null
  avg_regret: number | null
  luck_points: number
  worst: { turn: number; played: string; best: string; regret: number }[]
}

export interface Analysis {
  status: 'none' | 'queued' | 'running' | 'done' | 'error' | 'unsupported'
  progress?: [number, number]
  error?: string
  stale?: boolean
  result?: {
    turns: TurnReview[]
    summary: { p1: PlayerSummary; p2: PlayerSummary; biggest_luck: { turn: number; luck_p1_points: number }[] }
    seeds: number
    mode?: 'worlds' | 'perfect'
    model: string
    seconds: number
  }
}

export interface FormatCount {
  format_id: string
  format: string
  n: number
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, init)
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`
    try {
      const body = await res.json()
      if (body?.detail) detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
    } catch {
      /* not JSON */
    }
    throw new Error(detail)
  }
  return res.json() as Promise<T>
}

const json = (method: string, body: unknown): RequestInit => ({
  method,
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
})

export const api = {
  settings: () => call<Settings>('/api/settings'),
  saveSettings: (s: Partial<Pick<Settings, 'username' | 'poll_minutes'>>) =>
    call<Settings>('/api/settings', json('PUT', s)),
  profile: (refresh = false) => call<Profile>(`/api/profile${refresh ? '?refresh=true' : ''}`),
  sync: () => call<SyncResult>('/api/sync', { method: 'POST' }),
  formats: () => call<FormatCount[]>('/api/formats'),
  games: (q: { format?: string; result?: string; opponent?: string }) => {
    const p = new URLSearchParams()
    for (const [k, v] of Object.entries(q)) if (v) p.set(k, v)
    return call<Game[]>(`/api/games?${p}`)
  },
  game: (id: string) => call<GameDetail>(`/api/games/${encodeURIComponent(id)}`),
  review: (id: string, side?: 'p1' | 'p2') =>
    call<Review>(`/api/games/${encodeURIComponent(id)}/review${side ? `?side=${side}` : ''}`),
  analysis: (id: string) => call<Analysis>(`/api/games/${encodeURIComponent(id)}/analysis`),
  analyze: (id: string) => call<Analysis>(`/api/games/${encodeURIComponent(id)}/analysis`, json('POST', {})),
  saveTeam: (id: string, paste: string) =>
    call<{ ok: boolean }>(`/api/games/${encodeURIComponent(id)}/team`, json('PUT', { paste })),
  importUrl: (url: string) => call<{ id: string; added: boolean }>('/api/import/url', json('POST', { url })),
  importFile: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return call<{ id: string; added: boolean }>('/api/import/file', { method: 'POST', body: form })
  },
}
