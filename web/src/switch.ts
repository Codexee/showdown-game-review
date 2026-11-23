// A switch (role="switch") with optional icons or text around a small pixel track.
import { h } from './dom'

export function toggle(label: string, isOn: () => boolean, set: (on: boolean) => void, ...icons: Element[]) {
  const knob = h('span', { class: 'switch-knob' })
  const btn = h('button', { type: 'button', role: 'switch', class: 'toggle-switch', 'aria-label': label, title: label },
    icons[0], h('span', { class: 'switch-track', 'aria-hidden': 'true' }, knob), icons[1] ?? null)
  const sync = () => btn.setAttribute('aria-checked', String(isOn()))
  btn.addEventListener('click', () => { set(!isOn()); sync() })
  sync()
  return { el: btn, sync }
}
