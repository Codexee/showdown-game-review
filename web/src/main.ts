// Router: #/ is the games page, #/game/<id>[/<step>] is the review screen.
// DotGothic16: a Japanese dot-matrix gothic, close to the type DS games used, with
// unambiguous digits (Pixelify Sans was tried first: its 5 reads as S, its C as O).
import '@fontsource/dotgothic16/latin-400.css'
import '@fontsource/atkinson-hyperlegible/400.css'
import '@fontsource/atkinson-hyperlegible/700.css'
import './style.css'
import { h, statusLine } from './dom'
import { renderList } from './list'
import { prefsBar } from './prefs'
import { renderReview, reviewKeyHandler, setCurrent } from './review'

const app = document.querySelector<HTMLDivElement>('#app')!
const view = h('div', { class: 'view' })
app.append(prefsBar(), statusLine, view)

function route() {
  const m = location.hash.match(/^#\/game\/([^/]+)(?:\/(\d+))?$/)
  statusLine.textContent = ''
  if (m) {
    document.body.dataset.page = 'review'
    void renderReview(view, decodeURIComponent(m[1]), m[2] ? Number(m[2]) : null)
  } else {
    document.body.dataset.page = 'list'
    setCurrent(null)
    void renderList(view)
  }
  window.scrollTo(0, 0)
}

let lastGame = ''
window.addEventListener('hashchange', () => {
  // Stepping through turns rewrites the hash with replaceState (no event); a real
  // navigation changes the game or the page.
  const game = location.hash.match(/^#\/game\/([^/]+)/)?.[1] ?? ''
  if (game !== lastGame || !game) { lastGame = game; route() }
})
document.addEventListener('keydown', reviewKeyHandler)
lastGame = location.hash.match(/^#\/game\/([^/]+)/)?.[1] ?? ''
route()
