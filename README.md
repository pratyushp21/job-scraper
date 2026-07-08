# Job Scrapper

Pulls live job postings from companies' own public ATS APIs (Greenhouse, Lever,
Ashby) — the same data shown on their careers pages, so this is fully
above-board. Filters for project management / implementation / delivery /
BA-type roles in Bengaluru, Noida/Gurugram, Delhi-NCR, and remote-India.

No installation needed — everything runs on plain Python 3 (already on macOS).

## Daily workflow (5 minutes)

```bash
cd "job scrapper"

# 1. Fetch new jobs — only ones you haven't seen before are shown
python3 scraper.py

# 2. When she applies to one, log it in the tracker with one command
python3 scraper.py --track "https://job-boards.greenhouse.io/....../jobs/12345"

# 3. Draft a personalized outreach message + resume-tailoring notes for a job
python3 draft_outreach.py "https://.../jobs/12345" --contact "Priya Sharma, TA Lead"
```

## Files

| File | What it is |
|---|---|
| `config.json` | Companies to watch, title keywords, location filters — edit freely |
| `data/jobs.csv` | Every matching job found, deduped, append-only |
| `data/tracker.csv` | Her application tracker — open in Excel/Numbers/Sheets and edit |
| `resume.md` | **You add this**: paste her resume as plain text (needed for drafts) |
| `drafts/` | Generated outreach messages / prompts land here |

## Google Sheets

Simplest reliable route: in a Google Sheet, **File → Import → Upload →
`jobs.csv`** (choose "Replace current sheet"). Re-import after each run, or
keep the tracker itself as a Google Sheet and use `jobs.csv` just as the feed
of new roles. Direct API sync to Sheets needs a Google Cloud service-account
key — doable later if the manual import gets annoying; ask Claude Code to add
it when you're ready.

## Adding more companies

Every company on the current list was verified live. To add one, find which
ATS its careers page uses (the URL gives it away) and test:

- Careers URL contains `greenhouse.io` → `curl "https://boards-api.greenhouse.io/v1/boards/SLUG/jobs"`
- Contains `lever.co` → `curl "https://api.lever.co/v0/postings/SLUG?mode=json"`
- Contains `ashbyhq.com` → `curl "https://api.ashbyhq.com/posting-api/job-board/SLUG"`

The SLUG is in the careers-page URL (e.g. `job-boards.greenhouse.io/postman`
→ slug `postman`). If the curl returns JSON, add
`{ "name": "...", "ats": "...", "slug": "..." }` to `config.json`. Note some
big names (Swiggy, Zoho, Freshworks) use custom portals with no public API —
those you check manually or ask Claude Code to add a custom fetcher for.

## Scheduling (optional)

To run it automatically every morning at 9:00 and log the output:

```bash
crontab -e
# add this line:
0 9 * * * cd "/Users/pratyushpandey/Documents/Cluade Code/job scrapper" && /usr/bin/python3 scraper.py >> data/run.log 2>&1
```

Then each morning just open `data/run.log` or re-run `python3 scraper.py`
(it prints nothing new if there's nothing new).
