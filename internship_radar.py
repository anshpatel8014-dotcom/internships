#!/usr/bin/env python3
"""
internship_radar.py — surface NEW Summer-2027 aerospace internships the moment
they post, across Greenhouse / USAJOBS / Workday. Stdlib only (no pip installs).

Usage:
  python internship_radar.py            # poll everything, report new finds
  python internship_radar.py --check    # validate which Greenhouse tokens resolve
  python internship_radar.py --all      # show ALL current matches, not just new ones
  python internship_radar.py --reset    # forget seen history (re-surface everything)

Notify (optional, set as env vars):
  DISCORD_WEBHOOK   -> posts new finds to a Discord channel
  SLACK_WEBHOOK     -> posts new finds to Slack
  USAJOBS_KEY + USAJOBS_EMAIL -> enables the federal source

State + output live next to this script: seen.json, new_postings.md, all_matches.csv
"""

import json, os, re, sys, csv, urllib.request, urllib.error, datetime
from html import unescape
from pathlib import Path

import sources as SRC

HERE = Path(__file__).resolve().parent
SEEN_FILE = HERE / "seen.json"
DIGEST_FILE = HERE / "new_postings.md"
LOG_CSV = HERE / "all_matches.csv"
UA = "internship-radar/1.0 (personal job alerts)"
TIMEOUT = 25

# ------------------------------------------------------------------ matching ---
TARGET_YEAR = "2027"                             # the year you want, period
# \b word boundaries so "internal" / "international" do NOT match.
# Matches: intern, interns, internship, internships, co-op, coop, co op
INTERN_RE = re.compile(r"\bintern(?:ship)?s?\b|\bco[\s-]?ops?\b")
EXCLUDE_TERMS = ("high school",)                 # keep grad/PhD interns in
SEASONS_ALL = {"spring", "summer", "fall", "autumn", "winter"}
WANT_SEASON = "summer"
TAG_RE = re.compile(r"<[^>]+>")


def clean(html: str) -> str:
    return unescape(TAG_RE.sub(" ", html or "")).lower()


def classify(title: str, content: str):
    """Strict rule: 'intern/co-op' must be in the TITLE, and '2027' must appear.
    Returns (is_match, tags)."""
    title_l = clean(title)
    text = title_l + " " + clean(content)

    # 1) must be an internship — signal must be in the TITLE (kills "internal" noise)
    if not INTERN_RE.search(title_l):
        return False, []
    if any(x in text for x in EXCLUDE_TERMS):
        return False, []

    # 2) must actually be the 2027 cohort
    if TARGET_YEAR not in text:
        return False, []
    tags = ["intern", TARGET_YEAR]

    # 3) drop postings explicitly tied to a non-summer season
    seasons = {s for s in SEASONS_ALL if s in text}
    if seasons and WANT_SEASON not in seasons:
        return False, []
    if WANT_SEASON in seasons:
        tags.append("summer")
    return True, tags


# -------------------------------------------------------------------- http -----
def _get(url, headers=None):
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def _post(url, body, headers=None):
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        url, data=data,
        headers={"User-Agent": UA, "Content-Type": "application/json",
                 "Accept": "application/json", **(headers or {})},
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


# ----------------------------------------------------------------- sources -----
def fetch_greenhouse(name, token):
    url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"
    out = []
    try:
        data = _get(url)
    except urllib.error.HTTPError as e:
        print(f"  ! {name}: greenhouse HTTP {e.code} (bad token?)", file=sys.stderr)
        return out
    except Exception as e:
        print(f"  ! {name}: {e}", file=sys.stderr)
        return out
    for j in data.get("jobs", []):
        ok, tags = classify(j.get("title", ""), j.get("content", ""))
        if ok:
            out.append({
                "uid": f"gh:{token}:{j['id']}",
                "company": name, "title": j.get("title", ""),
                "location": (j.get("location") or {}).get("name", ""),
                "url": j.get("absolute_url", ""),
                "updated": j.get("updated_at", ""), "tags": tags, "source": "greenhouse",
            })
    return out


def fetch_lever(name, token):
    url = f"https://api.lever.co/v0/postings/{token}?mode=json"
    out = []
    try:
        data = _get(url)            # Lever returns a JSON array
    except urllib.error.HTTPError as e:
        print(f"  ! {name}: lever HTTP {e.code} (bad token?)", file=sys.stderr)
        return out
    except Exception as e:
        print(f"  ! {name}: {e}", file=sys.stderr)
        return out
    for j in data:
        ok, tags = classify(j.get("text", ""), j.get("descriptionPlain", ""))
        if ok:
            out.append({
                "uid": f"lever:{token}:{j.get('id','')}",
                "company": name, "title": j.get("text", ""),
                "location": (j.get("categories") or {}).get("location", ""),
                "url": j.get("hostedUrl", ""),
                "updated": j.get("createdAt", ""), "tags": tags, "source": "lever",
            })
    return out


def fetch_usajobs():
    key, email = os.getenv("USAJOBS_KEY"), os.getenv("USAJOBS_EMAIL")
    if not (key and email):
        return []
    hdr = {"Host": "data.usajobs.gov", "User-Agent": email, "Authorization-Key": key}
    out = []
    for kw in SRC.USAJOBS_KEYWORDS:
        url = ("https://data.usajobs.gov/api/search?ResultsPerPage=50"
               f"&Keyword={urllib.parse.quote(kw)}")
        try:
            data = _get(url, hdr)
        except Exception as e:
            print(f"  ! USAJOBS '{kw}': {e}", file=sys.stderr)
            continue
        items = data.get("SearchResult", {}).get("SearchResultItems", [])
        for it in items:
            d = it.get("MatchedObjectDescriptor", {})
            ok, tags = classify(d.get("PositionTitle", ""),
                                d.get("QualificationSummary", "") + " " +
                                d.get("UserArea", {}).get("Details", {}).get("JobSummary", ""))
            if ok:
                out.append({
                    "uid": f"usajobs:{it.get('MatchedObjectId','')}",
                    "company": d.get("OrganizationName", "Federal"),
                    "title": d.get("PositionTitle", ""),
                    "location": d.get("PositionLocationDisplay", ""),
                    "url": d.get("PositionURI", ""),
                    "updated": d.get("PublicationStartDate", ""),
                    "tags": tags, "source": "usajobs",
                })
    return out


def fetch_workday(name, tenant, dc, site):
    base = f"https://{tenant}.{dc}.myworkdayjobs.com"
    url = f"{base}/wday/cxs/{tenant}/{site}/jobs"
    out = []
    try:
        data = _post(url, {"appliedFacets": {}, "limit": 20, "offset": 0,
                           "searchText": "intern"})
    except Exception as e:
        print(f"  ! {name}: workday unavailable ({e})", file=sys.stderr)
        return out
    for j in data.get("jobPostings", []):
        path = j.get("externalPath", "")
        ok, tags = classify(j.get("title", ""), j.get("bulletFields", [""])[0] if j.get("bulletFields") else "")
        if ok:
            out.append({
                "uid": f"wd:{tenant}:{path}",
                "company": name, "title": j.get("title", ""),
                "location": j.get("locationsText", ""),
                "url": f"{base}/en-US/{site}{path}",
                "updated": j.get("postedOn", ""), "tags": tags, "source": "workday",
            })
    return out


# ------------------------------------------------------------------ notify -----
def _send_discord(webhook, msg):
    """Split into <2000-char chunks (Discord's hard limit) so nothing is dropped."""
    chunk = ""
    for line in msg.split("\n"):
        if len(chunk) + len(line) + 1 > 1900:
            if chunk:
                _post(webhook, {"content": chunk})
            chunk = line
        else:
            chunk = f"{chunk}\n{line}" if chunk else line
    if chunk:
        _post(webhook, {"content": chunk})


def _send_slack(webhook, msg):
    for i in range(0, len(msg), 3000):
        _post(webhook, {"text": msg[i:i + 3000]})


def notify(new):
    if not new:
        return
    lines = [f"🛰️ {len(new)} new aerospace internship(s):"]
    for m in new:                         # no cap — every match is sent
        lines.append(f"• **{m['company']}** — {m['title']} ({m['location']})\n  {m['url']}")
    msg = "\n".join(lines)
    dw, sw = os.getenv("DISCORD_WEBHOOK"), os.getenv("SLACK_WEBHOOK")
    try:
        if dw:
            _send_discord(dw, msg)
        if sw:
            _send_slack(sw, msg)
    except Exception as e:
        print(f"  ! notify failed: {e}", file=sys.stderr)


# -------------------------------------------------------------------- state ----
def load_seen():
    if SEEN_FILE.exists():
        return set(json.loads(SEEN_FILE.read_text()))
    return set()


def save_seen(seen):
    SEEN_FILE.write_text(json.dumps(sorted(seen), indent=0))


def write_outputs(new):
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    md = [f"# New internships — {stamp}", ""]
    if not new:
        md.append("_Nothing new this run._")
    for m in new:
        md.append(f"- **{m['company']}** — [{m['title']}]({m['url']})  "
                  f"`{m['location']}` _{' '.join(m['tags'])}_")
    DIGEST_FILE.write_text("\n".join(md) + "\n")

    new_file = not LOG_CSV.exists()
    with LOG_CSV.open("a", newline="") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(["found_at", "company", "title", "location", "url", "tags", "source"])
        for m in new:
            w.writerow([stamp, m["company"], m["title"], m["location"],
                        m["url"], " ".join(m["tags"]), m["source"]])


# --------------------------------------------------------------------- main ----
def check_tokens():
    print("Checking Greenhouse tokens...\n")
    for name, token in SRC.GREENHOUSE.items():
        url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs"
        try:
            n = len(_get(url).get("jobs", []))
            print(f"  OK   {name:22} ({token}) — {n} open roles")
        except urllib.error.HTTPError as e:
            print(f"  DEAD {name:22} ({token}) — HTTP {e.code}  <-- fix or remove")
        except Exception as e:
            print(f"  ERR  {name:22} ({token}) — {e}")
    print("\nChecking Lever tokens...\n")
    for name, token in SRC.LEVER.items():
        url = f"https://api.lever.co/v0/postings/{token}?mode=json"
        try:
            n = len(_get(url))
            print(f"  OK   {name:22} ({token}) — {n} open roles")
        except urllib.error.HTTPError as e:
            print(f"  DEAD {name:22} ({token}) — HTTP {e.code}  <-- fix or remove")
        except Exception as e:
            print(f"  ERR  {name:22} ({token}) — {e}")


def run(show_all=False):
    matches = []
    print("Polling Greenhouse boards...")
    for name, token in SRC.GREENHOUSE.items():
        matches += fetch_greenhouse(name, token)
    print("Polling Lever boards...")
    for name, token in SRC.LEVER.items():
        matches += fetch_lever(name, token)
    print("Polling Workday (primes, best-effort)...")
    for name, (tenant, dc, site) in SRC.WORKDAY.items():
        matches += fetch_workday(name, tenant, dc, site)
    print("Polling USAJOBS (federal)..." if os.getenv("USAJOBS_KEY")
          else "Skipping USAJOBS (set USAJOBS_KEY + USAJOBS_EMAIL to enable)")
    matches += fetch_usajobs()

    # dedupe within this run
    uniq = {m["uid"]: m for m in matches}
    matches = list(uniq.values())

    seen = load_seen()
    new = matches if show_all else [m for m in matches if m["uid"] not in seen]
    new.sort(key=lambda m: (m["company"], m["title"]))

    print(f"\n{len(matches)} total matches, {len(new)} {'shown' if show_all else 'NEW'}:\n")
    for m in new:
        print(f"  [{m['company']}] {m['title']}  —  {m['location']}  {m['tags']}")
        print(f"      {m['url']}")
    if not new:
        print("  (none)")

    write_outputs(new)
    if not show_all:
        notify(new)
        save_seen(seen | {m["uid"] for m in matches})

    print(f"\nDigest -> {DIGEST_FILE.name} | log -> {LOG_CSV.name}")
    if SRC.MANUAL_REMINDERS:
        print("\nManual (no API — set reminders):")
        for k, v in SRC.MANUAL_REMINDERS.items():
            print(f"  • {k}: {v}")


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    if arg == "--check":
        check_tokens()
    elif arg == "--reset":
        SEEN_FILE.unlink(missing_ok=True)
        print("Seen history cleared.")
    elif arg == "--all":
        run(show_all=True)
    else:
        run()
