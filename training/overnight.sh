#!/bin/sh
# Overnight training run (vault ADR-0005): build the full dataset, train with a time
# budget, install the best checkpoint for the app, then score it on future games.
# Keeps the Mac awake while it runs (caffeinate). Safe to re-run: training resumes.
#
#   ./training/overnight.sh            # defaults below
#   HOURS=10 SINCE=2026-01-01 ./training/overnight.sh
set -e
cd "$(dirname "$0")/.."
RUN=${RUN:-main}
HOURS=${HOURS:-9}
SINCE=${SINCE:-2026-01-01}
D=${D:-384}
LAYERS=${LAYERS:-6}
LOG=data/models/$RUN.log
mkdir -p data/models
exec >> "$LOG" 2>&1   # follow along with: tail -f data/models/main.log

echo "== $(date) overnight run $RUN: games since $SINCE, ${HOURS} h, d=$D layers=$LAYERS"
if [ ! -f data/train/ds/full/meta.json ]; then
  uv run python -m training.build_dataset --name full --hf 'data/hf/*.parquet' --since "$SINCE"
fi
caffeinate -i -s uv run python -m training.train --data full --run "$RUN" --hours "$HOURS" \
  --d "$D" --layers "$LAYERS" --heads 8 --ff $((D * 4)) --bs 2048 --lr 4e-4 --epochs 8 --eval-every 3000 --resume
# Score on games played after the training data ends (collected with inputlogs),
# then install the model for the app (the export quotes the future-games score).
if ls data/train/inputlog/gen9*.json >/dev/null 2>&1; then
  rm -rf data/train/ds/test
  uv run python -m training.build_dataset --name test --inputlog data/train/inputlog --both-sides --val-frac 0
  uv run python -m training.test_model --run "$RUN" --data test
fi
uv run python -m training.export --run "$RUN"
echo "== $(date) done"
