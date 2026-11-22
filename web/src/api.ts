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
  saveTeam: (id: string, paste: string) =>
    call<{ ok: boolean }>(`/api/games/${encodeURIComponent(id)}/team`, json('PUT', { paste })),
  importUrl: (url: string) => call<{ id: string; added: boolean }>('/api/import/url', json('POST', { url })),
  importFile: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return call<{ id: string; added: boolean }>('/api/import/file', { method: 'POST', body: form })
  },
}
