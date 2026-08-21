# Channel: `indeed` — Indeed Apply

**Lowest success rate of the four.** Indeed runs aggressive bot detection (Cloudflare interstitials,
frequent captchas) and automated applying is against their Terms. Run this channel last, expect most
jobs to land in `needs_human`, and never work around a challenge.

## Prefer the direct employer URL

Indeed rows very often carry a populated `job_url_direct` — in a sample scrape, 5 of 5 did. When
`apply.py` recognized the host as a known ATS it already routed the job to the `ats` channel. Rows
that reach *this* channel have either no direct URL or one on an unrecognized host (an employer
career portal such as `corporate.target.com` or a Salesforce recruiting site).

So: **if `fallback_url` is present, try it first.** An employer's own portal has no bot detection
and no ToS problem, and is usually a plain form. Read it, map fields by label, and apply the Step 5
lookup order. If it turns out to require an account, log `needs_human`.

Only fall back to Indeed's own flow when `fallback_url` is empty.

## Indeed-hosted flow

1. Navigate to the `job_url` (`https://www.indeed.com/viewjob?jk=<id>`).
2. If a Cloudflare or "verify you are human" interstitial appears — **stop this channel entirely**.
   Do not attempt to solve it. Report to the user.
3. `find` the "Apply now" button. Indeed Apply opens a multi-step wizard on `smartapply.indeed.com`.
4. Steps: contact info → resume (upload the tailored PDF; do not reuse an Indeed-hosted resume) →
   employer screening questions → review → submit.
5. `read_page` after every step.

## Watch for

- Indeed prefills from the user's Indeed profile. Verify every prefilled value against the client
  profile before submitting — a stale phone number or an outdated resume selection is easy to miss.
- Some employers attach timed assessments after the form. That is a `needs_human` bail, not
  something to attempt.
- "Relevant experience" free-text boxes are a common source of new answers-bank entries.

## Success signal

An "Application submitted" confirmation page. Indeed also emails a confirmation — a good
cross-check when the page state is ambiguous.

## Bail conditions — stop the whole channel

Any captcha or interstitial, a login wall, an assessment, or 3 consecutive failures.
