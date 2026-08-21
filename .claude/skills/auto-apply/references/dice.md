# Channel: `dice` — Dice Easy Apply

Most reliable of the three job boards. Dice's search API exposes `easyApply` directly, so
`apply.py` only routes a job here when Easy Apply is confirmed — no in-browser guessing needed.

Requires the user to be signed in to Dice in their own Chrome. If not, stop and ask them to sign in;
never log in on their behalf.

## Flow

1. Navigate to the job's `job_url` (`https://www.dice.com/job-detail/<guid>`).
2. `find` the "Easy apply" button. If only "Apply now" is present, the API data was stale — log
   `needs_human` and move on rather than following the external redirect.
3. The Easy Apply modal is a short wizard:
   - **Resume step** — Dice offers previously uploaded resumes plus an upload control. Always upload
     the freshly rendered PDF via `file_upload` rather than reusing a stored one, since the whole
     point is the role-tailored version.
   - **Questions step** — employer screening questions, usually 0–5. Radio/select/short-text. This
     is where the answers bank earns its keep.
   - **Review step** — a summary of what will be sent.
4. `read_page` between every step; the modal swaps content without a navigation.

## Useful pre-filtering

The CSV carries Dice-specific fields worth checking before applying:

- `sponsorship` (`willingToSponsor`) — `apply.py` already drops mismatches when the profile sets
  `requires_sponsorship: true`.
- `employment_type` — often `Contract` or `Full-time, Third Party`. If the user only wants full-time
  employment, surface this in the Step 3 shortlist table so they can prune before the run.

## Success signal

The modal closes and the job page shows "Application submitted" / an applied badge. Verify before
recording `submitted` — a modal that closed on an error is not a submission.

## Bail conditions

Session expired or a sign-in prompt appears mid-batch → stop the channel entirely and tell the user
to re-authenticate. Do not attempt to log in.
