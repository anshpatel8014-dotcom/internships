"""
Source registry for the internship radar.

Add/remove companies here without touching the main script.

HOW TO FIND A COMPANY'S GREENHOUSE TOKEN:
  Go to their careers page. If the URL looks like
      https://job-boards.greenhouse.io/SPACEX        -> token is "spacex"
      https://boards.greenhouse.io/embed/job_board?for=RELATIVITY  -> token is "relativity"
  then add it to GREENHOUSE below. Run `python internship_radar.py --check`
  to verify every token resolves before relying on it.

TOKENS MARKED  # ? VERIFY  ARE GUESSES — the --check run will tell you which
are real. Delete the ones that 404.
"""

# --- Greenhouse boards (the reliable backbone) ---------------------------------
# name : board_token
GREENHOUSE = {
    "SpaceX":            "spacex",            # confirmed
    "Rocket Lab":        "rocketlab",         # confirmed
    "Anduril":           "andurilindustries", # confirmed
    "Relativity Space":  "relativity",        # confirmed
    # --- verify with --check; delete any that come back DEAD ---
    "Blue Origin":       "blueorigin",        # ? VERIFY  (US persons only)
    "Stoke Space":       "stokespace",        # ? VERIFY
    "Sierra Space":      "sierraspace",       # ? VERIFY
    "Astranis":          "astranis",          # ? VERIFY
    "ABL Space":         "ablspacesystems",   # ? VERIFY
}

# --- Lever boards (api.lever.co/v0/postings/{token}) ---------------------------
LEVER = {
    "Venus Aerospace":   "venusaero",         # confirmed (rotating detonation engines)
    "Hermeus":           "hermeus",           # confirmed (hypersonics)
    # "Ursa Major":      "ursamajor",         # ? VERIFY — ATS unconfirmed, try it
}

# --- Workday tenants for the primes (best-effort; some return HTTP 422) ---------
# name : (tenant, datacenter, site_path)
#   from https://{tenant}.{dc}.myworkdayjobs.com/{site_path}
WORKDAY = {
    "Lockheed Martin":  ("lockheedmartin", "wd5", "Search"),
    "Northrop Grumman": ("ngc",            "wd1", "Northrop_Grumman_External_Site"),
    "RTX (Raytheon/P&W)":("rtx",           "wd1", "RTX"),
    "Boeing":           ("boeing",         "wd1", "external_careers"),
}

# --- USAJOBS (federal: Pathways, AFRL, national labs) ---------------------------
# Requires a FREE key from https://developer.usajobs.gov/apirequest/
# Set env vars USAJOBS_KEY and USAJOBS_EMAIL to enable. Keywords searched:
USAJOBS_KEYWORDS = ["aerospace intern", "propulsion intern", "mechanical engineer intern"]

# --- Manual / portal-only sources (no API — set a calendar reminder) ------------
MANUAL_REMINDERS = {
    "NASA OSTEM (intern.nasa.gov)": "Summer 2027 deadline ~Feb 26, 2027 — closed portal, apply manually",
    "Firefly Aerospace":            "Runs on ClearCompany (no clean API) — check firefly.hrmdirect.com manually",
}
