# Internship Radar — Summer 2027 Aerospace

Polls where aerospace internships actually post, filters to **Summer 2027**, and
pings you the moment a *new* one appears. No scraping, no auto-applying, no banned
accounts — just early warning so you apply in the first 48 hours (when it matters most).

## What it watches
- **Greenhouse** public API — SpaceX, Rocket Lab, Anduril, Relativity. Reliable core.
- **Lever** public API — Venus Aerospace (rotating detonation), Hermeus (hypersonics).
- **USAJOBS** — federal / Pathways / AFRL / national labs (optional, needs free key).
- **Workday** — Lockheed, Northrop, RTX, Boeing (best-effort; some tenants are flaky).
- **Manual** — NASA OSTEM (no API; **Feb 26, 2027** deadline) and Firefly (ClearCompany).

## Quick start (local)
```bash
python internship_radar.py --check     # 1. verify which company tokens are live
python internship_radar.py             # 2. first poll — surfaces everything as "new"
python internship_radar.py             # 3. later polls — only shows NEW since last run
```
First, run `--check` and delete any company in `sources.py` marked `# ? VERIFY`
that comes back `DEAD`.

## Get pinged automatically
Set any of these as environment variables (locally) or repo **Secrets** (GitHub):
- `DISCORD_WEBHOOK` — easiest. Channel → Settings → Integrations → Webhooks → copy URL.
- `SLACK_WEBHOOK` — Slack incoming webhook URL.
- `USAJOBS_KEY` + `USAJOBS_EMAIL` — free from https://developer.usajobs.gov/apirequest/

## Always-on (GitHub Actions — zero infrastructure)
1. Push this folder to a **private** GitHub repo.
2. Repo → Settings → Secrets and variables → Actions → add `DISCORD_WEBHOOK` (etc).
3. Done. `.github/workflows/radar.yml` runs every 4 hours, commits `seen.json` so it
   remembers what it's shown you, and DMs you only the new ones.

## Add a company
Open `sources.py`, drop the Greenhouse token into `GREENHOUSE`, run `--check`.
To find a token: their careers URL `job-boards.greenhouse.io/XXXX` → token is `XXXX`.

## Tune the filter
Top of `internship_radar.py`: `TARGET_YEARS`, `WANT_SEASON`, `EXCLUDE_TERMS`.
Tags on each hit tell you why it matched: `2027` / `summer` / `no-year` / `no-season`
(the `no-*` tags = season/year not stated in the posting, worth a manual glance).

## Files
- `internship_radar.py` — the engine
- `sources.py` — your editable company/source list
- `seen.json` — what you've already been shown (auto-managed)
- `new_postings.md` — digest of the latest run
- `all_matches.csv` — running log of everything found
