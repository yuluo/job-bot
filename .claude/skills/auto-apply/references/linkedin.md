# Channel: `linkedin` — LinkedIn Easy Apply

**Expect frequent failure, and treat that as correct behavior.** LinkedIn actively detects
application automation, and it is against their User Agreement. Accounts get restricted. This
channel runs second-to-last, at human pace, and bails early.

Never attempt to work around a block. If LinkedIn interrupts the flow, stop the channel.

## Easy Apply is not known in advance

jobspy exposes `easy_apply` on its model but drops it from the output DataFrame (`desired_order` in
`jobspy/util.py`), so the CSV's `easy_apply` is always empty for LinkedIn rows. `apply.py` therefore
routes **all** LinkedIn rows to this channel, and Easy Apply must be detected in the browser:

- "Easy Apply" button (LinkedIn-hosted modal) → proceed.
- "Apply" button (external redirect) → log `needs_human` with the URL. Do not follow it; the
  destination is an arbitrary employer portal with no playbook.

## Flow

1. Navigate to `https://www.linkedin.com/jobs/view/<id>`. Requires an active signed-in session in
   the user's Chrome — if a login wall appears, stop the channel and ask them to sign in.
2. `find` the Easy Apply button and click it.
3. The modal is a **multi-step wizard** with a progress bar. Steps vary by employer:
   - Contact info (prefilled from the LinkedIn profile — verify against the client profile).
   - Resume — choose "Upload resume" and use `file_upload` with the tailored PDF.
   - Screening questions — the step that generates new answers-bank entries. Often includes
     numeric "how many years of X" fields with strict validation.
   - Review.
4. `read_page` after **every** "Next" click. The modal replaces its contents in place.
5. The final button reads **"Submit application"**, not "Next" — check the label before clicking.
   Clicking "Next" expecting submit is the most common way to leave an application half-finished.

## Watch for

- **"Follow this company"** checkbox, usually checked by default on the review step. Uncheck it
  unless the user said otherwise — it posts activity to their network.
- Questions with a required numeric answer that the profile can't support. Ask; never round up.
- A "save for later" prompt on close — that is not a submission.

## Success signal

"Your application was sent to <company>" confirmation. Anything else is not a submit.

## Bail conditions — stop the whole channel, not just the job

Captcha or a "confirm you're a human" interstitial, an unusual-activity warning, a forced
re-authentication, or 3 consecutive failures. Report to the user and move on. Do not retry, do not
slow-loop, do not switch tactics.
