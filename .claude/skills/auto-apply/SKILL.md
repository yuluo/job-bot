---
name: auto-apply
description: Apply to scraped job postings using the candidate's tailored resume for that keyword, driving the user's logged-in Chrome. Fills each application from the candidate knowledge base, asks the user about anything new and remembers it, and gates each channel behind a dry-run approval before auto-submitting the rest. Use when the user wants to apply to jobs collected by scrape-jobs.
argument-hint: to <job keyword> jobs [limit N] [channels ats,dice,linkedin,indeed]
---

Submit applications for the candidate against a scraped job CSV, using the resume built for that
keyword. This repo holds one candidate; everything for a keyword lives in `roles/<slug>/`.

This skill **submits real applications on the user's behalf**. Every rule below about approval
gates, pacing, and prohibited fields is a hard constraint, not a default.

## Step 1 — Parse arguments

Arguments look like `to <job keyword> jobs [limit N] [channels ...]`.

- **Keyword slug** (the `<slug>`, and also the `--role` passed to every `knowledge.py` call): the
  text after `to`, with a trailing `jobs`/`positions`/`roles` removed, then slugified — lowercase,
  runs of non-alphanumerics → a single hyphen (`devops engineer` → `devops-engineer`). Same rule as
  `build-resume`, so all three skills agree on slugs.
- **limit N** → `--limit-per-channel N` (default 10). **channels a,b** → `--channels a,b`.

## Step 2 — Preflight

Do all of this before opening a browser.

1. **Knowledge base** — `.venv/bin/python knowledge.py init` creates `candidate/profile.yaml` and
   `candidate/answers.yaml` if absent and reports missing profile fields. If any are missing, ask
   the user for **all of them in one message**, then write them into the profile YAML. Do not
   proceed with an incomplete profile.
2. **Resume** — `roles/<slug>/resume.html` must exist. If not, stop and tell the user to run
   `/build-resume for <keyword> positions` first.
3. **PDF** — `.venv/bin/python render_pdf.py roles/<slug>/resume.html`. Confirm it prints a
   non-zero byte count.
4. **Upload path** — `file_upload` only accepts files the user has shared with this session. Test it
   once against a real file input before relying on it. If the `roles/` path is rejected, copy the
   PDF into the session scratchpad and upload from there for the rest of the run.

## Step 3 — Build the batch

```bash
.venv/bin/python apply.py <slug> [--channels ...] [--limit-per-channel N]
```

This picks the newest `roles/<slug>/jobs_*.csv`, classifies each posting into a channel, drops
anything already in the global `applied.csv` ledger, ranks by overlap with the profile's skills, and
writes `roles/<slug>/batch_<timestamp>.json`.

The ledger is global on purpose: a posting already applied to under a *different* keyword is
dropped here too, so the same role found by two searches never gets two applications.

Show the user the shortlist as a table (company, title, channel, location, salary) plus the
per-channel counts and what was dropped. **Do not open a browser until they have seen it.**

## Step 4 — Apply, one channel at a time

Work channels in this order — most to least reliable: **`ats` → `dice` → `linkedin` → `indeed`**.
Read `references/<channel>.md` before starting that channel.

### The dry run (first job in each channel)

1. Open the job's `apply_url` in a tab (`navigate`). Prefer `fallback_url` when present and the
   channel playbook says to.
2. Resolve every form field through the lookup order in Step 5.
3. Upload the resume PDF to the file input.
4. Screenshot the completed form **without submitting**.
5. Present to the user: the screenshot, and a field-by-field table of `field → value → source`,
   where source is `profile`, `answers bank (key, confidence)`, or `just asked`. The provenance is
   what makes the approval meaningful — a value with no source is a bug, not a guess to paper over.
6. **Wait for explicit approval in chat.** Then submit that job.

### After approval

Auto-submit the rest of that channel's batch. The approval covers **that channel, this run only** —
never another channel, never a later run. Re-run the dry run for each new channel.

### Pacing

- 20–60 seconds between submissions.
- Default cap of 10 per channel per run (`--limit-per-channel`).
- **Hard stop on 3 consecutive failures in a channel.** That pattern means the site is blocking;
  continuing only deepens the footprint. Report it and move to the next channel.

## Step 5 — Answering form fields

For each field, in order:

1. **Profile** — identity, authorization, preferences, experience, EEO. Use directly.
2. **Answers bank** — `.venv/bin/python knowledge.py lookup --role <slug> --question "<verbatim question>" [--company "<company>"]`

   **`--role` is required on every call.** It is what keeps a `per_role` answer recorded under one
   keyword from being served under another — omitting it is not a shortcut, it is a wrong answer on
   a real application.
   - `found: true`, `requires_personalization: false` → use `answer`, then
     `knowledge.py bump --role <slug> --key <key>`.
   - `found: true`, `requires_personalization: true` (scope `per_company`) → the stored answer is a
     **template**. Rewrite it for this employer and show the user the rewritten text before
     submitting. **Never** send a `per_company` answer verbatim to a different company — a stale
     "why I want to work at Acme" reaching Globex is the worst failure this skill can produce, and
     it fails silently.
   - `blocked: true` → see below.
3. **Ask** — pause the batch. Show the user the verbatim question, the company, the job URL, the
   field type, and any available options. Batch every unknown on the same form into **one** message
   rather than asking field by field. Then persist:
   ```bash
   .venv/bin/python knowledge.py record --role <slug> --question "..." --answer "..." \
     --scope global|per_role|per_company --type freetext|choice|boolean|number|date \
     --company "..." --job-url "..."
   ```
   Choose `scope` deliberately: `global` for facts that never change (years of Python, notice
   period), `per_role` for answers tied to the keyword, `per_company` for anything naming or
   flattering the employer.

**A new question pauses the run — it never skips the job and never gets guessed at.** This applies
after channel approval too.

## Hard rules

**Never enter, never store, never ask for:** SSN, government ID, driver's license, passport, date of
birth, bank or routing numbers, credit card details, or passwords. `knowledge.py` refuses these on
both `lookup` and `record`. If a form demands one, log the job `needs_human` and hand the user the
URL to finish themselves.

**Never**: create an account, log in, solve a captcha, or accept terms on the user's behalf.

**Suspend auto-submit and log `needs_human`** — even after channel approval — on a captcha or
bot-check, a login wall, a coding assessment or timed test, a redirect off the expected apply
domain, or a prohibited-identifier request. These are dead ends, unlike an unknown question.

**Never invent** experience, credentials, or dates. Answers come from the profile, the bank, or the
user — never from the model.

## Step 6 — Record every attempt

Append to the global `applied.csv` at the repo root **immediately after each job**, before moving
on, so an interrupted run never re-applies on resume. Columns: `applied_at, keyword, site, channel,
company, title, job_url, apply_url, status, notes` with
`status ∈ {submitted, skipped, failed, needs_human}`.

## Step 7 — Report

- Per-channel counts: submitted / skipped / failed / needs_human.
- The ledger path and the batch JSON path.
- An explicit list of `needs_human` jobs with URLs and the reason each one bailed — these are the
  user's to finish, so do not bury them.
- Any new answers-bank entries created this run, so the user can refine the wording by hand.
