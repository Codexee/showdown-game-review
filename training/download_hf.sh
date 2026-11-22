#!/bin/sh
# Download the [Gen 9] RANDOMBATTLE parquet files of HolidayOugi/pokemon-showdown-replays
# (public Showdown replay logs, no inputlogs, no license stated) into data/hf/. Resumable.
set -e
cd "$(dirname "$0")/../data/hf"
BASE="https://huggingface.co/datasets/HolidayOugi/pokemon-showdown-replays/resolve/main"
# smallest first, so a test run can start early
for n in 11 1 2 3 4 5 6 7 8 9 10; do
  f="[Gen 9] RANDOMBATTLE_part$n.parquet"
  out="gen9randombattle_part$n.parquet"
  [ -f "$out.done" ] && continue
  enc=$(printf '%s' "$f" | sed 's/\[/%5B/g; s/\]/%5D/g; s/ /%20/g')
  echo "$(date '+%H:%M:%S') downloading $out"
  curl -sS -L -C - -o "$out" "$BASE/$enc"
  touch "$out.done"
done
echo "$(date '+%H:%M:%S') all parts downloaded"
