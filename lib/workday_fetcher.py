"""
Fetcher for Workday-hosted career sites.

Workday's public job search is a POST endpoint, not a simple GET like
Greenhouse/Lever/Comeet:

  POST https://{tenant}.{wd_host}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs

Body:
  {
    "appliedFacets": {},
    "limit": 20,
    "offset": 0,
    "searchText": ""
  }

Response contains "jobPostings" (list) and "total" (int) -- paginate with
offset until you've collected `total` results.

Workday returns ALL locations globally by default. This fetcher does NOT
filter by location (Workday's location facet IDs are internal and differ
per tenant, making them brittle to hardcode). Instead, non-Israel roles
are expected to be filtered out later by keyword/relevance checks, since
location text is included in each job's "locationsText" field and can be
checked there if stricter filtering is wanted later.
"""

import re
import html
import requests

TIMEOUT = 20
PAGE_SIZE = 20
MAX_PAGES = 15  # safety cap: 15 * 20 = 300 jobs max per company per run


def _strip_html(raw: str) -> str:
    if not raw:
        return ""
    text = re.sub(r"<[^>]+>", " ", raw)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def fetch_workday(company_name: str, tenant: str, wd_host: str, site: str) -> list[dict]:
    base_url = f"https://{tenant}.{wd_host}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs"
    job_page_base = f"https://{tenant}.{wd_host}.myworkdayjobs.com/{site}"

    all_postings = []
    offset = 0

    for _ in range(MAX_PAGES):
        payload = {
            "appliedFacets": {},
            "limit": PAGE_SIZE,
            "offset": offset,
            "searchText": "",
        }
        try:
            resp = requests.post(base_url, json=payload, timeout=TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"[workday] {company_name} failed at offset {offset}: {e}")
            break

        postings = data.get("jobPostings", [])
        if not postings:
            break
        all_postings.extend(postings)

        total = data.get("total", len(all_postings))
        offset += PAGE_SIZE
        if offset >= total:
            break

    jobs = []
    for p in all_postings:
        path = p.get("externalPath", "")
        jobs.append({
            "external_id": f"workday:{tenant}:{p.get('bulletFields', [None])[0] or path}",
            "company": company_name,
            "title": p.get("title", ""),
            "location": p.get("locationsText", ""),
            "url": f"{job_page_base}{path}" if path else "",
            "description": "",  # Workday list endpoint doesn't include full description;
                                 # relevance check will work off title+location for these.
            "posted_at": p.get("postedOn"),
        })
    return jobs


def fetch_job_detail(tenant: str, wd_host: str, site: str, external_path: str) -> str:
    """
    Fetch the full description for a single Workday job posting.
    Call this AFTER a cheap title-level keyword pre-filter, not for every
    job -- Workday's detail endpoint is one request per job and this list
    can be large (Intel/Nvidia/Qualcomm routinely have 100+ open reqs).
    """
    detail_url = f"https://{tenant}.{wd_host}.myworkdayjobs.com/wday/cxs/{tenant}/{site}{external_path}"
    try:
        resp = requests.get(detail_url, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        raw = data.get("jobPostingInfo", {}).get("jobDescription", "")
        return _strip_html(raw)
    except Exception as e:
        print(f"[workday] detail fetch failed for {external_path}: {e}")
        return ""


def fetch_all_workday_jobs(companies: list[dict]) -> list[dict]:
    all_jobs = []
    for c in companies:
        jobs = fetch_workday(c["name"], c["tenant"], c["wd_host"], c["site"])
        print(f"[fetch_all_workday_jobs] {c['name']}: {len(jobs)} jobs")
        all_jobs.extend(jobs)
    return all_jobs
