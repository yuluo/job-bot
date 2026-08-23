---
name: scrape-jobs
description: Scrape ~20 job postings each from Indeed, LinkedIn, and Dice for a keyword and export to a CSV in roles/<slug>/. Use when the user wants to collect job postings for a search term.
argument-hint: <keyword> [location] [results]
---

Run the job scraper for the keyword given in the skill arguments and report the results.

## Parsing arguments

- The arguments are primarily the search keyword (e.g. `data engineer`, `power BI`).
- If the arguments clearly include a location (e.g. `... in Austin, TX`), pass it as `--location "Austin, TX"` and remove it from the keyword.
- If the arguments clearly include a result count (e.g. `... 50 results`), pass it as `--results 50` and remove it from the keyword. Default is 20 per site.
- If they name an employment type (`full-time`, `full time`, `contract`, `contractor`, `part-time`, `internship`), pass it as `--job-type fulltime|contract|parttime|internship` and remove it from the keyword.
- If they ask for remote work (`remote`, `work from home`, `wfh`), pass `--remote` and remove it from the keyword. Take care not to strip a keyword that genuinely contains the word — "remote sensing engineer" is a field, not a work arrangement; ask if it is ambiguous.
- If no keyword remains after parsing, ask the user for one.

## Running

1. Work from the repo root (where `scraper.py` lives).
2. If `.venv/` does not exist, set it up first:
   ```bash
   python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
   ```
3. Run the scraper in the background — the default 20-per-site run takes about 40 seconds, since it fetches the full description of every posting. Scale that estimate roughly linearly for larger `--results` values (100 per site is closer to 4-5 minutes):
   ```bash
   .venv/bin/python scraper.py "<keyword>" [--location "..."] [--results N]
   ```
4. Tell the user the run has started and roughly how long it takes, then wait for completion.

## Reporting

The script's final line has the summary:

```
indeed: N, linkedin: N, dice: N -> roles/<slug>/jobs_<timestamp>.csv (M rows)
```

**Relay any `note:` lines the script prints.** Filter support is uneven across the three boards and
the script says so at the end of a run:

- `--job-type` — honored by Indeed and Dice, **ignored by LinkedIn**, which returns unfiltered
  results. Verified: asking for contract roles returned 14 full-time LinkedIn postings out of 15.
- `--remote` — honored by Indeed and LinkedIn. Dice's remote field is unreliable (postings titled
  "... (Remote)" report `FALSE`), so its rows may include on-site roles.

Don't present a filtered scrape as uniformly filtered. If the user asked for contract work, tell
them the LinkedIn third of the results are not contract-only.

When the run finishes, report the per-site counts and the CSV path. If a site failed or returned fewer results (LinkedIn rate-limits aggressively, and starts refusing well before 100 results per IP), relay its stderr message and note that the rest of the run still succeeded — per-site failures are tolerated by design. Do not analyze the CSV contents unless the user asks.
