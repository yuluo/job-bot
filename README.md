# job-bot

Scrapes job postings from Indeed, LinkedIn, and Dice for a given keyword and exports them to a single CSV — useful for analyzing the core requirements of a role.

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Usage

```bash
.venv/bin/python scraper.py "data engineer"
.venv/bin/python scraper.py "machine learning engineer" --location "Austin, TX" --results 50
.venv/bin/python scraper.py "platform engineer" --out jobs.csv
```

Defaults to 100 results per site. Output is `output/jobs_<keyword>_<timestamp>.csv` with columns:

`site, title, company, location, date_posted, salary, job_url, description`

## How it works

- **Indeed + LinkedIn** are scraped via the [python-jobspy](https://github.com/speedyapply/JobSpy) library. LinkedIn descriptions are fetched per posting (`linkedin_fetch_description=True`), which is slower but needed for requirements analysis.
- **Dice** (`dice.py`) uses Dice's unofficial JSON search API, then fetches each job's detail page to extract the full description from the embedded React Server Components payload.

A failure on one site does not abort the run — the script collects what succeeds and prints per-site counts.

## Caveats

- LinkedIn rate-limits aggressively (~10 pages per IP). 100 results is at the edge; repeated runs from one IP may return fewer results or get temporarily blocked. JobSpy supports a `proxies` parameter if needed.
- Scraping LinkedIn is against its ToS; keep usage low-volume and personal.
- Dice's API endpoint and key are unofficial (taken from their own frontend) and may change without notice; all Dice logic is isolated in `dice.py`.
