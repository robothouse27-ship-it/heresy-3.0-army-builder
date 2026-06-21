#!/usr/bin/env python3
"""Set the Battlefield Role of every Primarch to "Warlord" (rulebook p285).

The eighteen Primarchs (plus their ascended/transfigured forms) carry the Warlord
Battlefield Role, NOT High Command — they are fielded in the Warlord Detachment.
BSData imported them as "High Command", so patch the built artifacts in place.

Idempotent: re-running only flips slots that aren't already "Warlord". Run after any
bundle rebuild (or fold into the standard injection step). Then re-encrypt the bundles.

Usage:  python3 build/fix_primarch_roles.py [--check]
"""
import json, sys, os

# Curated per-legion Primarch unit ids (+ daemon/ascended forms). Slug ids are stable.
PRIMARCHS = {
    "alpha-legion":      ["alpharius"],
    "blood-angels":      ["sanguinius"],
    "dark-angels":       ["lion-eljohnson"],
    "death-guard":       ["mortarion"],
    "emperors-children": ["fulgrim", "fulgrim-transfigured"],
    "imperial-fists":    ["rogal-dorn"],
    "iron-hands":        ["ferrus-manus"],
    "iron-warriors":     ["perturabo"],
    "night-lords":       ["konrad-curze"],
    "raven-guard":       ["corvus-corax"],
    "salamanders":       ["vulkan"],
    "sons-of-horus":     ["horus-lupercal", "horus-ascended"],
    "space-wolves":      ["leman-russ"],
    "thousand-sons":     ["magnus-the-red"],
    "ultramarines":      ["roboute-guilliman"],
    "white-scars":       ["jaghatai-khan"],
    "word-bearers":      ["lorgar-aurelian"],
    "world-eaters":      ["angron", "angron-transfigured"],
}
ROLE = "Warlord"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def patch_file(path, ids, check):
    """Return (n_changed, set_of_ids_present_here)."""
    if not os.path.exists(path):
        return 0, set()
    data = json.load(open(path))
    units = data if isinstance(data, list) else data.get("units", [])
    changed, present = 0, set()
    for u in units:
        if u.get("id") in ids:
            present.add(u["id"])
            if u.get("slot") != ROLE:
                if not check:
                    u["slot"] = ROLE
                changed += 1
    if changed and not check:
        json.dump(data, open(path, "w"), ensure_ascii=False, indent=1)
    return changed, present


def main():
    check = "--check" in sys.argv
    total = 0
    for legion, ids in PRIMARCHS.items():
        present = set()
        for fname in ("bundle.json", "units.json"):
            path = os.path.join(ROOT, "data_%s" % legion, fname)
            n, here = patch_file(path, ids, check)
            present |= here
            if n:
                print("%-22s %-12s  %d updated" % (legion, fname, n))
        for mid in ids:
            if mid not in present:
                print("  !! %s/%s not found in either file" % (legion, mid))
        total += sum(1 for _ in ids)  # placeholder; real count printed per-file above
    label = "Would set" if check else "Set"
    print("\n%s slot=Warlord on %d Primarch ids across 18 legions." %
          (label, sum(len(v) for v in PRIMARCHS.values())))


if __name__ == "__main__":
    main()
