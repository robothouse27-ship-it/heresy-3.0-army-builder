# Heresy 3.0 Army Builder

A shareable, self-hosted army list builder for the custom **Asuryani (Eldar)** HH3.0 playtest
ruleset. Single-file web app, works offline. The rules ship **encrypted** — the served files
contain only ciphertext, so the app can live on a **public** host (GitHub Pages) yet stay
readable only to people who have the passphrase.

## Quick start

Open **`index.html`** in a browser and enter the passphrase. The app loads `app/data.enc.js`
(the encrypted rules) and decrypts it in your browser with the passphrase — wrong passphrase,
no data. Everything runs locally; no internet needed after the page loads.

> If opening `index.html` directly via `file://` misbehaves, serve the folder instead:
> `python3 build/serve.py` then visit `http://127.0.0.1:8731`.

## What's in it

- **58 units** across all 16 battlefield-role slots (Primarch → Lords of War)
- **107 weapon profiles** (ranged + melee) resolved into each datasheet
- **22 wargear / equipment lists** wired into unit upgrade options
- **Real HH3.0 detachment system** (from the core rulebook): start with a Crusade Primary
  Detachment, fill its command slots to unlock Auxiliary/Apex detachments, bolt on
  Allied / Lord of War / Warlord with their point caps and thresholds enforced
- Live points counter, detachment legality checker, datasheets with full statlines
- Save / load lists (browser localStorage), JSON export/import, print-friendly view
- **Playtest tools:** tag any unit OP / Underpowered / Balanced and attach notes

## Updating the rules

The source of truth is the Word/Excel files in `2- Playtest Stage/`. After you edit them, run
the three-step build, **then commit and push the encrypted bundle**:

```bash
python3 build/extract.py            # unit docx/xlsx        -> data/*.json
python3 build/glossary.py           # rules/wargear/traits  -> data/glossary.json
python3 build/bundle.py             # data/*.json           -> app/data.js  (plaintext, git-ignored)
PW='Spaceelfs' node build/encrypt.js  # app/data.js         -> app/data.enc.js  (encrypted, committed)
git add app/data.enc.js && git commit -m "rules update" && git push
```

Reload the app (and re-enter the passphrase). `extract.py`/`bundle.py` are pure-Python stdlib;
`encrypt.js` uses Node's built-in crypto.

- `build/extract.py` — parses the docx unit files + weapons spreadsheet into JSON in `data/`.
- `build/glossary.py` — parses the Special Rules / Wargear / Traits docs into `data/glossary.json` (powers the clickable term pop-ups on datasheets).
- `build/bundle.py` — packs `data/` into the single plaintext `app/data.js`.
- `build/encrypt.js` — AES-256-GCM encrypts the bundle into `app/data.enc.js` (the only data file published).

### Health check

Before committing a data or app change, run:

```bash
bash build/check.sh
```

It validates every JSON file under `data/`/`data_*/` parses, runs the points engine
(`build/test_engine.js`) over the bundle and asserts 0 parse errors, and flags any
stray `console.log`/`debugger` left in `index.html`. Exits non-zero on any failure.

You can also hand-edit anything under `data/` directly (e.g. tweak a points cost), then re-run
`bundle.py` + `encrypt.js` — handy for "what if this cost 5 less" experiments.

## Privacy model (public repo + encrypted data)

- The repo is **public** so you can share a plain link, but it contains **no readable rules** —
  only `app/data.enc.js`, which is AES-256-GCM ciphertext. `.gitignore` keeps the plaintext
  sources (`2- Playtest Stage/`, `data/`, `app/data.js`, the PDFs) **out of git entirely**.
- The passphrase derives the decryption key in-browser (PBKDF2-SHA256, 200k iterations). Without
  it, the served files are useless.
- **Tradeoff:** anyone you give the passphrase to can read and re-share the rules. This stops
  random discovery, search indexing, and casual snooping — not a determined person who has the
  passphrase. Right level for sharing with a playtest group.
- **Change the passphrase:** re-run the build with `PW='NewPass' node build/encrypt.js`, commit
  `app/data.enc.js`, and tell your group the new word. (Nothing else to edit.)
- **Keep your plaintext rules safe:** they live only on your machine (git-ignored). Back up the
  folder, or mirror `2- Playtest Stage/` + `data/` to a separate **private** repo if you want
  version history of the rules themselves.

## Layout

```
index.html              the app (single file)            [committed]
app/data.enc.js         encrypted rules bundle           [committed]
build/                  extract.py, bundle.py, encrypt.js, serve.py   [committed]
app/data.js             plaintext bundle                 [git-ignored]
data/                   structured JSON rules            [git-ignored]
2- Playtest Stage/      source docx/xlsx rules           [git-ignored]
rosters/  playtests/    local saved data                 [git-ignored]
```

## Detachments

The army-building rules live in **`data/detachments.json`** — fully data-driven, so you can
reshape any detachment template during playtesting (edit the file, re-run the build below, reload).
The templates were transcribed from the HH3.0 core rulebook's Crusade Force Organisation Chart
(p.284) and cross-checked against the raw scan. Slots flagged `"verify": true` are readings of
the monochrome chart icons I wasn't 100% sure of (the vehicle/command icons are solid; a few
infantry-role mappings — Combat Pioneer / Shock Assault / First Strike / Heavy Support — are best
guesses). Confirm or change those role names whenever you like.

Unlock logic enforced by the app: each filled **High Command** slot → 1 Apex *or* Auxiliary;
each filled **Command** slot → 1 Auxiliary; Allied ≤25% (different faction); Lord of War needs
1,000+ pts; Warlord needs 3,000+ pts; Warlord + Lord of War units ≤25% combined.

## Notes / known limits

- The points engine auto-models squad size, character upgrades, and wargear-list picks. Each
  unit also has a manual **"Adjust pts"** field as an escape hatch for anything unusual.
- Allied "different faction" isn't enforced yet (the app is single-faction Asuryani for now).
- One terrain piece (Holo-Field Defence Line) has no statline by design.
