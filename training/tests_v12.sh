#!/bin/bash
# Small tests before training run v1.2 (vault plan-run-v12). Four 4-epoch runs, each scored on
# the pinned bank of future games, then paired gates. About 4-4.5 h.
#   ./training/tests_v12.sh            follow along: tail -f data/models/v12tests.log
# Resumable: a run whose best.pt and pinned-bank predictions exist is skipped.
cd "$(dirname "$0")/.."
LOG=data/models/v12tests.log
exec >> "$LOG" 2>&1
COMMON="--bs 2048 --lr 4e-4 --epochs 4 --d 256 --layers 6 --heads 8 --ff 1024 --resume"

run() {  # name data eval_every extra-args...
  local name=$1 data=$2 every=$3; shift 3
  if [ -f "data/models/$name/preds_test_pinned.npz" ]; then echo "== $name already done"; return; fi
  echo "== $(date '+%F %T') $name on $data: $*"
  caffeinate -i -s uv run python -m training.train --data "$data" --run "$name" --eval-every "$every" $COMMON "$@" \
    && uv run python -m training.test_model --run "$name" --data test_pinned \
    || echo "== $name FAILED"
}

echo "== $(date '+%F %T') v1.2 tests start"
run v12a medium 400
run v12b medium 400 --dropout 0.2 --wd 0.1
run v12c medium 400 --dropout 0.2 --wd 0.1 --value-weight-floor 0.2
run v12d mix25  800 --dropout 0.2 --wd 0.1
for pair in "v12a v12b" "v12b v12c" "v12b v12d" "main v12b" "main v12d"; do
  set -- $pair
  echo "== gate $1 vs $2"
  uv run python -m training.compare_runs --a "$1" --b "$2" --data test_pinned | tail -12
done
echo "== $(date '+%F %T') v1.2 tests done"
