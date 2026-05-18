#!/usr/bin/env python3
"""Fetch EMHI (Estonian Weather Service) observations and emit a JSON
snapshot for one or more named stations.

Default target: Lääne-Nigula (WMO 26124), ~15 km north of Madise. The
station has full meteorological instrumentation: pressure, humidity,
visibility, phenomenon text, gust speed — fields the road weather
station at Kurevere doesn't provide.

Why this script exists:
  The EMHI XML endpoint at ilmateenistus.ee is fronted by Cloudflare with
  no CORS headers, so the PWA can't fetch it directly from the browser.
  This script runs in GitHub Actions on a 15-min cron, parses out the
  relevant station(s), and writes a small JSON file. That file is then
  force-pushed to a 'data' orphan branch in the repo, which the PWA reads
  via raw.githubusercontent.com (which DOES allow CORS).

Usage:
    python3 scripts/fetch_emhi.py                       # default station(s)
    python3 scripts/fetch_emhi.py --stations 26124      # by WMO code
    python3 scripts/fetch_emhi.py --out data/emhi.json  # custom output

Exits non-zero on network or parse failure so the workflow can fail
loudly instead of silently committing stale data.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

EMHI_URL = "https://www.ilmateenistus.ee/ilma_andmed/xml/observations.php"
METEOALARM_URL = "https://feeds.meteoalarm.org/feeds/meteoalarm-legacy-atom-estonia"

# Counties we care about for warnings (CAP areaDesc match). Madise is in
# Lääne county; Hiiu/Saare/Pärnu/Harju are immediate neighbors.
TARGET_COUNTIES = {"Lääne county"}

# Fields we surface, in the order EMHI publishes them. Empty strings in
# the XML become None in the JSON so the PWA can detect "not measured".
FIELDS = [
    "phenomenon",
    "visibility",
    "precipitations",
    "airpressure",
    "relativehumidity",
    "airtemperature",
    "winddirection",
    "windspeed",
    "windspeedmax",
    "waterlevel",
    "waterlevel_eh2000",
    "watertemperature",
    "uvindex",
    "sunshineduration",
    "globalradiation",
]

DEFAULT_STATIONS = ["26124", "26123"]  # Lääne-Nigula, Haapsalu


def parse_float(s: str):
    if s is None:
        return None
    s = s.strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def fetch_xml(url: str) -> bytes:
    # EMHI's Cloudflare rejects obviously-botty UAs; a realistic UA gets
    # through reliably. We also accept-encoding identity so the response
    # is plain XML (no gzip).
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (compatible; MadiseIlmaradar/1.0; "
                "+https://github.com/indrekraag/weatherapp2)"
            ),
            "Accept": "text/xml, application/xml",
            "Accept-Language": "et, en;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        if resp.status != 200:
            raise RuntimeError(f"EMHI returned HTTP {resp.status}")
        return resp.read()


def extract_station(root: ET.Element, wmo: str) -> dict | None:
    for s in root.findall("station"):
        if (s.findtext("wmocode") or "").strip() == wmo:
            return s
    return None


def station_to_dict(s: ET.Element) -> dict:
    out = {
        "name": (s.findtext("name") or "").strip(),
        "wmocode": (s.findtext("wmocode") or "").strip(),
        "latitude": parse_float(s.findtext("latitude")),
        "longitude": parse_float(s.findtext("longitude")),
    }
    for f in FIELDS:
        raw = s.findtext(f)
        if f == "phenomenon":
            out[f] = (raw or "").strip() or None
        else:
            out[f] = parse_float(raw)
    return out


def fetch_warnings() -> list:
    """Pull MeteoAlarm Estonia ATOM and return active CAP warnings for
    counties listed in TARGET_COUNTIES. Returns a deduplicated list; if
    the fetch or parse fails, returns an empty list (non-fatal)."""
    try:
        # MeteoAlarm rejects a strict Accept header with 406; use */*
        req = urllib.request.Request(
            METEOALARM_URL,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (compatible; MadiseIlmaradar/1.0; "
                    "+https://github.com/indrekraag/weatherapp2)"
                ),
                "Accept": "*/*",
            },
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            xml_bytes = resp.read()
    except Exception as exc:
        print(f"MeteoAlarm fetch failed: {exc}", file=sys.stderr)
        return []

    ns = {
        "a": "http://www.w3.org/2005/Atom",
        "cap": "urn:oasis:names:tc:emergency:cap:1.2",
    }
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        print(f"MeteoAlarm parse failed: {exc}", file=sys.stderr)
        return []

    warnings: list[dict] = []
    seen: set[str] = set()
    for entry in root.findall("a:entry", ns):
        cap: dict[str, str] = {}
        for el in entry.iter():
            if "cap" in el.tag and el.text and el.text.strip():
                tag = el.tag.split("}")[-1]
                # Each CAP field appears once per polygon; keep the first value.
                cap.setdefault(tag, el.text.strip())
        area = cap.get("areaDesc", "")
        if area not in TARGET_COUNTIES:
            continue
        ident = cap.get("identifier", "")
        if ident and ident in seen:
            continue
        if ident:
            seen.add(ident)
        warnings.append({
            "event": cap.get("event"),
            "severity": cap.get("severity"),
            "areaDesc": area,
            "onset": cap.get("onset"),
            "expires": cap.get("expires"),
            "urgency": cap.get("urgency"),
            "certainty": cap.get("certainty"),
        })
    return warnings


def build_snapshot(xml_bytes: bytes, wmo_codes: list[str]) -> dict:
    root = ET.fromstring(xml_bytes)
    xml_ts = root.get("timestamp")
    obs_time = None
    if xml_ts and xml_ts.isdigit():
        obs_time = dt.datetime.fromtimestamp(int(xml_ts), tz=dt.timezone.utc).isoformat()

    stations = {}
    missing = []
    for wmo in wmo_codes:
        s = extract_station(root, wmo)
        if s is None:
            missing.append(wmo)
            continue
        d = station_to_dict(s)
        stations[wmo] = d

    snapshot = {
        "source": "EMHI / Estonian Weather Service",
        "source_url": EMHI_URL,
        "observation_time": obs_time,
        "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "stations": stations,
        "warnings": fetch_warnings(),
        "warnings_source": "MeteoAlarm / Estonian Environment Agency CAP feed",
        "warnings_target_counties": sorted(TARGET_COUNTIES),
    }
    if missing:
        snapshot["missing_wmo_codes"] = missing
    return snapshot


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="data/emhi.json")
    parser.add_argument(
        "--stations",
        nargs="+",
        default=DEFAULT_STATIONS,
        help="WMO codes (default: 26124 Lääne-Nigula)",
    )
    args = parser.parse_args()

    try:
        xml_bytes = fetch_xml(EMHI_URL)
    except urllib.error.HTTPError as e:
        print(f"HTTP error fetching EMHI: {e.code} {e.reason}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"Network error fetching EMHI: {e}", file=sys.stderr)
        return 2

    try:
        snap = build_snapshot(xml_bytes, args.stations)
    except ET.ParseError as e:
        print(f"XML parse error: {e}", file=sys.stderr)
        return 3

    if not snap["stations"]:
        print(f"No requested stations found. Missing: {snap.get('missing_wmo_codes')}", file=sys.stderr)
        return 4

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(snap, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {out_path} — observation_time={snap['observation_time']}, stations={list(snap['stations'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
