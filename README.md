# job-bot

A three-step job-hunting pipeline for **one candidate**: scrape postings for a role, build a resume tailored to what those postings actually ask for, then apply to them.

## Getting started

1. Fork this repo.
2. Drop your resume into `candidate/` — PDF, DOCX, Markdown, or text.
3. Run the pipeline for each role you're targeting:

```
/scrape-jobs data engineer
/build-resume for data engineer positions
/auto-apply to data engineer jobs
```

| Step | Skill | Script | Output |
|---|---|---|---|
| 1. Collect | `/scrape-jobs <keyword>` | `scraper.py` | `roles/<slug>/jobs_<timestamp>.csv` |
| 2. Tailor | `/build-resume for <keyword> positions` | `render_pdf.py` | `roles/<slug>/resume.{html,pdf}` |
| 3. Apply | `/auto-apply to <keyword> jobs` | `apply.py`, `knowledge.py` | `applied.csv` |

**One resume per keyword.** Everything for a role lives together in `roles/<slug>/`; the candidate's identity and accumulated application answers live once in `candidate/`.

## Layout

```
candidate/          your resume, profile.yaml, answers.yaml
roles/<slug>/       jobs_*.csv, resume.html, resume.pdf, batch_*.json
applied.csv         global ledger of every application attempt
template/           resume layout + experience content
```

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

Defaults to 100 results per site. Output is `roles/<slug>/jobs_<timestamp>.csv` with columns:

`site, title, company, location, date_posted, salary, employment_type, remote, sponsorship, easy_apply, job_url, job_url_direct, description`

The apply-oriented columns (`job_url_direct`, `easy_apply`, `sponsorship`, `employment_type`) are what let step 3 route a posting to the right application channel.

## How it works

- **Indeed + LinkedIn** are scraped via the [python-jobspy](https://github.com/speedyapply/JobSpy) library. LinkedIn descriptions are fetched per posting (`linkedin_fetch_description=True`), which is slower but needed for requirements analysis.
- **Dice** (`dice.py`) uses Dice's unofficial JSON search API, then fetches each job's detail page to extract the full description from the embedded React Server Components payload.

A failure on one site does not abort the run — the script collects what succeeds and prints per-site counts.

## Applying (`apply.py`, `knowledge.py`)

`apply.py` turns a scraped CSV into a shortlist, classifying each posting into a channel:

- **`ats`** — `job_url_direct` points at a known applicant tracking system (Greenhouse, Lever, Ashby, Workable, Breezy, …). Most reliable, no board ToS issue.
- **`dice`** — Dice Easy Apply, confirmed by the API's `easyApply` flag.
- **`linkedin`** / **`indeed`** — best-effort; both detect automation and often bail to `needs_human`.

It dedupes against the global `applied.csv` ledger by URL and by normalized company+title. The ledger is global on purpose: the same posting found under two different keywords never produces two applications.

`knowledge.py` maintains the candidate knowledge base under `candidate/`: a structured `profile.yaml` and an append-only `answers.yaml` Q&A bank. When an application asks something the profile can't answer, the skill asks once and records it, so later applications answer it automatically. Answers are scoped — `global` ones apply everywhere, `per_role` ones are visible only under the keyword they were recorded for, and `per_company` ones must be rewritten per employer. It refuses to store or enter SSNs, government IDs, bank details, or passwords.

```bash
.venv/bin/python knowledge.py init
.venv/bin/python apply.py <slug> --limit-per-channel 10
```

Browser automation runs in the user's own logged-in Chrome via the Claude in Chrome extension. It does **not** solve captchas, spoof fingerprints, or rotate proxies — a real profile avoids the signals a headless scraper trips, but the dominant detection signal is behavioral, which is why the skill paces submissions and hard-stops after three consecutive failures in a channel.

## Caveats

- LinkedIn rate-limits aggressively (~10 pages per IP). 100 results is at the edge; repeated runs from one IP may return fewer results or get temporarily blocked. JobSpy supports a `proxies` parameter if needed.
- Scraping LinkedIn is against its ToS; keep usage low-volume and personal. The same applies to applying — LinkedIn and Indeed both restrict accounts that automate applications, so `/auto-apply` runs those channels last, slowly, and expects them to fail.
- Only scrape artifacts (`roles/*/jobs_*.csv`, `roles/*/batch_*.json`) are gitignored — they're large and regenerable. `candidate/`, the tailored resumes, and `applied.csv` are committed and travel with your fork. Note that a fork of a public repo is public; see `candidate/README.md` if that matters for your `eeo` fields.
- Dice's API endpoint and key are unofficial (taken from their own frontend) and may change without notice; all Dice logic is isolated in `dice.py`.
