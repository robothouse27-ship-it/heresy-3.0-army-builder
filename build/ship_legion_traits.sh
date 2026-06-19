#!/usr/bin/env bash
# Inject per-legion armyRule (+ shared detachments/vehicles) into every legion
# bundle, then re-encrypt each into app/data.<aid>.enc.js. Run after editing
# data/legion-traits.json.  Usage: PW='Spaceelfs' bash build/ship_legion_traits.sh
set -euo pipefail
cd "$(dirname "$0")/.."
python3 build/inject_legion_extras.py
for d in data_*/; do
  aid="${d#data_}"; aid="${aid%/}"
  [ "$aid" = "asuryani" ] && continue
  PW="${PW:-Spaceelfs}" node build/encrypt_army.js "data_${aid}/bundle.json" "app/data.${aid}.enc.js"
done
echo "All legion bundles re-encrypted."
