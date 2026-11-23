// Runs the userscript in a sandbox with a fake Showdown client and fake GM_* APIs.
// Run: node --test userscript/
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import vm from 'node:vm'

const here = new URL('.', import.meta.url)
const SCRIPT = readFileSync(new URL('showdown-game-review.user.js', here), 'utf8')
const fixture = id => JSON.parse(readFileSync(new URL(`../server/tests/fixtures/${id}.json`, here), 'utf8'))
const RB = 'gen9randombattle-2705718015'

function sandbox({ client = 'old', serverUp = true, privateResponse = ']' + '[]' } = {}) {
  const posts = []
  const gets = []
  const timers = []
  const store = new Map()
  const received = []
  const receive = function (data) { received.push(data) }
  const win = {}
  if (client === 'old') win.app = { receive, user: { get: k => (k === 'name' ? 'Codexe' : 'codexe') } }
  else win.PS = { receive, user: { name: 'Codexe', userid: 'codexe' } }
  const ctx = {
    unsafeWindow: win,
    window: win,
    console: { debug() {}, log() {} },
    JSON, Promise, Map, Error, String, Array, encodeURIComponent,
    setTimeout: (fn, ms) => { timers.push({ fn, ms }); return timers.length },
    clearTimeout: () => {},
    setInterval: () => 1, // the client already exists, so the script hooks without waiting
    clearInterval: () => {},
    GM_getValue: (k, d) => (store.has(k) ? store.get(k) : d),
    GM_setValue: (k, v) => store.set(k, v),
    GM_xmlhttpRequest: req => {
      if (req.method === 'GET') {
        gets.push(req.url)
        req.onload({ status: 200, responseText: privateResponse })
        return
      }
      if (!serverUp) { req.onerror(); return }
      posts.push({ url: req.url, body: JSON.parse(req.data), headers: req.headers })
      req.onload({ status: 200, responseText: '{}' })
    },
  }
  vm.createContext(ctx)
  vm.runInContext(SCRIPT, ctx)
  const runTimers = () => { while (timers.length) timers.shift().fn() }
  return { win, posts, gets, store, received, runTimers, api: win.__showdownGameReview }
}

const flush = () => new Promise(r => setImmediate(r))

function feedBattle(win, roomid, log, { request = null, deinit = false } = {}) {
  const recv = (win.app || win.PS).receive.bind(win.app || win.PS)
  const lines = log.split('\n')
  const half = Math.floor(lines.length / 2)
  recv(`>${roomid}\n|init|battle\n|title|A vs. B\n` + lines.slice(0, half).join('\n'))
  if (request) recv(`>${roomid}\n|request|${JSON.stringify(request)}`)
  recv(`>${roomid}\n` + lines.slice(half).join('\n'))
  if (deinit) recv(`>${roomid}\n|deinit`)
}

for (const client of ['old', 'new']) {
  test(`${client} client: finished battle is sent once, after the rating lines`, async () => {
    const s = sandbox({ client })
    const roomid = `battle-${RB}`
    feedBattle(s.win, roomid, fixture(RB).log, { request: { side: { pokemon: [{ ident: 'p1: Dedenne' }] } } })
    assert.equal(s.received.length, 3, 'messages still reach the client')
    assert.equal(s.posts.length, 0, 'waits for the rating lines')
    s.runTimers()
    await flush()
    assert.equal(s.posts.length, 1)
    const { url, body, headers } = s.posts[0]
    assert.equal(url, 'http://127.0.0.1:8765/api/ingest')
    assert.equal(headers['Content-Type'], 'application/json')
    assert.equal(body.roomid, roomid)
    assert.equal(body.incomplete, false)
    assert.equal(body.username, 'Codexe')
    assert.ok(body.log.includes('|win|charizardslayer1'))
    assert.ok(body.log.includes("Codexe's rating: 1827"))
    assert.ok(!body.log.includes('|request|'))
    assert.equal(body.request.side.pokemon[0].ident, 'p1: Dedenne')
    s.win.__showdownGameReview.flushRoom(roomid, false)
    await flush()
    assert.equal(s.posts.length, 1, 'not sent twice')
  })
}

test('room closed before the end is sent as incomplete', async () => {
  const s = sandbox()
  const log = '|player|p1|Codexe|1|\n|player|p2|B|2|\n|start\n|turn|1\n|turn|2'
  s.win.app.receive(`>battle-gen9ou-77\n|init|battle\n${log}`)
  s.win.app.receive('>battle-gen9ou-77\n|deinit')
  await flush()
  assert.equal(s.posts.length, 1)
  assert.equal(s.posts[0].body.incomplete, true)
})

test('rooms that never started and non-battle rooms are ignored', async () => {
  const s = sandbox()
  s.win.app.receive('>lobby\n|c|someone|hi')
  s.win.app.receive('>battle-gen9ou-78\n|init|battle\n|j|someone')
  s.win.app.receive('>battle-gen9ou-78\n|deinit')
  await flush()
  assert.equal(s.posts.length, 0)
})

test('server down: battle is queued and sent on the next flush', async () => {
  const s = sandbox({ serverUp: false })
  feedBattle(s.win, `battle-${RB}`, fixture(RB).log)
  s.runTimers()
  await flush()
  assert.equal(s.posts.length, 0)
  assert.equal(JSON.parse(s.store.get('queue')).length, 1)
})

test('private replays: ids and passwords go to the server, nothing else', async () => {
  const results = [{ id: 'gen9ou-5', password: 'abc', uploadtime: 100, players: ['Codexe', 'x'], format: 'f' }]
  const s = sandbox({ privateResponse: ']' + JSON.stringify(results) })
  await s.api.syncPrivate()
  assert.equal(s.gets[0], 'https://replay.pokemonshowdown.com/api/replays/searchprivate?username=codexe')
  assert.deepEqual(s.posts[0].body, { username: 'Codexe', items: [{ id: 'gen9ou-5', password: 'abc', uploadtime: 100 }] })
})

test('private replays: logged out sends nothing', async () => {
  const s = sandbox({ privateResponse: ']{"actionerror":"Access denied: You must be logged in."}' })
  await s.api.syncPrivate()
  assert.equal(s.posts.length, 0)
})
