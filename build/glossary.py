#!/usr/bin/env python3
"""Build data/glossary.json — name -> description for Special Rules, Wargear, and Traits.
Heading-styled paragraphs in the docx mark entry names; following body paragraphs are the
description. Stdlib only."""
import zipfile, re, json, os
from xml.etree import ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC  = os.path.join(ROOT, "2- Playtest Stage")
OUT  = os.path.join(ROOT, "data", "glossary.json")
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'

PLACEHOLDER = re.compile(r'(LORE GOES HERE|TEMPLATE|GAMBIT GOES HERE|NAME GOES HERE|XXXXX|Text goes here|Go look at)', re.I)

def paras(path):
    """Yield (style, bold, text) for each non-empty paragraph."""
    z = zipfile.ZipFile(path)
    root = ET.fromstring(z.read('word/document.xml'))
    for el in root.find(W+'body'):
        if el.tag != W+'p':
            continue
        txt = ''.join(t.text or '' for t in el.iter(W+'t')).strip()
        if not txt:
            continue
        pPr = el.find(W+'pPr'); style = ''
        if pPr is not None:
            s = pPr.find(W+'pStyle')
            if s is not None: style = s.get(W+'val') or ''
        r = el.find(W+'r'); bold = False
        if r is not None:
            rPr = r.find(W+'rPr')
            if rPr is not None and rPr.find(W+'b') is not None: bold = True
        yield style, bold, txt

def by_headings(path, levels=("Heading2","Heading3","Heading4"), skip=()):
    """Group body paragraphs under their preceding heading."""
    out = {}; cur = None; buf = []
    def flush():
        if cur and buf:
            body = "\n".join(b for b in buf if not PLACEHOLDER.search(b)).strip()
            if body and cur not in skip:
                out[cur] = body
    for style, bold, txt in paras(path):
        if style in levels:
            flush(); cur = txt.strip(); buf = []
        elif style in ("Title","Heading1"):
            flush(); cur = None; buf = []
        else:
            if cur: buf.append(txt)
    flush()
    return out

def special_rules():
    return by_headings(os.path.join(SRC, "!6 - Asuryani Special Rules.docx"), levels=("Heading2",))

def wargear():
    return by_headings(os.path.join(SRC, "!4 - Asuryani Wargear.docx"))

def traits():
    path = os.path.join(SRC, "!2 - Asuryani Traits.docx")
    out = by_headings(path, skip=("Faction Traits","Traits","World-Runes","Allegiance"))
    # also capture the bold "[Keyword] - description" one-liners near the top
    for style, bold, txt in paras(path):
        m = re.match(r'^\s*(\[?[\w\' \-]+?\]?)\s*[-–]\s+(.+)$', txt)
        if bold and m and len(m.group(1)) < 24 and not PLACEHOLDER.search(txt):
            name = m.group(1).strip()
            out.setdefault(name, m.group(2).strip())
    return out

def core_rules():
    """Hand-authored core special rules, summarised from the rulebook."""
    p = os.path.join(ROOT, "data", "coreRules.json")
    if not os.path.exists(p):
        return {}
    d = json.load(open(p, encoding="utf-8"))
    return {k: v for k, v in d.items() if not k.startswith("_")}

def main():
    g = {
        "specialRules": special_rules(),
        "coreRules": core_rules(),
        "wargear": wargear(),
        "traits": traits(),
    }
    json.dump(g, open(OUT, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    for k, v in g.items():
        print(f"{k}: {len(v)} entries")
    print("\nspecial rules:", ", ".join(sorted(g["specialRules"])))

if __name__ == "__main__":
    main()
