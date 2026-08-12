# Job Scraper (Vercel + Supabase rebuild)

Hardware/EE job scraper. Scans company career pages every 6 hours, filters
for entry-level analog/mixed-signal/hardware relevance, alerts you on
Telegram for new matches.

## Architecture

- **Vercel Cron** triggers `/api/scan` every 6 hours
- **Fetchers** pull jobs from 4 different ATS API shapes:
  - Greenhouse / Lever / Comeet (`lib/fetchers.py`) — simple GET APIs
  - Workday (`lib/workday_fetcher.py`) — POST + pagination, title-only list
    then detail-fetch for keyword survivors
  - Oracle Cloud HCM (`lib/oracle_cloud_fetcher.py`) — Texas Instruments
- **Filters** (`lib/filters.py`) — hardware/EE keyword match + rejects
  senior-level titles and high years-of-experience requirements
- **Supabase Postgres** (`lib/storage.py`) — dedup across runs, replaces
  the original SQLite (serverless has no persistent disk)
- **Claude API** (`lib/relevance.py`) — scores survivors against your
  background, only alerts on score >= 7
- **Telegram** (`lib/notify.py`) — push notification per relevant job

## Company coverage

See `lib/companies.py` for the full list and inline notes on what's
verified vs. what still needs checking.

**Confirmed working:**
- Greenhouse: Innoviz, Valens, Arbe Robotics
- Lever: Wiliot, Mobileye (EU subdomain)
- Comeet: Tower Semiconductor, Elbit Systems, Nova, Camtek, Vayyar,
  NextSilicon, INSIGHTEC
- Workday: Intel, Nvidia, Qualcomm, Marvell, Applied Materials, Analog Devices
- Oracle Cloud: Texas Instruments

**Known gaps (need more research before adding):**
- Hailo — custom career portal, no public JSON API found
- CEVA, DSP Group, Sony Semi Israel, Trieye, Xsight Labs, SolarEdge,
  Ceragon, IAI, Rafael — ATS not yet verified
- Amazon (Annapurna Labs) — uses amazon.jobs, different system entirely,
  not yet wired in

## Setup

### 1. Supabase (do this on your phone, browser is fine)

1. Create a free project at supabase.com
2. Go to SQL Editor → New query → paste contents of `supabase_schema.sql` → Run
3. Go to Project Settings → API → copy the **Project URL** and the
   **service_role key** (NOT the anon/public key — this runs server-side
   and needs write access)

### 2. Telegram bot (if you don't already have one from the original version)

1. Message @BotFather on Telegram → `/newbot` → follow prompts → copy the token
2. Message your new bot anything, then visit
   `https://api.telegram.org/bot<TOKEN>/getUpdates` to find your `chat_id`

### 3. Push this code to GitHub

From a computer (this part is painful on mobile):

```bash
cd job_scraper_vercel
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/<you>/job-scraper.git
git push -u origin main
```

### 4. Deploy to Vercel

1. vercel.com → New Project → import the GitHub repo
2. Before first deploy, add environment variables (Settings → Environment
   Variables), using `.env.example` as the list:
   - `ANTHROPIC_API_KEY`
   - `SUPABASE_URL`
   - `SUPABASE_KEY`
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
   - `CRON_SECRET` (make up any random string)
3. Deploy

Vercel Cron will start hitting `/api/scan` on the schedule in `vercel.json`
(every 6 hours by default — adjust the cron expression there if you want
a different cadence; free tier supports cron but check current Vercel
plan limits on invocation frequency before relying on it).

### 5. Test manually

```bash
curl -X POST https://<your-project>.vercel.app/api/scan \
  -H "Authorization: Bearer <your CRON_SECRET>"
```

Check the Vercel function logs (Deployments → your deployment → Functions
→ scan) to see the fetch/filter/relevance counts per run.

## Adding more companies

- Greenhouse/Lever/Comeet: add an entry to `COMPANIES` in `lib/companies.py`
- Workday: add an entry to `WORKDAY_COMPANIES` — you need the `tenant`,
  `wd_host` (e.g. `wd1`, `wd5`, `wd12` — varies per company), and `site`
  name, found by visiting the company's careers page and reading the
  `myworkdayjobs.com` URL
- Oracle Cloud: add an entry to `ORACLE_CLOUD_COMPANIES`
- Something else entirely (custom portal like Hailo): needs a new fetcher
  module, no shortcut — inspect the site's network requests for a JSON API
  first before assuming you need to scrape HTML
