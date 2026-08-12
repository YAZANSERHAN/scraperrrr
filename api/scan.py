"""
Vercel serverless function entry point.
Triggered on a schedule by Vercel Cron (see vercel.json).

Flow:
  1. Fetch jobs from Greenhouse/Lever/Comeet companies
  2. Fetch jobs from Workday companies (title-only, then detail-fetch survivors)
  3. Fetch jobs from Oracle Cloud companies (Texas Instruments)
  4. Apply keyword + experience filters
  5. Drop anything already seen (Postgres/Supabase)
  6. Score remaining candidates with Claude for relevance
  7. Send Telegram alerts for relevant new jobs
  8. Mark alerted jobs as seen

Auth: this endpoint checks a CRON_SECRET header to prevent randoms from
triggering it and burning your Claude API quota. Vercel Cron sends this
automatically if CRON_SECRET is set as an env var.
"""

import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.companies import COMPANIES, WORKDAY_COMPANIES, ORACLE_CLOUD_COMPANIES
from lib.fetchers import fetch_all_jobs
from lib.workday_fetcher import fetch_all_workday_jobs, fetch_job_detail
from lib.oracle_cloud_fetcher import fetch_all_oracle_cloud_jobs
from lib.filters import apply_filters, keyword_filter
from lib.storage import filter_unseen, mark_seen
from lib.relevance import filter_by_relevance
from lib.notify import send_job_alert, send_summary


def run_scan() -> dict:
    # 1. Greenhouse / Lever / Comeet
    standard_jobs = fetch_all_jobs(COMPANIES)

    # 2. Workday -- title-only from the list endpoint, so pre-filter on
    #    title alone, THEN fetch full descriptions only for survivors
    #    (keeps request count sane -- Intel/Nvidia/Qualcomm can have 100+ reqs)
    workday_jobs_raw = fetch_all_workday_jobs(WORKDAY_COMPANIES)
    workday_title_survivors = [j for j in workday_jobs_raw if keyword_filter(j)]
    print(f"[scan] workday: {len(workday_jobs_raw)} total -> {len(workday_title_survivors)} pass title keyword filter")

    workday_company_lookup = {c["name"]: c for c in WORKDAY_COMPANIES}
    for job in workday_title_survivors:
        c = workday_company_lookup.get(job["company"])
        if not c:
            continue
        external_path = job["url"].replace(
            f"https://{c['tenant']}.{c['wd_host']}.myworkdayjobs.com/{c['site']}", ""
        )
        job["description"] = fetch_job_detail(c["tenant"], c["wd_host"], c["site"], external_path)

    # 3. Oracle Cloud (Texas Instruments)
    oracle_jobs = fetch_all_oracle_cloud_jobs(ORACLE_CLOUD_COMPANIES)

    all_jobs = standard_jobs + workday_title_survivors + oracle_jobs
    print(f"[scan] {len(all_jobs)} total jobs fetched across all sources")

    # 4. Keyword + experience filters (workday jobs already passed keyword once,
    #    but re-running is harmless and also applies the experience filter)
    filtered = apply_filters(all_jobs)
    print(f"[scan] {len(filtered)} jobs pass keyword+experience filters")

    # 5. Dedup against Postgres
    unseen = filter_unseen(filtered)
    print(f"[scan] {len(unseen)} jobs are new (not previously seen)")

    # 6. AI relevance check (only on new jobs -- keeps Claude API cost down)
    relevant = filter_by_relevance(unseen, min_score=7)
    print(f"[scan] {len(relevant)} jobs pass AI relevance check")

    # 7. Alert
    for job in relevant:
        send_job_alert(job)

    # 8. Mark ALL unseen jobs (not just relevant ones) as seen, so
    #    irrelevant jobs aren't re-scored by Claude on every future run
    mark_seen(unseen)

    send_summary(new_count=len(relevant), total_scanned=len(all_jobs))

    return {
        "total_fetched": len(all_jobs),
        "passed_filters": len(filtered),
        "new_unseen": len(unseen),
        "relevant_alerted": len(relevant),
    }


def handler(request):
    """Vercel Python runtime entry point."""
    cron_secret = os.environ.get("CRON_SECRET")
    if cron_secret:
        auth_header = request.headers.get("Authorization", "")
        if auth_header != f"Bearer {cron_secret}":
            return {
                "statusCode": 401,
                "body": json.dumps({"error": "unauthorized"}),
            }

    try:
        result = run_scan()
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(result),
        }
    except Exception as e:
        print(f"[scan] FATAL: {e}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(e)}),
        }
