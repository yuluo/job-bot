---
name: build-resume
description: Build a tailored, print-friendly HTML resume for the candidate by combining their personal info + education with the template's job experience, customized for a target job type using the scraped job data for that keyword. Use when the user wants to generate a resume for a target role.
argument-hint: for <job keyword> positions
---

Build a tailored, PDF-print-friendly HTML resume for the candidate and a target job type.

This repo holds **one candidate**. Their resume in `candidate/` supplies **identity and education
only**. The **layout, job experience, and skills come from `template/resume_template.html`**, then
get tailored toward the target role using that role's scraped job data.

One resume per keyword: everything for a keyword lives in `roles/<slug>/`.

## Step 1 — Parse arguments

The arguments look like: `for <job keyword> positions`.

- **Target keyword**: the text after `for`, with a trailing `positions` / `jobs` / `roles` removed
  (e.g. `power bi`). Normalize to a **slug**: lowercase, runs of non-alphanumeric characters → a
  single hyphen (`power bi` → `power-bi`, `data engineer` → `data-engineer`).
- **Source resume**: the first `pdf` / `docx` / `md` / `txt` file in `candidate/`, ignoring
  `profile.yaml`, `answers.yaml`, and `README.md`. If `candidate/` holds no such file, stop and tell
  the user to drop their resume into `candidate/`. If it holds more than one, list them and ask
  which to use.

## Step 2 — Locate the scraped job data

Find `roles/<slug>/jobs_*.csv`. If several match, pick the **newest** by the `YYYYMMDD-HHMMSS`
timestamp in the filename. If the folder or file is missing, list the available roles under `roles/`
and ask the user to either pick one or scrape first with `/scrape-jobs <keyword>`.

## Step 3 — Read the inputs

- **Candidate resume** (use Read for pdf/text): extract only the candidate's **name**, **location /
  contact info** (email, phone, city), and the **full education section**. Ignore their job history.
- **`template/resume_template.html`**: this is the source of the layout/CSS and the experience +
  skills content you will reuse.

## Step 4 — Mine the job data for tailoring

The CSV columns are `site,title,company,location,date_posted,salary,job_url,description`. These files
are large (tens of thousands of lines), so sample a healthy slice rather than reading the whole file.
Scan the `title` and `description` columns to find the **most frequently demanded tools, skills, and
keywords** for the role. Produce a short ranked keyword list to guide the tailoring.

## Step 5 — Generate the resume HTML

Clone the template's structure and CSS, then fill it in:

- **Header**: replace the `[ NAME ]`, `[ LOCATION ]`, `[ CONTACT ]` placeholders with the candidate's
  real name, location, and contact. Remove the dashed `placeholder` styling for these real values.
- **Skills**: start from the template's skills, then **reorder and emphasize** to foreground the
  keywords mined in Step 4. Only surface skills genuinely present in the template — this is
  emphasis and ordering, not fabrication.
- **Experience**: keep the template's job entries and dates, but **reword and reorder the bullets**
  to mirror the target role's language and priorities from Step 4. Company names may stay as the
  anonymized `[ Company A ]` / `[ Company B ]` placeholders.
- **Education**: replace the template's `[ University ]` block with the candidate's real education from
  Step 3.
- Preserve all print CSS — `@page`, `@media print`, `break-inside: avoid`, and the serif styling.

**Tailoring guardrail**: tailoring means re-emphasis, reordering, and rephrasing toward the target
role's vocabulary. Never invent experience, skills, or credentials the candidate or template don't
support.

## Step 6 — Write the output and report

Write the file to `roles/<slug>/resume.html` (e.g. `roles/power-bi/resume.html`), creating the
folder if needed.

Then render the print-ready PDF alongside it:

```bash
.venv/bin/python render_pdf.py roles/<slug>/resume.html
```

This drives headless Chrome and preserves the template's `@page` / `@media print` CSS. Report both
output paths, and mention that `/auto-apply to <keyword> jobs` can now submit applications using
this resume.
