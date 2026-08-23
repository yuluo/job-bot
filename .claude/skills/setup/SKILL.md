---
name: setup
description: One-time onboarding for a forked job-bot repo. Checks candidate/ for the user's resume and prompts for one if missing, transcribes it into an editable HTML template that every later tailored resume is built from, then reviews that transcription with the user before finishing. Also creates the venv and the candidate knowledge base. Use when the user has just forked the repo, dropped their resume in, or asks how to get started.
argument-hint: (no arguments)
---

One-time onboarding. Run this before anything else in a fresh fork.

The output that matters is **`candidate/resume_template.html`** — the candidate's real resume in
clean, editable HTML. Every tailored resume `/build-resume` produces is derived from it, so getting
it right is the whole point of this skill. That is why Step 8 is a checkpoint: you do not finish
until the candidate has confirmed the transcription is faithful.

Work through the steps in order and report what each one did.

## Step 1 — Environment

If `.venv/` does not exist:

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

If it already exists, skip it without comment.

## Step 2 — Knowledge base

```bash
.venv/bin/python knowledge.py init
```

Idempotent — it creates `candidate/profile.yaml` and `candidate/answers.yaml` only if they are
absent, and reports which profile fields are still missing. Don't ask the user for those values
here; Step 5 fills what the resume knows and `/auto-apply` asks for the rest.

## Step 3 — Find the resume

Look in `candidate/` for the first `pdf` / `docx` / `md` / `txt` file, ignoring `profile.yaml`,
`answers.yaml`, `README.md`, and `resume_template.html`.

- **Nothing found** — stop here. Tell the user to drop their resume into `candidate/`, name the
  accepted formats, and say that re-running `/setup` will pick it up. This is the normal first-run
  path, so phrase it as the next step, not as a failure.
- **More than one** — list them and ask which to use.

## Step 4 — Don't clobber existing work

If `candidate/resume_template.html` already exists, **stop and ask before regenerating it.**

The candidate is meant to hand-edit this file, and those edits flow into every resume built
afterward. Silently overwriting them is the worst thing this skill can do. If the user declines,
skip to Step 5 and leave the file untouched.

## Step 5 — Transcribe the resume into HTML

Read the resume (`Read` handles PDF and text directly), then write
`candidate/resume_template.html`.

**Take the styling from `template/resume_template.html`:** an empty skeleton holding the CSS and
class names and nothing else. Copy its entire `<style>` block verbatim — `@page`, `@media print`,
`break-inside: avoid`, the serif type — and reuse its class vocabulary:

`.page`, `.name`, `.contact-line`, `.section-title`, `.skill-row` / `.skill-label`, `.entry`,
`.entry-row`, `.entry-org`, `.entry-loc`, `.entry-role`, `.entry-dates`, `ul.bullets`

**Take all the content from the candidate's resume:**

- **Header** — real name, location, and contact details.
- **Skills** — every skill they list, grouped as they group them.
- **Experience** — **every job**, with its real company, location, title, date range, and **all** of
  its bullets.
- **Education** — the full education section.

Follow the template's section order (Skills → Experience → Education Background), but the number of
sections and entries follows the candidate's actual resume, not the template's. If they have a
section the template lacks — certifications, publications, projects — keep it, styled with the same
`.section-title` and `.entry` classes.

**Remove every `.placeholder` span and `[ ... ]` marker.** The skeleton is built from them; the
candidate's template must contain none. Every value is real now, so nothing should render with the
dashed placeholder styling.

**Never invent.** This is transcription, not authoring. If the resume doesn't state a location for a
job, leave it out rather than guessing. If it has no skills section, don't synthesize one. An empty
slot is correct; a plausible fabrication is not — and it would propagate into every application the
candidate sends.

## Step 6 — Pre-fill the profile

From the same read, write into `candidate/profile.yaml` what the resume states outright:

```bash
.venv/bin/python knowledge.py set --field identity.full_name --value "..."
.venv/bin/python knowledge.py set --field identity.email     --value "..."
.venv/bin/python knowledge.py set --field identity.phone     --value "..."
.venv/bin/python knowledge.py set --field identity.city      --value "..."
.venv/bin/python knowledge.py set --field identity.state     --value "..."
```

Also `identity.linkedin_url` and `identity.portfolio_url` when the resume lists them.

`set` refuses to overwrite a value that is already filled, so re-running `/setup` never clobbers a
correction the user made by hand. It also rejects an unknown field path, so a typo fails loudly.

**Only fields the resume actually states.** Work authorization, sponsorship, desired salary, start
date, and EEO are not on a resume — leave them empty for `/auto-apply` to ask about. Never write a
guessed value just to shorten the `missing` list.

`experience.total_years` can be inferred from the earliest employment date, but that is an
inference. **Report it as a suggestion** and let the user confirm it rather than writing it.

Finish by noting which fields are still missing.

## Step 7 — Render and open

```bash
.venv/bin/python render_pdf.py candidate/resume_template.html
open candidate/resume_template.html
```

`open` puts it in the user's default browser. Also send the rendered PDF with `SendUserFile` so it
is visible without leaving the terminal.

## Step 8 — Review it with the user (checkpoint)

**Stop here and get confirmation before finishing.** This file becomes the basis of every resume and
every application that follows, so an error here propagates to every employer the candidate contacts.
It is also the one moment they have the original in mind.

You transcribed this from a PDF. Content gets dropped or reordered silently — multi-column layouts,
tables, text inside images, and header/footer text are the usual culprits. A rendered page looks
fine whether or not a bullet went missing, so **do not ask "does this look right?" over the PDF
alone.** Give them an inventory they can check against their original:

```
Transcribed 2 roles, 11 bullets, 3 skill groups, 1 degree.

  Ant Technology LLC. — Business Intelligence Engineer
  Rockville, MD · 01/2026–present · 5 bullets

  Merkle (Dentsu Group) — Lead Data Analyst
  Remote · 07/2014–11/2024 · 6 bullets

  Skills: BI & Visualization (5), Data & SQL (4), Tools & Languages (6)
  Education: East China Normal University, Jan 2011 – May 2014

Profile pre-filled from the resume:
  name Claire Shi · claireshi0910@outlook.com · (626) 782-3631 · Rockville, MD
```

Counts are what make an omission visible — nobody spots a missing bullet by looking at a page, but
they will notice "5 bullets" when they wrote six. Call out anything you were unsure of: a date you
had to interpret, a section you couldn't place, text you skipped as decoration.

Then ask, with `AskUserQuestion`:

- **Looks right** — continue to Step 9.
- **Something's missing or wrong** — have them say what. Fix it in the HTML, re-render, show the
  updated inventory, and ask again. Repeat until they confirm; there is no limit on rounds here.
- **Contact details are wrong** — correct both the HTML and `profile.yaml`. `set` refuses to
  overwrite, so pass `--force` for those fields.

If the resume was a text or Markdown file rather than a PDF, say so — extraction was reliable, and
the review is a formality rather than a real risk. Don't manufacture concern you don't have.

## Step 9 — Report

Once they've confirmed:

- both output paths;
- which profile fields were filled, and which `/auto-apply` will still ask for;
- the `total_years` suggestion, if you have one;
- that `candidate/resume_template.html` is theirs to edit at any time, and edits flow into every
  resume built afterward;
- that the next step is `/scrape-jobs <keyword>` for whatever role they're targeting.
