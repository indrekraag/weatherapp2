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

**Status:** All work from the 2026-05-18 sessions committed and pushed. PWA is fully functional with three real weather stations (Kurevere road sensor + Lääne-Nigula and Haapsalu EMHI met stations), MeteoAlarm warning row for Lääne county, redesigned aurora card with 3-day Kp forecast chart, redesigned Päike + Kuu cards with shared hero layout.

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

## TODO / open questions

- [ ] Verify the new home-screen icon on the actual iPhone after re-installing as a web app
- [ ] Smoke-test on a real Android device (Indrek has Android users)
- [ ] Decide whether to add the iOS Badging API (`navigator.setAppBadge(temp)`) for a small numeric badge on the home-screen icon — discussed and parked
- [ ] Decide whether a native iOS widget (Capacitor + WidgetKit) is worth pursuing for a true live-temperature widget — parked, big complexity jump
- [ ] Consider switching XMLHttpRequest → `fetch()` for cleaner async code (not urgent)
- [ ] Consider adding *current* sun altitude + azimuth (changes minute-by-minute) — right now we only show azimuth at fixed rise/set times
- [ ] Consider adding neighbouring counties (Hiiu / Saare / Pärnu / Harju) to the warning filter — currently Lääne only

## In progress / mid-task

(Nothing in progress — last session ended at a clean checkpoint after the 2026-05-18 session push.)
