"""
AI relevance check using the Claude API.
Scores each pre-filtered job against the candidate's background and returns
only jobs above a relevance threshold, with a short reason attached.
"""

import os
import json
import anthropic

CANDIDATE_PROFILE = """
Final-year Electrical Engineering student at the Technion (Viterbi Faculty
of ECE), specializing in analog/mixed-signal IC design, expected graduation
early 2027. Works in a VLSI lab on a Y-Flash-based Time-Domain In-Memory
Computing ANN accelerator, designing and characterizing analog/mixed-signal
circuit blocks (e.g. LVR for a Voltage-to-Time Converter in CMOS 180nm).
Strong in Cadence Virtuoso, Spectre, Synopsys Design Vision, Cadence Innovus,
gm/ID sizing methodology. Coursework: Analog Circuit Design (100), Physical
Principles of Semiconductor Devices, Electronic Circuits. Looking for
entry-level / new-grad roles: analog IC design, mixed-signal, post-silicon
validation, hardware/embedded, chip design student positions. NOT interested
in senior roles, pure software/SDE roles, or roles requiring 4+ years
experience.
"""

SYSTEM_PROMPT = f"""You are screening job postings for this candidate:
{CANDIDATE_PROFILE}

For each job, respond with ONLY a JSON object (no markdown, no preamble):
{{"relevant": true/false, "score": 0-10, "reason": "one short sentence"}}

Score 7+ only if this is a genuinely strong fit for an entry-level EE/analog/
hardware candidate. Be strict -- reject senior roles, unrelated software
roles, and roles clearly requiring years of specialized experience the
candidate wouldn't have."""


def _get_client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


def score_job(client: anthropic.Anthropic, job: dict) -> dict:
    prompt = f"Title: {job['title']}\nCompany: {job['company']}\nLocation: {job['location']}\nDescription: {job['description'][:2000]}"

    try:
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=200,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        text = resp.content[0].text.strip()
        text = text.replace("```json", "").replace("```", "").strip()
        result = json.loads(text)
        return {
            "relevant": bool(result.get("relevant", False)),
            "score": int(result.get("score", 0)),
            "reason": result.get("reason", ""),
        }
    except Exception as e:
        print(f"[relevance] scoring failed for {job.get('title')}: {e}")
        # fail open with a low score rather than crashing the whole run
        return {"relevant": False, "score": 0, "reason": f"scoring error: {e}"}


def filter_by_relevance(jobs: list[dict], min_score: int = 7) -> list[dict]:
    if not jobs:
        return []

    client = _get_client()
    results = []
    for job in jobs:
        verdict = score_job(client, job)
        if verdict["relevant"] and verdict["score"] >= min_score:
            job = {**job, "relevance_score": verdict["score"], "relevance_reason": verdict["reason"]}
            results.append(job)
    return results
