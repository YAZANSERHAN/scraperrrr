"""
Target companies for the job scraper.
ats: one of "greenhouse", "lever", "comeet"
slug: identifier used in that ATS's public API URL

VERIFIED = confirmed working slug pattern.
Everything below is either previously verified or newly confirmed (NextSilicon).

TO ADD MORE COMPANIES (e.g. Intel, Qualcomm, Elbit, IAI, Rafael, Mobileye):
Most large multinationals and defense companies run on Workday, iCIMS, or
custom SAP SuccessFactors portals -- NOT Greenhouse/Lever/Comeet. They need
a separate scraper module (see workday.py stub below) since Workday has no
single universal public API pattern; each board must be wired in individually
once you find the exact tenant URL (usually <company>.wd1.myworkdayjobs.com/...).

HOW TO FIND A SLUG YOURSELF:
- Greenhouse: boards.greenhouse.io/<SLUG> or job-boards.greenhouse.io/<SLUG>
- Lever: jobs.lever.co/<SLUG>
- Comeet: comeet.com/jobs/<SLUG>/... (check page source for "comeet.com/careers-api")
"""

COMPANIES = [
    # ---- Greenhouse ----
    {"name": "Wix", "ats": "greenhouse", "slug": "wix"},
    {"name": "monday.com", "ats": "greenhouse", "slug": "monday"},
    {"name": "Redis", "ats": "greenhouse", "slug": "redislabs"},
    {"name": "Riskified", "ats": "greenhouse", "slug": "riskified"},
    {"name": "Fiverr", "ats": "greenhouse", "slug": "fiverr"},
    {"name": "Papaya Global", "ats": "greenhouse", "slug": "papayaglobal"},
    {"name": "Melio", "ats": "greenhouse", "slug": "melio"},
    {"name": "Innoviz Technologies", "ats": "greenhouse", "slug": "innoviz"},
    {"name": "Arbe Robotics", "ats": "greenhouse", "slug": "arberobotics"},
    {"name": "Valens Semiconductor", "ats": "greenhouse", "slug": "valens"},

    # ---- Lever ----
    {"name": "Wiliot", "ats": "lever", "slug": "wiliot"},
    {"name": "Via Transportation", "ats": "lever", "slug": "ridewithvia"},

    # ---- Comeet ----
    {"name": "Tower Semiconductor", "ats": "comeet", "slug": "towersemi"},
    {"name": "INSIGHTEC", "ats": "comeet", "slug": "insightec"},
    {"name": "Camtek", "ats": "comeet", "slug": "camtek"},
    {"name": "Nova Ltd", "ats": "comeet", "slug": "nova"},
    {"name": "Ramon.Space", "ats": "comeet", "slug": "ramon.space"},
    {"name": "Elbit Systems", "ats": "comeet", "slug": "elbitsystems"},
    {"name": "Orbotech / KLA Israel", "ats": "comeet", "slug": "kla"},
    {"name": "Vayyar Imaging", "ats": "comeet", "slug": "vayyar"},
    {"name": "NextSilicon", "ats": "comeet", "slug": "nextsilicon"},

    # ---- Lever (non-default subdomain) ----
    {"name": "Mobileye", "ats": "lever", "slug": "mobileye", "lever_subdomain": "eu"},

    # NOTE: The following are known EE/hardware-relevant companies but their
    # ATS/slug is NOT YET VERIFIED. Do not add blindly -- confirm the slug
    # resolves before uncommenting, or a bad slug will just silently return
    # 0 jobs.
    #
    # Unverified ATS -- check before adding:
    #   Hailo (custom portal, no public JSON API found -- hailo.ai/company-overview/careers/),
    #   CEVA, DSP Group, Sony Semiconductor Israel (Altair), Trieye,
    #   Xsight Labs, SolarEdge, Ceragon Networks, Onto Innovation Israel,
    #   Qualitau, SemiConductor Devices (SCD), Amazon Annapurna Labs (Amazon
    #   uses its own amazon.jobs system, not Greenhouse/Lever/Comeet),
    #   Israel Aerospace Industries (IAI), Rafael Advanced Defense Systems
]


# ---------------------------------------------------------------------------
# Workday companies (require workday_fetcher.py, different API shape than
# Greenhouse/Lever/Comeet: POST request to a tenant-specific /wday/cxs/ URL).
# tenant  = the subdomain before .myworkdayjobs.com (e.g. "intel" -> intel.wd1...)
# wd_host = the wdN.myworkdayjobs.com host, varies per company
# site    = the career site name in the URL path (varies per company)
# ---------------------------------------------------------------------------
WORKDAY_COMPANIES = [
    {"name": "Intel", "tenant": "intel", "wd_host": "wd1", "site": "External"},
    {"name": "Nvidia", "tenant": "nvidia", "wd_host": "wd5", "site": "NVIDIAExternalCareerSite"},
    {"name": "Qualcomm", "tenant": "qualcomm", "wd_host": "wd12", "site": "External"},
    {"name": "Marvell", "tenant": "marvell", "wd_host": "wd1", "site": "MarvellCareers"},
    {"name": "Applied Materials", "tenant": "amat", "wd_host": "wd1", "site": "External"},
    {"name": "Analog Devices", "tenant": "analogdevices", "wd_host": "wd1", "site": "External"},

    # NOTE: verify location filtering per company once running -- Workday
    # returns ALL global jobs by default; without a location facet you'll
    # get roles from every country the company hires in. See workday_fetcher.py
    # for how the location filter is applied (or left off, with the
    # relevance-check step relying on the job's returned location text
    # to reject non-Israel roles instead).
]

# ---------------------------------------------------------------------------
# Oracle Cloud HCM companies (yet another different API shape).
# ---------------------------------------------------------------------------
ORACLE_CLOUD_COMPANIES = [
    {"name": "Texas Instruments", "host": "edbz.fa.us2.oraclecloud.com", "site_number": "CX"},
]
