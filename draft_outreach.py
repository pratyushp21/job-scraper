#!/usr/bin/env python3
"""Draft a tailored outreach message (and resume-tailoring notes) for one job.

Builds a detailed prompt from the job row in data/jobs.csv plus your resume
(resume.md in this folder), then either:
  - pipes it through the `claude` CLI if installed (claude -p), or
  - saves the prompt to drafts/ so you can paste it into Claude yourself.

Usage:
  python3 draft_outreach.py JOB_URL
  python3 draft_outreach.py JOB_URL --contact "Priya Sharma, Talent Acquisition"

You review and send every message yourself — nothing is sent automatically.
"""

import argparse
import csv
import re
import shutil
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
JOBS_CSV = BASE / "data" / "jobs.csv"
RESUME = BASE / "resume.md"
DRAFTS = BASE / "drafts"

PROMPT_TEMPLATE = """You are helping a job seeker with ~3 years of experience as an \
IT project coordinator / ERP-CRM implementation specialist apply for this role:

Company: {company}
Title: {title}
Location: {location}
Job posting URL: {url}
{contact_line}

Her resume:
---
{resume}
---

Please produce three things:

1. OUTREACH MESSAGE: A short (under 120 words), warm, specific LinkedIn/email
   message to the contact person (or "the hiring team" if none given) asking
   about this role. No flattery, no buzzwords, one concrete hook from her
   experience that matches the role.

2. RESUME TAILORING: The 4-6 resume bullets she should emphasize or reword
   for this specific job, with suggested rewording.

3. KEYWORD GAPS: Keywords likely in this job description that her resume is
   missing, so she can address them honestly if she has the experience.
"""


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("url", help="job URL (must exist in data/jobs.csv)")
    p.add_argument("--contact", default="", help="name/role of the recruiter or hiring manager")
    args = p.parse_args()

    if not RESUME.exists():
        sys.exit("Put the resume in this folder as resume.md first (plain text is fine).")

    job = None
    with open(JOBS_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["url"] == args.url:
                job = row
                break
    if job is None:
        sys.exit(f"URL not found in data/jobs.csv — run scraper.py first: {args.url}")

    contact_line = f"Contact person: {args.contact}" if args.contact else ""
    prompt = PROMPT_TEMPLATE.format(
        company=job["company"], title=job["title"], location=job["location"],
        url=job["url"], contact_line=contact_line, resume=RESUME.read_text(),
    )

    DRAFTS.mkdir(exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", f"{job['company']}-{job['title']}".lower()).strip("-")

    if shutil.which("claude"):
        print(f"Drafting with Claude for [{job['company']}] {job['title']} ...\n")
        result = subprocess.run(["claude", "-p", prompt], capture_output=True, text=True)
        if result.returncode == 0:
            out = DRAFTS / f"{slug}.md"
            out.write_text(result.stdout)
            print(result.stdout)
            print(f"\nSaved to {out.relative_to(BASE)}")
            return
        print(f"claude CLI failed ({result.stderr.strip()}), saving prompt instead.", file=sys.stderr)

    out = DRAFTS / f"{slug}-PROMPT.md"
    out.write_text(prompt)
    print(f"Prompt saved to {out.relative_to(BASE)} — paste it into Claude to get the draft.")


if __name__ == "__main__":
    main()
