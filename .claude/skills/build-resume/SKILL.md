---
name: build-resume
description: Build a tailored, print-friendly HTML resume for a client by combining their personal info + education with the template's job experience, customized for a target job type using scraped job data in output/. Use when the user wants to generate a resume for a client and target role.
argument-hint: based off <client>.resume for <job keyword> positions
---

Build a tailored, PDF-print-friendly HTML resume for a client and a target job type.

The client's resume supplies **identity and education only**. The **layout, job experience, and
skills come from `template/resume_template.html`**, then get tailored toward the target role using
the scraped job data in `output/`.

## Step 1 — Parse arguments

The arguments look like: `based off <client>.resume for <job keyword> positions`.

- **Client**: the text after `based off` and before `for`. Strip a trailing `.resume`, then resolve
  to a file in `clients/` by basename, trying extensions `pdf`, `txt`, `md`, `docx` (e.g. `tom` →
  `clients/tom.pdf`). If `clients/` is missing or no match is found, list `clients/` and ask the
  user which file to use.
- **Target keyword**: the text after `for`, with a trailing `positions` / `jobs` / `roles` removed
  (e.g. `power bi`). Normalize to a **slug**: lowercase, runs of non-alphanumeric characters → a
  single hyphen (`power bi` → `power-bi`, `data engineer` → `data-engineer`).

## Step 2 — Locate the scraped job data

Find `output/jobs_<slug>_*.csv`. If several match, pick the **newest** by the `YYYYMMDD-HHMMSS`
timestamp in the filename. If none match, list the available slugs in `output/` and ask the user to
either pick one or scrape first with `/scrape-jobs <keyword>`.

## Step 3 — Read the inputs

- **Client resume** (use Read for pdf/text): extract only the client's **name**, **location /
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

- **Header**: replace the `[ NAME ]`, `[ LOCATION ]`, `[ CONTACT ]` placeholders with the client's
  real name, location, and contact. Remove the dashed `placeholder` styling for these real values.
- **Skills**: start from the template's skills, then **reorder and emphasize** to foreground the
  keywords mined in Step 4. Only surface skills genuinely present in the template — this is
  emphasis and ordering, not fabrication.
- **Experience**: keep the template's job entries and dates, but **reword and reorder the bullets**
  to mirror the target role's language and priorities from Step 4. Company names may stay as the
  anonymized `[ Company A ]` / `[ Company B ]` placeholders.
- **Education**: replace the template's `[ University ]` block with the client's real education from
  Step 3.
- Preserve all print CSS — `@page`, `@media print`, `break-inside: avoid`, and the serif styling.

**Tailoring guardrail**: tailoring means re-emphasis, reordering, and rephrasing toward the target
role's vocabulary. Never invent experience, skills, or credentials the client or template don't
support.

## Step 6 — Write the output and report

Create the `resume/` folder if needed and write the file to
`resume/<client>_<slug>_resume.html` (e.g. `resume/tom_power-bi_resume.html`).

Then render the print-ready PDF alongside it:

```bash
.venv/bin/python render_pdf.py resume/<client>_<slug>_resume.html
```

This drives headless Chrome and preserves the template's `@page` / `@media print` CSS. Report both
output paths, and mention that `/auto-apply for <client> to <keyword> jobs` can now submit
applications using this resume.
