#!/usr/bin/env node
// Replays a random-battle inputlog in Showdown's simulator and prints the TRUE battle
// state at the start of every turn (and at the end). This is the ground truth the
// Python log parser (server/battle/) is tested against, and the full-information
// training target from ADR-0009.
//
//   node tools/sim-states.cjs <built-showdown-dir> <replay.json>...
//
// Needs a checkout built at the commit named in the inputlog's >version line
// (see prototypes/inputlog-rebuild/README.md). One JSON line per replay on stdout.
'use strict';

const path = require('path');
const fs = require('fs');

const [simDir, ...files] = process.argv.slice(2);
if (!simDir || !files.length) {
  console.error('usage: node tools/sim-states.cjs <built-showdown-dir> <replay.json>...');
  process.exit(2);
}
const { BattleStream } = require(path.resolve(simDir, 'dist/sim/battle-stream.js'));

function nonzero(table) {
  const out = {};
  for (const [k, v] of Object.entries(table || {})) if (v) out[k] = v;
  return out;
}

function snapshotPokemon(p) {
  return {
    name: p.name,
    species: p.species.name,
    hp: p.hp,
    maxhp: p.maxhp,
    status: p.status || '',
    fainted: !!p.fainted,
    active: !!p.isActive,
    position: p.isActive ? p.position : null,
    boosts: p.isActive ? nonzero(p.boosts) : {},
    item: p.item || '',
    ability: p.ability || '',
    terastallized: p.terastallized || '',
    teraType: p.teraType || '',
    moves: p.baseMoveSlots.map(m => m.id),
    volatiles: p.isActive ? Object.keys(p.volatiles).sort() : [],
  };
}

function snapshot(battle) {
  return {
    turn: battle.turn,
    ended: !!battle.ended,
    weather: battle.field.weather || '',
    terrain: battle.field.terrain || '',
    pseudoWeather: Object.keys(battle.field.pseudoWeather).sort(),
    sides: battle.sides.map(side => ({
      id: side.id,
      name: side.name,
      sideConditions: Object.fromEntries(Object.entries(side.sideConditions)
        .map(([id, st]) => [id, st.layers || 1])),
      pokemon: side.pokemon.map(snapshotPokemon),
    })),
  };
}

async function states(replay) {
  const lines = replay.inputlog.split('\n').filter(l => l.startsWith('>'));
  const stream = new BattleStream({ noCatch: true });
  void (async () => { for await (const _ of stream) { /* discard output */ } })();
  const out = [];
  let lastTurn = -1;
  for (const line of lines) {
    await stream.write(line);
    const battle = stream.battle;
    if (battle && battle.turn !== lastTurn && battle.turn > 0 && !battle.ended) {
      lastTurn = battle.turn;
      out.push(snapshot(battle));
    }
    if (battle && battle.ended) break;
  }
  const battle = stream.battle;
  if (battle) out.push(snapshot(battle)); // final state
  return { id: replay.id, version: (replay.inputlog.match(/^>version (\w+)/) || [])[1] || null, states: out };
}

(async () => {
  for (const file of files) {
    const replay = JSON.parse(fs.readFileSync(file, 'utf8'));
    let result;
    try {
      result = await states(replay);
    } catch (err) {
      result = { id: replay.id, error: String(err && err.stack || err).split('\n').slice(0, 3).join(' | ') };
    }
    process.stdout.write(JSON.stringify(result) + '\n');
  }
})();
