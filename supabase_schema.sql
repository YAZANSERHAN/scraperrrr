-- Run this once in the Supabase SQL editor (Project -> SQL Editor -> New query)

create table if not exists seen_jobs (
  external_id text primary key,
  company text,
  title text,
  url text,
  relevance_score int,
  first_seen_at timestamptz default now()
);

-- Optional: index for querying by company later (e.g. "how many jobs seen per company")
create index if not exists idx_seen_jobs_company on seen_jobs (company);
