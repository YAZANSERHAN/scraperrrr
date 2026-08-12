"""
Vercel serverless function entry point.
Triggered on a schedule by Vercel Cron (see vercel.json).

IMPORTANT -- Hobby plan constraint:
Vercel's Hobby (free) plan hard-caps function execution at 10 seconds,
with NO override available (maxDuration in vercel.json is ignored on
Hobby). A full scan across 15+ companies -- including Workday pagination
and per-job detail fetches, plus a Claude API call per candidate job --
will not fit in 10 seconds.

So this endpoint processes ONE SOURCE GROUP per invocation, and chains
to the next group itself via a fire-and-forget HTTP call before
returning. Vercel Cron only triggers the first group each day; each
subsequent call triggers the next.

Groups: "standard" (Greenhouse/Lever/Comeet) -> "workday" -> "oracle"
Each group's fetch+filter+relevance+alert happens within its own
function invocation, so each stays under the 10s ceiling individually.
If a group is still too slow with the full company list, split it
further (e.g. two calls each covering half the Workday companies).
"""

import os
import sys
import json
import threading
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.companies import COMPANIES, WORKDAY_COMPANIES, ORACLE_CLOUD_COMPANIES
from lib.fetchers import fetch_all_jobs
from lib.workday_fetcher import fetch_all_workday_jobs, fetch_job_detail
from lib.oracle_cloud_fetcher import fetch_all_oracle_cloud_jobs
from lib.filters import apply_filters, keyword_filter
from lib.storage import filter_unseen, mark_seen
from lib.relevance import filter_by_relevance
from lib.notify import send_job_alert, send_summary

GROUP_ORDER = ["greenhouse_lever", "comeet", "workday_a", "workday_b", "oracle"]

# Hobby's 10s hard cap means each Claude relevance call (~1-3s) adds up fast.
# Cap how many jobs get AI-scored per invocation; any overflow just waits
# for the next day's run rather than risking a mid-scoring timeout that
# wastes the API calls already made.
MAX_RELEVANCE_CHECKS_PER_INVOCATION = 4


def _process_and_alert(jobs: list[dict]) -> dict:
    """Shared pipeline: filter -> dedup -> relevance -> alert -> mark seen."""
    filtered = apply_filters(jobs)
    unseen = filter_unseen(filtered)

    to_score = unseen[:MAX_RELEVANCE_CHECKS_PER_INVOCATION]
    overflow = unseen[MAX_RELEVANCE_CHECKS_PER_INVOCATION:]
    if overflow:
        print(f"[scan] {len(overflow)} unseen jobs deferred to next run (invocation budget)")

    relevant = filter_by_relevance(to_score, min_score=7)
    for job in relevant:
        send_job_alert(job)

    # Only mark SCORED jobs as seen -- overflow jobs stay unseen so
    # they're picked up and scored on the next day's run instead of
    # being silently dropped.
    mark_seen(to_score)

    return {
        "total_fetched": len(jobs),
        "passed_filters": len(filtered),
        "new_unseen": len(unseen),
        "scored_this_run": len(to_score),
        "deferred": len(overflow),
        "relevant_alerted": len(relevant),
    }


def run_greenhouse_lever_group() -> dict:
    companies = [c for c in COMPANIES if c["ats"] in ("greenhouse", "lever")]
    jobs = fetch_all_jobs(companies)
    print(f"[scan:greenhouse_lever] {len(jobs)} jobs fetched")
    return _process_and_alert(jobs)


def run_comeet_group() -> dict:
    companies = [c for c in COMPANIES if c["ats"] == "comeet"]
    jobs = fetch_all_jobs(companies)
    print(f"[scan:comeet] {len(jobs)} jobs fetched")
    return _process_and_alert(jobs)


def _run_workday_subset(companies: list[dict], label: str) -> dict:
    raw = fetch_all_workday_jobs(companies)
    survivors = [j for j in raw if keyword_filter(j)]
    print(f"[scan:{label}] {len(raw)} total -> {len(survivors)} pass title keyword filter")

    lookup = {c["name"]: c for c in companies}
    for job in survivors:
        c = lookup.get(job["company"])
        if not c:
            continue
        prefix = f"https://{c['tenant']}.{c['wd_host']}.myworkdayjobs.com/{c['site']}"
        external_path = job["url"].replace(prefix, "")
        job["description"] = fetch_job_detail(c["tenant"], c["wd_host"], c["site"], external_path)

    return _process_and_alert(survivors)


def run_workday_a_group() -> dict:
    # First half of the Workday company list -- keeps each invocation's
    # fetch+paginate step well under the 10s Hobby ceiling
    half = WORKDAY_COMPANIES[: len(WORKDAY_COMPANIES) // 2]
    return _run_workday_subset(half, "workday_a")


def run_workday_b_group() -> dict:
    half = WORKDAY_COMPANIES[len(WORKDAY_COMPANIES) // 2 :]
    return _run_workday_subset(half, "workday_b")


def run_oracle_group() -> dict:
    jobs = fetch_all_oracle_cloud_jobs(ORACLE_CLOUD_COMPANIES)
    print(f"[scan:oracle] {len(jobs)} jobs fetched")
    return _process_and_alert(jobs)


GROUP_RUNNERS = {
    "greenhouse_lever": run_greenhouse_lever_group,
    "comeet": run_comeet_group,
    "workday_a": run_workday_a_group,
    "workday_b": run_workday_b_group,
    "oracle": run_oracle_group,
}


def _trigger_next_group(base_url: str, current_group: str, cron_secret: str | None) -> None:
    """Fire-and-forget call to kick off the next group without waiting
    for it to finish -- keeps THIS invocation's response fast, and lets
    the next group run in its own fresh 10s window."""
    idx = GROUP_ORDER.index(current_group)
    if idx + 1 >= len(GROUP_ORDER):
        return  # this was the last group

    next_group = GROUP_ORDER[idx + 1]
    url = f"{base_url}/api/scan?group={next_group}"
    req = urllib.request.Request(url, method="POST")
    if cron_secret:
        req.add_header("Authorization", f"Bearer {cron_secret}")

    def _fire():
        try:
            urllib.request.urlopen(req, timeout=3)
        except Exception as e:
            # Expected: we're not waiting for the response, a timeout here
            # just means we didn't wait around -- the next group's own
            # invocation continues independently of this one.
            print(f"[scan] triggered next group '{next_group}' (fire-and-forget): {e}")

    threading.Thread(target=_fire, daemon=True).start()


def handler(request):
    """Vercel Python runtime entry point."""
    cron_secret = os.environ.get("CRON_SECRET")
    if cron_secret:
        auth_header = request.headers.get("Authorization", "")
        if auth_header != f"Bearer {cron_secret}":
            return {"statusCode": 401, "body": json.dumps({"error": "unauthorized"})}

    # Which group to run -- Vercel Cron always hits this with no query
    # param, so default to the first group; the chain triggers the rest.
    group = request.args.get("group", GROUP_ORDER[0]) if hasattr(request, "args") else GROUP_ORDER[0]
    if group not in GROUP_RUNNERS:
        return {"statusCode": 400, "body": json.dumps({"error": f"unknown group '{group}'"})}

    try:
        result = GROUP_RUNNERS[group]()

        # Chain to the next group before returning, so the full scan
        # completes across multiple short invocations instead of one
        # long one that would exceed Hobby's 10s cap.
        host = request.headers.get("host", "")
        if host:
            _trigger_next_group(f"https://{host}", group, cron_secret)

        result["group"] = group
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(result),
        }
    except Exception as e:
        print(f"[scan:{group}] FATAL: {e}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(e), "group": group}),
        }
