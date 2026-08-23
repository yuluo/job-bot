---
name: build-resume
description: Build a tailored, print-friendly HTML resume for the candidate by re-emphasizing their own experience toward a target job type, using the scraped job data for that keyword. Requires /setup to have generated candidate/resume_template.html first. Use when the user wants to generate a resume for a target role.
argument-hint: for <job keyword> positions
---

Build a tailored, PDF-print-friendly HTML resume for the candidate and a target job type.

This repo holds **one candidate**. All content — identity, skills, experience, education — comes
from **`candidate/resume_template.html`**, the editable master that `/setup` transcribed from their
real resume and that they may have hand-edited since. This skill re-emphasizes that content toward
the target role using that role's scraped job data.

`template/resume_template.html` is an empty **layout skeleton** — CSS and class names only, no
content. It is not an input to this skill; the candidate's template already carries that CSS.

One resume per keyword: everything for a keyword lives in `roles/<slug>/`.

## Step 1 — Parse arguments

The arguments look like: `for <job keyword> positions`.

- **Target keyword**: the text after `for`, with a trailing `positions` / `jobs` / `roles` removed
  (e.g. `power bi`). Normalize to a **slug**: lowercase, runs of non-alphanumeric characters → a
  single hyphen (`power bi` → `power-bi`, `data engineer` → `data-engineer`).
**Precondition**: `candidate/resume_template.html` must exist. If it doesn't, stop and tell the
user to run `/setup` first. Do not fall back to `template/resume_template.html` — that would quietly
put a stranger's experience on the candidate's resume.

## Step 2 — Locate the scraped job data

Find `roles/<slug>/jobs_*.csv`. If several match, pick the **newest** by the `YYYYMMDD-HHMMSS`
timestamp in the filename. If the folder or file is missing, list the available roles under `roles/`
and ask the user to either pick one or scrape first with `/scrape-jobs <keyword>`.

## Step 3 — Read the inputs

**`candidate/resume_template.html`** is the single source: layout, CSS, identity, skills, every job
with its bullets, and education. Read it in full — there is no second input to reconcile, and the
raw resume PDF is not read at this stage.

## Step 4 — Mine the job data for tailoring

The CSV columns are `site,title,company,location,date_posted,salary,job_url,description`. These files
are large (tens of thousands of lines), so sample a healthy slice rather than reading the whole file.
Scan the `title` and `description` columns to find the **most frequently demanded tools, skills, and
keywords** for the role. Produce a short ranked keyword list to guide the tailoring.

## Step 5 — Generate the resume HTML

Start from the candidate's template and adjust emphasis — the structure, CSS, and facts carry over
unchanged:

- **Header**: keep the candidate's name, location, and contact exactly as they are.
- **Skills**: **reorder and emphasize** to foreground the keywords mined in Step 4. Only skills the
  candidate already lists — this is ordering and emphasis, not addition.
- **Experience**: keep **every job**, with its company, title, location, and dates exactly as
  written. Reword and reorder the **bullets** to mirror the target role's language and priorities
  from Step 4. A bullet may be rephrased or moved; it may not be invented, and a job may not be
  dropped.
- **Education**: carry over unchanged.
- Preserve all print CSS — `@page`, `@media print`, `break-inside: avoid`, and the serif styling.

**Tailoring guardrail**: this is the candidate's real career. Tailoring means re-emphasis,
reordering, and rephrasing toward the target role's vocabulary. Never add a skill, employer, title,
date, or credential their template doesn't contain, and never soften a date range to fit a job
description. If the role wants something they don't have, the honest answer is that the resume
doesn't show it.

**Never** emit `[ NAME ]`, `[ Employer ]`, `[ Job title ]`, or any other `[ ... ]` placeholder, and
never carry a `.placeholder` span into the output. A placeholder in a finished resume means the
skeleton was read instead of the candidate's template.

## Step 6 — Write and render

Write the file to `roles/<slug>/resume.html` (e.g. `roles/power-bi/resume.html`), creating the
folder if needed. Then render the print-ready PDF alongside it:

```bash
.venv/bin/python render_pdf.py roles/<slug>/resume.html
open roles/<slug>/resume.html
```

This drives headless Chrome and preserves the template's `@page` / `@media print` CSS. Send the PDF
with `SendUserFile` so it is visible without leaving the terminal.

## Step 7 — Review it with the user (checkpoint)

**Stop here and get confirmation before saying this resume is ready.** It is the last human look
before it goes to employers, and the failure mode is specific: tailoring that quietly drifts into
overclaiming. The candidate is the only one who can tell you a rephrased bullet no longer describes
what they actually did.

Show them the **changes**, not the resume — they already know what their resume says, and a rendered
page makes a reworded bullet hard to spot:

```
Tailored for devops engineer, from 60 postings.
Top demanded: ci/cd (38), aws (26), terraform (16), kubernetes (15), observability (13).

Skills — reordered, nothing added or removed:
  Infrastructure → "Cloud & IaC", moved first (AWS and Terraform lead the mined list)
  Languages moved last

Bullets — reworded, 5 of 5 kept:
  Northwind #1  "Ran multi-tenant Kubernetes clusters..."
              → "Operated multi-tenant Kubernetes clusters... cutting p99 deploy time"
              (moved to #2; "deploy" is the role's vocabulary)
  Northwind #2  Terraform bullet promoted to #1, wording unchanged

Unchanged: every employer, title, location, date, and the education section.
Nothing added that is not in your template.
```

That last line is the one that matters. State it explicitly every time, and if you *can't* state it
— if the target role wanted something and you stretched a bullet to reach for it — say that instead
and let them decide. Never soften a date range or imply seniority the template doesn't support.

Then ask with `AskUserQuestion`:

- **Looks good** — continue to Step 8.
- **A bullet overclaims** — they say which; revert it to the template's wording or reword as they
  direct, re-render, show the updated summary, ask again.
- **Wrong emphasis** — re-tailor with their steer (e.g. "lead with the Go work, not the Kubernetes
  work") and show the summary again.

Loop until they confirm. If the tailoring was light — a couple of reorderings and nothing reworded
— say so plainly rather than inflating a short list into a ceremony.

## Step 8 — Report

Once confirmed, report both output paths and mention that `/auto-apply to <keyword> jobs` can now
submit applications using this resume.
