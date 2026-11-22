#!/bin/sh
# Overnight training run (vault ADR-0005, benchmark-best-in-class): build the full
# dataset, train with a time budget, score on the pinned bank of future games, run the
# paired gate against the installed model, and install only if it isn't worse.
# Keeps the Mac awake while it runs (caffeinate). Safe to re-run: training resumes.
#
#   ./training/overnight.sh            # defaults below
#   HOURS=10 SINCE=2026-01-01 ./training/overnight.sh
set -e
cd "$(dirname "$0")/.."
RUN=${RUN:-main}
HOURS=${HOURS:-9}
SINCE=${SINCE:-2026-01-01}
D=${D:-256}            # ~6-8M params: small and trained longer (Jaxcalibur, mikumiku)
LAYERS=${LAYERS:-6}
LOG=data/models/$RUN.log
mkdir -p data/models
exec >> "$LOG" 2>&1   # follow along with: tail -f data/models/main.log

echo "== $(date) overnight run $RUN: games since $SINCE, ${HOURS} h, d=$D layers=$LAYERS"
if [ ! -f data/train/ds/full/meta.json ]; then
  uv run python -m training.build_dataset --name full --hf 'data/hf/*.parquet' --since "$SINCE" --workers "$(sysctl -n hw.ncpu)"
fi
if [ ! -f data/train/ds/test_pinned/meta.json ]; then
  uv run python -m training.build_dataset --name test_pinned --inputlog data/train/test_pinned --both-sides --val-frac 0 --workers "$(sysctl -n hw.ncpu)"
fi
caffeinate -i -s uv run python -m training.train --data full --run "$RUN" --hours "$HOURS" \
  --d "$D" --layers "$LAYERS" --heads 8 --ff $((D * 4)) --bs 2048 --lr 4e-4 --epochs 8 --eval-every 3000 --resume

uv run python -m training.test_model --run "$RUN" --data test_pinned

# Paired gate against the installed model, if it has predictions on the same bank.
CUR=$(uv run python -c "import torch; print(torch.load('data/models/current.pt', weights_only=False)['info']['run'])" 2>/dev/null || echo "")
VERDICT="no installed model"
if [ -n "$CUR" ] && [ "$CUR" != "$RUN" ] && [ -f "data/models/$CUR/preds_test_pinned.npz" ]; then
  uv run python -m training.compare_runs --a "$CUR" --b "$RUN" --data test_pinned > /dev/null
  VERDICT=$(uv run python -c "import json; print(json.load(open('data/models/$RUN/gate_vs_${CUR}_test_pinned.json'))['verdict'])")
fi
echo "== gate vs $CUR: $VERDICT"
case "$VERDICT" in
  "b is worse"*) echo "== not installing: the new model is worse than $CUR on the pinned bank" ;;
  *) uv run python -m training.export --run "$RUN" ;;
esac
echo "== $(date) done"
