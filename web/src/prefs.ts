// Display switches in the top right: dark/light theme and motion on/off. Saved per browser;
// until the user picks, they follow the system settings (index.html sets them before paint).
import { h } from './dom'
import { icon } from './list'
import { toggle } from './switch'

const KEY = { theme: 'sr-theme', motion: 'sr-motion' }
const root = document.documentElement
const saved = (k: string) => { try { return localStorage.getItem(k) } catch { return null } }
const save = (k: string, v: string) => { try { localStorage.setItem(k, v) } catch { /* private mode: not saved */ } }

export function prefsBar(): HTMLElement {
  const theme = toggle('Dark mode', () => root.dataset.theme === 'dark', on => {
    root.dataset.theme = on ? 'dark' : 'light'
    save(KEY.theme, root.dataset.theme)
  }, icon('sun', ''), icon('moon', ''))
  const motion = toggle('Motion', () => root.dataset.motion !== 'off', on => {
    root.dataset.motion = on ? 'on' : 'off'
    save(KEY.motion, root.dataset.motion)
  }, icon('motion', ''))
  // Follow the system while the user hasn't chosen.
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
    if (!saved(KEY.theme)) { root.dataset.theme = e.matches ? 'dark' : 'light'; theme.sync() }
  })
  window.matchMedia('(prefers-reduced-motion: reduce)').addEventListener('change', e => {
    if (!saved(KEY.motion)) { root.dataset.motion = e.matches ? 'off' : 'on'; motion.sync() }
  })
  return h('div', { class: 'prefs', role: 'group', 'aria-label': 'Display' }, theme.el, motion.el)
}
