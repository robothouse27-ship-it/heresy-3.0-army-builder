#!/usr/bin/env python3
"""Convert hand-authored English `options` lines into structured `upgrades`.

Conservative: only consumes a line it can parse with confidence. Anything it
can't is left in `options` (the app shows residual options text below the
interactive controls, so no information is ever lost).

Usage: python3 build/options_to_upgrades.py            # dry-run report
       python3 build/options_to_upgrades.py --write     # rewrite overlay files
"""
import json, re, sys, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES = ["overlay_legion-common.json", "overlay_space-wolves.json"]
SKIP_UNITS = {"grey-slayer-pack"}  # already hand-authored

def price(s):
    """First points value in a fragment: '(+15)', '+15 points', '+1 point'."""
    m = re.search(r"\+\s*(\d+)\s*point", s) or re.search(r"\(\s*\+\s*(\d+)\s*\)", s)
    return int(m.group(1)) if m else 0

# --- subject (who) -> (model label, limit) -------------------------------
def subject(opt):
    o = opt.strip()
    m = re.match(r"^For every (\w+) Models?,?\s+(?:up to (\w+)\s+|one|a single)?\b", o, re.I)
    if m and re.match(r"^For every \w+ Models?", o, re.I):
        n = {"five":5,"two":2,"three":3,"four":4,"ten":10}.get(m.group(1).lower())
        if n: return ("Squad", "per%d"%n, re.sub(r"^For every \w+ Models?,?\s+(?:up to \w+\s+[\w' \-]+?|one|a single)?\s*(?:in this Unit\s+)?", "", o, flags=re.I))
    m = re.match(r"^Up to (\w+)\s+([A-Za-z][\w' \-]*?)\s+(?:in this Unit\s+)?(?:may|each)", o, re.I)
    if m:
        n = {"one":1,"two":2,"three":3,"four":4,"five":5}.get(m.group(1).lower())
        if n: return (m.group(2).strip().title(), n, re.sub(r"^Up to \w+\s+[A-Za-z][\w' \-]*?\s+(?:in this Unit\s+)?", "", o, flags=re.I))
    m = re.match(r"^One\s+([A-Za-z][\w' \-]*?)\s+(?:in this Unit\s+)?may\b", o, re.I)
    if m: return (m.group(1).strip().title(), 1, re.sub(r"^One\s+[A-Za-z][\w' \-]*?\s+(?:in this Unit\s+)?", "", o, flags=re.I))
    m = re.match(r"^(?:Any|Every|All)\s+([A-Za-z][\w' \-]*?)\s+(?:in this Unit\s+)?(?:with a [\w ]+\s+)?may\b", o, re.I)
    if m:
        model = m.group(1).strip().title()
        if model.lower() in ("model","models"): model = "Any model"
        return (model, "any", re.sub(r"^(?:Any|Every|All)\s+[A-Za-z][\w' \-]*?\s+(?:in this Unit\s+)?", "", o, flags=re.I))
    m = re.match(r"^This Model\s+(?:with a [\w ]+\s+)?(?:may|must)\b", o, re.I)
    if m: return ("Squad", 1, re.sub(r"^This Model\s+", "", o, flags=re.I))
    m = re.match(r"^The\s+([A-Z][\w' \-]*?)\s+(?:in this Unit\s+)?(?:with a [\w ]+\s+)?may\b", o)
    if m: return (m.group(1).strip(), 1, re.sub(r"^The\s+[A-Z][\w' \-]*?\s+(?:in this Unit\s+)?", "", o))
    return (None, None, None)

# --- predicate (what) -> upgrade dict ------------------------------------
LIST_RE = re.compile(r"from the ([\w' \-]+?)\s+[Ll]ist")

def parse_choices(frag):
    """'a Power fist (+15), Lightning claw (+10) or Thunder hammer (+15 points)'
       -> [{name,pts}]; returns None if it doesn't look like an inline choice list."""
    # strip leading 'for a/an/one '
    f = re.sub(r"^\s*for\s+(?:a |an |one |its |their )?", "", frag, flags=re.I)
    # split on commas and ' or '
    parts = re.split(r",|\bor\b", f)
    out = []
    for p in parts:
        p = p.strip().rstrip(".")
        if not p: continue
        nm = re.sub(r"\s*\(?\+\s*\d+\s*point.*$", "", p)
        nm = re.sub(r"\s*\(\s*\+\s*\d+\s*\)\s*$", "", nm).strip()
        nm = re.sub(r"\s+for$", "", nm).strip(" .")
        nm = re.sub(r"^(?:a|an|one)\s+", "", nm, flags=re.I)        # drop leading article
        nm = re.sub(r"\s*\(free\)\s*", "", nm, flags=re.I).strip()   # "(free)" tag
        nm = re.sub(r"\s+per Model$", "", nm, flags=re.I).strip()
        if not nm or len(nm) > 48: return None
        out.append({"name": nm[0].upper()+nm[1:], "pts": price(p)})
    return out or None

def predicate(model, limit, pred):
    """Return an upgrade dict, or None if not confidently parseable."""
    p = pred.strip()
    note = ""
    mnote = re.search(r"\bgaining\b.*$", p)
    if mnote: note = mnote.group(0).strip(" .,"); p = p[:mnote.start()].strip().rstrip(",")
    # cut trailing conditional asides
    p = re.sub(r"\s*\((?:not available|except|unless)[^)]*\)\s*", " ", p, flags=re.I).strip()

    up = {"model": model, "limit": limit}
    if note: up["note"] = note

    # exchange ("... exchanged for X" / "exchanged — select from the L list")
    m = re.search(r"(?:have its|have both its|have their|have)\s+(.+?)\s+exchanged\s*(?:for|[—,-]+)?\s*(?:select from\s+)?(.*)$", p, re.I)
    if m:
        replaces = m.group(1).strip(); rest = m.group(2).strip()
        up["replaces"] = replaces[0].upper()+replaces[1:]
        lm = LIST_RE.search(rest)
        if lm:
            up["list"] = lm.group(1).strip().title()+" List"
            # inline priced alternatives alongside the list -> extra dropdown entries
            extras = parse_choices(rest[:lm.start()] + " or " + rest[lm.end():]) or []
            PLACE = {"", "one item", "an item", "item", "one", "its", "their"}
            extras = [c for c in extras if c["name"].strip().lower() not in PLACE and c["pts"]]
            if extras: up["extraChoices"] = extras
            return up
        ch = parse_choices(rest)
        if ch:
            up["choices"] = ch
            if limit == 1 and len(ch) > 1: up["pickOne"] = True
            return up
        return None
    # additive item(s) from a list ("may/each select one item from the L list")
    m = re.search(r"(?:may each have|may select|must select|may have)\s+(?:one item|an item)?\s*from the ([\w' \-]+?)\s+[Ll]ist", p, re.I)
    if m and "exchanged" not in p:
        up["list"] = m.group(1).strip().title()+" List"; return up
    # take / be upgraded with / have one X selected — additive
    m = re.search(r"(?:may each take|may take|may be upgraded with|may each have|may have one|may have)\s+(.+)$", p, re.I)
    if m:
        rest = m.group(1).strip()
        # "up to two of the following ...: A (+x), B (+y)"
        mm = re.search(r"up to (\w+) of the following[^:]*:\s*(.+)$", rest, re.I)
        if mm:
            n = {"one":1,"two":2,"three":3}.get(mm.group(1).lower())
            ch = parse_choices(mm.group(2))
            if n and ch: up["limit"]=n; up["choices"]=ch; return up
            return None
        # multiple priced alternatives joined by 'or' ("a Legion standard (+10) or Company standard (+20)")
        if " or " in rest and re.search(r"\(\s*\+\s*\d+|\+\s*\d+\s*point", rest):
            ch = parse_choices(re.sub(r"\s+selected for (?:it|them).*$", "", rest, flags=re.I))
            if ch and len(ch) > 1:
                up["choices"] = ch
                if limit == 1: up["pickOne"] = True
                return up
        # single additive item, optional price (incl. 'for free')
        nm = re.sub(r"\s+selected for (?:it|them).*$", "", rest, flags=re.I)
        nm = re.sub(r"\s+for \+?\s*\d+\s*point.*$", "", nm, flags=re.I)
        nm = re.sub(r"\s+for free.*$", "", nm, flags=re.I)
        nm = re.sub(r"^(?:a |an |one |their )", "", nm.strip(), flags=re.I).strip(" .")
        if nm and len(nm) <= 48 and " or " not in nm:
            up["choices"] = [{"name": nm[0].upper()+nm[1:], "pts": price(rest)}]
            return up
    return None

def convert_unit(u, uid):
    opts = u.get("options", [])
    ups, residual = [], []
    for o in opts:
        model, limit, pred = subject(o)
        up = predicate(model, limit, pred) if model else None
        if up: ups.append(up)
        else: residual.append(o)
    return ups, residual

def main():
    write = "--write" in sys.argv
    tot_lines = tot_done = 0
    full = part = 0
    for fn in FILES:
        path = os.path.join(ROOT, "build", fn)
        data = json.load(open(path, encoding="utf-8"))
        for uid, u in data.get("units", {}).items():
            if uid in SKIP_UNITS or not u.get("options"): continue
            ups, residual = convert_unit(u, uid)
            n = len(u["options"]); done = n - len(residual)
            tot_lines += n; tot_done += done
            if done == n and n: full += 1
            elif done: part += 1
            mark = "OK " if not residual else ("~~ " if ups else "XX ")
            print(f"  {mark}{uid:40} {done}/{n}")
            for r in residual: print(f"        · {r[:95]}")
            if write and ups:
                u["upgrades"] = ups
                u["options"] = residual
        if write:
            json.dump(data, open(path, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"\n  lines converted: {tot_done}/{tot_lines} ({100*tot_done//max(tot_lines,1)}%)  "
          f"fully-covered units: {full}  partial: {part}")
    if write: print("  WROTE overlay files.")

if __name__ == "__main__":
    main()
