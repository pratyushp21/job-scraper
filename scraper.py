#!/usr/bin/env python3
"""Job scraper v2.

Sources (all public/legitimate APIs):
  - Company career boards: Greenhouse, Lever, Ashby, SmartRecruiters, Workable,
    Recruitee (companies listed in config.json)
  - Remote-job feeds: Remotive, RemoteOK
  - Adzuna aggregator (optional; needs free API keys in .env - see SETUP.md)

Maintains in data/:
  jobs.csv     - every matching job ever seen, deduped by URL, with an
                 `active` flag (jobs that vanish from a company board get
                 marked inactive automatically)
  tracker.csv  - your application tracker; --track adds rows, you edit status

Also prints follow-up reminders from tracker.csv on every run.

Usage:
  python3 scraper.py                # fetch everything, update CSVs, show new
  python3 scraper.py --all          # ignore keyword/location filters
  python3 scraper.py --track URL    # log an application into tracker.csv
  python3 scraper.py --export-json  # also write site/jobs.json for the dashboard

Standard library only. Adzuna keys are read from .env (ADZUNA_APP_ID /
ADZUNA_APP_KEY) or environment variables; the source is skipped if absent.
"""

import argparse
import csv
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
JOBS_CSV = DATA / "jobs.csv"
TRACKER_CSV = DATA / "tracker.csv"
SITE_JSON = BASE / "site" / "jobs.json"

JOBS_FIELDS = ["date_found", "company", "title", "location", "url", "source",
               "posted_at", "active", "match_score"]
TRACKER_FIELDS = ["company", "title", "url", "date_applied", "status",
                  "resume_version", "contact_person", "follow_up_date", "notes"]

UA = {"User-Agent": "Mozilla/5.0 (personal job-search tool)"}


def load_env():
    env_file = BASE / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())


def fetch_json(url, post_body=None):
    data = json.dumps(post_body).encode() if post_body is not None else None
    headers = dict(UA)
    if data:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=25) as resp:
        return json.load(resp)


# ---------------- company-board fetchers ----------------

def fetch_greenhouse(slug):
    for j in fetch_json(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs").get("jobs", []):
        yield {"title": j.get("title", ""),
               "location": (j.get("location") or {}).get("name", ""),
               "url": j.get("absolute_url", ""),
               "posted_at": (j.get("updated_at") or "")[:10]}


def fetch_lever(slug):
    for j in fetch_json(f"https://api.lever.co/v0/postings/{slug}?mode=json"):
        yield {"title": j.get("text", ""),
               "location": (j.get("categories") or {}).get("location", "") or "",
               "url": j.get("hostedUrl", ""),
               "posted_at": ""}


def fetch_ashby(slug):
    for j in fetch_json(f"https://api.ashbyhq.com/posting-api/job-board/{slug}").get("jobs", []):
        locs = [j.get("location", "")] + [s.get("location", "")
                                          for s in j.get("secondaryLocations") or []]
        yield {"title": j.get("title", ""),
               "location": "; ".join(l for l in locs if l),
               "url": j.get("jobUrl", "") or j.get("applyUrl", ""),
               "posted_at": (j.get("publishedAt") or "")[:10]}


def fetch_smartrecruiters(slug):
    offset = 0
    while True:
        data = fetch_json(
            f"https://api.smartrecruiters.com/v1/companies/{slug}/postings?limit=100&offset={offset}")
        batch = data.get("content", [])
        for j in batch:
            loc = j.get("location") or {}
            city = ", ".join(x for x in [loc.get("city", ""), loc.get("country", "")] if x)
            yield {"title": j.get("name", ""),
                   "location": city,
                   "url": f"https://jobs.smartrecruiters.com/{slug}/{j.get('id')}",
                   "posted_at": (j.get("releasedDate") or "")[:10]}
        offset += len(batch)
        if not batch or offset >= data.get("totalFound", 0):
            break


def fetch_workable(slug):
    data = fetch_json(f"https://apply.workable.com/api/v3/accounts/{slug}/jobs",
                      post_body={"query": "", "location": [], "department": [],
                                 "worktype": [], "remote": []})
    for j in data.get("results", []):
        loc = j.get("location") or {}
        yield {"title": j.get("title", ""),
               "location": ", ".join(x for x in [loc.get("city", ""), loc.get("country", "")] if x),
               "url": f"https://apply.workable.com/{slug}/j/{j.get('shortcode')}/",
               "posted_at": (j.get("published") or "")[:10]}


def fetch_recruitee(slug):
    for j in fetch_json(f"https://{slug}.recruitee.com/api/offers/").get("offers", []):
        yield {"title": j.get("title", ""),
               "location": j.get("location", "") or "",
               "url": j.get("careers_url", ""),
               "posted_at": (j.get("published_at") or "")[:10]}


FETCHERS = {
    "greenhouse": fetch_greenhouse,
    "lever": fetch_lever,
    "ashby": fetch_ashby,
    "smartrecruiters": fetch_smartrecruiters,
    "workable": fetch_workable,
    "recruitee": fetch_recruitee,
}

# ---------------- feed sources (remote boards + aggregator) ----------------

def fetch_remotive(cfg):
    seen = set()
    for term in cfg["title_keywords"][:6]:
        q = urllib.parse.quote(term)
        for j in fetch_json(f"https://remotive.com/api/remote-jobs?search={q}").get("jobs", []):
            url = j.get("url", "")
            if url in seen:
                continue
            seen.add(url)
            yield {"company": j.get("company_name", "?"),
                   "title": j.get("title", ""),
                   "location": j.get("candidate_required_location", "") or "Remote",
                   "url": url,
                   "posted_at": (j.get("publication_date") or "")[:10]}


def fetch_remoteok(cfg):
    data = fetch_json("https://remoteok.com/api")
    for j in data:
        if not isinstance(j, dict) or not j.get("position"):
            continue
        yield {"company": j.get("company", "?"),
               "title": j.get("position", ""),
               "location": j.get("location", "") or "Remote",
               "url": j.get("url", ""),
               "posted_at": (j.get("date") or "")[:10]}


def fetch_adzuna(cfg):
    app_id, app_key = os.environ.get("ADZUNA_APP_ID"), os.environ.get("ADZUNA_APP_KEY")
    if not (app_id and app_key):
        return
    az = cfg["sources"]["adzuna"]
    seen = set()
    for term in az["search_terms"]:
        for city in az["cities"]:
            params = urllib.parse.urlencode({
                "app_id": app_id, "app_key": app_key,
                "what": term, "where": city, "results_per_page": 50,
                "content-type": "application/json"})
            url = f"https://api.adzuna.com/v1/api/jobs/{az['country']}/search/1?{params}"
            try:
                results = fetch_json(url).get("results", [])
            except Exception as e:
                print(f"  !! adzuna ({term} / {city}): {e}", file=sys.stderr)
                continue
            for j in results:
                # redirect_url carries per-request tracking tokens; strip them
                # so the same ad dedupes across runs
                jurl = j.get("redirect_url", "").split("?")[0]
                if jurl in seen:
                    continue
                seen.add(jurl)
                yield {"company": (j.get("company") or {}).get("display_name", "?"),
                       "title": j.get("title", "").replace("<strong>", "").replace("</strong>", ""),
                       "location": (j.get("location") or {}).get("display_name", ""),
                       "url": jurl,
                       "posted_at": (j.get("created") or "")[:10]}


# ---------------- filtering + persistence ----------------

def fix_mojibake(s):
    """Repair UTF-8 text that a source double-encoded (e.g. 'â€“' -> '–')."""
    if "â" in s or "Ã" in s:
        for enc in ("windows-1252", "latin-1"):
            try:
                return s.encode(enc).decode("utf-8")
            except (UnicodeEncodeError, UnicodeDecodeError):
                continue
    return s


def title_ok(title, keywords):
    return not keywords or any(k in title.lower() for k in keywords)


def location_ok(loc, allowed):
    return not allowed or not loc or any(a in loc.lower() for a in allowed)


def load_jobs():
    rows = {}
    if JOBS_CSV.exists():
        with open(JOBS_CSV, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                r.setdefault("active", "yes")
                r.setdefault("match_score", "")
                url = r["url"]
                if r.get("source") == "adzuna":
                    url = url.split("?")[0]  # merge rows saved before URL canonicalization
                    r["url"] = url
                if url in rows:  # keep the earliest sighting
                    if r["date_found"] < rows[url]["date_found"]:
                        rows[url]["date_found"] = r["date_found"]
                    continue
                for k in ("title", "company", "location"):
                    r[k] = fix_mojibake(r.get(k, ""))
                rows[url] = {k: r.get(k, "") for k in JOBS_FIELDS}
    return rows


def save_jobs(rows):
    ordered = sorted(rows.values(), key=lambda r: (r["date_found"], r["company"]), reverse=True)
    with open(JOBS_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=JOBS_FIELDS)
        w.writeheader()
        w.writerows(ordered)


def ensure_tracker():
    if not TRACKER_CSV.exists():
        with open(TRACKER_CSV, "w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=TRACKER_FIELDS).writeheader()


def print_followups():
    if not TRACKER_CSV.exists():
        return
    today = date.today().isoformat()
    due = []
    with open(TRACKER_CSV, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            d = (r.get("follow_up_date") or "").strip()
            if d and d <= today and (r.get("status") or "").lower() not in ("rejected", "offer", "closed"):
                due.append(r)
    if due:
        print("\n*** FOLLOW-UPS DUE ***")
        for r in due:
            print(f"  [{r['company']}] {r['title']} — status: {r['status']}, due {r['follow_up_date']}")


def export_json(rows):
    SITE_JSON.parent.mkdir(exist_ok=True)
    jobs = [r for r in rows.values() if r["active"] == "yes"]
    jobs.sort(key=lambda r: r["date_found"], reverse=True)
    SITE_JSON.write_text(json.dumps(
        {"generated": date.today().isoformat(), "jobs": jobs}, indent=1))
    print(f"\nDashboard data written to {SITE_JSON.relative_to(BASE)} ({len(jobs)} active jobs)")


# ---------------- commands ----------------

def cmd_scrape(show_all):
    cfg = json.loads((BASE / "config.json").read_text())
    keywords = [] if show_all else [k.lower() for k in cfg["title_keywords"]]
    locations = [] if show_all else [l.lower() for l in cfg["locations"]]
    remote_ok = [l.lower() for l in cfg.get("remote_locations_ok", [])]

    rows = load_jobs()
    today = date.today().isoformat()
    new_rows = []

    def add(company, j, source):
        url = j["url"]
        if not url:
            return
        if url in rows:
            rows[url]["active"] = "yes"
        else:
            row = {"date_found": today, "company": fix_mojibake(company),
                   "title": fix_mojibake(j["title"]),
                   "location": fix_mojibake(j["location"]), "url": url, "source": source,
                   "posted_at": j["posted_at"], "active": "yes", "match_score": ""}
            rows[url] = row
            new_rows.append(row)

    # company boards (with closed-job detection)
    for co in cfg["companies"]:
        try:
            jobs = list(FETCHERS[co["ats"]](co["slug"]))
        except Exception as e:
            print(f"  !! {co['name']} ({co['ats']}/{co['slug']}): {e}", file=sys.stderr)
            continue
        current = {j["url"] for j in jobs}
        hits = [j for j in jobs
                if title_ok(j["title"], keywords) and location_ok(j["location"], locations)]
        for j in hits:
            add(co["name"], j, co["ats"])
        closed = 0
        for url, r in rows.items():
            if r["source"] == co["ats"] and r["company"] == co["name"] \
                    and r["active"] == "yes" and url not in current:
                r["active"] = "no"
                closed += 1
        print(f"  {co['name']:<12} {len(jobs):>4} open, {len(hits):>3} match"
              + (f", {closed} closed" if closed else ""))

    # remote feeds: filter title + remote-location whitelist
    feeds = []
    if cfg["sources"].get("remotive"):
        feeds.append(("remotive", fetch_remotive))
    if cfg["sources"].get("remoteok"):
        feeds.append(("remoteok", fetch_remoteok))
    if os.environ.get("ADZUNA_APP_ID"):
        feeds.append(("adzuna", fetch_adzuna))
    else:
        print("  (adzuna skipped — no API keys yet, see SETUP.md)")

    for name, fn in feeds:
        try:
            jobs = list(fn(cfg))
        except Exception as e:
            print(f"  !! {name}: {e}", file=sys.stderr)
            continue
        n = 0
        for j in jobs:
            if not title_ok(j["title"], keywords):
                continue
            loc = j["location"].lower()
            if name in ("remotive", "remoteok") and not show_all:
                if loc and not any(x in loc for x in remote_ok):
                    continue
            add(j["company"], j, name)
            n += 1
        print(f"  {name:<12} {len(jobs):>4} fetched, {n:>3} match")

    save_jobs(rows)
    ensure_tracker()

    if new_rows:
        print(f"\n{len(new_rows)} new job(s):\n")
        for r in new_rows:
            print(f"  [{r['company']}] {r['title']} — {r['location']}\n    {r['url']}")
    else:
        print("\nNo new jobs since last run.")

    print_followups()
    export_json(rows)


def cmd_track(url):
    ensure_tracker()
    rows = load_jobs()
    job = rows.get(url)
    if job is None:
        sys.exit(f"URL not found in jobs.csv: {url}")
    with open(TRACKER_CSV, "a", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=TRACKER_FIELDS).writerow({
            "company": job["company"], "title": job["title"], "url": url,
            "date_applied": date.today().isoformat(), "status": "applied",
            "resume_version": "", "contact_person": "", "follow_up_date": "", "notes": ""})
    print(f"Added to tracker: [{job['company']}] {job['title']}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--all", action="store_true", help="skip keyword/location filters")
    p.add_argument("--track", metavar="URL", help="log an application into tracker.csv")
    p.add_argument("--export-json", action="store_true",
                   help="(kept for compatibility; the dashboard JSON is now always written)")
    args = p.parse_args()
    DATA.mkdir(exist_ok=True)
    load_env()
    if args.track:
        cmd_track(args.track)
    else:
        cmd_scrape(args.all)
