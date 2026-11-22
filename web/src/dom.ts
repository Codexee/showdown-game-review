// Small DOM helpers. Text always goes in through textContent: player and Pokemon
// names come from other people.

type Child = Node | string | number | null | false | undefined

export function h<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  props: Record<string, string | undefined> = {},
  ...children: Child[]
): HTMLElementTagNameMap[K] {
  const el = document.createElement(tag)
  for (const [k, v] of Object.entries(props)) if (v !== undefined) el.setAttribute(k, v)
  for (const c of children) if (c !== null && c !== false && c !== undefined) el.append(typeof c === 'number' ? String(c) : c)
  return el
}

const SVG_NS = 'http://www.w3.org/2000/svg'
export function s<K extends keyof SVGElementTagNameMap>(
  tag: K, attrs: Record<string, string | number> = {}, ...children: (SVGElement | string)[]
): SVGElementTagNameMap[K] {
  const el = document.createElementNS(SVG_NS, tag)
  for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, String(v))
  for (const c of children) el.append(c)
  return el
}

export const fmtDate = (t: number | null | undefined) =>
  t ? new Date(t * 1000).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' }) : 'Unknown date'

export function fmtAgo(t: number | null | undefined): string {
  if (!t) return 'never'
  const sec = Math.round(Date.now() / 1000 - t)
  if (sec < 60) return 'just now'
  if (sec < 3600) return `${Math.round(sec / 60)} min ago`
  if (sec < 86400) return `${Math.round(sec / 3600)} h ago`
  return fmtDate(t)
}

export const pct = (x: number) => `${Math.round(x * 100)}%`

// One status line per page, read out by screen readers.
export const statusLine = h('p', { class: 'status', role: 'status', 'aria-live': 'polite' })
export function say(msg: string, kind: 'ok' | 'error' = 'ok') {
  statusLine.textContent = msg
  statusLine.dataset.kind = kind
}
export const errText = (err: unknown) => (err instanceof Error ? err.message : String(err))

export function sprite(id: string, back: boolean, alt: string, cls = 'sprite'): HTMLImageElement {
  const img = h('img', {
    class: cls, alt, loading: 'lazy', decoding: 'async', width: '96', height: '96',
    src: `/sprites/${back ? 'gen5-back' : 'gen5'}/${encodeURIComponent(id)}.png`,
  })
  img.addEventListener('error', () => img.classList.add('missing'), { once: true })
  return img
}
