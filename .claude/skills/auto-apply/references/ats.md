# Channel: `ats` — direct applicant tracking systems

Highest-reliability channel. These are the employer's own hosted forms, so there is no board ToS
issue and no bot-detection arms race. `apply.py` routes a job here when `job_url_direct`'s host
matches a known ATS.

Always drive with `find` → `read_page` → `form_input` / `file_upload` → `computer` click. Never
click blind coordinates; these forms reflow.

## Greenhouse (`boards.greenhouse.io`, `job-boards.greenhouse.io`)

- Single long form, no pagination. Everything is visible after one `read_page`.
- Resume input is `input[type=file]` labelled "Resume/CV". It usually offers "Attach, Dropbox, or
  Google Drive" — use the file input directly via `file_upload`, never the picker buttons.
- Custom questions appear as plain `<input>`, `<textarea>`, or `<select>` under "Additional
  Information". These are the main source of new answers-bank entries.
- EEO fields are at the bottom and always optional — use the profile's `eeo` values.
- Submit: a single "Submit Application" button. Success = a "Thank you" / confirmation panel
  replacing the form.

## Lever (`jobs.lever.co`)

- Single page. Resume upload is `input[name=resume]`; Lever **auto-parses** it and backfills name,
  email, and phone. Upload the PDF *first*, wait for parsing, then read the page again and correct
  any field it filled wrong — do not assume the parse was right.
- Additional questions live in `.application-question` blocks.
- Submit: "Submit application". Success = redirect to a `/thanks` URL.

## Ashby (`jobs.ashbyhq.com`)

- React form, fields render lazily. `read_page` after any expand/scroll, not once at the top.
- Resume input accepts drag-and-drop but also exposes a real `input[type=file]`.
- Submit: "Submit Application". Success = an inline confirmation card.

## Workable (`apply.workable.com`)

- Straightforward single form. Resume input labelled "Upload a file".
- Some employers enable a cover-letter textarea — fill from `defaults.cover_letter_template`,
  personalized per company.
- Submit: "Submit application".

## Breezy (`*.breezy.hr`)

- Single form, minimal custom questions. Resume input labelled "Resume".
- Submit: "Apply for this job".

## Workday (`*.myworkdayjobs.com`) — default to `needs_human`

Workday nearly always requires **creating a per-employer account** before the form is reachable,
which this skill must never do. Log Workday jobs as `needs_human` with the URL and move on.

The exception: if the user is already signed in to that specific employer's Workday tenant and the
apply flow opens directly into the form, it can be completed. Workday is a multi-step wizard —
`read_page` between every step, and expect an "Autofill with Resume" option that behaves like
Lever's parse and needs the same verification.

## Other hosts

`smartrecruiters.com`, `jobvite.com`, `icims.com`, `recruitee.com`, `teamtailor.com`,
`bamboohr.com` all follow the same single-form shape. Read the page, map fields by their labels, and
apply the Step 5 lookup order. iCIMS often gates behind an account — treat it like Workday if it
does.

## Bail conditions

Any captcha, login wall, or redirect off the ATS domain → `needs_human`, do not retry.
