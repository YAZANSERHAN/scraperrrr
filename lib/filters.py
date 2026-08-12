"""
Two-stage cheap filtering before the AI relevance check:
1. keyword_filter -- does this look like a hardware/EE role at all?
2. experience_filter -- does this look entry-level / new-grad friendly?
"""

import re
from .keywords import HARDWARE_KEYWORDS, SENIOR_TITLE_MARKERS, YEARS_EXPERIENCE_PATTERN, MAX_ACCEPTABLE_YEARS


def keyword_filter(job: dict) -> bool:
    haystack = f"{job.get('title', '')} {job.get('description', '')}".lower()
    return any(kw in haystack for kw in HARDWARE_KEYWORDS)


def experience_filter(job: dict) -> bool:
    """Return True if the job PASSES (looks entry-level-friendly)."""
    title = job.get("title", "").lower()
    desc = job.get("description", "").lower()

    for marker in SENIOR_TITLE_MARKERS:
        if marker in title:
            return False

    years_found = [int(y) for y in re.findall(YEARS_EXPERIENCE_PATTERN, desc)]
    if years_found and min(years_found) > MAX_ACCEPTABLE_YEARS:
        # every years-requirement mentioned exceeds the threshold
        return False

    return True


def apply_filters(jobs: list[dict]) -> list[dict]:
    survivors = []
    for job in jobs:
        if not keyword_filter(job):
            continue
        if not experience_filter(job):
            continue
        survivors.append(job)
    return survivors
