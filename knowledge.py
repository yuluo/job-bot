import argparse
import datetime
import json
import os
import re
import sys

import yaml

CANDIDATE_DIR = "candidate"

MATCH_THRESHOLD = 0.75

BLOCKED_PATTERNS = (
    r"\bssn\b",
    r"social security",
    r"\bein\b",
    r"driver'?s? licen[cs]e",
    r"passport",
    r"government[- ]issued",
    r"date of birth",
    r"\bdob\b",
    r"bank",
    r"routing number",
    r"account number",
    r"credit card",
    r"\bpassword\b",
)

REQUIRED_PROFILE_FIELDS = [
    ("identity", "full_name"),
    ("identity", "email"),
    ("identity", "phone"),
    ("identity", "city"),
    ("identity", "state"),
    ("authorization", "work_authorized_us"),
    ("authorization", "requires_sponsorship"),
    ("preferences", "desired_salary"),
    ("preferences", "earliest_start"),
    ("experience", "total_years"),
]

PROFILE_SCAFFOLD = {
    "identity": {
        "full_name": None,
        "email": None,
        "phone": None,
        "city": None,
        "state": None,
        "country": "United States",
        "linkedin_url": None,
        "portfolio_url": None,
    },
    "authorization": {
        "work_authorized_us": None,
        "requires_sponsorship": None,
        "visa_status": None,
    },
    "preferences": {
        "desired_salary": None,
        "earliest_start": None,
        "willing_to_relocate": None,
        "remote_preference": None,
    },
    "experience": {"total_years": None, "years_by_skill": {}},
    "eeo": {
        "gender": "decline_to_answer",
        "race": "decline_to_answer",
        "veteran_status": "decline_to_answer",
        "disability_status": "decline_to_answer",
    },
    "defaults": {
        "cover_letter_template": None,
        "referral_source": None,
        "notice_period": None,
    },
}

STOPWORDS = {
    "a", "an", "the", "do", "does", "did", "you", "your", "yours", "are", "is", "was",
    "have", "has", "had", "will", "would", "can", "could", "should", "please", "what",
    "which", "why", "how", "many", "much", "any", "at", "in", "on", "of", "for", "to",
    "with", "and", "or", "if", "this", "that", "be", "been", "we", "us", "our", "i",
    "me", "my", "position", "role", "job", "opportunity", "company", "here", "there",
}


def profile_path():
    return os.path.join(CANDIDATE_DIR, "profile.yaml")


def answers_path():
    return os.path.join(CANDIDATE_DIR, "answers.yaml")


def in_scope(entry, role):
    """A per_role entry only applies to the role it was recorded under."""
    if entry.get("scope") != "per_role":
        return True
    return entry.get("role") == role


def is_blocked(question):
    text = (question or "").lower()
    return any(re.search(p, text) for p in BLOCKED_PATTERNS)


def normalize(question, company=None):
    text = (question or "").lower()
    if company:
        text = text.replace(str(company).lower(), " ")
    text = re.sub(r"\{[a-z_]+\}", " ", text)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    tokens = [t for t in text.split() if t and t not in STOPWORDS]
    return tokens


def slug_key(question, company=None):
    tokens = normalize(question, company)
    return "-".join(tokens[:6]) or "unnamed-question"


def similarity(a_tokens, b_tokens):
    if not a_tokens or not b_tokens:
        return 0.0
    a, b = set(a_tokens), set(b_tokens)
    return len(a & b) / len(a | b)


def load_yaml(path, default):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh) or default


def dump_yaml(path, data):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        yaml.safe_dump(data, fh, sort_keys=False, allow_unicode=True, width=100)


def missing_fields(profile):
    missing = []
    for section, field in REQUIRED_PROFILE_FIELDS:
        value = (profile.get(section) or {}).get(field)
        if value is None or value == "":
            missing.append(f"{section}.{field}")
    return missing


def cmd_init(args):
    ppath, apath = profile_path(), answers_path()
    created = []
    if not os.path.exists(ppath):
        dump_yaml(ppath, PROFILE_SCAFFOLD)
        created.append(ppath)
    if not os.path.exists(apath):
        dump_yaml(apath, [])
        created.append(apath)
    profile = load_yaml(ppath, {})
    print(json.dumps({"created": created, "missing": missing_fields(profile)}, indent=2))


def cmd_profile(args):
    profile = load_yaml(profile_path(), {})
    print(
        json.dumps(
            {
                "exists": os.path.exists(profile_path()),
                "profile": profile,
                "missing": missing_fields(profile),
            },
            indent=2,
            default=str,
        )
    )


def cmd_lookup(args):
    if is_blocked(args.question):
        print(
            json.dumps(
                {
                    "found": False,
                    "blocked": True,
                    "reason": "question requests a prohibited identifier; "
                    "do not answer, do not store, log the job needs_human",
                },
                indent=2,
            )
        )
        return

    entries = [e for e in load_yaml(answers_path(), []) if in_scope(e, args.role)]
    target = normalize(args.question, args.company)
    key = slug_key(args.question, args.company)

    best, best_score, how = None, 0.0, None
    for entry in entries:
        if entry.get("key") == key:
            best, best_score, how = entry, 1.0, "key"
            break
        candidates = [entry.get("question", "")] + list(entry.get("variants") or [])
        for candidate in candidates:
            s = similarity(target, normalize(candidate, args.company))
            if s > best_score:
                best, best_score, how = entry, s, "variant" if candidate != entry.get("question") else "question"

    if best and best_score >= MATCH_THRESHOLD:
        scope = best.get("scope", "global")
        print(
            json.dumps(
                {
                    "found": True,
                    "key": best.get("key"),
                    "answer": best.get("answer"),
                    "answer_type": best.get("answer_type"),
                    "scope": scope,
                    "role": best.get("role"),
                    "matched_on": how,
                    "confidence": round(best_score, 3),
                    "reuse_count": best.get("reuse_count", 0),
                    "requires_personalization": scope == "per_company",
                    "stored_question": best.get("question"),
                },
                indent=2,
                default=str,
            )
        )
        return

    print(
        json.dumps(
            {
                "found": False,
                "blocked": False,
                "suggested_key": key,
                "nearest": (best or {}).get("question"),
                "nearest_confidence": round(best_score, 3),
            },
            indent=2,
            default=str,
        )
    )


def cmd_record(args):
    if is_blocked(args.question):
        print("refusing to store a prohibited identifier", file=sys.stderr)
        sys.exit(2)

    path = answers_path()
    entries = load_yaml(path, [])
    key = args.key or slug_key(args.question, args.company)

    # Only update an entry that actually applies to this role — otherwise the same
    # question asked under two roles would overwrite one role's answer with the other's.
    for entry in entries:
        if entry.get("key") == key and in_scope(entry, args.role):
            variants = list(entry.get("variants") or [])
            if args.question != entry.get("question") and args.question not in variants:
                variants.append(args.question)
                entry["variants"] = variants
            entry["answer"] = args.answer
            entry["reuse_count"] = entry.get("reuse_count", 0) + 1
            dump_yaml(path, entries)
            print(json.dumps({"updated": key, "reuse_count": entry["reuse_count"]}, indent=2))
            return

    entry = {
        "key": key,
        "question": args.question,
        "answer_type": args.type,
        "answer": args.answer,
        "variants": [],
        "scope": args.scope,
        "asked_at": args.asked_at or datetime.date.today().isoformat(),
        "first_seen": {"company": args.company, "job_url": args.job_url},
        "reuse_count": 1,
    }
    if args.scope == "per_role":
        entry["role"] = args.role
    entries.append(entry)
    dump_yaml(path, entries)
    print(json.dumps({"created": key, "scope": args.scope, "role": entry.get("role"), "total_entries": len(entries)}, indent=2))


def cmd_bump(args):
    path = answers_path()
    entries = load_yaml(path, [])
    for entry in entries:
        if entry.get("key") == args.key and in_scope(entry, args.role):
            entry["reuse_count"] = entry.get("reuse_count", 0) + 1
            dump_yaml(path, entries)
            print(json.dumps({"key": args.key, "reuse_count": entry["reuse_count"]}, indent=2))
            return
    print(f"no entry with key {args.key!r}", file=sys.stderr)
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Candidate knowledge base for auto-apply")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init", help="create profile + answers scaffolding")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("profile", help="print the profile and any missing fields")
    p.set_defaults(func=cmd_profile)

    p = sub.add_parser("lookup", help="look up an application question")
    p.add_argument("--question", required=True)
    p.add_argument("--role", required=True, help="keyword slug, e.g. 'data-engineer'")
    p.add_argument("--company", default=None)
    p.set_defaults(func=cmd_lookup)

    p = sub.add_parser("record", help="store an answer the user supplied")
    p.add_argument("--question", required=True)
    p.add_argument("--answer", required=True)
    p.add_argument("--role", required=True, help="keyword slug, e.g. 'data-engineer'")
    p.add_argument("--scope", default="global", choices=["global", "per_role", "per_company"])
    p.add_argument("--type", default="freetext", choices=["freetext", "choice", "boolean", "number", "date"])
    p.add_argument("--company", default=None)
    p.add_argument("--job-url", default=None)
    p.add_argument("--key", default=None)
    p.add_argument("--asked-at", default=None)
    p.set_defaults(func=cmd_record)

    p = sub.add_parser("bump", help="increment reuse_count after a reuse")
    p.add_argument("--key", required=True)
    p.add_argument("--role", required=True, help="keyword slug, e.g. 'data-engineer'")
    p.set_defaults(func=cmd_bump)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
