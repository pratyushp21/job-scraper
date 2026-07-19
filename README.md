# Job Scrapper

An open job-feed aggregator for project management / implementation /
delivery / BA roles, built on **public ATS and job-board APIs** — the same
data companies publish on their own careers pages. No LinkedIn/Naukri
scraping, no logins, nothing against anyone's terms.

**Sources:** Greenhouse, Lever, Ashby, SmartRecruiters, Workable, Recruitee
company boards (19 verified companies included) + Remotive and RemoteOK
remote-job feeds + optional Adzuna aggregator (free API key).

**New here? Read [SETUP.md](SETUP.md)** — it walks through everything,
including where to paste the Adzuna keys and how to host the dashboard free
on GitHub Pages.

## Daily use

```bash
python3 scraper.py --export-json          # fetch new jobs + follow-up reminders
python3 scraper.py --track "<job url>"    # log an application in the tracker
python3 draft_outreach.py "<job url>"     # tailored outreach draft for a job
```

## What's inside

| Path | What it is |
|---|---|
| `scraper.py` | Fetches all sources, filters, dedupes, detects closed jobs, reminds about follow-ups |
| `config.json` | Companies, keywords, locations, Adzuna search terms — edit freely |
| `draft_outreach.py` | Drafts a personalized outreach message + resume tailoring notes per job |
| `site/` | Interactive dashboard (search/filter UI) — deployable to GitHub Pages/Netlify |
| `data/jobs.csv` | All jobs found, deduped, with active/closed status |
| `data/tracker.csv` | Application tracker (private, gitignored) |
| `.github/workflows/scrape.yml` | Daily cloud refresh + free hosting via GitHub Actions/Pages |

## Adding companies

Find the company's careers page, identify its ATS from the URL, verify with
curl, add to `config.json`:

| ATS | Test URL |
|---|---|
| Greenhouse | `https://boards-api.greenhouse.io/v1/boards/SLUG/jobs` |
| Lever | `https://api.lever.co/v0/postings/SLUG?mode=json` |
| Ashby | `https://api.ashbyhq.com/posting-api/job-board/SLUG` |
| SmartRecruiters | `https://api.smartrecruiters.com/v1/companies/SLUG/postings` |
| Workable | POST `https://apply.workable.com/api/v3/accounts/SLUG/jobs` |
| Recruitee | `https://SLUG.recruitee.com/api/offers/` |

If it returns JSON with jobs, add `{ "name": "...", "ats": "...", "slug": "..." }`.

## Privacy

`resume.md`, `.env` (API keys), `drafts/`, and the tracker are gitignored —
they never leave your machine. Only public job listings are ever published.

MIT licensed.
