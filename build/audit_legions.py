#!/usr/bin/env python3
"""Read-only audit: compare each legion's UNIQUE units against the Liber OCR text.

The 60 generic Legiones Astartes datasheets live in overlay_legion-common.json and are
already authored, so this focuses on each legion's legion-specific units. For every such
unit it reports: whether a matching datasheet was found in the book, the data points value
vs the points OCR'd from that page (OCR garbles digits — verify visually), and whether the
data carries any options/wargear (90% of imported units have none). It also lists datasheet
titles found in the book that aren't matched by ANY legion's data (candidate missing units).

Usage:  python3 build/audit_legions.py            # all legions -> /tmp/legion_audit.md
Source of truth: /tmp/liber_astartes_ocr.txt (loyalists), /tmp/liber_hereticus_ocr.txt (traitors).
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOYAL = {"dark-angels","white-scars","space-wolves","imperial-fists","blood-angels",
         "iron-hands","ultramarines","salamanders","raven-guard"}
GENERIC = set(json.load(open(f"{ROOT}/build/overlay_legion-common.json"))["units"].keys())

def norm(s):
    return re.sub(r"[^A-Z0-9]", "", (s or "").upper())

def load_pages(path):
    """Return list of {page, title, text, norm_head, is_sheet} for one OCR file."""
    if not os.path.exists(path):
        return []
    pages = []
    raw = open(path, encoding="utf-8").read()
    parts = re.split(r"===== PDF PAGE (\d+) =====\n", raw)
    for i in range(1, len(parts), 2):
        num = int(parts[i]); text = parts[i+1]
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        head = " ".join(lines[:6])
        is_sheet = bool(re.search(r"UNIT\s*COMPOSITION", text, re.I))
        # the datasheet title is the leading ALL-CAPS line(s) before UNIT COMPOSITION
        title = lines[0] if lines else ""
        pages.append({"page": num, "title": title, "text": text,
                      "norm_head": norm(head), "is_sheet": is_sheet})
    return pages

def find_points(text):
    m = re.search(r"Points?\s*[:\-]?\s*([0-9Oo]{1,4})", text)
    return m.group(1) if m else "?"

def match_unit(name, pages):
    """Find the datasheet page whose heading contains the unit name (normalized)."""
    n = norm(name)
    if not n: return None
    # prefer datasheet pages; fall back to any page
    for sheets_only in (True, False):
        for p in pages:
            if sheets_only and not p["is_sheet"]:
                continue
            if n in p["norm_head"]:
                return p
    # last resort: match on the longest token (e.g. a character surname)
    toks = [t for t in re.split(r"[^A-Za-z0-9]+", name) if len(t) >= 5]
    toks.sort(key=len, reverse=True)
    for t in toks[:1]:
        for p in pages:
            if p["is_sheet"] and norm(t) in p["norm_head"]:
                return p
    return None

def main():
    astartes = load_pages("/tmp/liber_astartes_ocr.txt")
    hereticus = load_pages("/tmp/liber_hereticus_ocr.txt")
    if not astartes or not hereticus:
        print("OCR text not ready yet — run build/ocr_all.sh first.", file=sys.stderr)
    out = ["# Legion unit audit — data vs Liber (OCR)\n",
           "_Auto-generated, read-only. Stats trust BSData; OCR points/options are advisory "
           "(digits garble — verify against the book image). Focuses on legion-unique units; "
           "the 60 generic datasheets are authored in overlay_legion-common.json._\n"]
    matched_titles = {"Astartes": set(), "Hereticus": set()}
    summary = []
    for d in sorted(x for x in os.listdir(ROOT) if x.startswith("data_")):
        aid = d.replace("data_", "")
        book = "Astartes" if aid in LOYAL else "Hereticus"
        pages = astartes if aid in LOYAL else hereticus
        units = json.load(open(f"{ROOT}/{d}/units.json"))
        uniq = [u for u in units if u["id"] not in GENERIC]
        out.append(f"\n## {aid}  ({book})  — {len(uniq)} legion-unique units\n")
        out.append("| unit | slot | data pts | book pts | opts | wargear | book page |")
        out.append("|---|---|--:|--:|--:|--:|---|")
        nf = 0
        for u in sorted(uniq, key=lambda x: x["name"]):
            p = match_unit(u["name"], pages)
            opts = len(u.get("options") or [])
            wg = sum(len(v) for v in (u.get("wargear") or {}).values())
            if p:
                matched_titles[book].add(p["page"])
                bp = find_points(p["text"]); pg = str(p["page"])
            else:
                nf += 1; bp = "—"; pg = "**NOT FOUND**"
            flag = "" if p else " ⚠"
            out.append(f"| {u['name']}{flag} | {u.get('slot','')} | {u.get('pointsValue','')} "
                       f"| {bp} | {opts} | {wg} | {pg} |")
        summary.append((aid, book, len(uniq), nf))
        out.append(f"\n_{len(uniq)-nf}/{len(uniq)} matched in book; {nf} not found._\n")

    # datasheet pages in each book not matched by any legion-unique data unit
    for book, pages in (("Astartes", astartes), ("Hereticus", hereticus)):
        unmatched = [p for p in pages if p["is_sheet"] and p["page"] not in matched_titles[book]]
        out.append(f"\n## Unmatched datasheet pages — Liber {book} "
                   f"({len(unmatched)} pages)\n")
        out.append("_Datasheet pages (have 'Unit Composition') not matched to any legion-unique "
                   "unit. Many are the 60 generic datasheets (expected); the rest are candidate "
                   "missing/mismatched units — scan the titles._\n")
        for p in unmatched:
            out.append(f"- p{p['page']}: {p['title'][:70]}")

    open("/tmp/legion_audit.md", "w", encoding="utf-8").write("\n".join(out))
    print("Wrote /tmp/legion_audit.md\n")
    print(f"{'legion':18} {'book':10} {'unique':>6} {'notfound':>8}")
    for aid, book, n, nf in summary:
        print(f"{aid:18} {book:10} {n:6d} {nf:8d}")
    print(f"\nTOTAL not-found: {sum(s[3] for s in summary)} / {sum(s[2] for s in summary)}")

if __name__ == "__main__":
    main()
