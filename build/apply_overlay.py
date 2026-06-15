#!/usr/bin/env python3
"""Apply build/overlay_<aid>.json onto the already-built data_<aid>/{units,bundle}.json.

Used when the BSData source catalogues aren't checked out locally (so bsdata.py
can't be re-run from scratch) but we still want the hand-authored, book-accurate
overlay reflected in the shipped artifacts. Keep this in step with bsdata.py's
overlay handling. Usage: python3 build/apply_overlay.py space-wolves
"""
import json, os, sys

aid = sys.argv[1] if len(sys.argv) > 1 else "space-wolves"
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ov = json.load(open(os.path.join(root, "build", f"overlay_{aid}.json"), encoding="utf-8"))
ov_units = ov.get("units", {})
ov_lists = ov.get("wargearLists", {})

# scalar/array fields copied verbatim from the overlay onto each unit
DIRECT = ["lore", "wargear", "traits", "options", "composition", "sizeRules",
          "baseCost", "pointsValue"]

def patch_unit(u):
    ov_u = ov_units[u["id"]]
    for k in DIRECT:
        if k in ov_u:
            u[k] = ov_u[k]
    if "specialRules" in ov_u:
        u["specialRules"] = {"_": ov_u["specialRules"]}

def patch_file(path, is_bundle):
    d = json.load(open(path, encoding="utf-8"))
    arr = d["units"] if is_bundle else d
    n = 0
    for u in arr:
        if u.get("id") in ov_units:
            patch_unit(u); n += 1
    if is_bundle and ov_lists:
        d.setdefault("wargearLists", {}).update(ov_lists)
    json.dump(d, open(path, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"  patched {n} units in {os.path.relpath(path, root)}")

base = os.path.join(root, "data_" + aid)
patch_file(os.path.join(base, "units.json"), False)
patch_file(os.path.join(base, "bundle.json"), True)
print(f"done ({len(ov_units)} units defined in overlay)")
