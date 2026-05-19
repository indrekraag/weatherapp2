# Visual design pass — session log (2026-05-18)

This log captures the long visual iteration session on `index.html` after
the data architecture was already stable (CLAUDE.md "Recent changes —
PWA + multi-station + warnings session" covers that earlier work).

State at end of session: **uncommitted local changes to `index.html`**
only. No new files (other than this log). The git working tree should
show a single modified file.

---

## What changed, by area

### Body background — multi-layer "alive" feel
- `body` now carries the full background: three radial-gradient cyan/teal
  blobs + a vertical linear sweep that's a touch brighter on the same
  tone. `background-attachment: fixed` so the blobs anchor to the
  viewport regardless of scroll.
- Earlier attempt used `body::before` for the blobs but they were hidden
  behind opaque card / parent backgrounds (`position: fixed` + z-index
  pitfalls). Moving the blobs into `body`'s `background:` shorthand
  fixed it.
- Brightness on the gradient sweep dialled to ~10 % with the dropoff
  ending ~15 % earlier than the card edge (so the highlight reads
  behind the cards, not at the screen edges).

### Card material — "Liquid Glass"
- `--surface` lowered to `rgba(10,18,28,0.82)` (from 0.92) so the body
  background shows through faintly.
- Cards / buttons use a chamfered bevel: `box-shadow` with multiple
  insets (top-left highlight `rgba(255,255,255,0.18)`, bottom-right
  shadow `rgba(0,0,0,0.3)`, soft outer drop) plus a thin
  `border: 1px solid rgba(70,125,170,0.38)`.
- Saved iteration milestones as `/* Preset 1..9 */` comment blocks
  inside the CSS for design version tracking. Current production
  settings sit at the top of the CSS block; the presets below are
  rollback references.

### Topbar
- MADISE wordmark removed from the page top (kept on the home-screen
  icon only).
- Live clock centred in topbar-main. Soft refresh (↻) and hard refresh
  (⟲) buttons in topbar-sub, right-aligned. "Uuendatud" text shrunk to
  match the new compact topbar.

### Hetkeilm card — hero layout

```
+18.4°                              [ ICON ]
                                  NÕRK SADU
TUNDUB         9°
KASTEPUNKT     7°                  [RADAR][SAT]
TUUL           3.4 m/s ↑
SADU           0.0 mm/h
ÕHURÕHK     1014 hPa
NIISKUS         86 %
UV             3.2 Mõõdukas
NÄHTAVUS       25 km
ÖÖKÜLM        ei                   <— alt-loc starts below
KUREVERE
+17.4°         4.5 m/s ↑ · 0.0 mm/h
LÄÄNE-NIGULA
+18.1°         5.2 m/s ↑ · 0.0 mm/h
HAAPSALU
+18.3°         4.8 m/s ↑ · 0.0 mm/h
```

- Big temp on the left (`.wx-temp-big`, 50 px monospace).
- Condition **icon stacked above** condition text on the right
  (`.wx-cond-line` switched to `flex-direction: column`, items
  right-aligned, gap 4 px).
- Text uppercased — `text-transform: uppercase`, 14 px, letter-spacing
  1 px — same vocabulary as the row labels.
- "Tundub nagu" renamed to **Tundub**.
- Päikesetõusuni text colour set to the same plain colour as Järgmine
  täiskuu (no `rise`/`set` warm tint).

### Shared label column — `--label-col: 105px`
All three vertical contexts inside the Hetkeilm card share the same
value-column anchor at x = 105 px:

| Context        | CSS                                                      |
|----------------|----------------------------------------------------------|
| `.wx-meta`     | `grid-template-columns: var(--label-col) auto; column-gap: 0` |
| `.row-label`   | `min-width: var(--label-col)` (was 88 px)                |
| `.wx-station-row` | `grid-template-columns: var(--label-col) auto; column-gap: 0` |

105 px is just wider than "KASTEPUNKT" at 14 px uppercase / 1 px
letter-spacing (~95 px rendered) so the longest label has a few px of
breathing room before the value column.

### Alt-location station blocks (Kurevere / Lääne-Nigula / Haapsalu)
- HTML restructured: title alone on line 1; line 2 is a 2-col grid
  with `temp-cell` in col 1 (temp stays at x=0 like the original
  layout) and `wind-rain-cell` in col 2 (left edge at x=105 lines up
  with the TUUL data column above).
- Wind / rain order swapped: wind first, then rain after a `·`
  separator.
- Both wind and rain values now use `val.sm` (17 px) to match
  Tundub/Kastepunkt.
- **Bug fix:** `renderStation()` was assigning
  `el.className = 'val ' + (t < 0 ? 'cold' : 'warm')` on the alt-loc
  temp during updates, which stripped the `sm` class. Changed to
  `'val sm ' + …`.

### Diffuse-glass weather icons (replaced emoji)
Replaced the `☀️ 🌤️ ⛅ ☁️ 🌧️ 🌦️ 🌙` set with inline SVG icons that
match the card/button glass material.

- Library: `WX_ICONS = { sun, moon, cloud, partly-day, partly-night,
  rain, light-rain }` (light-rain falls back to `rain` at night).
- Shared `<defs>`: `cl-grad` (white→cyan vertical), `sun-grad`
  (cream→amber→orange), `moon-grad` (white→pale-cyan), `cl-shine` /
  `sun-shine` (radial highlight overlay), `drop-grad` (for raindrop
  fills).
- Cloud silhouette is a Lucide-derived 2-bump path scaled into a
  64×64 viewBox (`CLOUD_PATH`); a smaller variant (`CLOUD_PATH_SM`)
  is used as the secondary element behind the sun/moon for "partly"
  and "light-rain".
- Container `.wx-cond-icon-big` is 48×48 inline-flex with
  `filter: drop-shadow(0 2px 3px rgba(0,0,0,0.5))
  drop-shadow(0 0 8px rgba(126,207,255,0.2))` — same material as the
  chamfered card / button bezels.
- `currentSkyText()` was changed to return `{ text, icon: <key> }`
  instead of `{ text, icon: <emoji> }`. The renderer does
  `byId('wx-cond-icon').innerHTML = WX_ICONS[sky.icon]`.

### Row spacing
- `.row` `margin-bottom: 15px → 4px` to match the `row-gap: 4px`
  inside `.wx-meta`.
- Added `line-height: 1` on `.row` so the browser's inherited ~1.2
  line-height doesn't quietly add ~3 px between rows.

### Font consistency
- Every data value inside the Hetkeilm card is `val.sm` (17 px).
- Every row label and meta label is 14 px uppercase 1 px-letter-spaced
  (`.row-label`, `.wx-meta-label` share this vocabulary).
- 2-col cards: Päike Tõus / Loojang reduced from `val.sm` to `val.xs`
  (15 px) so they match the Kuu values.
- Row icons globally hidden (`.row-icon { display: none }`). The
  inline diffuse-glass SVG vocabulary is the replacement.

---

## Known open visual nits (next session candidates)

- **Cloud silhouette** — current path is a clean 2-bump Lucide-derived
  shape. If Indrek still finds it too plain, redraw with a smoother
  3-bump path (left/mid/right humps with a flat base).
- **Text-bottom = temp-bottom alignment** — the earlier strict
  alignment ("Nõrk sadu text bottom on the big temp bottom") is no
  longer enforced now that the icon sits above the text. Items
  naturally flow from the top of `.wx-hero-right`. If we want strict
  bottom-alignment back, the cleanest fix is to pull `.wx-meta` out of
  `.wx-hero-row` so the row's height is governed by `max(temp,
  cond-line)` only.
- **RADAR / SAT button placement** — abs-positioned to the bottom-right
  of `.wx-hero-right`. With the new row spacing this lands near
  Kastepunkt's baseline. Sanity-check this is still where Indrek wants
  the buttons.

---

## How to commit and push (when ready)

From `~/wa2/`:

```bash
git status                # should show only index.html + CLAUDE.md + progress.md
git diff                  # review
git add -A
git commit -m "Visual design pass: liquid glass, hetkeilm hero, diffuse-glass icons, shared label column"
git push
```

Then on iPhone: hard-refresh via the topbar ⟲ button (or remove + re-add
the home-screen icon if SW caching gets in the way).

---

# Follow-up session — flat diffused glass (2026-05-19)

Short session after the bevel work was committed (`d55c211`).

## Preset 11 — flat diffused glass (committed `b63f611`)

The bevel made the cards feel skeuomorphic against the modern glass
material. Replaced with a flatter treatment that keeps the diffuse
refraction but drops the 3D-ness.

**Kept:**
- `backdrop-filter: blur(24px) saturate(140%)` (the actual glass effect)
- SVG noise grain (organic frosted texture)
- A faint top-down white highlight (`linear-gradient(to bottom,
  rgba(255,255,255,0.04) 0%, transparent 40%)`) — hint of light without
  any "lit edge" feel
- A single soft outer drop shadow (`0 8px 28px rgba(0,0,0,0.35)`)
- A 1 px hairline white inset highlight on the top edge

**Removed:**
- All chamfered bevel halos (the negative-spread inset shadows)
- Sharp 1 px edge highlights (top/left white, bottom/right black)
- The 135° diagonal sheen and the bottom 6 % black fade
- The radial cyan inner glow
- The bottom-right corner shadow concentration
- The cyan-tinted border (now plain `rgba(255,255,255,0.08)`)

Same treatment applied to `.topbar` so the topbar and cards share one
material.

The chamfered-bevel state is preserved as **Preset 10** in the
design-presets comment for rollback.

## CSS-parsing bug — nested `/* */` in Preset 10 comment

After saving Preset 10 the page rendered with **all text black**. Root
cause: the preset description contained an inline annotation written as
`/* cyan-ish edge */` *inside* the outer `/* */` CSS comment block.
CSS doesn't allow nested block comments — the inner `*/` closes the
outer comment early, and everything that follows up to the next `*/`
becomes invalid CSS that the parser tries (and fails) to interpret.
The casualty in our case was the `html, body { color: var(--text) }`
rule that came shortly after, which the parser dropped. With no
explicit text colour, the body inherited the browser-default black.

Fix: changed the inline annotation to `// cyan-ish edge` (no parse
meaning to CSS — just text inside the still-open outer comment).

**Lesson:** in the design-presets comment, never use `/* */` for
inline annotations. Use `//` instead, even though it isn't a CSS
comment token — inside a `/* */` block it's just characters.

There is a tiny check command for this:

```bash
python3 -c "
import re
html = open('index.html').read()
m = re.search(r'<style>(.*?)</style>', html, re.DOTALL)
css = m.group(1) if m else ''
i, depth = 0, 0
while i < len(css):
    if css[i:i+2] == '/*':
        if depth: print(f'NESTED /* line {css[:i].count(chr(10))+1}')
        depth += 1; i += 2
    elif css[i:i+2] == '*/':
        depth -= 1
        if depth < 0: print(f'STRAY */ line {css[:i].count(chr(10))+1}'); depth = 0
        i += 2
    else: i += 1
print('final depth:', depth)"
```

Run this whenever the page suddenly renders in default browser styles.

## Centering experiment — tried, reverted

Tried pulling `.wx-temp-big` out of `.wx-hero-row` and making it a
standalone full-width centered block above the row, with the meta on
the row's left and the icon+text+buttons on the row's right.

Verdict from Indrek: doesn't fit. Reverted — temp is back on the
left, meta directly under it, icon+text+buttons on the right of the
flex row. No code change persists from this experiment; working tree
is clean.

If revisited later: the centering itself works fine technically, the
issue is visual. A centered temp by itself makes the card feel
asymmetric because the icon+text are still to one side. A "full
centered" layout would require putting the icon+text *below* the temp
(centered too) instead of beside it.

## Material-design open questions for next session

These are the candidates if Indrek still feels the page reads as
"off." Ranked by how cheap they are to try:

1. **Mute the cyan saturation.** Border, card title, `cold` colour,
   accent button text, and body blobs all carry cyan/teal. The page
   reads as "blue+techy." Experiment: shift `--accent`, `--cold`, and
   `--border` toward near-white with very faint cyan tint. Reserve
   strong colour for meaningful signal only (the warm/cold temp
   gradient).
2. **Single font family.** Currently values use `ui-monospace`
   (terminal feel) while labels use `system-ui`. Try `system-ui`
   everywhere with `font-variant-numeric: tabular-nums` for column
   alignment.
3. **Body bg toned down.** With the bevels gone the body blobs are
   more visible through the cards. If still too saturated, dial the
   blob alphas down 30-40% or drop one of the three.
