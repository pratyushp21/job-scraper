# Job Scrapper — your personal job feed

**One dashboard for all the jobs you care about, refreshed automatically
every morning — plus a tracker for your applications and AI-assisted outreach
drafts based on your own resume.**

Job portals are noisy, and the best openings often appear on company career
pages days before they show up anywhere else. Nobody has time to check 30
career pages, three remote-job boards, and an aggregator every day. This tool
does it for you.

## What it does

1. **Collects jobs from everywhere** — straight from companies' own public
   job boards (Greenhouse, Lever, Ashby, SmartRecruiters, Workable,
   Recruitee), remote-job boards (Remotive, RemoteOK), and the Adzuna
   aggregator. All via public APIs these platforms provide for exactly this
   purpose — no logins, no scraping tricks, nothing against anyone's terms.
2. **Cleans it up** — filters to your roles and cities, removes duplicates,
   and detects when a posting quietly closes.
3. **Shows it on a dashboard** — a simple web page you can search and filter.
   Host it free on GitHub Pages; it refreshes itself daily.
4. **Analyzes jobs against your resume** — paste your resume in once, and for
   any job it drafts a personalized recruiter message, tells you which resume
   bullets to emphasize, and lists keywords your resume is missing. You
   review and send everything yourself — no bots apply on your behalf.
5. **Tracks your applications** — one command logs each application (company,
   role, date, status), and it reminds you when a follow-up is due.

No installation needed: plain Python 3, which is already on macOS and Linux.

## Quick start (2 minutes)

```bash
git clone https://github.com/YOUR-USERNAME/job-scraper.git
cd job-scraper
python3 scraper.py
```

That's it. Jobs land in `data/jobs.csv`, and the dashboard data is generated
automatically. To view the dashboard locally:

```bash
cd site && python3 -m http.server 8080
# open http://localhost:8080
```

## Make it YOURS (the important part)

Everything is driven by one file: **`config.json`**.

- `companies` — the career boards to watch. Add any company you like (see
  "Adding companies" below).
- `title_keywords` — words that must appear in the job title. Change
  `"project manager"` to `"data analyst"` or `"ux designer"` and the whole
  tool re-targets to your field.
- `locations` — your cities. Currently Bengaluru / Noida / Gurugram /
  Delhi-NCR / India-remote; edit to anywhere.
- `sources.adzuna.search_terms` and `.cities` — what the Adzuna aggregator
  searches for.

A designer in Mumbai and a data analyst in Pune can run this exact tool with
a two-minute config edit.

## Everyday commands

```bash
python3 scraper.py                       # fetch new jobs + follow-up reminders
python3 scraper.py --all                 # everything, ignoring your filters
python3 scraper.py --track "<job url>"   # log "I applied to this" in the tracker
python3 draft_outreach.py "<job url>" --contact "Name, Role"
                                         # outreach draft + resume tips for a job
```

For the resume features, paste your resume as plain text into a file called
`resume.md` in this folder first. It stays on your machine — it is gitignored
and never uploaded anywhere.

## Optional power-ups

- **Adzuna aggregator** (thousands more portal listings): free API key from
  [developer.adzuna.com](https://developer.adzuna.com/), then create `.env`:
  ```
  ADZUNA_APP_ID=your_id
  ADZUNA_APP_KEY=your_key
  ```
- **Auto-refresh every morning + free public dashboard**: push this repo to
  GitHub, enable Pages (Settings → Pages → Source: GitHub Actions), add your
  Adzuna keys as repository secrets, and the included workflow scrapes daily
  and publishes your dashboard at `https://you.github.io/job-scraper/`.
- **Local daily run instead**: one cron line —
  `0 9 * * * cd /path/to/job-scraper && python3 scraper.py >> data/run.log 2>&1`

Full step-by-step details for all of this: **[SETUP.md](SETUP.md)**.

## Adding companies

Find the company's careers page, spot its ATS from the URL, verify the feed
exists, add one line to `config.json`:

| ATS | Test URL |
|---|---|
| Greenhouse | `https://boards-api.greenhouse.io/v1/boards/SLUG/jobs` |
| Lever | `https://api.lever.co/v0/postings/SLUG?mode=json` |
| Ashby | `https://api.ashbyhq.com/posting-api/job-board/SLUG` |
| SmartRecruiters | `https://api.smartrecruiters.com/v1/companies/SLUG/postings` |
| Workable | POST `https://apply.workable.com/api/v3/accounts/SLUG/jobs` |
| Recruitee | `https://SLUG.recruitee.com/api/offers/` |

If the URL returns JSON with jobs, add
`{ "name": "Company", "ats": "greenhouse", "slug": "SLUG" }` to `companies`.

## What's in the folder

| Path | What it is |
|---|---|
| `scraper.py` | Fetches all sources, filters, dedupes, detects closed jobs, reminds about follow-ups |
| `config.json` | Your companies, keywords, cities — the file that makes it yours |
| `draft_outreach.py` | Per-job outreach message + resume-tailoring suggestions |
| `site/` | The dashboard (plain HTML/JS, deployable anywhere static) |
| `data/jobs.csv` | Every job found, deduped, with active/closed status |
| `data/tracker.csv` | Your application tracker (private, gitignored) |
| `.github/workflows/scrape.yml` | Daily cloud refresh + GitHub Pages deploy |

## Privacy

Your resume, API keys, outreach drafts, and application tracker are all
gitignored — they never leave your machine. Only public job listings are ever
published to the dashboard.

MIT licensed. Fork it, remix it, share it.
