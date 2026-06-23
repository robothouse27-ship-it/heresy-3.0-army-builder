#!/usr/bin/env python3
"""Thousand Sons — the Prosperine Arcana (Liber Hereticus p220-225).

Every TS model is already a Psyker (Cult Arcana army rule). This adds the *choice*:
each eligible unit may take one Prosperine Arcana for +10 pts (one of 5 Cults), each
granting a Trait + a Psychic Power + a Psychic Weapon/Reaction.

Eligible = Thousand Sons Trait, NOT Vehicle/Walker/Automata Type, NOT Unique, and NOT
a unit whose datasheet already grants an Arcana (Khenetai / Numerologist / Prosperine
Sorcerer / Arch-Sorcerer). Patches data_thousand-sons/bundle.json in place:
  (a) a "Prosperine Arcana" pick upgrade (+10, 5 choices) on each eligible unit
  (b) glossary entries for the 5 Cults + their 10 powers (full rules text)
  (c) a "The Prosperine Arcana" army-rule entry
Idempotent. Re-encrypt + sync the clean app after.

Usage:  python3 build/add_ts_arcana.py [--check]
"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUNDLE = os.path.join(ROOT, "data_thousand-sons", "bundle.json")
CHECK = "--check" in sys.argv

CULTS = ["Raptora", "Pyrae", "Pavoni", "Corvidae", "Athanaean"]
ARCANA_UP = {
    "model": "Prosperine Arcana",
    "limit": 1,
    "pickOne": True,
    "note": "One per unit (+10 pts) — grants a Cult Trait + a Psychic Power + a Psychic Weapon/Reaction. See Army Rules.",
    "choices": [{"name": c, "pts": 10} for c in CULTS],
}

# --- glossary: the 5 Cults (Traits) ---
CULT_GLOSS = {
    "Raptora": "Prosperine Arcana (Cult of psychokinesis). Every model in the unit gains the Crushing Force Psychic Weapon, the Kine Shield Psychic Reaction and the 'Raptora' Trait. The Raptora bend physical reality with their will — conjuring shields of force and crushing foes from afar.",
    "Pyrae": "Prosperine Arcana (Cult of fire). Every model in the unit gains the Inferno Shield Psychic Power, the Burning Grasp Psychic Weapon and the 'Pyrae' Trait. The Pyrae control and create fire, their thoughts becoming hell-storms.",
    "Pavoni": "Prosperine Arcana (Cult of biomancy). Every model in the unit gains the Stoneform Psychic Reaction, the Bloodboil Psychic Weapon and the 'Pavoni' Trait. The Pavoni shape living flesh — hardening their own and boiling the blood of foes.",
    "Corvidae": "Prosperine Arcana (Cult of fate). Every model in the unit gains the Fated Shots and Paths of Consequence Psychic Powers and the 'Corvidae' Trait. The Corvidae are soothsayers who touch the flow of time and consequence.",
    "Athanaean": "Prosperine Arcana (Cult of the mind). Every model in the unit gains the Clarity Psychic Power, the Emanation of Dread Psychic Weapon and the 'Athanaean' Trait. The Athanaean master thought itself, binding the Legion together in battle.",
}

# --- glossary: the 10 powers (Special Rules) ---
POWER_GLOSS = {
    "Crushing Force": "(Psychic Weapon — Raptora) Melee. Strength 9, AP 4, Damage 2; Armourbane, Psychic, Force (D). Visualising the foe in their grasp, the practitioner crushes them with telekinetic force.",
    "Kine Shield": "(Psychic Reaction, Blessing — Raptora) Declared at the start of Step 3 of a Shooting Attack targeting a unit with a Raptora model; costs 1 Reaction Allotment point. On a successful Manifestation Check, every model in the target unit gains a 4+ Shrouded Damage Mitigation Roll against the attack's wounds (lasts until the end of the sub-phase).",
    "Inferno Shield": "(Psychic Power, Blessing — Pyrae) Manifested at the end of the Declare Weapons and Set Initiative step of a Combat, on a unit with a Pyrae model. While it lasts (until the Combat is resolved), at the end of each Initiative Step every enemy unit that scored any Hits on the bearer's unit suffers D6 Hits at Strength 4, AP -, Damage 1.",
    "Burning Grasp": "(Psychic Weapon — Pyrae) Melee. Strength 8, AP 2; Critical Hit (6+), Psychic, Breaching (5+), Armourbane. The initiates melt away even the thickest plate with a single touch.",
    "Stoneform": "(Psychic Reaction, Blessing — Pavoni) Declared at the start of Step 3 of a Shooting Attack targeting a unit with a Pavoni model; costs 1 Reaction Allotment point. On a successful Manifestation Check, every model in the reacting unit gains +2 Toughness (lasts until the end of the sub-phase).",
    "Bloodboil": "(Psychic Weapon — Pavoni) Ranged 12\". Strength 2, AP 2, Damage 2; Poisoned (2+), Psychic. Focusing their power on a single foe, the Pavoni heat the enemy's blood, scorching organs and rupturing veins.",
    "Fated Shots": "(Psychic Power, Blessing — Corvidae) Manifested in the Shooting Phase at the start of Step 4 of a Shooting Attack by a unit with a Corvidae model. On success, all ranged Weapons in the unit (except those with Blast) gain Rending (5+) for that attack.",
    "Paths of Consequence": "(Psychic Power, Curse — Corvidae) Manifested in the Effects Sub-Phase of the Start Phase, targeting an enemy unit within 18\" and Line of Sight of a Corvidae model. On success, every model in the target suffers -2 Movement (to a minimum of 0) and must take a Dangerous Terrain Test the first time it moves each phase, until the start of your next Turn.",
    "Clarity": "(Psychic Power, Blessing — Athanaean) Manifested in the Effects Sub-Phase of the Start Phase, targeting a friendly Thousand Sons unit within 18\" and Line of Sight of an Athanaean model. On success, choose one Tactical Status a model in the unit has — it is removed from every model in that unit.",
    "Emanation of Dread": "(Psychic Weapon — Athanaean) Ranged 24\". Strength 1, AP -; Panic (1), Psychic. Every possible death and misfortune is projected into the target's mind, casting doubt and indecision.",
}

ARMY_RULE_ENTRY = {
    "name": "The Prosperine Arcana",
    "text": (
        "The psychic powers of the Thousand Sons were focused around the disciplines of their Cult temples. "
        "Each unit from your Army with the Thousand Sons Trait — excluding units with the Vehicle or Automata Type "
        "or the Unique Sub-Type — may be given one of the following Prosperine Arcana for +10 points per unit. "
        "A unit may only ever be given one. The discipline is granted to every model in the unit, but not to models "
        "that join it later. Some units (such as the Khenetai Occult Cabal, Numerologist Cabal and Prosperine "
        "Sorcerer) already have their own Arcana and cannot be given one from this list.\n\n"
        "Raptora — Crushing Force (Psychic Weapon), Kine Shield (Psychic Reaction).\n\n"
        "Pyrae — Inferno Shield (Psychic Power), Burning Grasp (Psychic Weapon).\n\n"
        "Pavoni — Stoneform (Psychic Reaction), Bloodboil (Psychic Weapon).\n\n"
        "Corvidae — Fated Shots and Paths of Consequence (Psychic Powers).\n\n"
        "Athanaean — Clarity (Psychic Power), Emanation of Dread (Psychic Weapon).\n\n"
        "If a model Manifesting a power gained from a Prosperine Arcana suffers Perils of the Warp, do not roll on "
        "the Perils table; instead the unit suffers D3 wounds, each AP 2 Damage 1, ignoring Cover Saves and Damage "
        "Mitigation Rolls. If a unit with an Arcana gains a Psychic Weapon, only one model in it may use that weapon "
        "each time the unit is selected to make attacks."
    ),
}

VEHICLE_TYPES = ("Vehicle", "Walker", "Automata")


def is_excluded(u, gloss_sr):
    types = " ".join((p.get("stats") or {}).get("Type", "") for p in u.get("profiles", []))
    if any(t in types for t in VEHICLE_TYPES):
        return "vehicle/automata"
    if "Unique" in types or u.get("id") in ("magnus-the-red", "ahzek-ahriman", "magistus-amon"):
        return "unique"
    # already grants/precludes an Arcana per its own special-rule text
    rules = []
    if isinstance(u.get("specialRules"), dict):
        for v in u["specialRules"].values():
            rules += [x for x in v if x]
    for r in rules:
        d = gloss_sr.get(r, "")
        if "cannot have a Prosperine Arcana selected" in d or ("considered to have the" in d and "Prosperine Arcana" in d):
            return "has own arcana"
    return None


def main():
    b = json.load(open(BUNDLE))
    gloss = b.setdefault("glossary", {})
    gsr = gloss.setdefault("specialRules", {})
    gtr = gloss.setdefault("traits", {})

    # (b) glossary
    g_added = 0
    for k, v in CULT_GLOSS.items():
        if gtr.get(k) != v:
            if not CHECK: gtr[k] = v
            g_added += 1
    for k, v in POWER_GLOSS.items():
        if gsr.get(k) != v:
            if not CHECK: gsr[k] = v
            g_added += 1
    if gsr.get("Prosperine Arcana") is None and not CHECK:
        gsr["Prosperine Arcana"] = ARMY_RULE_ENTRY["text"].split("\n\n")[0]
        g_added += 1

    # (a) upgrades on eligible units
    eligible, excluded = [], []
    for u in b["units"]:
        why = is_excluded(u, gsr)
        if why:
            excluded.append((u["id"], why)); continue
        eligible.append(u["id"])
        ups = u.setdefault("upgrades", [])
        if not any(isinstance(x, dict) and x.get("model") == "Prosperine Arcana" for x in ups):
            if not CHECK: ups.append(json.loads(json.dumps(ARCANA_UP)))

    # (c) army rule
    ar = b.get("armyRule")
    ar = ar if isinstance(ar, list) else ([ar] if ar else [])
    if not any(isinstance(x, dict) and x.get("name") == ARMY_RULE_ENTRY["name"] for x in ar):
        if not CHECK: ar.append(ARMY_RULE_ENTRY)
        b["armyRule"] = ar
        ar_added = True
    else:
        ar_added = False

    if not CHECK:
        json.dump(b, open(BUNDLE, "w"), ensure_ascii=False, indent=1)

    print("%s:" % ("DRY RUN" if CHECK else "APPLIED"))
    print("  eligible units (Arcana picker): %d" % len(eligible))
    print("  excluded: %d (%s)" % (len(excluded), ", ".join(sorted({w for _, w in excluded}))))
    print("  glossary entries added/updated: %d" % g_added)
    print("  army-rule 'The Prosperine Arcana' added: %s" % ar_added)


if __name__ == "__main__":
    main()
