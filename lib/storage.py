"""
Postgres (Supabase) storage for deduplication across scraper runs.
Replaces the original SQLite implementation since Vercel serverless
functions have no persistent local disk.

Required env vars:
  SUPABASE_URL   -- e.g. https://xxxx.supabase.co
  SUPABASE_KEY   -- service_role key (NOT the anon key -- this runs server-side)

Table schema (create this once in the Supabase SQL editor):

  create table seen_jobs (
    external_id text primary key,
    company text,
    title text,
    url text,
    relevance_score int,
    first_seen_at timestamptz default now()
  );
"""

import os
from supabase import create_client, Client

_client: Client | None = None


def get_client() -> Client:
    global _client
    if _client is None:
        url = os.environ["SUPABASE_URL"]
        key = os.environ["SUPABASE_KEY"]
        _client = create_client(url, key)
    return _client


def filter_unseen(jobs: list[dict]) -> list[dict]:
    """Return only jobs whose external_id isn't already in seen_jobs."""
    if not jobs:
        return []

    client = get_client()
    ids = [j["external_id"] for j in jobs]

    # Supabase/Postgrest .in_() has practical limits; chunk to be safe
    seen_ids = set()
    chunk_size = 200
    for i in range(0, len(ids), chunk_size):
        chunk = ids[i:i + chunk_size]
        resp = client.table("seen_jobs").select("external_id").in_("external_id", chunk).execute()
        seen_ids.update(row["external_id"] for row in resp.data)

    return [j for j in jobs if j["external_id"] not in seen_ids]


def mark_seen(jobs: list[dict]) -> None:
    """Insert newly-alerted jobs into seen_jobs so they aren't re-alerted."""
    if not jobs:
        return

    client = get_client()
    rows = [
        {
            "external_id": j["external_id"],
            "company": j["company"],
            "title": j["title"],
            "url": j["url"],
            "relevance_score": j.get("relevance_score"),
        }
        for j in jobs
    ]
    # upsert to avoid crashing on rare race-condition duplicates
    client.table("seen_jobs").upsert(rows, on_conflict="external_id").execute()
