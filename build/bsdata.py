#!/usr/bin/env python3
"""Import a Legion army from the BSData Horus Heresy 3rd edition catalogues
(BattleScribe XML used by New Recruit) into this app's data JSON.

Resolves cross-file entryLink / infoLink references by global id index.
Outputs (under data_<army>/): units/*.json-like list, weapons.json, glossary.json.
Weapon stat records match this app's existing weapons.json schema, so datasheets
render identically. Stdlib only.

Usage: python3 build/bsdata.py /tmp/hh3 "Space Wolves" space-wolves
"""
import sys, re, json, os
from xml.etree import ElementTree as ET

NS = "{http://www.battlescribe.net/schema/catalogueSchema}"
def lt(el): return el.tag.replace(NS, "")
def slug(s):
    s = re.sub(r"[’']", "", s or "")
    return re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()

# BSData over-capitalises minor words ("Caster Of Runes In Terminator Armour").
MINOR_WORDS = {"of","in","with","the","and","on","to","for","a","an","or","by"}
def fix_caps(name):
    parts = (name or "").split(" ")
    return " ".join(w.lower() if i>0 and w.lower() in MINOR_WORDS else w
                    for i,w in enumerate(parts))

STAT_KEYS = ["M","WS","BS","S","T","W","I","A","LD","CL","WP","IN","SAV","INV"]
SLOT_MAP = {
    "High Command":"High Command","Command":"Command","Retinue":"Retinue","Elites":"Elites",
    "Heavy Assault":"Heavy Assault","Troops":"Troops","Support":"Support","War-engine":"War-Engines",
    "Transport":"Transports","Heavy Transport":"Heavy Transports","Recon":"Reconnaissance",
    "Fast Attack":"Fast Attack","Armour":"Armour","Lord of War":"Lords of War",
    "Fortification":"Fortifications","Primarch":"Primarch","High Command":"High Command",
}

def _direct_role(el):
    for cl in el.findall(NS+"categoryLinks/"+NS+"categoryLink"):
        nm=(cl.get("name") or "").strip()
        if nm in SLOT_MAP: return SLOT_MAP[nm]
    return None

class Index:
    """Global id -> element maps across all loaded catalogues."""
    def __init__(self):
        self.entry={}; self.group={}; self.profile={}; self.rule={}; self.cat={}
        self.link_role={}  # targetId -> slot, from force-org entryLinks
        self.roots=[]
    def register(self, root):
        for el in root.iter():
            t = lt(el); i = el.get("id")
            if t=="entryLink":
                tid=el.get("targetId"); role=_direct_role(el)
                if tid and role and tid not in self.link_role: self.link_role[tid]=role
            if not i: continue
            if t=="selectionEntry": self.entry[i]=el
            elif t=="selectionEntryGroup": self.group[i]=el
            elif t=="profile": self.profile[i]=el
            elif t=="rule": self.rule[i]=el
            elif t=="categoryEntry": self.cat[i]=el.get("name")
    def load(self, path):
        root = ET.parse(path).getroot(); self.roots.append(root)
        self.register(root)

def chars(prof):
    return {c.get("name"):(c.text or "").strip() for c in prof.iter(NS+"characteristic")}

def is_statline(prof):
    n = {c.get("name") for c in prof.iter(NS+"characteristic")}
    return {"M","WS","BS","T","W"} <= n

def _point_cost(el):
    for c in el.findall(NS+"costs/"+NS+"cost"):
        if (c.get("name") or "").startswith("Point"):
            try: return int(float(c.get("value","0")))
            except: return 0
    return 0

def points(el):
    # direct child costs first (avoid summing nested)
    v = _point_cost(el)
    if v: return v
    # squadrons/batteries carry the cost on a single per-model/crew child entry
    for se in el.findall(NS+"selectionEntries/"+NS+"selectionEntry"):
        v = _point_cost(se)
        if v: return v
    return 0

def _minmax(el):
    """parent-scoped min/max selection counts for a model/unit child entry."""
    mn=mx=None
    for c in el.findall(NS+"constraints/"+NS+"constraint"):
        if c.get("field")=="selections" and c.get("scope")=="parent":
            if c.get("type")=="min": mn=c.get("value")
            if c.get("type")=="max": mx=c.get("value")
    def to_i(v):
        try: return int(float(v))
        except: return None
    return to_i(mn), to_i(mx)

INVARIANT_PLURALS = {"Chosen","Deathsworn","Wolf-kin","Varagyr"}
def plural(n):
    n=(n or "").strip()
    head=n.split()[-1] if n else n
    if head in INVARIANT_PLURALS or n.endswith("i"): return n  # Chosen, Cataphractii
    if n.endswith("y") and (len(n)<2 or n[-2].lower() not in "aeiou"): return n[:-1]+"ies"
    if n.endswith("fe"): return n[:-2]+"ves"
    if n.endswith("f"): return n[:-1]+"ves"
    if n.endswith(("s","x","z","ch","sh")): return n+"es"
    return n+"s"

def squad_economics(entry):
    """Asuryani-style pricing: base squad cost = sum(min x per-model cost) over
    the unit's model/sub-unit children, plus a composition string and
    'May include up to N additional ...' size rules. Costs in HH3.0 BSData sit on
    per-model (or per-crew) children, so the unit-level cost is often a placeholder
    (e.g. Fenrisian Wolf Pack lists 1pt while each Wolf is 9). Falls back to the
    unit-level cost for single-model entries (e.g. characters) that price the unit
    directly. Returns (points, composition_str, size_rules)."""
    members=[]  # (name, per_cost, mn, mx) for children that are taken by default
    upgrades=[] # (name, per_cost, extra, is_unit) for "+N more" size rules
    for se in entry.findall(NS+"selectionEntries/"+NS+"selectionEntry"):
        if se.get("type") not in ("model","unit"): continue
        mn,mx=_minmax(se)
        per=_point_cost(se)
        nm=fix_caps((se.get("name") or "").strip())
        if mn and mn>0:
            members.append((nm,per,mn,mx))
        if per and mx is not None and mn is not None and mx>mn:
            upgrades.append((nm,per,mx-mn,se.get("type")=="unit"))
    # New Recruit sums the unit-level cost with each member's cost x count. The
    # unit-level cost typically prices the leader model (a Sergeant costs the same
    # as a rank-and-file model, folded in here), so it must be added, not ignored.
    base=_point_cost(entry)+sum(per*mn for (nm,per,mn,mx) in members)
    if not base:  # characters / vehicles priced wholly on the unit itself
        base=points(entry)
    comp="\n".join(f"{mn} {nm}" for (nm,per,mn,mx) in members)
    # "per model" wording is what the app's list-builder parser keys on; crew/squadron
    # units (type=unit members) read "per <Crew>", mirroring the Asuryani datasheets.
    size=[f"May include up to {extra} additional {plural(nm)} at +{per} points "
          f"per {nm if is_unit else 'model'}"
          for (nm,per,extra,is_unit) in upgrades]
    return base, comp, size

# ---- weapon + glossary harvesting (global) ----
def harvest_weapons(idx):
    out={}
    for p in idx.profile.values():
        tn = p.get("typeName") or ""
        if tn not in ("Ranged Weapon","Melee Weapon"): continue
        name = (p.get("name") or "").strip()
        if not name: continue
        c = chars(p); sid = slug(name)
        if sid in out: continue
        if tn=="Ranged Weapon":
            rec={"Type":c.get("Type",""),"Ranged Weapon":name,"R":c.get("R"),"FP":c.get("FP"),
                 "RS":c.get("RS"),"AP":c.get("AP"),"D":c.get("D"),
                 "Special Rules":c.get("Special Rules",""),"Traits":c.get("Traits",""),
                 "category":"ranged","id":sid}
        else:
            rec={"Type":c.get("Type",""),"Melee Weapon":name,"IM":c.get("IM"),"AM":c.get("AM"),
                 "SM":c.get("SM"),"AP":c.get("AP"),"D":c.get("D"),
                 "Special Rules":c.get("Special Rules",""),"Traits":c.get("Traits",""),
                 "category":"melee","id":sid}
        out[sid]=rec
    return out

def harvest_glossary(idx):
    # app shape: {specialRules:{Name:desc}, traits:{}, wargear:{}, coreRules:{}}
    out={"specialRules":{},"traits":{},"wargear":{},"coreRules":{}}
    for r in idx.rule.values():
        nm=(r.get("name") or "").strip()
        if not nm: continue
        d=r.find(NS+"description")
        desc=("".join(d.itertext()).strip() if d is not None else "")
        out["specialRules"].setdefault(nm,desc)
    for p in idx.profile.values():
        tn=(p.get("typeName") or "")
        nm=(p.get("name") or "").strip()
        if not nm or tn in ("Ranged Weapon","Melee Weapon","Profile"): continue
        bucket = "traits" if "Trait" in tn else "wargear" if "Wargear" in tn or "Equipment" in tn else "specialRules"
        body="; ".join(f"{k}: {v}" for k,v in chars(p).items() if v)
        out[bucket].setdefault(nm,body)
    return out

# ---- per-unit resolution ----
def find_slot(entry, idx):
    # 1) force-org entryLink that references this unit carries the slot
    r = idx.link_role.get(entry.get("id"))
    if r: return r
    # 2) fall back to a direct role categoryLink on the unit
    r = _direct_role(entry)
    if r: return r
    # 3) Primarchs ("Paragon") have no role link — surface them in High Command
    for cl in entry.iter(NS+"categoryLink"):
        if "Paragon" in (cl.get("name") or ""): return "High Command"
    return None

def collect_equipment(entry, idx, seen, depth=0):
    """Walk a unit subtree, return (weapon_names, wargear_names, rule_names)."""
    we=set(); wg=set(); rules=set()
    if depth>6 or entry is None: return we,wg,rules
    eid=entry.get("id")
    if eid in seen: return we,wg,rules
    seen=seen|{eid}
    # profiles directly on this entry
    for p in entry.findall(NS+"profiles/"+NS+"profile"):
        tn=p.get("typeName") or ""; nm=(p.get("name") or "").strip()
        if tn in ("Ranged Weapon","Melee Weapon"): we.add(nm)
    # infoLinks -> profiles/rules
    for il in entry.findall(NS+"infoLinks/"+NS+"infoLink"):
        tid=il.get("targetId"); p=idx.profile.get(tid); r=idx.rule.get(tid)
        if p is not None:
            tn=p.get("typeName") or ""; nm=(p.get("name") or "").strip()
            if tn in ("Ranged Weapon","Melee Weapon"): we.add(nm)
            elif tn not in ("Profile",): wg.add(nm)
        elif r is not None:
            rules.add((r.get("name") or "").strip())
    # child entries
    for se in entry.findall(NS+"selectionEntries/"+NS+"selectionEntry"):
        if se.get("type")=="model":
            w2,g2,r2=collect_equipment(se,idx,seen,depth+1); we|=w2; wg|=g2; rules|=r2
        elif se.get("type") in ("upgrade",):
            nm=(se.get("name") or "").strip()
            has_w=any((p.get("typeName") in ("Ranged Weapon","Melee Weapon")) for p in se.iter(NS+"profile"))
            if has_w:
                w2,g2,r2=collect_equipment(se,idx,seen,depth+1); we|=w2; wg|=g2; rules|=r2
            else: wg.add(nm)
    # entryLinks -> resolve
    for el in entry.findall(NS+"selectionEntryGroups/"+NS+"selectionEntryGroup")+\
              entry.findall(NS+"entryLinks/"+NS+"entryLink"):
        if lt(el)=="entryLink":
            tid=el.get("targetId"); tgt=idx.entry.get(tid) or idx.group.get(tid)
            if tgt is not None:
                w2,g2,r2=collect_equipment(tgt,idx,seen,depth+1); we|=w2; wg|=g2; rules|=r2
        else:
            w2,g2,r2=collect_equipment(el,idx,seen,depth+1); we|=w2; wg|=g2; rules|=r2
    return we,wg,rules

def composition(entry, idx):
    for se in entry.findall(NS+"selectionEntries/"+NS+"selectionEntry"):
        if se.get("type")=="model":
            mn=mx=None
            for c in se.findall(NS+"constraints/"+NS+"constraint"):
                if c.get("field")=="selections" and c.get("scope")=="parent":
                    if c.get("type")=="min": mn=c.get("value")
                    if c.get("type")=="max": mx=c.get("value")
            nm=(se.get("name") or "Model").strip()
            if mn and mx and mn!=mx: return f"{mn}-{mx} {nm}"
            if mn: return f"{mn} {nm}"
    return ""

# Variant suffixes/prefixes that BSData models as separate units; collapsed
# into a base unit + priced option (see collapse_variants).
VARIANT_PATTERNS = [
    (r"^Mounted (.+)$", "Mounted"),
    (r"^(.+) [Ww]ith Jump Packs?$", "With Jump Packs"),
    (r"^(.+) [Oo]n Scimitar Jetbikes?$", "On Scimitar Jetbikes"),
    (r"^(.+) [Ii]n Saturnine Terminator Armour$", "In Saturnine Terminator Armour"),
    (r"^(.+) [Ii]n Terminator Armour$", "In Terminator Armour"),
]
def collapse_variants(units):
    """Fold Mounted/Jump Pack/Terminator consul variants into their base unit
    as priced options, when a base unit exists in the same slot."""
    by_name={u["name"]:u for u in units.values()}
    drop=set()
    for sid,u in list(units.items()):
        for pat,label in VARIANT_PATTERNS:
            m=re.match(pat,u["name"])
            if not m: continue
            base=by_name.get(m.group(1).strip())
            if base and base["slot"]==u["slot"] and base["id"]!=u["id"]:
                delta=u["pointsValue"]-base["pointsValue"]
                opt=f"{label} (+{delta} points)" if delta>0 else label
                base.setdefault("options",[])
                if opt not in base["options"]: base["options"].append(opt)
                drop.add(sid)
            break
    for sid in drop: units.pop(sid,None)
    return len(drop)

def nested_unit_ids(army_roots):
    """ids of type=unit entries nested as children of another unit (e.g. Rapier
    Crew inside Rapier Battery) — surfaced via the parent, not standalone."""
    nested=set()
    for root in army_roots:
        for entry in root.iter(NS+"selectionEntry"):
            if entry.get("type")!="unit": continue
            for ch in entry.findall(NS+"selectionEntries/"+NS+"selectionEntry"):
                if ch.get("type")=="unit": nested.add(ch.get("id"))
    return nested

def build_units(idx, army_roots):
    units={}
    nested=nested_unit_ids(army_roots)
    for root in army_roots:
        for entry in root.iter(NS+"selectionEntry"):
            if entry.get("type")!="unit": continue
            if entry.get("id") in nested: continue
            name=fix_caps((entry.get("name") or "").strip())
            if not name: continue
            profs=[]; seen_pn=set()
            for p in entry.iter(NS+"profile"):
                if not is_statline(p): continue
                pn=re.sub(r"\s+"," ",(p.get("name") or "").strip())
                if pn in seen_pn: continue  # drop repeated nested-crew profiles
                seen_pn.add(pn)
                profs.append({"name":pn,"stats":{k:v for k,v in chars(p).items()}})
            if not profs: continue
            sid=slug(name)
            if sid in units: continue
            we,wg,rules=collect_equipment(entry,idx,set())
            pts,comp,size=squad_economics(entry)
            if not comp: comp=composition(entry,idx)
            wargear={}
            allgear=sorted(we)+sorted(wg)
            if allgear: wargear["_"]=allgear
            sr={}
            if rules: sr["_"]=sorted(x for x in rules if x)
            units[sid]={
                "id":sid,"name":name,"slot":find_slot(entry,idx) or "Unsorted",
                "composition":comp,
                "baseCost":f"{pts} points" if pts else "","pointsValue":pts,
                "sizeRules":size,"lore":[],"profiles":profs,
                "wargear":wargear,"specialRules":sr,"traits":[],"types":{},"options":[],
            }
    folded=collapse_variants(units)
    if folded: print(f"  collapsed {folded} variant units into base + options")
    return units

def main():
    repo=sys.argv[1]; legion=sys.argv[2]; aid=sys.argv[3]
    shared=["Weapons","Wargear","Special Rules","Traits","Legiones Astartes","Psychic"]
    idx=Index()
    idx.load(os.path.join(repo,"Horus Heresy 3rd Edition.gst"))
    for s in shared:
        p=os.path.join(repo,s+".cat")
        if os.path.exists(p): idx.load(p)
    legion_root=ET.parse(os.path.join(repo,legion+".cat")).getroot()
    idx.roots.append(legion_root)
    idx.register(legion_root)

    weapons=harvest_weapons(idx)
    glossary=harvest_glossary(idx)
    # army units = Legiones Astartes common pool + this Legion's catalogue
    la=[r for r in idx.roots if r.get("name","").strip().endswith("Legiones Astartes")]
    units=build_units(idx,[legion_root]+la)

    out=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),"data_"+aid)
    os.makedirs(out,exist_ok=True)
    json.dump(list(units.values()),open(os.path.join(out,"units.json"),"w"),indent=1)
    json.dump(list(weapons.values()),open(os.path.join(out,"weapons.json"),"w"),indent=1)
    json.dump(glossary,open(os.path.join(out,"glossary.json"),"w"),indent=1)

    from collections import Counter
    gterms=sum(len(v) for v in glossary.values())
    print(f"{legion}: {len(units)} units, {len(weapons)} weapons, {gterms} glossary terms")
    for slot,n in sorted(Counter(u['slot'] for u in units.values()).items(),key=lambda x:-x[1]):
        print(f"  {slot:18} {n}")
    print("\nSamples:")
    for u in list(units.values())[:8]:
        s=u["profiles"][0]["stats"]
        line=" ".join(f"{k}{s.get(k,'-')}" for k in ["M","WS","BS","S","T","W","I","A","SAV"])
        print(f"  [{u['slot']}] {u['name']} ({u['pointsValue']}pts) {line}  gear={len(u['wargear'].get('_',[]))}")

if __name__=="__main__":
    main()
