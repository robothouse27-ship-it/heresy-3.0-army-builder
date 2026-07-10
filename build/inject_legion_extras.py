#!/usr/bin/env python3
"""Inject Legiones-Astartes-shared content into every legion bundle (NOT Asuryani):
  - data/detachments-legiones.json  -> bundle.detachments.auxiliary  (faction Auxiliary detachments)
  - data/vehicles-legion.json       -> bundle.units                  (shared Legion vehicles)
  - data/wargear-lists-legion.json  -> bundle.wargearLists           (shared Legion wargear lists)
  - data/legion-traits.json         -> bundle.armyRule               (per-legion core trait)
Idempotent: replaces prior copies by id / key. Run after bsdata/overlay rebuilds, then encrypt.
Usage: python3 build/inject_legion_extras.py
"""
import json, glob, os, re
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load(p):
    fp = os.path.join(ROOT, p)
    return json.load(open(fp, encoding="utf-8")) if os.path.exists(fp) else {}

fac = load("data/detachments-legiones.json").get("auxiliary", [])
veh = load("data/vehicles-legion.json").get("units", [])
wlists = load("data/wargear-lists-legion.json").get("wargearLists", {})  # slug-key -> {name, items}
traits = load("data/legion-traits.json")          # { "<aid>": {name, text} | [ {name,text}, ... ] }
fac_ids = {f["id"] for f in fac}
veh_ids = {v["id"] for v in veh}

n = 0
for f in glob.glob(os.path.join(ROOT, "data_*/bundle.json")):
    aid = re.search(r"data_([a-z-]+)/bundle\.json$", f).group(1)
    b = json.load(open(f, encoding="utf-8"))
    det = b.get("detachments") or {}
    aux = [a for a in det.get("auxiliary", []) if a.get("id") not in fac_ids]
    det["auxiliary"] = aux + [dict(x) for x in fac]
    b["detachments"] = det
    units = [u for u in b.get("units", []) if u.get("id") not in veh_ids]
    b["units"] = units + [dict(x) for x in veh]
    wl = b.get("wargearLists") or {}
    for k, v in wlists.items():
        wl[k] = json.loads(json.dumps(v))   # upsert by slug key (deep copy)
    b["wargearLists"] = wl
    if aid in traits:
        b["armyRule"] = traits[aid]
    json.dump(b, open(f, "w", encoding="utf-8"), ensure_ascii=False)
    n += 1

have = sum(1 for f in glob.glob(os.path.join(ROOT, "data_*/bundle.json"))
           if re.search(r"data_([a-z-]+)/bundle\.json$", f).group(1) in traits)
print(f"injected {len(fac)} faction detachments + {len(veh)} vehicles + {len(wlists)} wargear lists + {have} legion traits into {n} legion bundles")
