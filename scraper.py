#!/usr/bin/env python3
"""Job scraper: pulls live postings from public ATS APIs (Greenhouse, Lever,
Ashby) for the companies in config.json, filters by title keywords and
location, and maintains two CSVs in data/:

  jobs.csv      - every matching job ever seen (append-only, deduped by URL)
  tracker.csv   - your application tracker (created once; you edit it)

Usage:
  python3 scraper.py              # fetch, filter, update jobs.csv, show new jobs
  python3 scraper.py --all        # ignore keyword/location filters (see everything)
  python3 scraper.py --track URL  # copy a job from jobs.csv into tracker.csv

No dependencies beyond the Python standard library.
"""

import argparse
import csv
import json
import sys
import urllib.request
from datetime import date
from pathlib import Path

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
JOBS_CSV = DATA / "jobs.csv"
TRACKER_CSV = DATA / "tracker.csv"

JOBS_FIELDS = ["date_found", "company", "title", "location", "url", "source", "posted_at"]
TRACKER_FIELDS = [
    "company", "title", "url", "date_applied", "status",
    "resume_version", "contact_person", "follow_up_date", "notes",
]

UA = {"User-Agent": "Mozilla/5.0 (job-search script; personal use)"}


def fetch_json(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.load(resp)


def fetch_greenhouse(slug):
    data = fetch_json(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs")
    for j in data.get("jobs", []):
        yield {
            "title": j.get("title", ""),
            "location": (j.get("location") or {}).get("name", ""),
            "url": j.get("absolute_url", ""),
            "posted_at": (j.get("updated_at") or "")[:10],
        }


def fetch_lever(slug):
    data = fetch_json(f"https://api.lever.co/v0/postings/{slug}?mode=json")
    for j in data:
        cats = j.get("categories") or {}
        yield {
            "title": j.get("text", ""),
            "location": cats.get("location", "") or "",
            "url": j.get("hostedUrl", ""),
            "posted_at": "",
        }


def fetch_ashby(slug):
    data = fetch_json(f"https://api.ashbyhq.com/posting-api/job-board/{slug}")
    for j in data.get("jobs", []):
        locs = [j.get("location", "")] + [
            s.get("location", "") for s in j.get("secondaryLocations") or []
        ]
        yield {
            "title": j.get("title", ""),
            "location": "; ".join(l for l in locs if l),
            "url": j.get("jobUrl", "") or j.get("applyUrl", ""),
            "posted_at": (j.get("publishedAt") or "")[:10],
        }


FETCHERS = {"greenhouse": fetch_greenhouse, "lever": fetch_lever, "ashby": fetch_ashby}


def matches(job, keywords, locations):
    title = job["title"].lower()
    if keywords and not any(k in title for k in keywords):
        return False
    loc = job["location"].lower()
    if locations and loc and not any(l in loc for l in locations):
        return False
    return True


def load_existing_urls():
    if not JOBS_CSV.exists():
        return set()
    with open(JOBS_CSV, newline="", encoding="utf-8") as f:
        return {row["url"] for row in csv.DictReader(f)}


def append_jobs(rows):
    new_file = not JOBS_CSV.exists()
    with open(JOBS_CSV, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=JOBS_FIELDS)
        if new_file:
            w.writeheader()
        w.writerows(rows)


def ensure_tracker():
    if not TRACKER_CSV.exists():
        with open(TRACKER_CSV, "w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=TRACKER_FIELDS).writeheader()


def cmd_scrape(show_all):
    cfg = json.loads((BASE / "config.json").read_text())
    keywords = [] if show_all else [k.lower() for k in cfg["title_keywords"]]
    locations = [] if show_all else [l.lower() for l in cfg["locations"]]

    seen = load_existing_urls()
    new_rows, today = [], date.today().isoformat()

    for co in cfg["companies"]:
        try:
            jobs = list(FETCHERS[co["ats"]](co["slug"]))
        except Exception as e:
            print(f"  !! {co['name']} ({co['ats']}/{co['slug']}): {e}", file=sys.stderr)
            continue
        hits = [j for j in jobs if matches(j, keywords, locations)]
        fresh = [j for j in hits if j["url"] and j["url"] not in seen]
        print(f"  {co['name']:<12} {len(jobs):>4} open roles, {len(hits):>3} match, {len(fresh):>3} new")
        for j in fresh:
            seen.add(j["url"])
            new_rows.append({
                "date_found": today, "company": co["name"], "title": j["title"],
                "location": j["location"], "url": j["url"],
                "source": co["ats"], "posted_at": j["posted_at"],
            })

    if new_rows:
        append_jobs(new_rows)
        print(f"\n{len(new_rows)} new job(s) added to {JOBS_CSV.relative_to(BASE)}:\n")
        for r in new_rows:
            print(f"  [{r['company']}] {r['title']} — {r['location']}\n    {r['url']}")
    else:
        print("\nNo new jobs since last run.")
    ensure_tracker()


def cmd_track(url):
    ensure_tracker()
    job = None
    if JOBS_CSV.exists():
        with open(JOBS_CSV, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row["url"] == url:
                    job = row
                    break
    if job is None:
        sys.exit(f"URL not found in jobs.csv: {url}")
    with open(TRACKER_CSV, "a", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=TRACKER_FIELDS).writerow({
            "company": job["company"], "title": job["title"], "url": url,
            "date_applied": date.today().isoformat(), "status": "applied",
            "resume_version": "", "contact_person": "", "follow_up_date": "", "notes": "",
        })
    print(f"Added to tracker: [{job['company']}] {job['title']}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--all", action="store_true", help="skip keyword/location filters")
    p.add_argument("--track", metavar="URL", help="copy a job from jobs.csv into tracker.csv")
    args = p.parse_args()
    DATA.mkdir(exist_ok=True)
    if args.track:
        cmd_track(args.track)
    else:
        cmd_scrape(args.all)
