# Legion crests

Drop a legion symbol image here named `<army-id>.png` and it will replace the
generic group glyph (✠ / ✶) in the header crest, the Army Rules panel, and the
army picker. No code change needed — `crestMarkup()` in `index.html` loads
`app/crests/<id>.png` and falls back to the group glyph if the file is missing.

Recommended: square-ish, transparent background, light/monochrome so the accent
glow reads on the dark theme. ~64–128px is plenty (the header renders it at 22px,
the panel at 34px). PNG by default; if you'd rather ship SVG/WEBP, tell me and I'll
switch the `crestImg` extension for that legion.

Expected filenames:

| Army | File |
|---|---|
| Dark Angels | `dark-angels.png` |
| White Scars | `white-scars.png` |
| Space Wolves | `space-wolves.png` |
| Imperial Fists | `imperial-fists.png` |
| Blood Angels | `blood-angels.png` |
| Iron Hands | `iron-hands.png` |
| Ultramarines | `ultramarines.png` |
| Salamanders | `salamanders.png` |
| Raven Guard | `raven-guard.png` |
| Sons of Horus | `sons-of-horus.png` |
| Death Guard | `death-guard.png` |
| Emperor's Children | `emperors-children.png` |
| Iron Warriors | `iron-warriors.png` |
| Night Lords | `night-lords.png` |
| World Eaters | `world-eaters.png` |
| Thousand Sons | `thousand-sons.png` |
| Word Bearers | `word-bearers.png` |
| Alpha Legion | `alpha-legion.png` |
