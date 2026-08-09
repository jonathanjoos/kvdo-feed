#!/usr/bin/env python3
"""
Scrape KV Oostende Diksmuide league fixtures from kv-do.be/kalender/
and emit two .ics feeds: HOME games and AWAY games (league only).

Runs in GitHub Actions. No paid services, no API keys.
"""
import re
import sys
import hashlib
import urllib.request
from datetime import datetime, timedelta, timezone

URL = "https://kv-do.be/kalender/"
STADIUM = "Versluys Arena, Stadionlaan, 8400 Oostende, Belgium"

# Cup competitions to exclude — we only want league ("competitie") games.
# Detected via the match detail-page slug in the page HTML.
CUP_SLUG_MARKERS = ("croky-cup", "beker-van-vl", "beker-vl")

DUTCH_MONTHS = {
    "januari": 1, "februari": 2, "maart": 3, "april": 4, "mei": 5, "juni": 6,
    "juli": 7, "augustus": 8, "september": 9, "oktober": 10, "november": 11, "december": 12,
}

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (kvdo-feed-bot)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")

def strip_tags(s):
    return re.sub(r"<[^>]+>", " ", s)

def parse_matches(html):
    """
    Locate the 'Geplande matchen' (scheduled) section, stop at 'Afgelopen'
    (finished), and pull structured fields per match: two team names, a Dutch
    date, a time, and the detail-page slug (used to identify cup games).
    """
    start = html.find("Geplande matchen")
    end = html.find("Afgelopen", start if start != -1 else 0)
    section = html[start:end] if start != -1 and end != -1 else html

    text = strip_tags(section)
    text = re.sub(r"[ \t]+", " ", text)

    slugs = re.findall(r"/kalender/([a-z0-9\-]+)/", section)

    date_re = re.compile(
        r"([A-Za-zÀ-ÿ0-9 .&'\-]+?)\s+VS\s+([A-Za-zÀ-ÿ0-9 .&'\-]+?)\s+"
        r"(?:maandag|dinsdag|woensdag|donderdag|vrijdag|zaterdag|zondag)\s+"
        r"(\d{1,2})\s+([a-z]+)\s+(\d{4})\s+(\d{1,2}:\d{2})",
        re.IGNORECASE,
    )

    matches = []
    for i, m in enumerate(date_re.finditer(text)):
        home = m.group(1).strip()
        away = m.group(2).strip()
        day = int(m.group(3))
        month = DUTCH_MONTHS.get(m.group(4).lower())
        year = int(m.group(5))
        hh, mm = map(int, m.group(6).split(":"))
        if not month:
            continue
        slug = slugs[i] if i < len(slugs) else ""
        matches.append({
            "home": home, "away": away,
            "dt": datetime(year, month, day, hh, mm),
            "slug": slug,
        })
    return matches

def is_league(match):
    return not any(mk in match["slug"] for mk in CUP_SLUG_MARKERS)

def is_home(match):
    # KVDO plays at home when listed as the first (home) team.
    return match["home"].strip().upper() in ("KVDO", "KV OOSTENDE DIKSMUIDE", "KV OOSTENDE")

def esc(s):
    return s.replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;").replace("\n", "\\n")

def build_ics(matches, calname, home_side):
    """home_side=True -> location is the stadium; False -> 'Uit' (away)."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    L = [
        "BEGIN:VCALENDAR", "VERSION:2.0",
        "PRODID:-//KVDO Feed//League Fixtures//NL",
        "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
        f"X-WR-CALNAME:{esc(calname)}",
        "X-WR-TIMEZONE:Europe/Brussels",
        "REFRESH-INTERVAL;VALUE=DURATION:PT12H",
        "X-PUBLISHED-TTL:PT12H",
        "BEGIN:VTIMEZONE", "TZID:Europe/Brussels",
        "BEGIN:DAYLIGHT", "TZOFFSETFROM:+0100", "TZOFFSETTO:+0200", "TZNAME:CEST",
        "DTSTART:19700329T020000", "RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU", "END:DAYLIGHT",
        "BEGIN:STANDARD", "TZOFFSETFROM:+0200", "TZOFFSETTO:+0100", "TZNAME:CET",
        "DTSTART:19701025T030000", "RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU", "END:STANDARD",
        "END:VTIMEZONE",
    ]
    count = 0
    for mt in matches:
        dt = mt["dt"]
        end = dt + timedelta(hours=2)
        uid = hashlib.md5(f"{mt['home']}{mt['away']}{dt.date()}".encode()).hexdigest() + "@kvdo"
        loc = STADIUM if home_side else "Uit"
        kind = "Thuiswedstrijd" if home_side else "Uitwedstrijd"
        L += [
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{stamp}",
            f"DTSTART;TZID=Europe/Brussels:{dt.strftime('%Y%m%dT%H%M%S')}",
            f"DTEND;TZID=Europe/Brussels:{end.strftime('%Y%m%dT%H%M%S')}",
            f"SUMMARY:{esc(mt['home'] + ' - ' + mt['away'])}",
            f"LOCATION:{esc(loc)}",
            f"DESCRIPTION:{esc(kind + ' KVDO (competitie). Bron: ' + URL)}",
            "END:VEVENT",
        ]
        count += 1
    L.append("END:VCALENDAR")
    return "\r\n".join(L) + "\r\n", count

def write_feed(matches, filename, calname, home_side):
    ics, n = build_ics(matches, calname, home_side)
    with open(filename, "w", encoding="utf-8") as f:
        f.write(ics)
    return n

def main():
    html = fetch(URL)
    allm = parse_matches(html)
    league = [m for m in allm if is_league(m)]
    league.sort(key=lambda m: m["dt"])

    home = [m for m in league if is_home(m)]
    away = [m for m in league if not is_home(m)]

    n_home = write_feed(home, "kvdo-thuis.ics", "KVDO Thuiswedstrijden (Competitie)", True)
    n_away = write_feed(away, "kvdo-uit.ics",   "KVDO Uitwedstrijden (Competitie)",   False)

    print(f"Parsed {len(allm)} scheduled matches; league={len(league)} "
          f"(home={n_home}, away={n_away})")

    if len(league) == 0:
        # Fail loudly so a broken scrape doesn't silently overwrite good feeds.
        print("WARNING: 0 league matches parsed — site layout may have changed.", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
