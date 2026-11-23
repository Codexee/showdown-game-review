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

function sandbox({ client = 'old', serverUp = true, privateResponse = ']' + '[]', uploaded = () => ({ found: true }),
                   store: initial = {} } = {}) {
  const posts = []
  const gets = []
  const timers = []
  const store = new Map(Object.entries(initial))
  const received = []
  const sent = [] // [roomid, text] commands the script sent to Showdown
  const receive = function (data) { received.push(data) }
  const rooms = {}
  // Both clients keep rooms by id; a room's send(text) goes to that room, and the client's
  // send(text, roomid) is the fallback (old client.js app.send, new client-main.ts PS.send).
  const addRoom = id => { rooms[id] = { send: text => sent.push([id, text]) } }
  const clientSend = (text, roomid) => sent.push([roomid, text])
  const win = {}
  if (client === 'old') win.app = { receive, rooms, send: clientSend, user: { get: k => (k === 'name' ? 'Codexe' : 'codexe') } }
  else win.PS = { receive, rooms, send: clientSend, user: { name: 'Codexe', userid: 'codexe' } }
  let uploadCalls = 0
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
      const reply = req.url.endsWith('/api/ingest-uploaded') ? uploaded(uploadCalls++) : {}
      req.onload({ status: 200, responseText: JSON.stringify(reply) })
    },
  }
  vm.createContext(ctx)
  vm.runInContext(SCRIPT, ctx)
  timers.length = 0 // drop the start-up private listing; tests call syncPrivate() themselves
  const runTimers = () => { while (timers.length) timers.shift().fn() }
  // Timers whose callbacks await a request schedule the next timer later: keep going.
  const settle = async () => { for (let i = 0; i < 10; i++) { runTimers(); await flush() } }
  return { win, posts, gets, store, received, sent, timers, addRoom, runTimers, settle, api: win.__showdownGameReview }
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
    const s = sandbox({ client, store: { autoUpload: false } }) // upload: see the auto-upload tests
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
  const s = sandbox({ serverUp: false, store: { autoUpload: false } })
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

// ---- auto-upload (2026-11-23): /savereplay silent after a game you played
const paths = s => s.posts.map(p => p.url.replace('http://127.0.0.1:8765', ''))

for (const client of ['old', 'new']) {
  test(`${client} client: a finished game you played is uploaded and fetched by the app`, async () => {
    const s = sandbox({ client })
    const roomid = `battle-${RB}`
    s.addRoom(roomid)
    feedBattle(s.win, roomid, fixture(RB).log)
    assert.deepEqual(s.sent, [], 'nothing before the rating lines')
    s.runTimers() // the 4 s wait after |win|
    assert.deepEqual(s.sent, [[roomid, '/savereplay silent']], "the client button's command, without the popup")
    await s.settle()
    assert.deepEqual(paths(s), ['/api/ingest', '/api/ingest-uploaded'])
    assert.deepEqual(s.posts[1].body, { roomid })
    assert.equal(s.gets.length, 0, 'found on the first check: no private listing')
  })
}

test('auto-upload: room object missing, falls back to the client send(text, roomid)', async () => {
  const s = sandbox({ client: 'new' })
  feedBattle(s.win, `battle-${RB}`, fixture(RB).log)
  s.runTimers()
  assert.deepEqual(s.sent, [[`battle-${RB}`, '/savereplay silent']])
})

test('auto-upload: retries until the replay exists, then stops', async () => {
  const s = sandbox({ uploaded: n => ({ found: n >= 1 }) })
  s.addRoom(`battle-${RB}`)
  feedBattle(s.win, `battle-${RB}`, fixture(RB).log)
  await s.settle()
  assert.deepEqual(paths(s), ['/api/ingest', '/api/ingest-uploaded', '/api/ingest-uploaded'])
  assert.equal(s.gets.length, 0)
})

test('auto-upload: never found publicly, lists private replays once', async () => {
  const s = sandbox({ uploaded: () => ({ found: false }) })
  s.addRoom(`battle-${RB}`)
  feedBattle(s.win, `battle-${RB}`, fixture(RB).log)
  await s.settle()
  assert.equal(paths(s).filter(p => p === '/api/ingest-uploaded').length, 3, 'three checks, no more')
  assert.deepEqual(s.gets, ['https://replay.pokemonshowdown.com/api/replays/searchprivate?username=codexe'])
})

test('auto-upload: a hidden battle renamed at the end uploads under its new (password) id', async () => {
  const s = sandbox()
  const oldId = `battle-${RB}`
  const newId = `${oldId}-abc123pw`
  s.addRoom(newId) // the client renames its own room object too
  const lines = fixture(RB).log.split('\n')
  const win = lines.findIndex(l => l.startsWith('|win|'))
  s.win.app.receive(`>${oldId}\n|init|battle\n` + lines.slice(0, win).join('\n'))
  s.win.app.receive(`>${oldId}\n|noinit|rename|${newId}|A vs. B`)
  s.win.app.receive(`>${newId}\n` + lines.slice(win).join('\n'))
  await s.settle()
  assert.deepEqual(s.sent, [[newId, '/savereplay silent']])
  assert.equal(s.posts[0].body.roomid, newId, 'one game, under the new id')
  assert.ok(s.posts[0].body.log.includes('|win|'), 'lines from both ids are kept')
  assert.ok(!s.posts[0].body.log.includes('|noinit|'))
  assert.deepEqual(s.posts[1].body, { roomid: newId })
})

test('auto-upload: spectated battles are saved but never uploaded', async () => {
  const s = sandbox()
  const log = fixture(RB).log.replaceAll('Codexe', 'SomeoneElse')
  s.addRoom(`battle-${RB}`)
  feedBattle(s.win, `battle-${RB}`, log)
  await s.settle()
  assert.deepEqual(s.sent, [])
  assert.deepEqual(paths(s), ['/api/ingest'])
})

test('auto-upload: turned off in settings, the game is still saved', async () => {
  const s = sandbox({ store: { autoUpload: false } })
  s.addRoom(`battle-${RB}`)
  feedBattle(s.win, `battle-${RB}`, fixture(RB).log)
  await s.settle()
  assert.deepEqual(s.sent, [])
  assert.deepEqual(paths(s), ['/api/ingest'])
})

test('auto-upload: unfinished games are not uploaded', async () => {
  const s = sandbox()
  s.addRoom('battle-gen9ou-77')
  s.win.app.receive('>battle-gen9ou-77\n|init|battle\n|player|p1|Codexe|1|\n|player|p2|B|2|\n|start\n|turn|1')
  s.win.app.receive('>battle-gen9ou-77\n|deinit')
  await s.settle()
  assert.deepEqual(s.sent, [])
})

test('auto-upload with the app down: Showdown still uploads, both sends are queued', async () => {
  const s = sandbox({ serverUp: false })
  s.addRoom(`battle-${RB}`)
  feedBattle(s.win, `battle-${RB}`, fixture(RB).log)
  await s.settle()
  assert.deepEqual(s.sent, [[`battle-${RB}`, '/savereplay silent']])
  const q = JSON.parse(s.store.get('queue'))
  assert.deepEqual(q.map(i => i.path), ['/api/ingest', '/api/ingest-uploaded'])
  assert.deepEqual(q[1].body, { roomid: `battle-${RB}` })
})
