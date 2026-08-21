import argparse
import csv
import datetime
import glob
import json
import os
import re
import sys
import urllib.parse

import pandas as pd

APPLICATIONS_DIR = "applications"
LEDGER = os.path.join(APPLICATIONS_DIR, "applied.csv")

LEDGER_COLUMNS = [
    "applied_at",
    "client",
    "keyword",
    "site",
    "channel",
    "company",
    "title",
    "job_url",
    "apply_url",
    "status",
    "notes",
]

ATS_HOSTS = (
    "greenhouse.io",
    "lever.co",
    "ashbyhq.com",
    "myworkdayjobs.com",
    "workable.com",
    "smartrecruiters.com",
    "jobvite.com",
    "icims.com",
    "bamboohr.com",
    "breezy.hr",
    "recruitee.com",
    "teamtailor.com",
)

CHANNELS = ("ats", "dice", "linkedin", "indeed")

STOPWORDS = {
    "and", "or", "the", "a", "an", "of", "for", "to", "in", "on", "with", "at",
    "senior", "sr", "junior", "jr", "staff", "lead", "principal", "ii", "iii", "iv",
}


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")


def truthy(value):
    if isinstance(value, bool):
        return value
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return False
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def newest_csv(slug):
    matches = sorted(glob.glob(os.path.join("output", f"jobs_{slug}_*.csv")))
    if not matches:
        return None
    return max(matches, key=lambda p: re.search(r"_(\d{8}-\d{6})\.csv$", p).group(1))


def ats_host(url):
    if not url or (isinstance(url, float) and pd.isna(url)):
        return None
    host = urllib.parse.urlparse(str(url)).netloc.lower()
    for known in ATS_HOSTS:
        if host == known or host.endswith("." + known):
            return known
    return None


def classify(row):
    """Return (channel, apply_url, reason)."""
    direct = row.get("job_url_direct")
    host = ats_host(direct)
    if host:
        return "ats", str(direct), host

    site = str(row.get("site") or "").lower()
    if site == "dice":
        if truthy(row.get("easy_apply")):
            return "dice", str(row.get("job_url")), "dice easy apply"
        return "unknown", str(row.get("job_url")), "dice, not easy apply"
    if site == "linkedin":
        return "linkedin", str(row.get("job_url")), "linkedin (easy apply detected in browser)"
    if site == "indeed":
        return "indeed", str(row.get("job_url")), "indeed apply"
    return "unknown", str(row.get("job_url")), f"unrecognized site {site!r}"


def dedupe_key(row):
    company = slugify(row.get("company") or "")
    title = " ".join(
        w for w in slugify(row.get("title") or "").split("-") if w not in STOPWORDS
    )
    return f"{company}|{title}"


def read_ledger():
    seen_urls, seen_keys = set(), set()
    if not os.path.exists(LEDGER):
        return seen_urls, seen_keys
    with open(LEDGER, newline="", encoding="utf-8") as fh:
        for entry in csv.DictReader(fh):
            if entry.get("status") == "skipped":
                continue
            if entry.get("job_url"):
                seen_urls.add(entry["job_url"])
            seen_keys.add(dedupe_key(entry))
    return seen_urls, seen_keys


def append_ledger(entries):
    os.makedirs(APPLICATIONS_DIR, exist_ok=True)
    exists = os.path.exists(LEDGER)
    with open(LEDGER, "a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=LEDGER_COLUMNS)
        if not exists:
            writer.writeheader()
        for entry in entries:
            writer.writerow({k: entry.get(k, "") for k in LEDGER_COLUMNS})


def load_profile(client):
    path = os.path.join("clients", f"{client}.profile.yaml")
    if not os.path.exists(path):
        return {}
    import yaml

    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def score(row, skills):
    if not skills:
        return 0
    haystack = f"{row.get('title') or ''} {row.get('description') or ''}".lower()
    return sum(1 for skill in skills if skill.lower() in haystack)


def parse_salary_floor(value):
    if not value or (isinstance(value, float) and pd.isna(value)):
        return None
    numbers = [float(n.replace(",", "")) for n in re.findall(r"[\d,]+(?:\.\d+)?", str(value))]
    numbers = [n for n in numbers if n > 1000]
    return min(numbers) if numbers else None


def main():
    parser = argparse.ArgumentParser(
        description="Build an application shortlist from a scraped job CSV"
    )
    parser.add_argument("slug", help="keyword slug, e.g. 'devops-engineer'")
    parser.add_argument("--client", required=True, help="client name")
    parser.add_argument("--channels", default=",".join(CHANNELS))
    parser.add_argument("--limit-per-channel", type=int, default=10)
    parser.add_argument("--location", default=None)
    parser.add_argument("--min-salary", type=float, default=None)
    parser.add_argument("--csv", default=None, help="explicit CSV path")
    parser.add_argument("--out", default=None, help="explicit batch JSON path")
    args = parser.parse_args()

    slug = slugify(args.slug)
    path = args.csv or newest_csv(slug)
    if not path:
        available = sorted(
            {
                re.sub(r"^jobs_|_\d{8}-\d{6}\.csv$", "", os.path.basename(p))
                for p in glob.glob("output/jobs_*.csv")
            }
        )
        print(f"No CSV for slug {slug!r}. Available: {', '.join(available) or 'none'}", file=sys.stderr)
        sys.exit(1)

    df = pd.read_csv(path)
    for column in ("job_url_direct", "easy_apply", "sponsorship", "employment_type", "remote"):
        if column not in df.columns:
            df[column] = None

    profile = load_profile(args.client)
    skills = list((profile.get("experience") or {}).get("years_by_skill") or {})
    needs_sponsorship = bool((profile.get("authorization") or {}).get("requires_sponsorship"))

    wanted = [c.strip() for c in args.channels.split(",") if c.strip()]
    seen_urls, seen_keys = read_ledger()

    buckets = {c: [] for c in wanted}
    dropped = {
        "already_applied": 0,
        "duplicate_in_batch": 0,
        "unknown_channel": 0,
        "sponsorship": 0,
        "filtered": 0,
    }
    batch_keys = set()

    for _, row in df.iterrows():
        channel, apply_url, reason = classify(row)
        if channel == "unknown" or channel not in buckets:
            dropped["unknown_channel"] += 1
            continue
        key = dedupe_key(row)
        if str(row.get("job_url")) in seen_urls or key in seen_keys:
            dropped["already_applied"] += 1
            continue
        if key in batch_keys:
            dropped["duplicate_in_batch"] += 1
            continue
        if needs_sponsorship and row.get("sponsorship") is not None and not truthy(row.get("sponsorship")):
            dropped["sponsorship"] += 1
            continue
        if args.location and args.location.lower() not in str(row.get("location") or "").lower():
            dropped["filtered"] += 1
            continue
        if args.min_salary:
            floor = parse_salary_floor(row.get("salary"))
            if floor is not None and floor < args.min_salary:
                dropped["filtered"] += 1
                continue

        batch_keys.add(key)
        buckets[channel].append(
            {
                "channel": channel,
                "channel_reason": reason,
                "site": row.get("site"),
                "company": row.get("company"),
                "title": row.get("title"),
                "location": row.get("location"),
                "salary": None if pd.isna(row.get("salary")) else row.get("salary"),
                "employment_type": None if pd.isna(row.get("employment_type")) else row.get("employment_type"),
                "job_url": row.get("job_url"),
                "apply_url": apply_url,
                "fallback_url": None if pd.isna(row.get("job_url_direct")) else row.get("job_url_direct"),
                "match_score": score(row, skills),
            }
        )

    batch = []
    for channel in CHANNELS:
        if channel not in buckets:
            continue
        ranked = sorted(buckets[channel], key=lambda j: -j["match_score"])
        batch.extend(ranked[: args.limit_per_channel])

    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    os.makedirs(APPLICATIONS_DIR, exist_ok=True)
    out_path = args.out or os.path.join(APPLICATIONS_DIR, f"batch_{slug}_{stamp}.json")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(
            {
                "client": args.client,
                "keyword_slug": slug,
                "source_csv": path,
                "created_at": stamp,
                "jobs": batch,
            },
            fh,
            indent=2,
            default=str,
        )

    counts = {c: sum(1 for j in batch if j["channel"] == c) for c in CHANNELS if c in buckets}
    summary = ", ".join(f"{c}: {n}" for c, n in counts.items())
    print(f"source: {path} ({len(df)} rows)")
    print(f"dropped: {dropped}")
    print(f"{summary} -> {out_path} ({len(batch)} jobs)")


if __name__ == "__main__":
    main()
