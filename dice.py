import html
import json
import re
import time

import requests

SEARCH_URL = "https://job-search-api.svc.dhigroupinc.com/v1/dice/jobs/search"
API_KEY = "1YAt0R9wBg4WfsF9VB2778F5CHLAPMVW3WAZcKd8"
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}


def _strip_html(text):
    text = re.sub(r"<(br|/p|/li|/div|/tr|/ul|/h[1-6])[^>]*>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\s*\n\s*", "\n", text)
    return text.strip()


def _decode_rsc_blob(page):
    chunks = re.findall(r'self\.__next_f\.push\(\[1,\s*"(.*?)"\]\)', page, re.S)
    parts = []
    for chunk in chunks:
        try:
            parts.append(json.loads('"' + chunk + '"'))
        except ValueError:
            parts.append(chunk.encode().decode("unicode_escape", "ignore"))
    return "".join(parts)


def fetch_description(session, url):
    resp = session.get(url, headers=BROWSER_HEADERS, timeout=20)
    resp.raise_for_status()
    blob = _decode_rsc_blob(resp.text)
    ref = re.search(r'"description":"\$([0-9a-fA-F]+)"', blob)
    if not ref:
        return None
    chunk = re.search(r"(?:^|\n)%s:T([0-9a-fA-F]+)," % ref.group(1), blob)
    if not chunk:
        return None
    length = int(chunk.group(1), 16)
    raw = blob.encode("utf-8")
    start = len(blob[: chunk.end()].encode("utf-8"))
    return _strip_html(raw[start : start + length].decode("utf-8", "ignore"))


def search(keyword, location=None, results_wanted=100, fetch_descriptions=True):
    session = requests.Session()
    raw_jobs = []
    page = 1
    while len(raw_jobs) < results_wanted:
        params = {"q": keyword, "page": page, "pageSize": min(results_wanted, 100)}
        if location:
            params["location"] = location
        resp = session.get(
            SEARCH_URL, params=params, headers={"x-api-key": API_KEY}, timeout=20
        )
        resp.raise_for_status()
        data = resp.json().get("data", [])
        if not data:
            break
        raw_jobs.extend(data)
        page += 1

    rows = []
    for job in raw_jobs[:results_wanted]:
        description = job.get("summary") or ""
        url = job.get("detailsPageUrl")
        if fetch_descriptions and url:
            try:
                full = fetch_description(session, url)
                if full:
                    description = full
            except requests.RequestException:
                pass
            time.sleep(0.3)
        rows.append(
            {
                "site": "dice",
                "title": job.get("title"),
                "company": job.get("companyName"),
                "location": (job.get("jobLocation") or {}).get("displayName"),
                "date_posted": job.get("postedDate"),
                "salary": job.get("salary"),
                "employment_type": job.get("employmentType"),
                "remote": job.get("workFromHomeAvailability"),
                "sponsorship": job.get("willingToSponsor"),
                "easy_apply": job.get("easyApply"),
                "job_url": url,
                "job_url_direct": None,
                "description": description,
            }
        )
    return rows
