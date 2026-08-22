# Your files go here

**Step 1 — drop your resume into this folder.** PDF, DOCX, Markdown, or plain text. Any filename
works.

**Step 2 — run `/setup`.** It reads your resume and writes `resume_template.html` — your whole
career in clean, editable HTML — then fills in what it can of `profile.yaml`.

**Step 3 — check `resume_template.html`.** It opens in your browser automatically. Read it against
your original: PDFs with columns, tables, or images are where a line most often gets dropped or
reordered. Fix anything wrong directly in the HTML.

That last step matters more than it sounds. Every tailored resume is built from this file, so a
correction here is a correction everywhere, and a mistake here follows you into every application.

Then, for each role you're targeting:

```
/scrape-jobs data engineer
/build-resume for data engineer positions
/auto-apply to data engineer jobs
```

## What lives here

| File | What it is |
|---|---|
| your resume | the original you dropped in — read once by `/setup`, then left alone |
| `resume_template.html` | **the master.** Your full resume, yours to edit. Every tailored resume derives from it |
| `resume_template.pdf` | a rendered preview of the above, so you can see what it looks like printed |
| `profile.yaml` | the answers nearly every application asks for |
| `answers.yaml` | questions you've been asked before, so you're not asked twice |

`/setup` never overwrites edits you've made — it asks first if `resume_template.html` already
exists, and `profile.yaml` values you've corrected by hand are left alone.

`/setup` only fills profile fields your resume actually states — name, contact, location. Work
authorization, salary expectations, and start date aren't on a resume, so `/auto-apply` asks you for
those the first time it needs them.

## A note on what gets committed

Everything in this folder **is committed to git**, including `profile.yaml`. If you forked this repo
from a public one, your fork is public too — GitHub forks of public repos cannot be made private.

`profile.yaml` has an `eeo` block (gender, race, veteran and disability status). It defaults to
`decline_to_answer`. If you fill it in and would rather it not be public, add
`candidate/profile.yaml` to `.gitignore` before committing.
