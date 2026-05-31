# Madise Ilmaradar

Personal PWA weather screen for our country house in Madise, western Estonia (58.81627°N, 23.74447°E). One self-contained HTML file served by GitHub Pages, installable to iPhone/Android home screens as a fullscreen web app.

- **Repo:** https://github.com/indrekraag/weatherapp2
- **Live:** https://indrekraag.github.io/weatherapp2/
- **Local folder:** `/Users/indrekraag/wa2/`

This file is the project bible. **Read it in full at the start of every session before doing anything else.** It auto-loads in Claude Code when you work in this folder. Update it whenever something non-obvious changes.

---

## Session start procedure

1. Read this entire file
2. `git status` to check working tree
3. `git pull` to fetch latest from GitHub
4. Summarize **Current state** (bottom of file) back to me so I can confirm or correct
5. Ask what we're working on before changing anything

## Session end procedure

1. `git status` to review what changed
2. Update the **Recent changes** and **TODO** sections of this file if anything material happened
3. Stage, commit, push:
   ```
   git add -A
   git commit -m "<descriptive message>"
   git push
   ```
4. Confirm the push succeeded before closing

---

## What the app shows

All in Estonian. Top-down stack:

- **Topbar** — pulse-dot, location (Madise), live clock, "uuendatud" timestamp with stale-after-10min amber indicator, **soft refresh** (↻) and **hard refresh** (⟲ — clears localStorage + SW caches, force-reloads) buttons
- **Meteo warning row** — slim 1-line strip: "Hoiatusi pole" muted when no active CAP warnings for Lääne county; coloured by severity (minor=yellow, moderate=amber, severe/extreme=red) when active. Translated to Estonian.
- **Storm/heavy-rain alert banner** — transient banner from Open-Meteo forecast for next 12 h (separate from the persistent meteo warning row above)
- **Hetkeilm** (current weather): big temp hero + condition; rows for tundub-nagu, kastepunkt; then *two inline weather-station sub-blocks* showing Kurevere (tarktee road station) and Lääne-Nigula + Haapsalu (EMHI) with temp · precip · wind ↑ each; then full data rows (tuul, sadu, rõhk, niiskus, UV, nähtavus, öökülm + frost warning)
- **Täna tunniti** — horizontal hourly strip (4 tiles always fit, scroll for more), "Võimaliku saju alguseni: …" caption
- **7 päeva** — horizontal daily strip (4 tiles fit, scroll for more)
- **Päike** — shared **card-hero** at top (sun disc with day/night toggle + day length + "päikest" caption), then Tõus / Loojang / Loojanguni rows with azimuth in degrees beside each rise/set time
- **Kuu** — shared **card-hero** at top (moon phase emoji + phase name + illumination %), then Tõus / Loojang / Järgmine täiskuu rows with azimuth in degrees beside each rise/set time
- **Õietolm** (pollen): Üldine, Kask, Hein, Lepp
- **Virmalised** (aurora): 24h max Kp (with G-scale label), Tõenäosus (Ovation visibility % at Madise), Bz (solar wind), 72h mini bar-chart (24 cells × 3 h, colour-coded by storm tier)

## Data sources

All endpoints listed below are confirmed CORS-open from `indrekraag.github.io` **unless noted otherwise**.

- **Open-Meteo** `api.open-meteo.com/v1/forecast?…&models=ecmwf_ifs` — ECMWF IFS model output (~9 km grid). Current + hourly + daily + 7-day forecast.
- **Open-Meteo Air Quality** `air-quality-api.open-meteo.com/v1/air-quality` — pollen
- **NOAA SWPC** (aurora / space weather):
  - `services.swpc.noaa.gov/products/noaa-planetary-k-index-forecast.json` — 3-day Kp forecast (`{time_tag, kp, observed, noaa_scale}` array; `observed` is `"observed"` or `"predicted"`)
  - `services.swpc.noaa.gov/json/ovation_aurora_latest.json` — Ovation aurora visibility model (lat/lng grid of probabilities)
  - `services.swpc.noaa.gov/products/solar-wind/mag-1-day.json` — solar wind interplanetary magnetic field (Bz is what we read)
  - NOTE: NOAA changed the planetary-k-index JSON shape from array-of-arrays to array-of-objects (see `renderAurora` / `renderKpForecast`).
- **Estonian Transport Administration (tarktee.mnt.ee) — ArcGIS REST**:
  - `tarktee.mnt.ee/tarktee/rest/services/road_weather_stations/MapServer/0/query?where=site_name='Kurevere'&outFields=*&f=json` — Kurevere road weather station (air_temp, road_temp, road_status, precipitation_type/intensity, wind_speed/dir, air_humidity, visibility, measurement_time)
  - Other DATEX endpoints under `/api/v1/datex/…` require auth (cookie-based) and have **no CORS** — only the ArcGIS REST endpoints are open.
- **EMHI (Estonian Weather Service)** `ilmateenistus.ee/ilma_andmed/xml/observations.php` — **CORS-closed, Cloudflare-bot-protected**. We bridge it via GitHub Actions (see Architecture below). Has 152 stations including Lääne-Nigula (WMO 26124), Haapsalu (26123), and many more.
- **MeteoAlarm** `feeds.meteoalarm.org/feeds/meteoalarm-legacy-atom-estonia` — Pan-European warning aggregator, CAP/ATOM format. **CORS-closed** — same GH Actions bridge. (Tip: Accept header must be `*/*` — strict `application/atom+xml` returns 406.)
- **Local astronomy** — sun rise/set + altitude/azimuth via Meeus simplified algorithm; moon ecliptic position via leading-term Brown lunar theory; moonrise/set by iterating 10-min altitude crossings.

If you ever want raw EMHI station readings without going through our bridge, you can run `python3 scripts/fetch_emhi.py` locally — it writes `data/emhi.json` (gitignored).

## Architecture

```
~/wa2/
├── index.html                          # single-file PWA (CSS + JS inline)
├── manifest.json                       # PWA install metadata
├── sw.js                               # service worker (stale-while-revalidate app shell)
├── icons/
│   ├── generate_icons.py               # PIL script — regenerates all icon sizes
│   └── *.png                           # 180 / 192 / 512 + 512-maskable + 16/32 favicons
├── scripts/
│   └── fetch_emhi.py                   # CORS bridge: fetches EMHI + MeteoAlarm,
│                                       # writes data/emhi.json with stations + warnings
├── screenshots.py                      # Playwright multi-viewport screenshotter
├── .github/workflows/emhi.yml          # cron */15 + workflow_dispatch + push trigger;
│                                       # runs fetch_emhi.py; force-pushes emhi.json to
│                                       # 'data' orphan branch (single rolling commit)
├── .gitignore                          # excludes .venv, shots/, data/, backup files
└── CLAUDE.md                           # this file
```

**Data flow:**

1. Service worker pre-caches the app shell. Stale-while-revalidate on same-origin assets; pass-through on weather APIs (those are cached in localStorage instead).
2. On page load, `hydrateFromCache()` reads each `wx.*` key from localStorage and renders immediately — app shows last-known data even offline.
3. Then `fetch*` functions run in parallel:
   - `fetchWeatherAndForecast()` → Open-Meteo
   - `fetchPollen()` → Open-Meteo air quality
   - `fetchKpForecast()` / `fetchOvation()` / `fetchSolarWind()` → NOAA SWPC
   - `fetchKurevere()` → tarktee ArcGIS REST (road weather station)
   - `fetchLaaneNigula()` → first tries same-origin `data/emhi.json` (for local dev), falls back to `raw.githubusercontent.com/indrekraag/weatherapp2/data/emhi.json` (production). Single fetch populates **three** UI areas via the same payload: Lääne-Nigula station, Haapsalu station, and the meteo warning row.
4. Every successful response is saved via `saveCache(key, data)` with a 6 h TTL.
5. setInterval re-fetches each source on its own cadence (see Conventions).

**Why the EMHI/MeteoAlarm bridge:** Both endpoints are CORS-closed and Cloudflare-bot-protected, so free public CORS proxies (corsproxy.io, allorigins.win) get blocked. Instead, the GH Actions workflow runs every 15 min in GitHub's data centers, fetches the XML, parses it into compact JSON, and **force-pushes a single rolling commit** to a `data` orphan branch in this same repo. The PWA reads from `raw.githubusercontent.com/indrekraag/weatherapp2/data/emhi.json` — raw.githubusercontent.com sends `Access-Control-Allow-Origin: *`, so it works from any browser origin. Main branch stays clean (no data commits).

## Conventions

- **Language:** Estonian throughout
- **Location label:** "Madise" (was "Keravere" before the 2026-05-18 rebrand)
- **Coordinates:** 58.81627, 23.74447 — hardcoded in `CONFIG.lat`, `CONFIG.lng` (index.html)
- **Style:** vanilla JS, XMLHttpRequest (not fetch), no dependencies, no framework
- **Refresh cadence (intervals):**
  - Open-Meteo weather: 5 min
  - Open-Meteo pollen: 1 h
  - NOAA Kp forecast: 30 min
  - NOAA Ovation + solar wind: 5 min
  - Tarktee Kurevere: 5 min
  - EMHI Lääne-Nigula + Haapsalu + warnings (one fetch): 5 min (CDN cache TTL ~5 min)
  - Sun times: 30 min (recompute)
  - Moon phase + rise/set: 1 h
  - Sun countdown DOM tick: 1 s
  - Full page reload: 2 h (safety belt for long-running tabs)
- **Stale indicator:** the "uuendatud" timestamp turns amber if data is >10 min old
- **Pair-card alignment:** Päike and Kuu share `.card-hero` class so their first data row (Tõus) lines up across both cards
- **Pair-card alignment:** Õietolm and Virmalised share the icon-as-left-rail row layout for consistency
- **Forecast tiles:** `flex: 0 0 calc((100% - 24px) / 4)` — exactly 4 tiles always visible regardless of viewport, scroll for more, slim 4 px scrollbar, scroll-snap

## Local development

```bash
cd ~/wa2
python3 -m http.server 8123          # serves on localhost:8123
```

- **Mac Chrome:** `http://localhost:8123` → DevTools → Application tab for SW/manifest/cache debugging
- **iPhone over hotspot:** when the Mac is on iPhone Personal Hotspot, the phone reaches the Mac at `http://172.20.10.8:8123` (check current LAN IP with `ipconfig getifaddr en0`)
- **Safari Responsive Design Mode:** Develop menu → Enter Responsive Design Mode (⌃⌥⌘R). iPhone 15 Pro Max viewport is **430 × 932**. Note: safe-area-insets aren't simulated, so the phone view in standalone mode looks slightly different.

### Multi-size screenshot pipeline (Playwright)

```bash
source .venv/bin/activate                    # one-time, then reuse the venv
python3 screenshots.py                       # all device sizes
python3 screenshots.py android-small pixel7  # subset
```

Devices defined in `screenshots.py`:

| Name | Size | Notes |
|---|---|---|
| `android-small` | 360 × 800 | Small Android floor |
| `pixel7` | 393 × 851 | Pixel 7 / iPhone 14 |
| `iphone14-plus` | 430 × 932 | iPhone 15 Pro Max / S22 Ultra |
| `fold-folded` | 320 × 800 | Z Fold folded (rare; accept some truncation) |
| `fold-unfolded` | 717 × 921 | Galaxy Fold unfolded |
| `ipad-mini` | 768 × 1024 | iPad mini portrait |

Outputs to `shots/` (gitignored).

### Manually regenerate `data/emhi.json` locally

```bash
python3 scripts/fetch_emhi.py
```

Writes a fresh snapshot to `data/emhi.json` (gitignored on main). The PWA's `fetchLaaneNigula` tries this same-origin file first before falling back to the production raw URL — handy for offline iteration on the warning row UI.

### Regenerate icons

```bash
cd icons
python3 generate_icons.py
```

Writes all 7 PNGs (180, 192, 512, 512-maskable, 16, 32, apple-touch-icon=180). Edit the MADISE wordmark or colors inside the script.

## Deployment

Push to `main` → GitHub Pages serves automatically. Propagation usually <1 min.

```bash
git add -A
git commit -m "..."
git push
```

The GitHub Actions workflow (`.github/workflows/emhi.yml`) has these triggers:
- `schedule: */15 * * * *` — auto-runs every 15 min
- `workflow_dispatch` — manually trigger from the Actions tab
- `push: paths: [scripts/fetch_emhi.py, .github/workflows/emhi.yml]` — auto-runs when script or workflow itself changes

It force-pushes to the `data` branch. The data branch is **never merged** back to main — it lives independently as a single rolling commit.

To refresh on iPhone after deploy: remove from home screen + re-add (otherwise the cached service worker may stick around). The "⟲ hard refresh" button in the topbar also clears localStorage + SW caches in-place if you don't want to reinstall.

## What NOT to do

- Don't introduce a build step or framework — this stays single-file vanilla HTML/JS
- Don't commit `.venv/`, `shots/`, `data/`, `.DS_Store`, `__pycache__/`, or `index_backup_pre_pwa.html`
- Don't use modern-only JS APIs without checking iOS Safari support — the user's iPhone is the primary device
- Don't break the offline cache — if you refactor fetch logic, keep `saveCache` + `hydrateFromCache` working
- Don't write to a DOM ID that doesn't exist (`byId('x').textContent = …` throws on null and **halts subsequent JS**). When deleting an HTML row, search the JS for `byId('that-id')` and remove the writes too. Hot tip: there's a Python one-liner near the bottom of this file that lists all orphan references.
- Don't auto-push without updating "Recent changes" if anything material happened
- Don't add the `Accept: application/atom+xml` header when fetching MeteoAlarm — it returns 406. Use `Accept: */*`.

### Orphan-ID checker (paste into terminal when debugging "JS died")

```bash
python3 -c "
import re
html = open('index.html').read()
refs = set(re.findall(r\"byId\(['\\\"]([a-zA-Z0-9-]+)['\\\"]\)\", html))
ids = set(re.findall(r' id=\"([a-zA-Z0-9-]+)\"', html))
print('orphans:', sorted(refs - ids))"
```

---

## Current state

**Status:** `index.html` is now a fully-external redesign (`redesign_90`, `6a67369`) replacing the prior in-repo Preset 11 build. The visual system, CSS architecture, and likely much of the JS has been rewritten by Indrek outside this repo (filename pattern `~/Downloads/madise-redesign{N}.html` or `~/Downloads/madise-redesign_{N}.html` — both numbering styles in use). As of 2026-05-31 the JS render layer **has** been read/edited (icon + rain-threshold work, see below) — confirmed the file is a fully functional app (~4150 lines, single main `<script>` block). Key render fns: `currentSkyText`, `weatherCodeToSVG`, `skyIconSVG`, `renderPrecipTypes`, `renderDaily`. `renderHourly` is an **empty stub** ("hourly-strip removed — now bar charts in forecast-card"), so the hourly weather-symbol surface is the 3-hourly **precip-type row** (`renderPrecipTypes`). The old CSS-class conventions (`.wx-cond-line`, `.wx-meta`, `.card-hero`, `--label-col`) are stale; the CSS layer is still un-audited. The prior in-repo build is preserved at `indexvana.html` on remote (created via the GitHub web UI as a backup before the swap to `redesign3`). Live: https://indrekraag.github.io/weatherapp2/

A local `python3 -m http.server 8123` runs persistently in `~/wa2/` for phone preview — when on regular WiFi the iPhone reaches the Mac at `http://192.168.1.209:8123` (Mac LAN IP), not the hotspot-only `172.20.10.8`.

## Recent changes (2026-05-31 — 7-day tap → day-detail bottom sheet)

Tap any day in the **7 päeva** strip → a glass **bottom sheet** opens showing that day's 24 h; **swipe left/right** to move between days without closing (native scroll-snap carousel, one panel per day). Built entirely in JS (no body-HTML edits), appended to `<body>` on first open.

- Per-day panel: header (weekday + `D. kuu`, e.g. "Teisipäev · 3. juuni"; day 0 = "Täna", day 1 = "Homme"), summary row (hi/lo, total precip, max wind, sunrise·sunset via `calcSunTimes`), then three `renderSpark` sparklines (temp / precip mm·h⁻¹ / wind, the last with direction arrows) + a **3-hourly condition-icon row** using the precip-aware `skyIconSVG`.
- **No extra network** — every value is sliced from the already-fetched hourly arrays (`forecast_days=8`), matched to the day by `hourly.time[k].slice(0,10) === daily.time[di]`. The full payload is stashed in a new global `WX_LAST` (set at the top of `renderWeather`).
- New helpers: `openDaySheet(di)` / `closeDaySheet()` / `_buildDayPanel` / `_hourSliceForDay` / `_daySheetEnsure` / `_wireDaySheet`; arrays `ET_DAY_FULL`, `ET_MONTHS`. Day tiles got `data-di` + `cursor:pointer`; a single delegated click listener on `#daily-strip` (guarded by `strip.__sheetWired`) opens the sheet. Close via backdrop tap, ✕ button, Esc, or swipe-down on the grip.
- `renderSpark` reads `el.clientWidth`, so sparklines are drawn in a double-`requestAnimationFrame` **after** the sheet is visible (else width 0 → no bars). All `.daysheet*` CSS is appended before the last `</style>`.
- Verified (Playwright, real data): 7 panels, 24 bars per sparkline, 8 icons, correct ET date header, tiles tappable, **0 console errors**; `node --check` both inline scripts OK; orphan-ID check clean.

## Recent changes (2026-05-31 — precip-aware icons + Erik Flowers glyph swap)

First real in-repo edit to the redesign_90 JS. Two intertwined changes to the weather-symbol logic:

- **No rain glyph when there's effectively no rain.** Open-Meteo's WMO `weathercode` flags "drizzle/rain" even for a 0.1 mm trace, so the 7-day strip painted a raindrop on dry days. New unified picker `skyIconSVG(code, precipAmt, isDay)` with `var RAIN_MIN_MM = 0.5;` — a precip code (51 drizzle … 86 snow-showers) with `< 0.5 mm` returns the cloud glyph instead; thunderstorms (≥95) always show. Threshold chosen with Indrek. Wired into all three weather-symbol surfaces: **Hetkeilm hero**, the **3-hourly precip-type row** (`renderPrecipTypes` gained a `precipArr` param, fed `next24Mm`), and the **7-day strip**. Also: `currentSkyText`'s "Nõrk sadu" cutoff moved `0.1 → RAIN_MIN_MM` so phrase and icon agree, and the 7-day rain figure now reads `—` (dry) below 0.5 mm (was `< 0.1`).
- **Icon set → Erik Flowers "Weather Icons"** (SIL OFL 1.1, github.com/erikflowers/weather-icons). Replaced each `WX_SVG` condition glyph (keys preserved: `clearDay clearNight partlyCloudy cloudy fog drizzle rain snow thunder`) with the official single-path SVG, viewBox `0 0 30 30`, tinted inline (sun amber `#f5b942`, thunder violet, rest cool greys/blues). Embedded inline — no webfont, stays single-file & offline. The `sunrise` key was left as the old gradient art (not a condition icon).
- **Gotcha logged:** Erik Flowers' raw SVG `d=""` path data contains **literal newlines** — embedding verbatim into a single-quoted JS string breaks it (`SyntaxError: Invalid or unexpected token`). Collapse whitespace (`re.sub(r'\s+',' ',d)`) before embedding. Verified after: `node --check` on both inline scripts OK, 16/16 logic unit-tests pass, orphan-ID check clean, icons render (Playwright).

## Recent changes (2026-05-21 → 2026-05-24 — redesign_86 / _90 iteration cycle)

Two more drop-ins from `~/Downloads/` on top of the small in-repo touch-ups (`600baea`, `023b9fc`, `59e5b77` — three "Update index.html" web-UI edits between this session and the prior one):

- `54bfdcd` — `madise-redesign_86.html` drop-in (+4 −3 lines vs upstream once rebased; size 301 KB)
- `6a67369` — `madise-redesign_90.html` drop-in (+30 −7 lines vs `_86`; size 302 KB) — current HEAD

Naming note: Indrek's Downloads now uses `madise-redesign_{N}.html` (with underscore) — not the same numbering line as the earlier `madise-redesign{N}.html` (no underscore) commits like `004f02a` redesign86 / `5961a29` redesign87. Treat the underscored vs non-underscored series as independent counters.

Workflow nit: when deploying, `git pull --rebase` first inside `~/wa2/` — there have been several upstream `Update index.html` web-UI edits between drop-ins, and skipping the pull risks a divergent push. The local Python http.server stayed running across sessions; no need to restart it for each drop-in.

## Recent changes (2026-05-19 → 2026-05-20 — external redesign drop-in session)

This session was a long iteration loop where Indrek produced ~80+ redesign builds outside the repo (`madise-redesign{N}.html` and `madise-v1.0.html` in `~/Downloads/`) and I deployed each one to the local Python `http.server` on port 8123 for live phone review over hotspot (`http://172.20.10.8:8123`). Only a few of those builds were committed to git:

- `04ee68f` — first redesign drop (redesign5)
- `b230ca1` — redesign13
- `004f02a` — redesign86 (rebased over `2f8f831` `Update fetch_emhi.py` from the PC)
- `5961a29` — redesign87 (current `HEAD`)

In between, the rest of the iterations (redesign6 through redesign85, v1.0, etc.) were local-only via `cp ~/Downloads/madise-redesign{N}.html ~/wa2/index.html`. Indrek hard-refreshed the iPhone tab each time to bust the SW cache.

Merge note: while Indrek was iterating, the GitHub web UI was also used to rename old/new files (`8631c7d` "Rename madise-redesign3.html to index.html", `67acf9e` "Rename index.html to indexvana.html", `444baee` "Add files via upload"). One merge conflict was resolved in `264303e` by keeping our local redesign5 over the remote's redesign3. From `004f02a` onward I switched to `git pull --rebase` before every push to avoid further conflicts.

### What the redesign actually changed

I have **not** read through the new `index.html` line by line. From file sizes (54 KB → ~407 KB peak → ~215 KB v1.0 → ~135 KB current) the new build is materially larger than the prior in-repo build (97 KB), which suggests inline SVG / icon work + significant CSS rewriting. **Before doing any future edits to the page, re-read `index.html` from scratch — the older sections of this CLAUDE.md (architecture, conventions, what NOT to do) may still hold for the data/PWA/build layer, but the rendering / CSS layer should be treated as a clean slate until verified.**

### What's still trustworthy in this CLAUDE.md

These sections describe the data + ops layer, which the redesign did not touch:

- "Data sources" — Open-Meteo / NOAA SWPC / tarktee / EMHI endpoints are still the same
- "Architecture" — single-file PWA, sw.js, manifest.json, GitHub-Actions EMHI bridge → `data` orphan branch, same `raw.githubusercontent.com` read path
- "Local development" — `python3 -m http.server 8123` workflow, Playwright screenshot pipeline
- "Deployment" — push main → GitHub Pages
- "What NOT to do" — gitignore, fetch headers, orphan-ID checker tip

These should be re-verified against the new `index.html`:

- "Conventions" subsections referencing specific CSS classes (`--label-col`, `.card-hero`, `.wx-meta`, etc.) — likely stale
- The whole "Recent changes (2026-05-18 — visual design pass)" section below — describes pre-redesign CSS that's been replaced
- The 2026-05-19 icon-position fix (the `.wx-cond-line` margin-top hack) — no longer applies; that selector may not even exist in the new build

## Recent changes (2026-05-18 — PWA + multi-station + warnings session)

This was a long single-day session that built up the project from the bare-bones original to its current state. Listing in roughly the order things were added:

### Initial PWA migration
- **Rebrand:** Keravere → Madise (title, manifest, label, CONFIG.label, icon wordmark)
- **Title:** "Madise Ilmaradar" (was "Ilmaradar – Keravere")
- **Manifest:** `manifest.json` (name, theme color, standalone display, three icon sizes incl. maskable)
- **Service worker:** `sw.js` — stale-while-revalidate on app shell, network-only on weather APIs, fonts cached opportunistically
- **Offline caching:** every successful API response saved to `localStorage` with 6 h TTL; `hydrateFromCache()` renders cached data immediately on load
- **Refactor:** all fetch functions split into `render*` + `fetch*` pairs to support cache hydration without code duplication
- **Icons:** PNGs at 180/192/512 + 512 maskable + 16/32 favicons; design is "MADISE" wordmark in accent blue with pulse-dot prefix on dark navy. Generator: `icons/generate_icons.py`. Icon is **static** — iOS PWAs cannot redraw home-screen icons.
- **Meta tags:** `apple-touch-icon`, `apple-mobile-web-app-title=Madise`, `application-name=Madise`, `theme-color=#060d14`, `mobile-web-app-capable=yes`
- **Backup:** `index_backup_pre_pwa.html` (local-only rollback copy)

### Tooling
- Playwright installed in `.venv/`; `screenshots.py` captures full-page renders at 6 device widths
- `.gitignore` for `.DS_Store`, `.venv/`, `shots/`, `__pycache__/`, `index_backup_pre_pwa.html`, `data/`

### Layout iteration
- 2-col cards (Päike / Kuu / Õietolm / Virmalised) use icon-as-left-rail CSS grid: icon spans full row height, label + value stack to its right
- Label font in 2-col cards reduced to 12 px / 0.5 px letter-spacing + `white-space:nowrap` so "JÄRGMINE TÄISKUU" fits one line at 360 px+
- Tuul row tightened: "puhangud" → "puh", trailing redundant m/s removed, gap 5→4 px, label min-width 104→88 px, `flex-wrap` safety net
- Wind direction arrow bumped to 28 px and coloured `--cold`
- "Täiskuu" → "Järgmine täiskuu"
- "Muru" → "Hein"
- "UV indeks" → "UV"
- "Sademed algavad" → "Võimaliku saju alguseni"
- Loojanguni countdown: dropped seconds (was `7t 05m 14s`, now `7t 05m`)

### Topbar
- Soft refresh (↻) and hard refresh (⟲) buttons moved from topbar-main to topbar-sub (the "uuendatud" row), right-aligned
- Hard refresh: clears all `wx.*` from localStorage, evicts the SW cache, reloads

### Aurora card redesign
- Old "Kp praegu / Tõenäosus / Uuendus" replaced with **24h max Kp** (with G-scale tier), **Tõenäosus** (Ovation probability % at Madise), **Bz** (solar wind, colored by direction), **72h** (24-cell mini bar chart of next 3 days, colored by Kp / G-scale)
- New endpoints: `noaa-planetary-k-index-forecast.json`, `ovation_aurora_latest.json`, `solar-wind/mag-1-day.json`
- NOAA changed the planetary-k-index JSON shape from array-of-arrays to array-of-objects — fixed parser

### Kurevere subsection in Hetkeilm card
- Reverse-engineered the tarktee.mnt.ee ArcGIS REST endpoint to find Kurevere road weather station (~6 km from Madise)
- Renders inline sub-block in Hetkeilm card showing real ground-truth temp · precip · wind ↑ from the road station (vs Open-Meteo's model output)

### EMHI bridge (Lääne-Nigula + Haapsalu)
- Investigated CORS situation on EMHI XML — closed, Cloudflare-bot-protected
- Built GitHub Actions bridge: `scripts/fetch_emhi.py` runs every 15 min, fetches `ilma_andmed/xml/observations.php`, parses out targeted WMO stations (26124 Lääne-Nigula + 26123 Haapsalu), writes JSON, force-pushes to a `data` orphan branch
- PWA reads from `raw.githubusercontent.com` (CORS-open) with same-origin `data/emhi.json` fallback for local dev
- Three station sub-blocks now stacked in Hetkeilm card (Kurevere, Lääne-Nigula, Haapsalu), each with their own source label (`tarktee` / `EMHI`)
- UV index hero now sourced from EMHI Haapsalu when available (real station measurement overrides Open-Meteo's often-zero forecast)

### Päike + Kuu card redesign (shared `.card-hero`)
- Both cards now have an identical `.card-hero` block at the top → first data row (Tõus) aligns horizontally between them
- Päike hero: sun **disc** (pure CSS, no emoji rays) with warm glow during day, switches to 🌙 crescent moon with cool blue glow when sun below horizon
- Kuu hero: moon phase emoji + phase name + illumination %
- Päike data rows: Tõus / Loojang / Loojanguni (dropped Valgust, Eilsest)
- Kuu data rows: Tõus / Loojang / Järgmine täiskuu (dropped Järgmine noorkuu)
- Each rise/set row shows azimuth in degrees inline: `TÕUS 04:48 48°` (no compass label, just the number — fits on one line for both 2-digit and 3-digit azimuths)
- Added solar/lunar astronomy: Meeus simplified for sun, leading-term Brown for moon, full atan2 azimuth formula with cos(δ) factor (the simpler `tan(δ)` version is wrong for high latitudes — gave SE instead of NE for Estonian sunrise)
- Moonrise/moonset computed by 10-min iteration on altitude zero-crossings

### Meteo warning row
- MeteoAlarm Estonia ATOM/CAP feed parsed in `fetch_emhi.py` (filters to Lääne county)
- Slim row above Hetkeilm: muted "Hoiatusi pole" when empty, severity-coloured `⚡ Äike · homme 21:00–07:00` when active. Event names translated to Estonian.

### Forecast strip alignment
- Tunniti + 7 päeva strips now use `flex: 0 0 calc((100% - 24px) / 4)` on each tile → exactly 4 tiles fit per viewport regardless of width
- Slim 4 px scrollbars at the bottom of each strip
- Scroll-snap so tiles snap into place

### Bug fixes
- The `byId('day-change').textContent = …` line was still referencing a row we deleted earlier in the session — it threw on null and halted all subsequent JS, leaving the page showing only the client-side-computed sun/moon panels. Removed the orphan reference. Added the orphan-ID checker recipe above.

## Recent changes (2026-05-18 — visual design pass)

Long iterative session on the look and feel after the data build-out was stable. Highlights (see `progress.md` for the full list with file/line context):

### Liquid Glass aesthetic
- Card + button bezels: chamfered look via layered inset `box-shadow` (top-left highlight, bottom-right shadow, faint halo). Saved over many "Preset N" comment blocks in the CSS during iteration.
- Card surface lowered to `rgba(10,18,28,0.82)` (`--surface`) so the body's multi-layer background (radial cyan/teal blobs + vertical-stripe gradient sweep) shows through subtly. Blobs live in body's `background:` with `background-attachment: fixed` (the earlier `body::before` pseudo-element approach was invisible behind opaque card bgs).
- RADAR / SAT mini-buttons mirror the card material with their own chamfered bevel.

### Hetkeilm hero layout
- Big temp on the left; condition **icon stacked above** condition text on the right, both right-aligned, text uppercased (`LAUSPILVES`, `NÕRK SADU` etc.) at 14 px / 1 px letter-spacing so it matches the row label vocabulary.
- Tundub / Kastepunkt now sit in a 2-col CSS grid (`.wx-meta`) directly under the big temp.
- "Tundub nagu" → "Tundub". Päikesetõusuni colour now matches Järgmine täiskuu (no warm rise/set tint).

### Shared label column (`--label-col: 105px`)
The Hetkeilm card has three vertical contexts that all line up at x=105:
1. `.wx-meta` → grid `var(--label-col) auto` with column-gap 0 → Tundub / Kastepunkt values
2. `.row-label` → `min-width: var(--label-col)` → TUUL / SADU / ÕHURÕHK / NIISKUS / UV / NÄHTAVUS / ÖÖKÜLM values
3. `.wx-station-row` → grid `var(--label-col) auto` → alt-loc wind value lands at x=105 (rain follows)

### Alt-location stations (Kurevere / Lääne-Nigula / Haapsalu)
- Title alone on line 1 (e.g. `KUREVERE`). Line 2 is a 2-col grid: `temp-cell` in col 1 (temp stays at x=0 like before), `wind-rain-cell` in col 2 starting at x=105.
- Wind / rain order swapped earlier (wind before rain) and both promoted to `val.sm` (17 px) to match Tundub/Kastepunkt vocabulary.
- `renderStation()` was stripping the `sm` class on the temp element during data update — fixed.

### Inline SVG weather icons (replaced emoji)
- New `WX_ICONS` library at the top of the JS section. Eight conditions: `sun`, `moon`, `cloud`, `partly-day`, `partly-night`, `rain`, `light-rain` (light-rain falls back to `rain` at night).
- Style: filled silhouettes with a translucent top-to-bottom gradient (white → cool blue for clouds; warm yellow for sun; cool tone for moon), a faint white bezel stroke (~0.7 px), and a radial highlight overlay to fake the light source on glass. Shared `<defs>` block (`cl-grad`, `sun-grad`, `moon-grad`, `cl-shine`, `sun-shine`, `drop-grad`).
- Cloud silhouette is a Lucide-derived clean two-bump path scaled into a 64×64 viewBox (`CLOUD_PATH` + smaller `CLOUD_PATH_SM` for combined "partly" / "light-rain" variants).
- Container `.wx-cond-icon-big` is 48×48 with `drop-shadow(0 2px 3px rgba(0,0,0,0.5))` plus a soft cyan outer glow — the same material vocabulary as the chamfered card / button bevels.
- `currentSkyText` now returns `{ text, icon: 'sun' | 'moon' | ... }`; the renderer does `byId('wx-cond-icon').innerHTML = WX_ICONS[sky.icon]`.

### Row spacing
- `.row` margin-bottom dropped 15 → 4 px to match the `row-gap: 4px` in `.wx-meta`. Added `line-height: 1` on `.row` so the inherited 1.2 line-height stops eating the difference.

### Font consistency pass
- All Hetkeilm data values are `val.sm` (17 px). All row labels and meta labels are 14 px uppercase 1 px-letter-spaced.
- 2-col cards: Päike Tõus/Loojang dropped from `val.sm` → `val.xs` so they match the Kuu values.
- Row icons globally hidden (`.row-icon { display: none }`) — the inline SVG aesthetic replaces them.

## TODO / open questions

- [ ] Verify the new home-screen icon on the actual iPhone after re-installing as a web app
- [ ] Smoke-test on a real Android device (Indrek has Android users)
- [ ] Decide whether to add the iOS Badging API (`navigator.setAppBadge(temp)`) for a small numeric badge on the home-screen icon — discussed and parked
- [ ] Decide whether a native iOS widget (Capacitor + WidgetKit) is worth pursuing for a true live-temperature widget — parked, big complexity jump
- [ ] Consider switching XMLHttpRequest → `fetch()` for cleaner async code (not urgent)
- [ ] Consider adding *current* sun altitude + azimuth (changes minute-by-minute) — right now we only show azimuth at fixed rise/set times
- [ ] Consider adding neighbouring counties (Hiiu / Saare / Pärnu / Harju) to the warning filter — currently Lääne only

## Recent changes (2026-05-19 — flat-glass + centering experiment)

Short follow-up session after the bevel commit. Two outcomes:

### Preset 11 — flat diffused glass (committed `b63f611`)
- Replaced the chamfered-bevel `.card` / `.topbar` styling with a flatter
  treatment: kept `backdrop-filter: blur(24px) saturate(140%)`, the SVG
  noise grain, a faint top-down highlight, a hairline white border, and
  a single soft outer drop shadow. Removed: inset bevel halos, sharp 1
  px black bottom/right edges, diagonal 135° sweep, radial inner cyan
  glow, bottom-right corner shadow concentration.
- Bevel state preserved as **Preset 10** in the design-presets comment
  for rollback (commit `d55c211` covers the old bevel verbatim).

### Bug fix — nested `/* */` in Preset 10 comment (same commit)
- The first save of Preset 10 contained `border: 1px solid var(--border); /* cyan-ish edge */` *inside* an outer `/* */` CSS comment block.
  CSS comments don't nest — the inner `*/` closed the outer comment,
  turning the rest of the preset description into invalid CSS. The CSS
  parser dropped the `html, body { color: var(--text) }` rule (and
  probably several more around it), so all page text fell back to the
  browser-default **black**.
- Lesson: **never put `/* */` inside another `/* */`** in the design
  preset comments. Use `//` (which has no meaning in CSS but is fine
  as part of comment text) for inline annotations when needed.

### Centering experiment (reverted, not committed)
- Tried pulling `.wx-temp-big` out of the hero flex row and making it a
  full-width centered block above the row (with meta + cond on the row
  below). User judged it doesn't fit — reverted to the left-aligned
  temp + meta layout from the previous commit. Working tree clean.

## In progress / mid-task

- Nothing in progress. Working tree is clean as of session end. The two
  open material-design questions left over:
  - Is the page reading too **cyan/blue saturated**? Border, card title,
    `cold` colour, accent buttons, body blobs are all cyan/teal. A
    candidate experiment is muting the cyan vars (`--accent`, `--cold`,
    `--border`) toward neutral-white so colour is reserved for meaningful
    signal only (the warm/cold temp gradient).
  - Is the **mono+sans split** between values (`ui-monospace`) and
    labels (`system-ui`) reading as "data-terminal"? An experiment is
    using `system-ui` everywhere with `font-variant-numeric: tabular-nums`
    for column alignment.
- Open visual nits noted in earlier session log (`progress.md`):
  - Cloud silhouette could be redrawn with a smoother 3-bump path.
  - The cond-icon-over-text block doesn't enforce "text bottom = big
    temp bottom" anymore — items naturally stack at the top of
    `.wx-hero-right`.
  - RADAR / SAT buttons still abs-positioned to bottom-right of
    `.wx-hero-right` — verify alignment after each row-spacing change.
  - Icon-vs-buttons collision fixed 2026-05-19 by lifting `.wx-cond-line`
    with `margin-top: -28px`. If the condition string ever wraps to 4+
    lines on a very narrow viewport, the bottom of the text could still
    reach the buttons — re-verify if you add a longer Estonian condition
    string.
