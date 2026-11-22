#!/usr/bin/env node
// Prototype for vault ADR-0009: rebuild a random-battle replay from its inputlog.
//
//   node rebuild.cjs <built-showdown-dir> <replay.json>...
//
// For each replay, runs Showdown's simulator (the checkout must be at the commit named
// in the inputlog's >version line) on the inputlog, then:
//   - compares the simulator's spectator log with the replay's public log, line by line,
//     ignoring lines the simulator never produces (chat, joins, timestamps, timer, ratings);
//   - extracts both players' full teams (moves, item, ability, Tera type, EVs, IVs, level).
// Prints one JSON object per replay on stdout.
'use strict';

const path = require('path');
const fs = require('fs');

const [simDir, ...files] = process.argv.slice(2);
if (!simDir || !files.length) {
  console.error('usage: node rebuild.cjs <built-showdown-dir> <replay.json>...');
  process.exit(2);
}
const { BattleStream } = require(path.resolve(simDir, 'dist/sim/battle-stream.js'));
const { extractChannelMessages } = require(path.resolve(simDir, 'dist/sim/battle.js'));

// Lines the server adds around the simulator's output (room/chat/timer/ladder).
const SERVER_ONLY = new Set([
  'j', 'J', 'l', 'L', 'n', 'N', 'c', 'c:', 'chat', 't:', 'raw', 'html', 'uhtml', 'inactive',
  'inactiveoff', 'b', 'B', 'title', 'init', 'expire', 'notify', 'hidelines', 'unlink', 'zbreak', 'debug',
  'badge', // ladder badge shown at battle start
  '',      // ||text: room messages, e.g. "X is ready for game 2." in best-of-3
]);
// The server, not the simulator, writes these -message lines when a game ends early.
const SERVER_MESSAGE = /^\|-message\|.*(forfeited\.|lost due to inactivity\.|left the battle\.)$/;

function battleLines(log) {
  let started = false;
  return log.split('\n').filter(line => {
    if (!line.startsWith('|') || line === '|') return false;
    const parts = line.split('|');
    if (parts[1] === 'start') started = true;
    if (SERVER_ONLY.has(parts[1])) return false;
    if (SERVER_MESSAGE.test(line)) return false;
    // After |start, |player| lines are the server announcing a leave (no name) or a
    // rejoin (name again), not battle events.
    if (parts[1] === 'player' && (started || !parts[3])) return false;
    return true;
  });
}

// |player|p1|Name|avatar|rating: the server fills avatar/rating; compare only side + name.
const norm = line => (line.startsWith('|player|') ? line.split('|').slice(0, 4).join('|') : line);

async function rebuild(replay) {
  const inputlog = replay.inputlog;
  const version = (inputlog.split('\n')[0].match(/^>version (\w+)/) || [])[1] || null;
  const stream = new BattleStream({ noCatch: true });
  // Drain output so the stream doesn't block.
  void (async () => { for await (const _ of stream) { /* discard */ } })();
  await stream.write(inputlog);
  const battle = stream.battle;
  const full = battle.log.join('\n');
  const spectator = extractChannelMessages(full, [0])[0].join('\n');

  // Uploaded replay logs show exact HP for both sides (checked on gen9randombattle-2717776712),
  // so compare against the omniscient channel (-1); fall back to the spectator channel.
  const omniscient = extractChannelMessages(full, [-1])[-1].join('\n');
  const want = battleLines(replay.log).map(norm);
  const viaOmni = battleLines(omniscient).map(norm);
  const viaSpec = battleLines(spectator).map(norm);
  const firstMismatch = got => {
    for (let i = 0; i < Math.max(want.length, got.length); i++) if (want[i] !== got[i]) return i;
    return -1;
  };
  const omniAt = firstMismatch(viaOmni);
  const specAt = firstMismatch(viaSpec);
  const channel = omniAt === -1 || (specAt !== -1 && omniAt >= specAt) ? 'omniscient' : 'spectator';
  const got = channel === 'omniscient' ? viaOmni : viaSpec;
  let firstDiff = null;
  for (let i = 0; i < Math.max(want.length, got.length); i++) {
    if (want[i] !== got[i]) {
      firstDiff = { index: i, replay: want[i] ?? null, sim: got[i] ?? null,
        context: want.slice(Math.max(0, i - 2), i) };
      break;
    }
  }
  const teams = battle.sides.map(side => side.team.map(set => ({
    species: set.species, level: set.level, item: set.item, ability: set.ability,
    teraType: set.teraType, moves: set.moves, evs: set.evs, ivs: set.ivs, gender: set.gender,
  })));
  return {
    id: replay.id,
    version,
    match: firstDiff === null,
    channel,
    lines: { replay: want.length, sim: got.length },
    firstDiff,
    winner: battle.winner,
    turns: battle.turn,
    teams,
  };
}

(async () => {
  for (const file of files) {
    const replay = JSON.parse(fs.readFileSync(file, 'utf8'));
    let out;
    try {
      out = await rebuild(replay);
    } catch (err) {
      out = { id: replay.id, match: false, error: String(err && err.stack || err).split('\n').slice(0, 3).join(' | ') };
    }
    process.stdout.write(JSON.stringify(out) + '\n');
  }
})();
