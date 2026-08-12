"""
Fetcher for Oracle Cloud HCM-hosted career sites (e.g. Texas Instruments).

Public search endpoint:
  POST https://{host}/hcmRestApi/resources/latest/recruitingCEJobRequisitions

Body (minimal):
  {
    "finder": "findReqs;siteNumber={site_number}",
    "limit": 25,
    "offset": 0
  }

This is a different JSON shape from Workday/Greenhouse/Lever again --
Oracle's own HCM REST API convention.
"""

import re
import html
import requests

TIMEOUT = 20
PAGE_SIZE = 25
MAX_PAGES = 15


def _strip_html(raw: str) -> str:
    if not raw:
        return ""
    text = re.sub(r"<[^>]+>", " ", raw)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def fetch_oracle_cloud(company_name: str, host: str, site_number: str) -> list[dict]:
    url = f"https://{host}/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
    job_page_base = f"https://{host}/hcmUI/CandidateExperience/en/sites/{site_number}/job"

    all_reqs = []
    offset = 0

    for _ in range(MAX_PAGES):
        params = {
            "finder": f"findReqs;siteNumber={site_number},limit={PAGE_SIZE},offset={offset}",
        }
        try:
            resp = requests.get(url, params=params, timeout=TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"[oracle_cloud] {company_name} failed at offset {offset}: {e}")
            break

        items = data.get("items", [])
        if not items:
            break
        reqs = items[0].get("requisitionList", []) if items else []
        if not reqs:
            break

        all_reqs.extend(reqs)
        offset += PAGE_SIZE
        if len(reqs) < PAGE_SIZE:
            break

    jobs = []
    for r in all_reqs:
        req_id = r.get("Id") or r.get("RequisitionNumber", "")
        jobs.append({
            "external_id": f"oracle:{host}:{req_id}",
            "company": company_name,
            "title": r.get("Title", ""),
            "location": r.get("PrimaryLocation", ""),
            "url": f"{job_page_base}/{req_id}",
            "description": _strip_html(r.get("ShortDescriptionStr", "") or r.get("ExternalDescriptionStr", "")),
            "posted_at": r.get("PostedDate"),
        })
    return jobs


def fetch_all_oracle_cloud_jobs(companies: list[dict]) -> list[dict]:
    all_jobs = []
    for c in companies:
        jobs = fetch_oracle_cloud(c["name"], c["host"], c["site_number"])
        print(f"[fetch_all_oracle_cloud_jobs] {c['name']}: {len(jobs)} jobs")
        all_jobs.extend(jobs)
    return all_jobs
