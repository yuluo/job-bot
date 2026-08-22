# Your files go here

**Drop your resume into this folder** — PDF, DOCX, Markdown, or plain text. Any filename works.

That's the only manual step. Then run:

```
/scrape-jobs data engineer          # collect postings for a role
/build-resume for data engineer positions
/auto-apply to data engineer jobs
```

Repeat for each role you're targeting. Each keyword gets its own folder under `roles/`, with its own
tailored resume.

## What else lives here

| File | What it is |
|---|---|
| your resume | the source of truth for your name, contact details, and education |
| `profile.yaml` | generated — the answers nearly every application asks for |
| `answers.yaml` | generated — questions you've been asked before, so you're not asked twice |

Both YAML files are created for you by `/auto-apply` on its first run. You can edit them by hand at
any time; nothing overwrites a value you changed.

## A note on what gets committed

Everything in this folder **is committed to git**, including `profile.yaml`. If you forked this repo
from a public one, your fork is public too — GitHub forks of public repos cannot be made private.

`profile.yaml` has an `eeo` block (gender, race, veteran and disability status). It defaults to
`decline_to_answer`. If you fill it in and would rather it not be public, add
`candidate/profile.yaml` to `.gitignore` before committing.
