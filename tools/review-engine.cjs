#!/usr/bin/env node
// Simulator side of move review (roadmap stage 6, vault benchmark-best-in-class P1).
// A JSON-lines service on stdin/stdout, driven by server/review/engine.py.
//
//   node tools/review-engine.cjs <built-showdown-dir>
//
// Requests (one JSON object per line), each answered by one JSON line:
//   {"cmd":"load","inputlog":"..."}
//       Replays a random-battle inputlog (at the commit it names; the caller picks the
//       checkout). For every turn start it keeps a serialized copy of the battle, the
//       legal choices of each side and the choice each side actually made.
//       -> {"turns":[{"turn":t,"options":{"p1":[...],"p2":[...]},"played":{"p1":"move 2","p2":"switch 3"}}],
//           "winner":"name"|null}
//   {"cmd":"expand","turn":t,"pairs":[["move 1","switch 3"],...],"seeds":16}
//       For each pair and seed: restore the turn-start copy, reseed the dice, make both
//       choices and play to the next decision. When a side must replace a fainted
//       Pokemon, every replacement is a separate branch (the caller lets that side pick).
//       -> {"cells":[{"pair":i,"seed":k,"invalid":bool,"branches":[{"switch":{"side":"p1","choice":"switch 4"}|null,
//            "lines":[...omniscient protocol lines of the step...],"ended":bool,"winner":"name"|null}]}]}
//   {"cmd":"quit"}
'use strict';

const path = require('path');
const crypto = require('crypto');
const readline = require('readline');

const simDir = process.argv[2];
if (!simDir) {
  console.error('usage: node tools/review-engine.cjs <built-showdown-dir>');
  process.exit(2);
}
const { BattleStream } = require(path.resolve(simDir, 'dist/sim/battle-stream.js'));
const { extractChannelMessages } = require(path.resolve(simDir, 'dist/sim/battle.js'));
const { State } = require(path.resolve(simDir, 'dist/sim/state.js'));
const { PRNG } = require(path.resolve(simDir, 'dist/sim/prng.js'));

const MAX_BRANCH_STEPS = 6; // safety: forced switches after forced switches

let turns = new Map(); // turn -> {state, options, played}
let finalWinner = null;

function seedFor(k) {
  return 'sodium,' + crypto.createHash('sha256').update('review-seed-' + k).digest('hex').slice(0, 32);
}

function optionsFor(side) {
  const req = side.activeRequest;
  if (!req || req.wait || req.forceSwitch || !req.active) return [];
  const active = req.active[0];
  const out = [];
  const moves = active.moves || [];
  moves.forEach((m, i) => {
    if (m.disabled) return;
    out.push(`move ${i + 1}`);
    if (active.canTerastallize) out.push(`move ${i + 1} terastallize`);
  });
  if (!active.trapped && !active.maybeTrapped) {
    req.side.pokemon.forEach((p, i) => {
      if (i === 0 || p.active || p.condition.endsWith(' fnt')) return;
      out.push(`switch ${i + 1}`);
    });
  }
  return out;
}

// The client sends choices as e.g. "move uturn", "move 2 terastallize", "switch 3" or
// "team ..."; turn them into the option format "move N[ terastallize]" / "switch N".
function normalize(side, raw) {
  const text = raw.replace(/\s+/g, ' ').trim().toLowerCase();
  const tera = /\bterastallize\b/.test(text);
  const rest = text.replace(/\bterastallize\b/, '').trim();
  const m = rest.match(/^(move|switch) (.+?)( [-+]?\d+)?$/);
  if (!m) return text;
  if (m[1] === 'switch') {
    if (/^\d+$/.test(m[2])) return `switch ${m[2]}`;
    const i = side.activeRequest.side.pokemon.findIndex(p => p.ident.split(': ')[1].toLowerCase().replace(/[^a-z0-9]/g, '') === m[2].replace(/[^a-z0-9]/g, ''));
    return i >= 0 ? `switch ${i + 1}` : text;
  }
  let idx = /^\d+$/.test(m[2]) ? Number(m[2]) : 0;
  if (!idx) {
    const id = m[2].replace(/[^a-z0-9]/g, '');
    const moves = side.activeRequest.active[0].moves;
    idx = moves.findIndex(mv => mv.id === id || mv.move.toLowerCase().replace(/[^a-z0-9]/g, '') === id) + 1;
  }
  return idx ? `move ${idx}${tera ? ' terastallize' : ''}` : text;
}

// What each option means, for labels and for mapping to the policy: the active
// Pokemon's move ids and names, and the nickname / species of each team slot.
function choiceInfo(side) {
  const req = side.activeRequest;
  const active = req.active ? req.active[0] : { moves: [] };
  return {
    moves: (active.moves || []).map(m => ({ id: m.id, name: m.move })),
    team: req.side.pokemon.map(p => ({ name: p.ident.split(': ')[1], species: p.details.split(',')[0] })),
    canTera: active.canTerastallize || null,
  };
}

function omniLines(battle, from) {
  const chunk = battle.log.slice(from).join('\n');
  return extractChannelMessages(chunk, [-1])[-1];
}

async function load(inputlog) {
  turns = new Map();
  finalWinner = null;
  const stream = new BattleStream({ noCatch: true });
  void (async () => { for await (const _ of stream) { /* discard */ } })();
  let recorded = -1;
  for (const line of inputlog.split('\n')) {
    if (!line.startsWith('>')) continue;
    const battle = stream.battle;
    if (battle && !battle.ended && battle.turn > 0 && battle.turn !== recorded &&
        battle.sides.every(s => s.activeRequest && !s.activeRequest.wait && !s.activeRequest.forceSwitch)) {
      recorded = battle.turn;
      turns.set(battle.turn, {
        // A JSON string: State.deserializeBattle modifies an object passed to it, so every
        // restore must start from a fresh parse.
        state: JSON.stringify(State.serializeBattle(battle)),
        options: { p1: optionsFor(battle.sides[0]), p2: optionsFor(battle.sides[1]) },
        info: { p1: choiceInfo(battle.sides[0]), p2: choiceInfo(battle.sides[1]) },
        played: {},
      });
    }
    const m = line.match(/^>(p[12]) (.*)$/);
    if (m && battle && turns.has(battle.turn)) {
      const side = battle.sides[m[1] === 'p1' ? 0 : 1];
      const entry = turns.get(battle.turn);
      if (m[2] === 'undo') delete entry.played[m[1]];
      else if (side.requestState === 'move') entry.played[m[1]] = normalize(side, m[2]);
    }
    await stream.write(line);
  }
  const battle = stream.battle;
  finalWinner = battle && battle.ended ? (battle.winner || null) : null;
  return {
    turns: [...turns.entries()].map(([turn, e]) => ({ turn, options: e.options, info: e.info, played: e.played })),
    winner: finalWinner,
  };
}

function pendingSwitch(battle) {
  for (const side of battle.sides) {
    const req = side.activeRequest;
    if (req && req.forceSwitch && req.forceSwitch.some(Boolean)) return side;
  }
  return null;
}

function forcedOptions(side) {
  const req = side.activeRequest;
  return req.side.pokemon
    .map((p, i) => (i > 0 && !p.active && !p.condition.endsWith(' fnt') ? `switch ${i + 1}` : null))
    .filter(Boolean);
}

function settle(battle) {
  // After the turn's choices: resolve any further forced switches with the default pick
  // until both sides face a normal decision or the game ends.
  for (let i = 0; i < MAX_BRANCH_STEPS && !battle.ended; i++) {
    const side = pendingSwitch(battle);
    if (!side) return;
    if (!battle.choose(side.id, 'default')) return;
  }
}

function expand(turn, pairs, seeds) {
  const entry = turns.get(turn);
  if (!entry) return { error: `no turn ${turn}` };
  const cells = [];
  pairs.forEach(([c1, c2], pi) => {
    for (let k = 0; k < seeds; k++) {
      const battle = State.deserializeBattle(entry.state);
      battle.prng = new PRNG(seedFor(k));
      const start = battle.log.length;
      let ok = false;
      try {
        ok = battle.choose('p1', c1) && battle.choose('p2', c2);
      } catch (e) {
        ok = false;
      }
      if (!ok) { cells.push({ pair: pi, seed: k, invalid: true, branches: [] }); continue; }
      const branches = [];
      const side = !battle.ended && pendingSwitch(battle);
      if (side) {
        const mid = JSON.stringify(State.serializeBattle(battle));
        const prngSeed = battle.prng.getSeed();
        for (const choice of forcedOptions(side)) {
          const b = State.deserializeBattle(mid);
          b.prng = new PRNG(prngSeed);
          if (!b.choose(side.id, choice)) continue;
          settle(b);
          branches.push({ switch: { side: side.id, choice }, lines: omniLines(b, start), ended: !!b.ended, winner: b.winner || null });
        }
      } else {
        branches.push({ switch: null, lines: omniLines(battle, start), ended: !!battle.ended, winner: battle.winner || null });
      }
      cells.push({ pair: pi, seed: k, invalid: false, branches });
    }
  });
  return { cells };
}

const rl = readline.createInterface({ input: process.stdin });
rl.on('line', async (raw) => {
  let req;
  try { req = JSON.parse(raw); } catch { process.stdout.write(JSON.stringify({ error: 'bad json' }) + '\n'); return; }
  let res;
  try {
    if (req.cmd === 'load') res = await load(req.inputlog);
    else if (req.cmd === 'expand') res = expand(req.turn, req.pairs, req.seeds || 16);
    else if (req.cmd === 'quit') { process.exit(0); }
    else res = { error: `unknown cmd ${req.cmd}` };
  } catch (e) {
    res = { error: String(e && e.stack || e).split('\n').slice(0, 3).join(' | ') };
  }
  process.stdout.write(JSON.stringify(res) + '\n');
});
