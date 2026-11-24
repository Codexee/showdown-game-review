# showdown-game-review

chess.com game review for [Pokémon Showdown](https://pokemonshowdown.com). Runs locally

# Features
- Auto-saves uploaded replays by username with an optional browser script that saves all games
- Replays games in a custom UI with eval bar and win graph
- Grades choices by change in win chance, accounting for luck, and gives each player an accuracy score (currently limited to gen9randombattle)

# Planned Features
- Move analysis for every gamemode
- Evaluation for every game mode
- Guessing sets from turn order and damage rolls

## Quick start

You need [uv](https://docs.astral.sh/uv/), [Node.js](https://nodejs.org) 20 or newer, and git. macOS or Linux.

```bash
git clone https://github.com/Codexee/showdown-game-review.git
cd showdown-game-review
./start.sh
```

The first run of `start.sh` runs `setup.sh`, which installs the Python packages (uv fetches Python 3.13 itself; PyTorch is a few hundred MB) and builds the web app. Then the app opens at <http://127.0.0.1:8765>. Enter your Showdown username and press **Sync**.

## Win-chance model

The eval bar and move review use a small network trained on Random Battle replays. `setup.sh` downloads the published one from the [latest release](https://github.com/Codexee/showdown-game-review/releases/latest) (28 MB, checked against its SHA-256; skip with `NO_MODEL=1`). It calls the winner from each turn 68% of the time on games it never saw, against 63% for a remaining-HP estimate. To update an existing install to a newer release, delete `data/models/current.pt` and run `./setup.sh` again. Without a model, the eval bar falls back to that estimate and move review is off.

Training your own takes some disk space (tens of GB) and hours on a laptop GPU:

```bash
uv sync                                    # adds the dev tools
./training/download_hf.sh                  # public Showdown replay logs from Hugging Face
uv run python -m training.collect --days 14   # recent replays with full battle data, for testing
RUN=my-model ./training/overnight.sh       # build the dataset, train, test, install if better
```

`overnight.sh` installs the model to `data/models/current.pt` only if it beats the one already installed. The full pipeline, its options and the test bank are described in `vault/specs/spec-eval-model.md`. The first move review also downloads and builds Showdown's simulator at the replay's version, which takes a minute.

## Save every battle (optional)

Install [Tampermonkey](https://www.tampermonkey.net/), then open the app's **Auto-save every battle** section and install the userscript. With the app running, each battle you play on play.pokemonshowdown.com is saved a few seconds after it ends. It only sends battle logs to the app on your computer, and your Showdown login stays in your browser.

## What's where

| Path | What |
|---|---|
| `server/` | FastAPI app: archive (SQLite), sync, parser, review endpoints |
| `server/review/` | Move review: choice matrices on the real simulator, sampled hidden sets |
| `web/` | The UI (Vite + TypeScript, no framework) |
| `training/` | Dataset building, training, testing and the install gate |
| `userscript/` | The Tampermonkey script |
| `vault/` | Project notes and decisions (an Obsidian vault) |
| `data/` | Your games, sprites cache and models (not in git) |

Settings via environment variables: `SGR_DATA_DIR`, `SGR_USERNAME`, `SGR_POLL_MINUTES`, `SGR_REQUEST_DELAY`, `SGR_POLLER=0` (turns the background sync off).

## Tests

```bash
uv sync && uv run python -m pytest server/tests
node --test userscript/userscript.test.mjs
```

## Credits

Battle data and sprites come from [Pokémon Showdown](https://github.com/smogon/pokemon-showdown); Random Battle set odds from [pkmn/randbats](https://data.pkmn.cc). Pokémon and its sprites are © Nintendo, Game Freak and The Pokémon Company; this is an unofficial fan project for reviewing finished games.
