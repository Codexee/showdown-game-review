// ==UserScript==
// @name         Showdown Game Review: save every battle
// @namespace    showdown-game-review.local
// @version      0.2.0
// @description  Uploads each battle you finish to Showdown's replay site (as the client's own button does) and sends it, and your private replay list, to the local Showdown Game Review app.
// @match        https://play.pokemonshowdown.com/*
// @grant        GM_xmlhttpRequest
// @grant        GM_getValue
// @grant        GM_setValue
// @grant        GM_registerMenuCommand
// @grant        unsafeWindow
// @connect      127.0.0.1
// @connect      localhost
// @connect      replay.pokemonshowdown.com
// @run-at       document-idle
// @noframes
// ==/UserScript==

/*
 * How it works (vault: spec-replay-sync, stage 2b)
 * - Wraps the client's message entry point: app.receive (old client, live in 2026-11)
 *   or PS.receive (new client, whose socket may live in a Web Worker). Every message
 *   passes through unchanged.
 * - Buffers each battle room's lines from |init|battle. On |win| or |tie| it waits a
 *   few seconds for the rating lines, then POSTs the log to the local server.
 *   A room that closes before the end is sent with incomplete=true.
 * - Your own |request| messages hold your full team; the last one is sent too.
 * - Auto-upload (on by default; toggle it in the Tampermonkey menu): after a battle you
 *   played ends, it sends `/savereplay silent` to the room, the same command as the
 *   client's "Upload and share replay" button, minus the popup. The server keeps the
 *   room's own privacy: a hidden battle (or one after /hidereplay) uploads as a private
 *   replay. Then it tells the local server, which downloads the replay (with the
 *   inputlog that move review needs) at once instead of waiting for the poller.
 *   Spectated battles are never uploaded.
 * - Every 15 minutes (and on load) it asks replay.pokemonshowdown.com for your private
 *   replays, using your browser's login, and sends only ids + passwords to the local
 *   server, which downloads them itself. Your password and cookies never leave the browser.
 * - If the local server is down, sends are queued in script storage and retried.
 */
(function () {
  'use strict';

  const SERVER = GM_getValue('serverUrl', 'http://127.0.0.1:8765');
  const SEND_DELAY_MS = 4000; // rating |raw| lines arrive just after |win|
  const PRIVATE_EVERY_MS = 15 * 60 * 1000;
  // After /savereplay: ask the local server to fetch the replay at these delays (from the
  // upload). One replay-server request each; stops at the first hit.
  const UPLOAD_CHECKS_MS = [8000, 30000, 120000];
  const MAX_QUEUE = 200;
  const W = typeof unsafeWindow !== 'undefined' ? unsafeWindow : window;
  const log = (...a) => console.debug('[showdown-game-review]', ...a);

  // ---------------------------------------------------------------- transport
  function post(path, body) {
    return new Promise((resolve, reject) => {
      GM_xmlhttpRequest({
        method: 'POST',
        url: SERVER + path,
        headers: { 'Content-Type': 'application/json' },
        data: JSON.stringify(body),
        timeout: 15000,
        onload: r => (r.status >= 200 && r.status < 300 ? resolve(r) : reject(new Error(`HTTP ${r.status}: ${r.responseText}`))),
        onerror: () => reject(new Error('network error')),
        ontimeout: () => reject(new Error('timeout')),
      });
    });
  }

  function getText(url) {
    return new Promise((resolve, reject) => {
      GM_xmlhttpRequest({
        method: 'GET',
        url,
        timeout: 15000,
        onload: r => resolve(r.responseText),
        onerror: () => reject(new Error('network error')),
        ontimeout: () => reject(new Error('timeout')),
      });
    });
  }

  // ---------------------------------------------------------------- retry queue
  const loadQueue = () => {
    try { return JSON.parse(GM_getValue('queue', '[]')); } catch { return []; }
  };
  const saveQueue = q => GM_setValue('queue', JSON.stringify(q.slice(-MAX_QUEUE)));

  async function send(path, body) {
    try {
      await post(path, body);
      return true;
    } catch (e) {
      // 4xx means the server rejected it; retrying won't help.
      if (/^HTTP 4\d\d/.test(e.message)) { log('rejected', path, e.message); return false; }
      log('queued for retry', path, e.message);
      const q = loadQueue();
      q.push({ path, body });
      saveQueue(q);
      return false;
    }
  }

  async function flushQueue() {
    const q = loadQueue();
    if (!q.length) return;
    saveQueue([]);
    for (const item of q) await send(item.path, item.body);
  }

  // ---------------------------------------------------------------- settings
  const autoUploadOn = () => GM_getValue('autoUpload', true) !== false;
  function registerMenu() {
    if (typeof GM_registerMenuCommand !== 'function') return;
    const label = () => (autoUploadOn() ? '✓ ' : '✗ ') + 'Auto-upload replays (click to turn ' + (autoUploadOn() ? 'off' : 'on') + ')';
    GM_registerMenuCommand(label(), () => {
      GM_setValue('autoUpload', !autoUploadOn());
      log('auto-upload', autoUploadOn() ? 'on' : 'off');
      // Tampermonkey shows the new label after the next page load.
    });
  }

  // ---------------------------------------------------------------- battle capture
  // roomid -> { id, lines: [], request: obj|null, ended: bool, sent: bool, timer }
  const rooms = new Map();

  function currentUser() {
    try {
      if (W.app && W.app.user) return W.app.user.get('name') || W.app.user.get('userid') || '';
      if (W.PS && W.PS.user) return W.PS.user.name || W.PS.user.userid || '';
    } catch { /* client not ready */ }
    return '';
  }

  const toID = s => String(s || '').toLowerCase().replace(/[^a-z0-9]/g, '');

  /** True if the logged-in user is p1..p4 in this log (not a spectator). */
  function playedIn(lines) {
    const me = toID(currentUser());
    if (!me) return false;
    return lines.some(l => l.startsWith('|player|') && toID(l.split('|')[3]) === me);
  }

  function flushRoom(roomid, incomplete) {
    const room = rooms.get(roomid);
    if (!room || room.sent) return;
    clearTimeout(room.timer);
    room.sent = true;
    rooms.delete(roomid);
    if (!room.lines.some(l => l.startsWith('|player|'))) return; // never really started
    if (incomplete && !room.lines.some(l => l === '|start')) return;
    void send('/api/ingest', {
      roomid,
      log: room.lines.join('\n'),
      request: room.request,
      username: currentUser(),
      incomplete,
    });
    if (!incomplete && autoUploadOn() && playedIn(room.lines)) uploadReplay(roomid);
  }

  // ---------------------------------------------------------------- auto-upload
  /** Send a command to a room the way the client's own buttons do. */
  function sendToRoom(roomid, text) {
    const client = W.app || W.PS;
    const room = client && client.rooms && client.rooms[roomid];
    if (room && typeof room.send === 'function') { room.send(text); return true; }
    if (client && typeof client.send === 'function') { client.send(text, roomid); return true; } // both clients: send(msg, roomid)
    return false;
  }

  /** POST and return the parsed JSON body, or null if the local server is down. */
  async function postJSON(path, body) {
    try {
      const r = await post(path, body);
      try { return JSON.parse(r.responseText || '{}'); } catch { return {}; }
    } catch (e) {
      if (/^HTTP 4\d\d/.test(e.message)) { log('rejected', path, e.message); return {}; }
      return null;
    }
  }

  function uploadReplay(roomid) {
    if (!sendToRoom(roomid, '/savereplay silent')) { log('could not send /savereplay to', roomid); return; }
    log('uploading replay', roomid);
    let i = 0;
    const check = async () => {
      const res = await postJSON('/api/ingest-uploaded', { roomid });
      if (res === null) { // app not running: keep it for the next page load
        const q = loadQueue();
        q.push({ path: '/api/ingest-uploaded', body: { roomid } });
        saveQueue(q);
        return;
      }
      if (res.found) { log('replay saved by the app', roomid); return; }
      if (++i < UPLOAD_CHECKS_MS.length) { setTimeout(check, UPLOAD_CHECKS_MS[i] - UPLOAD_CHECKS_MS[i - 1]); return; }
      // Not public under this id: likely a private replay whose password the room id
      // didn't carry. Listing private replays finds it; the poller covers the rest.
      void syncPrivate();
    };
    setTimeout(check, UPLOAD_CHECKS_MS[0]);
  }

  function onMessage(data) {
    if (typeof data !== 'string' || !data.startsWith('>battle-')) return;
    const nl = data.indexOf('\n');
    const roomid = data.slice(1, nl < 0 ? undefined : nl).trim();
    const body = nl < 0 ? '' : data.slice(nl + 1);
    let room = rooms.get(roomid);
    for (const line of body.split('\n')) {
      if (line.startsWith('|init|battle')) {
        // A fresh full log (joining or reconnecting). Start over.
        if (room) clearTimeout(room.timer);
        room = { id: roomid, lines: [], request: null, ended: false, sent: false, timer: 0 };
        rooms.set(roomid, room);
        continue;
      }
      if (!room) continue; // joined mid-stream without |init|; ignore
      if (line.startsWith('|request|')) {
        const json = line.slice('|request|'.length);
        if (json) { try { room.request = JSON.parse(json); } catch { /* ignore */ } }
        continue;
      }
      if (line.startsWith('|deinit')) { flushRoom(room.id, !room.ended); return; }
      if (line.startsWith('|noinit|rename|')) {
        // A hidden battle is renamed at the end to battle-<format>-<n>-<password>pw
        // (Showdown rooms.ts setPrivate); later messages use the new id.
        const newid = line.split('|')[3];
        if (newid && newid.startsWith('battle-') && newid !== room.id) {
          rooms.delete(room.id);
          room.id = newid;
          rooms.set(newid, room);
        }
        continue;
      }
      room.lines.push(line);
      if (!room.ended && (line.startsWith('|win|') || line === '|tie' || line.startsWith('|tie|'))) {
        room.ended = true;
        const r = room;
        r.timer = setTimeout(() => flushRoom(r.id, false), SEND_DELAY_MS);
      }
    }
  }

  // ---------------------------------------------------------------- private replays
  async function syncPrivate() {
    const user = currentUser();
    if (!user) return;
    const uid = toID(user);
    let text;
    try {
      text = await getText(`https://replay.pokemonshowdown.com/api/replays/searchprivate?username=${encodeURIComponent(uid)}`);
    } catch (e) { log('private search failed', e.message); return; }
    if (!text || text[0] !== ']') { log('unexpected private search response', String(text).slice(0, 120)); return; }
    let results;
    try { results = JSON.parse(text.slice(1)); } catch { return; }
    if (!Array.isArray(results)) { log('private search:', results && results.actionerror); return; }
    const items = results.slice(0, 50).map(r => ({ id: r.id, password: r.password || null, uploadtime: r.uploadtime }));
    if (items.length) await send('/api/ingest-private', { username: user, items });
  }

  // ---------------------------------------------------------------- hook the client
  function hook() {
    const target = W.app && typeof W.app.receive === 'function' ? W.app
      : W.PS && typeof W.PS.receive === 'function' ? W.PS : null;
    if (!target) return false;
    if (target.receive.__showdownGameReview) return true;
    const original = target.receive;
    const wrapped = function (data) {
      try { onMessage(data); } catch (e) { log('capture error', e); }
      return original.apply(this, arguments);
    };
    wrapped.__showdownGameReview = true;
    target.receive = wrapped;
    log('hooked', target === W.app ? 'old client (app.receive)' : 'new client (PS.receive)');
    return true;
  }

  // Exposed for tests (server/tests run this file in Node with stubs).
  W.__showdownGameReview = { onMessage, flushRoom, rooms, syncPrivate, flushQueue, hook, uploadReplay };

  registerMenu();

  if (!hook()) {
    let tries = 0;
    const wait = setInterval(() => {
      if (hook() || ++tries > 120) clearInterval(wait); // give up after ~60 s
    }, 500);
  }
  void flushQueue();
  setTimeout(() => void syncPrivate(), 10000); // after login settles
  setInterval(() => { void flushQueue(); void syncPrivate(); }, PRIVATE_EVERY_MS);
})();
