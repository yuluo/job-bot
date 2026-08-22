---
name: scrape-jobs
description: Scrape ~100 job postings each from Indeed, LinkedIn, and Dice for a keyword and export to a CSV in roles/<slug>/. Use when the user wants to collect job postings for a search term.
argument-hint: <keyword> [location] [results]
---

Run the job scraper for the keyword given in the skill arguments and report the results.

## Parsing arguments

- The arguments are primarily the search keyword (e.g. `data engineer`, `power BI`).
- If the arguments clearly include a location (e.g. `... in Austin, TX`), pass it as `--location "Austin, TX"` and remove it from the keyword.
- If the arguments clearly include a result count (e.g. `... 50 results`), pass it as `--results 50` and remove it from the keyword. Default is 100 per site.
- If no keyword remains after parsing, ask the user for one.

## Running

1. Work from the repo root (where `scraper.py` lives).
2. If `.venv/` does not exist, set it up first:
   ```bash
   python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
   ```
3. Run the scraper in the background — a full 100-per-site run takes ~4-5 minutes because it fetches the full description of every posting:
   ```bash
   .venv/bin/python scraper.py "<keyword>" [--location "..."] [--results N]
   ```
4. Tell the user the run has started and roughly how long it takes, then wait for completion.

## Reporting

The script's final line has the summary:

```
indeed: N, linkedin: N, dice: N -> roles/<slug>/jobs_<timestamp>.csv (M rows)
```

When the run finishes, report the per-site counts and the CSV path. If a site failed or returned fewer results (LinkedIn rate-limits around 100 results per IP), relay its stderr message and note that the rest of the run still succeeded — per-site failures are tolerated by design. Do not analyze the CSV contents unless the user asks.
