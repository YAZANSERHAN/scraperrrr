"""
Fetchers for public ATS job-board APIs.
Each returns a normalized list of dicts:
  {
    "external_id": str,   # unique id from the ATS, used for dedup
    "company": str,
    "title": str,
    "location": str,
    "url": str,
    "description": str,   # plain text, HTML stripped
    "posted_at": str | None,
  }
"""

import re
import html
import requests

TIMEOUT = 15


def _strip_html(raw: str) -> str:
    if not raw:
        return ""
    text = re.sub(r"<[^>]+>", " ", raw)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def fetch_greenhouse(company_name: str, slug: str) -> list[dict]:
    url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
    try:
        resp = requests.get(url, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[greenhouse] {company_name} ({slug}) failed: {e}")
        return []

    jobs = []
    for job in data.get("jobs", []):
        jobs.append({
            "external_id": f"greenhouse:{slug}:{job.get('id')}",
            "company": company_name,
            "title": job.get("title", ""),
            "location": (job.get("location") or {}).get("name", ""),
            "url": job.get("absolute_url", ""),
            "description": _strip_html(job.get("content", "")),
            "posted_at": job.get("updated_at"),
        })
    return jobs


def fetch_lever(company_name: str, slug: str, subdomain: str = "api") -> list[dict]:
    """
    subdomain: most companies use the default api.lever.co, but some
    (e.g. Mobileye) are hosted on a region subdomain like api.eu.lever.co.
    Pass subdomain="eu" for those.
    """
    host = "api.lever.co" if subdomain == "api" else f"api.{subdomain}.lever.co"
    url = f"https://{host}/v0/postings/{slug}?mode=json"
    try:
        resp = requests.get(url, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[lever] {company_name} ({slug}) failed: {e}")
        return []

    jobs = []
    for job in data:
        desc_parts = [job.get("descriptionPlain", "") or _strip_html(job.get("description", ""))]
        for L in job.get("lists", []):
            desc_parts.append(L.get("text", ""))
            desc_parts.append(_strip_html(L.get("content", "")))
        jobs.append({
            "external_id": f"lever:{slug}:{job.get('id')}",
            "company": company_name,
            "title": job.get("text", ""),
            "location": (job.get("categories") or {}).get("location", ""),
            "url": job.get("hostedUrl", ""),
            "description": " ".join(p for p in desc_parts if p),
            "posted_at": str(job.get("createdAt", "")),
        })
    return jobs


def fetch_comeet(company_name: str, slug: str) -> list[dict]:
    url = f"https://www.comeet.com/careers-api/2.0/company/{slug}/positions"
    try:
        resp = requests.get(url, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[comeet] {company_name} ({slug}) failed: {e}")
        return []

    jobs = []
    for job in data:
        location_parts = [
            job.get("location", {}).get("name", "") if isinstance(job.get("location"), dict) else "",
        ]
        desc = " ".join(
            _strip_html(section.get("value", ""))
            for section in job.get("details", [])
            if isinstance(section, dict)
        )
        jobs.append({
            "external_id": f"comeet:{slug}:{job.get('uid')}",
            "company": company_name,
            "title": job.get("name", ""),
            "location": ", ".join(p for p in location_parts if p),
            "url": job.get("url_comeet_hosted_page", "") or job.get("url", ""),
            "description": desc,
            "posted_at": None,
        })
    return jobs


FETCHERS = {
    "greenhouse": fetch_greenhouse,
    "lever": fetch_lever,
    "comeet": fetch_comeet,
}


def fetch_all_jobs(companies: list[dict]) -> list[dict]:
    """Fetch jobs from every company in the list, skipping failures gracefully."""
    all_jobs = []
    for c in companies:
        fetcher = FETCHERS.get(c["ats"])
        if not fetcher:
            print(f"[fetch_all_jobs] unknown ATS '{c['ats']}' for {c['name']}, skipping")
            continue
        if c["ats"] == "lever" and "lever_subdomain" in c:
            jobs = fetcher(c["name"], c["slug"], subdomain=c["lever_subdomain"])
        else:
            jobs = fetcher(c["name"], c["slug"])
        print(f"[fetch_all_jobs] {c['name']}: {len(jobs)} jobs")
        all_jobs.extend(jobs)
    return all_jobs
