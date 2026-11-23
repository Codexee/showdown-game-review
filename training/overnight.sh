#!/bin/sh
# Overnight training run (vault ADR-0005, plan-run-v12): build or check the dataset, train
# with a time budget, score on the pinned bank of future games, run the paired gate against
# the installed model, and install only if the gate says the new model is better.
# Keeps the Mac awake while it runs (caffeinate).
#
#   RUN=v12 ./training/overnight.sh                       # defaults below
#   RUN=v12 SINCE=2025-01-01 DROPOUT=0.2 WD=0.1 ./training/overnight.sh
#   RUN=v12 RESUME=1 ./training/overnight.sh              # continue a stopped run
#   RUN=v12 DRY_RUN=1 ./training/overnight.sh             # only the checks and the gate; never installs
#
# Safety rules (vault 2026-11-23-codex-review, finding 1):
# - RUN must be a new name, never the installed model's run (whose gate would be skipped).
#   An existing run is refused unless RESUME=1.
# - The dataset is named after its dates, and an existing one must match SINCE / RANGES.
# - Install only on "b is better" (whole 90% band below zero, both players' views). "No
#   clear difference" keeps the installed model unless INSTALL_IF_TIE=1. A missing or
#   failed gate keeps it too.
set -e
cd "$(dirname "$0")/.."
RUN=${RUN:-v12}
HOURS=${HOURS:-9}            # a ceiling; the LR and value-weight schedules end at EPOCHS
EPOCHS=${EPOCHS:-4}
SINCE=${SINCE:-2026-01-01}
RANGES=${RANGES:-}           # e.g. '2025-01-01:,' ; replaces SINCE when set
D=${D:-256}                  # ~7M params: small and trained longer (Jaxcalibur, mikumiku)
LAYERS=${LAYERS:-6}
DROPOUT=${DROPOUT:-0.1}
WD=${WD:-0.05}
VW_FLOOR=${VW_FLOOR:-1.0}    # 1.0 = no value-weight schedule
EVAL_EVERY=${EVAL_EVERY:-1500}
RESUME=${RESUME:-0}
DRY_RUN=${DRY_RUN:-0}
INSTALL_IF_TIE=${INSTALL_IF_TIE:-0}
if [ -n "$RANGES" ]; then DATES="ranges $RANGES"; DS=${DS:-full-$(echo "$RANGES" | tr -c 'A-Za-z0-9\n' '_')}
else DATES="since $SINCE"; DS=${DS:-full-$SINCE}; fi
LOG=data/models/$RUN.log
mkdir -p data/models
[ "$DRY_RUN" = 1 ] || exec >> "$LOG" 2>&1   # follow along with: tail -f data/models/<RUN>.log

fail() { echo "== $(date '+%F %T') stopped: $*"; exit 1; }
py() { uv run python -c "$1"; }

CUR=$(py "import torch; print(torch.load('data/models/current.pt', weights_only=False)['info']['run'])" 2>/dev/null || echo "")
CUR_STEP=$(py "import torch; print(torch.load('data/models/current.pt', weights_only=False)['info']['step'])" 2>/dev/null || echo "")
echo "== $(date '+%F %T') overnight run $RUN on $DS ($DATES), ${HOURS} h ceiling, $EPOCHS epochs, d=$D layers=$LAYERS dropout=$DROPOUT wd=$WD value-weight floor=$VW_FLOOR; installed: ${CUR:-none}@${CUR_STEP:-?}"

[ "$RUN" != "$CUR" ] || fail "RUN=$RUN is the installed model's run; pick a new name"
if [ "$DRY_RUN" != 1 ]; then
  if [ -d "data/models/$RUN" ] && [ "$RESUME" != 1 ]; then fail "data/models/$RUN exists; use a new RUN or RESUME=1"; fi
  RESUME_FLAG=""; [ "$RESUME" = 1 ] && RESUME_FLAG="--resume"

  # Dataset: build it, or check that the existing one has the requested dates.
  if [ -f "data/train/ds/$DS/meta.json" ]; then
    py "import json,sys; m=json.load(open('data/train/ds/$DS/meta.json')); want=('$RANGES' or '', '' if '$RANGES' else '$SINCE'); got=(m.get('ranges') or '', '' if m.get('ranges') else m.get('since')); sys.exit(0 if want==got else f'dataset $DS has {got}, wanted {want}')" \
      || fail "dataset $DS doesn't match the requested dates"
  elif [ -n "$RANGES" ]; then
    uv run python -m training.build_dataset --name "$DS" --hf 'data/hf/*.parquet' --ranges "$RANGES" --workers "$(sysctl -n hw.ncpu)"
  else
    uv run python -m training.build_dataset --name "$DS" --hf 'data/hf/*.parquet' --since "$SINCE" --workers "$(sysctl -n hw.ncpu)"
  fi
  if [ ! -f data/train/ds/test_pinned/meta.json ]; then
    uv run python -m training.build_dataset --name test_pinned --inputlog data/train/test_pinned --both-sides --val-frac 0 --workers "$(sysctl -n hw.ncpu)"
  fi

  caffeinate -i -s uv run python -m training.train --data "$DS" --run "$RUN" --hours "$HOURS" --epochs "$EPOCHS" \
    --d "$D" --layers "$LAYERS" --heads 8 --ff $((D * 4)) --bs 2048 --lr 4e-4 --eval-every "$EVAL_EVERY" \
    --dropout "$DROPOUT" --wd "$WD" --value-weight-floor "$VW_FLOOR" $RESUME_FLAG
  uv run python -m training.test_model --run "$RUN" --data test_pinned
fi

# Paired gate against the installed model, on the same bank, both players' views.
VERDICT="no installed model"
if [ -n "$CUR" ]; then
  [ -f "data/models/$CUR/preds_test_pinned.npz" ] || fail "no pinned-bank predictions for the installed run $CUR; run training.test_model --run $CUR --data test_pinned first. Not installing."
  INC_STEP=$(py "import json; print(json.load(open('data/models/$CUR/test_test_pinned.json'))['step'])" 2>/dev/null || echo "")
  [ "$INC_STEP" = "$CUR_STEP" ] || fail "the installed model is $CUR@$CUR_STEP but its pinned-bank predictions are from step ${INC_STEP:-?}. Not installing."
  uv run python -m training.compare_runs --a "$CUR" --b "$RUN" --data test_pinned > /dev/null \
    || fail "the gate could not run. Not installing."
  VERDICT=$(py "import json; print(json.load(open('data/models/$RUN/gate_vs_${CUR}_test_pinned.json'))['verdict'])")
fi
echo "== gate $RUN vs ${CUR:-none}: $VERDICT"
case "$VERDICT" in
  "b is better"*|"no installed model") INSTALL=1 ;;
  "no clear difference"*) INSTALL=$INSTALL_IF_TIE ;;
  *) INSTALL=0 ;;
esac
if [ "$INSTALL" = 1 ] && [ "$DRY_RUN" = 1 ]; then
  echo "== dry run: would install with: uv run python -m training.export --run $RUN"
elif [ "$INSTALL" = 1 ]; then
  uv run python -m training.export --run "$RUN"
else
  echo "== not installing: $CUR stays installed"
fi
echo "== $(date '+%F %T') done"
