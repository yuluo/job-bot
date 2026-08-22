# The candidate knowledge base

Two YAML files under `candidate/` — this repo holds one candidate. Managed by `knowledge.py`, but
plain enough that the user can hand-edit them between runs. The skill re-reads them each run and
never overwrites a value the user changed by hand.

## `candidate/profile.yaml`

Created by `knowledge.py init`. The fields nearly every application asks for.

```yaml
identity:
  full_name: Jane Doe
  email: jane@example.com
  phone: "+1 555 010 1234"
  city: Austin
  state: TX
  country: United States
  linkedin_url: https://www.linkedin.com/in/janedoe
  portfolio_url: null
authorization:
  work_authorized_us: true
  requires_sponsorship: false
  visa_status: null
preferences:
  desired_salary: 165000
  earliest_start: "2026-09-15"
  willing_to_relocate: false
  remote_preference: remote
experience:
  total_years: 8
  years_by_skill: { kubernetes: 5, terraform: 4, aws: 8, python: 6 }
eeo:
  gender: decline_to_answer
  race: decline_to_answer
  veteran_status: decline_to_answer
  disability_status: decline_to_answer
defaults:
  cover_letter_template: null
  referral_source: Job board
  notice_period: 2 weeks
```

`years_by_skill` does double duty: it answers "how many years of X" questions, and `apply.py` uses
its keys to rank the shortlist by description overlap.

`knowledge.py profile` prints the profile plus a `missing` list of required fields.

## `candidate/answers.yaml`

The learned Q&A bank. Starts empty and grows every run — this is why the skill gets quieter the more
it is used.

```yaml
- key: years-experience-kubernetes
  question: How many years of experience do you have with Kubernetes?
  answer_type: number
  answer: "5"
  variants:
    - Years of Kubernetes experience?
  scope: global          # global | per_role | per_company
  asked_at: "2026-08-21"
  first_seen: { company: Acme, job_url: "https://..." }
  reuse_count: 7
```

### `scope` — the field that keeps reuse honest

| scope | meaning | reuse behavior |
|---|---|---|
| `global` | a fact that doesn't change | replayed verbatim under any role |
| `per_role` | tied to one keyword | **enforced in code** — carries a `role:` field and is invisible to `lookup` under any other role |
| `per_company` | names or flatters the employer | **template only** — must be rewritten per employer and shown to the user before submitting |

`per_role` entries are filtered out of the match loop entirely when the role doesn't match, so they
cannot even surface as `nearest`. Two roles can therefore hold different answers to the same
question without colliding — recording "Which BI tool do you prefer?" under `power-bi` and
`data-engineer` produces two independent entries.

A `per_company` answer replayed verbatim to a different company is the worst failure this skill can
produce, and it fails silently. `knowledge.py lookup` returns `requires_personalization: true` for
these; honor it.

## Matching

`knowledge.py lookup --role <slug> --question "..." [--company "..."]` resolves in this order: exact
`key` → stored `question` → `variants` → normalized token-overlap similarity, over the entries in
scope for `--role`. Normalization lowercases, strips punctuation, drops the company name and generic
filler words.

`--role` is required on `lookup`, `record`, and `bump`.

Auto-accept threshold is **0.75 Jaccard**. It is deliberately strict: "years of experience with
Terraform" scores 0.5 against the Kubernetes entry above and correctly does **not** match. A wrong
match here puts a wrong answer on a real application, so when in doubt the skill asks.

## Prohibited identifiers

`knowledge.py` refuses SSN, EIN, government ID, driver's license, passport, date of birth, bank and
routing numbers, credit card details, and passwords — on `lookup` (returns `blocked: true`) and on
`record` (exits non-zero). These are never asked for, never stored, and never entered. A form
demanding one makes the job `needs_human`.
