import argparse
import datetime
import os
import re
import sys

import pandas as pd

import dice

COLUMNS = [
    "site",
    "title",
    "company",
    "location",
    "date_posted",
    "salary",
    "employment_type",
    "remote",
    "sponsorship",
    "easy_apply",
    "job_url",
    "job_url_direct",
    "description",
]


def _salary(row):
    lo = row.get("min_amount")
    hi = row.get("max_amount")
    if pd.notna(lo) and pd.notna(hi):
        amount = f"{lo:,.0f} - {hi:,.0f}"
    elif pd.notna(lo):
        amount = f"{lo:,.0f}"
    elif pd.notna(hi):
        amount = f"{hi:,.0f}"
    else:
        return None
    interval = row.get("interval")
    return f"{amount} / {interval}" if pd.notna(interval) else amount


def scrape_jobspy_site(site, keyword, location, results, job_type=None, remote=False):
    from jobspy import scrape_jobs

    kwargs = {
        "site_name": [site],
        "search_term": keyword,
        "results_wanted": results,
        "country_indeed": "USA",
    }
    if location:
        kwargs["location"] = location
    if job_type:
        kwargs["job_type"] = job_type
    if remote:
        kwargs["is_remote"] = True
    if site == "linkedin":
        kwargs["linkedin_fetch_description"] = True
    df = scrape_jobs(**kwargs)
    if df is None or df.empty:
        return pd.DataFrame(columns=COLUMNS)
    out = pd.DataFrame(
        {
            "site": site,
            "title": df.get("title"),
            "company": df.get("company"),
            "location": df.get("location"),
            "date_posted": df.get("date_posted"),
            "salary": df.apply(_salary, axis=1),
            "employment_type": df.get("job_type"),
            "remote": df.get("is_remote"),
            "sponsorship": None,
            "easy_apply": None,
            "job_url": df.get("job_url"),
            "job_url_direct": df.get("job_url_direct"),
            "description": df.get("description"),
        }
    )
    return out


def main():
    parser = argparse.ArgumentParser(
        description="Scrape job postings from Indeed, LinkedIn, and Dice into a CSV"
    )
    parser.add_argument("keyword", help="search keyword, e.g. 'data engineer'")
    parser.add_argument("--location", default=None, help="optional location filter")
    parser.add_argument("--results", type=int, default=20, help="results per site")
    parser.add_argument(
        "--job-type",
        default=None,
        choices=["fulltime", "parttime", "contract", "internship"],
        help="employment type filter",
    )
    parser.add_argument(
        "--remote", action="store_true", help="remote postings only"
    )
    parser.add_argument("--out", default=None, help="output CSV path")
    args = parser.parse_args()

    frames = []
    counts = {}

    for site in ("indeed", "linkedin"):
        print(f"Scraping {site}...", flush=True)
        try:
            df = scrape_jobspy_site(
                site, args.keyword, args.location, args.results, args.job_type, args.remote
            )
            counts[site] = len(df)
            if not df.empty:
                frames.append(df)
        except Exception as exc:
            print(f"{site}: failed ({exc})", file=sys.stderr)
            counts[site] = 0

    print("Scraping dice...", flush=True)
    try:
        rows = dice.search(
            args.keyword,
            args.location,
            args.results,
            job_type=args.job_type,
            remote=args.remote,
        )
        counts["dice"] = len(rows)
        if rows:
            frames.append(pd.DataFrame(rows))
    except Exception as exc:
        print(f"dice: failed ({exc})", file=sys.stderr)
        counts["dice"] = 0

    if not frames:
        print("No jobs found on any site.", file=sys.stderr)
        sys.exit(1)

    combined = pd.concat(frames, ignore_index=True)[COLUMNS]

    # Sort newest first. date_posted mixes 'YYYY-MM-DD' (indeed/linkedin) with
    # ISO-8601 'YYYY-MM-DDTHH:MM:SSZ' (dice), so sort on the date prefix parsed
    # to a real date; unparseable or missing dates sink to the bottom.
    combined["_posted"] = pd.to_datetime(
        combined["date_posted"].astype(str).str[:10], errors="coerce"
    )
    combined = combined.sort_values(
        "_posted", ascending=False, na_position="last"
    ).drop(columns="_posted")

    if args.out:
        out_path = args.out
    else:
        slug = re.sub(r"[^a-z0-9]+", "-", args.keyword.lower()).strip("-")
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        role_dir = os.path.join("roles", slug)
        os.makedirs(role_dir, exist_ok=True)
        out_path = os.path.join(role_dir, f"jobs_{stamp}.csv")
    combined.to_csv(out_path, index=False)

    summary = ", ".join(f"{site}: {n}" for site, n in counts.items())
    print(f"{summary} -> {out_path} ({len(combined)} rows)")

    # LinkedIn accepts the f_JT filter but returns unfiltered results; asking for
    # contract roles comes back full of full-time ones. Say so at the moment it
    # matters rather than letting the CSV imply the filter applied everywhere.
    if args.job_type and counts.get("linkedin"):
        print(
            f"note: LinkedIn ignores --job-type; its {counts['linkedin']} rows are unfiltered. "
            "Indeed and Dice honored it.",
            file=sys.stderr,
        )
    if args.remote and counts.get("dice"):
        print(
            f"note: Dice's remote flag is unreliable; its {counts['dice']} rows may include "
            "on-site roles. Indeed and LinkedIn honored --remote.",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
