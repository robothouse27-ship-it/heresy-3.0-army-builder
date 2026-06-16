#!/usr/bin/env python3
"""Inject Legiones-Astartes-shared content into every legion bundle (NOT Asuryani):
  - data/detachments-legiones.json  -> bundle.detachments.auxiliary  (faction Auxiliary detachments)
  - data/vehicles-legion.json       -> bundle.units                  (shared Legion vehicles)
Idempotent: replaces prior copies by id. Run after bsdata/overlay rebuilds, then encrypt.
Usage: python3 build/inject_legion_extras.py
"""
import json, glob, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load(p):
    fp = os.path.join(ROOT, p)
    return json.load(open(fp, encoding="utf-8")) if os.path.exists(fp) else {}

fac = load("data/detachments-legiones.json").get("auxiliary", [])
veh = load("data/vehicles-legion.json").get("units", [])
fac_ids = {f["id"] for f in fac}
veh_ids = {v["id"] for v in veh}

n = 0
for f in glob.glob(os.path.join(ROOT, "data_*/bundle.json")):
    b = json.load(open(f, encoding="utf-8"))
    det = b.get("detachments") or {}
    aux = [a for a in det.get("auxiliary", []) if a.get("id") not in fac_ids]
    det["auxiliary"] = aux + [dict(x) for x in fac]
    b["detachments"] = det
    units = [u for u in b.get("units", []) if u.get("id") not in veh_ids]
    b["units"] = units + [dict(x) for x in veh]
    json.dump(b, open(f, "w", encoding="utf-8"), ensure_ascii=False)
    n += 1

print(f"injected {len(fac)} faction detachments + {len(veh)} vehicles into {n} legion bundles")
