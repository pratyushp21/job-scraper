# Setup Guide

Follow this top to bottom once; after that daily use is a single command.

## 1. Requirements

- macOS or Linux with Python 3.9+ (`python3 --version` — already on your Mac).
- No packages to install. Everything uses the Python standard library.

## 2. First run

```bash
cd "job scrapper"
python3 scraper.py
```

This fetches all sources, writes `data/jobs.csv`, creates `data/tracker.csv`,
and always regenerates `site/jobs.json` — so the dashboard is up to date
after every run, automatically.

## 3. Add resume (needed for outreach drafts)

Create `resume.md` in this folder and paste her resume as plain text.
This file stays local — it is gitignored and never uploaded anywhere.

## 4. Adzuna integration (paste your API keys here)

1. Sign up free at https://developer.adzuna.com/ (takes ~2 minutes).
2. From the dashboard, copy your **Application ID** and **Application Key**.
3. Create a file named `.env` in this folder containing exactly:

```
ADZUNA_APP_ID=paste_your_app_id_here
ADZUNA_APP_KEY=paste_your_app_key_here
```

4. Run `python3 scraper.py` again — the "adzuna skipped" line disappears and
   Adzuna results (which indirectly cover much of Naukri/LinkedIn via
   aggregation) flow into the same `jobs.csv`.

`.env` is gitignored: your keys never leave your machine or reach GitHub.
Search terms and cities for Adzuna are editable in `config.json` under
`sources.adzuna`.

## 5. View the dashboard locally

```bash
cd site && python3 -m http.server 8080
```

Open http://localhost:8080 — searchable, filterable feed of all active jobs.
Re-run `python3 scraper.py --export-json` to refresh the data.

## 6. Daily automation (optional)

```bash
crontab -e
```

Add:

```
0 9 * * * cd "/Users/pratyushpandey/Documents/Cluade Code/job scrapper" && /usr/bin/python3 scraper.py >> data/run.log 2>&1
```

Every morning at 9:00 the feed refreshes itself; check `data/run.log` or the
dashboard.

## 7. Publish it publicly (free hosting for ~100 users)

**Netlify cannot run the Python scraper** — it only serves static files. The
right free setup is **GitHub (repo + Actions + Pages)**: Actions runs the
scraper on a schedule in the cloud, commits fresh `jobs.json`, and Pages
serves the dashboard. All free, and a static page easily handles 100 or
100,000 visitors.

1. Create a GitHub repo and push this folder (`.gitignore` already protects
   `resume.md`, `.env`, `data/`, `drafts/`).
2. In the repo: **Settings → Pages → Source: GitHub Actions**.
3. The included workflow `.github/workflows/scrape.yml` does the rest: it
   runs the scraper every morning (and on manual trigger), rebuilds
   `site/jobs.json`, and deploys `site/` to Pages.
4. Your public URL will be `https://<your-username>.github.io/<repo-name>/`
   — share that on LinkedIn.
5. Optional Adzuna in the cloud: add `ADZUNA_APP_ID` and `ADZUNA_APP_KEY`
   as **repository secrets** (Settings → Secrets and variables → Actions);
   the workflow picks them up automatically. Never commit the `.env` file.

If you specifically want Netlify: point Netlify at the repo with publish
directory `site/` — it will serve the same dashboard, but you still need the
GitHub Action (or your cron job + a push) to refresh `jobs.json`. GitHub
Pages alone is simpler; use Netlify only if you want its custom-domain or
preview features.

**What stays private vs public:** the published site contains only public job
listings (`site/`). The tracker, resume, drafts, and API keys never leave
your machine.

## 8. Daily routine after setup

```bash
python3 scraper.py                        # see what's new + follow-ups due
python3 scraper.py --track "<job url>"    # after she applies somewhere
python3 draft_outreach.py "<job url>" --contact "Name, Role"   # outreach draft
```

## 9. Wrap-up checklist for publishing to GitHub

The local git repo is already initialized with an initial commit, and the
`.gitignore` is verified to exclude `.env`, `resume.md`, `drafts/`, and the
tracker. What's left for you:

1. Create an empty repo on github.com (e.g. `job-scrapper`) — no README/license
   (they already exist here).
2. Connect and push (if a remote is already configured — check with
   `git remote -v` — skip the `remote add` line):
   ```bash
   cd "job scrapper"
   git remote add origin https://github.com/<your-username>/job-scrapper.git
   git push -u origin main
   ```
3. On GitHub: **Settings → Pages → Build and deployment → Source: GitHub Actions**.
4. **Settings → Secrets and variables → Actions → New repository secret** —
   add `ADZUNA_APP_ID` and `ADZUNA_APP_KEY` (same values as your `.env`).
5. Go to the **Actions** tab → "Scrape jobs and deploy dashboard" →
   **Run workflow** to trigger the first cloud run; after it finishes your
   dashboard is live at `https://<your-username>.github.io/job-scrapper/`.
   From then on it refreshes itself daily at 09:00 IST.
6. Sanity check before sharing the link: open the live URL, confirm jobs load,
   and confirm the repo shows no `.env` or `resume.md` file.
