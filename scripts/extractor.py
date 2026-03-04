"""
Clara Pipeline - Transcript Extractor
Converts raw call transcripts into structured Account Memo JSON
Uses rule-based extraction + Claude API (free via Anthropic API key)
"""

import json
import re
import os
import sys
from datetime import datetime
from pathlib import Path


# ─────────────────────────────────────────────
# SCHEMA
# ─────────────────────────────────────────────

def empty_account_memo(account_id: str, company_name: str = "") -> dict:
    return {
        "account_id": account_id,
        "company_name": company_name,
        "version": "v1",
        "created_at": datetime.utcnow().isoformat() + "Z",
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "business_hours": {
            "days": [],
            "start": None,
            "end": None,
            "timezone": None
        },
        "office_address": None,
        "services_supported": [],
        "emergency_definition": [],
        "emergency_routing_rules": {
            "primary_contact": None,
            "phone_tree": None,
            "order": [],
            "fallback": None,
            "timeout_seconds": None
        },
        "non_emergency_routing_rules": {
            "during_hours": None,
            "after_hours": None,
            "collect_details": True
        },
        "call_transfer_rules": {
            "timeout_seconds": None,
            "retries": None,
            "on_fail_message": None
        },
        "integration_constraints": [],
        "after_hours_flow_summary": None,
        "office_hours_flow_summary": None,
        "questions_or_unknowns": [],
        "notes": ""
    }


# ─────────────────────────────────────────────
# RULE-BASED EXTRACTORS (zero-cost fallback)
# ─────────────────────────────────────────────

TIMEZONE_PATTERNS = [
    (r'\bEST\b|\bEastern\b', 'America/New_York'),
    (r'\bCST\b|\bCentral\b', 'America/Chicago'),
    (r'\bMST\b|\bMountain\b', 'America/Denver'),
    (r'\bPST\b|\bPacific\b', 'America/Los_Angeles'),
    (r'\bAST\b|\bAtlantic\b', 'America/Halifax'),
]

DAY_PATTERNS = [
    'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday',
    'mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun',
    'weekdays', 'weekends', 'monday through friday', 'monday to friday',
    'monday-friday', 'mon-fri'
]

TIME_PATTERN = re.compile(
    r'\b(\d{1,2})(?::(\d{2}))?\s*(am|pm|AM|PM)\b'
)

EMERGENCY_KEYWORDS = [
    'sprinkler leak', 'sprinkler activation', 'fire alarm', 'fire suppression',
    'active fire', 'flooding', 'water flowing', 'system triggered',
    'alarm going off', 'building evacuation', 'life safety', 'smoke detector',
    'carbon monoxide', 'gas leak', 'immediate danger', 'injury', 'evacuation'
]

SERVICE_KEYWORDS = [
    'fire protection', 'sprinkler', 'fire alarm', 'suppression', 'inspection',
    'hvac', 'electrical', 'extinguisher', 'backflow', 'monitoring',
    'facility maintenance', 'alarm contractor', 'service trade'
]


def extract_timezone(text: str) -> str | None:
    for pattern, tz in TIMEZONE_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return tz
    return None


def extract_business_hours(text: str) -> dict:
    hours = {"days": [], "start": None, "end": None, "timezone": None}

    # Days
    text_lower = text.lower()
    if 'monday through friday' in text_lower or 'monday to friday' in text_lower or 'mon-fri' in text_lower or 'monday-friday' in text_lower:
        hours['days'] = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    elif 'weekdays' in text_lower:
        hours['days'] = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    else:
        found = []
        day_map = {
            'mon': 'Monday', 'tue': 'Tuesday', 'wed': 'Wednesday',
            'thu': 'Thursday', 'fri': 'Friday', 'sat': 'Saturday', 'sun': 'Sunday',
            'monday': 'Monday', 'tuesday': 'Tuesday', 'wednesday': 'Wednesday',
            'thursday': 'Thursday', 'friday': 'Friday', 'saturday': 'Saturday', 'sunday': 'Sunday'
        }
        for abbr, full in day_map.items():
            if re.search(r'\b' + abbr + r'\b', text_lower) and full not in found:
                found.append(full)
        hours['days'] = found

    # Times
    times = TIME_PATTERN.findall(text)
    parsed_times = []
    for h, m, period in times:
        hh = int(h)
        mm = int(m) if m else 0
        if period.lower() == 'pm' and hh != 12:
            hh += 12
        elif period.lower() == 'am' and hh == 12:
            hh = 0
        parsed_times.append(f"{hh:02d}:{mm:02d}")

    if len(parsed_times) >= 2:
        hours['start'] = parsed_times[0]
        hours['end'] = parsed_times[1]
    elif len(parsed_times) == 1:
        hours['start'] = parsed_times[0]

    hours['timezone'] = extract_timezone(text)
    return hours


def extract_services(text: str) -> list:
    found = []
    text_lower = text.lower()
    for kw in SERVICE_KEYWORDS:
        if kw in text_lower and kw not in found:
            found.append(kw)
    return found


def extract_emergencies(text: str) -> list:
    found = []
    text_lower = text.lower()
    for kw in EMERGENCY_KEYWORDS:
        if kw in text_lower and kw not in found:
            found.append(kw)
    return found


def extract_phone_numbers(text: str) -> list:
    pattern = re.compile(r'\b(\+?1[-.\s]?)?(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})\b')
    return [m.group(0).strip() for m in pattern.finditer(text)]


def extract_integration_constraints(text: str) -> list:
    constraints = []
    text_lower = text.lower()
    if 'never create' in text_lower or 'do not create' in text_lower:
        sentences = text.split('.')
        for s in sentences:
            if 'never create' in s.lower() or 'do not create' in s.lower():
                constraints.append(s.strip())
    if 'servicetrade' in text_lower or 'service trade' in text_lower:
        sentences = text.split('.')
        for s in sentences:
            if 'servicetrade' in s.lower() or 'service trade' in s.lower():
                c = s.strip()
                if c and c not in constraints:
                    constraints.append(c)
    return constraints


def extract_company_name(text: str) -> str:
    patterns = [
        r"(?:this is|calling from|we are|company is|company name is|I\'m with|I am with)\s+([A-Z][A-Za-z\s&,\.]+?)(?:\.|,|\n|and |we )",
        r"([A-Z][A-Za-z\s]+(?:Fire|Protection|Services|Systems|Solutions|Group|Co\.|Inc\.|LLC))",
    ]
    for p in patterns:
        m = re.search(p, text)
        if m:
            return m.group(1).strip()
    return ""


def rule_based_extract(transcript: str, account_id: str) -> dict:
    """Pure rule-based extraction - zero cost, zero LLM"""
    memo = empty_account_memo(account_id)
    memo['company_name'] = extract_company_name(transcript)
    memo['business_hours'] = extract_business_hours(transcript)
    memo['services_supported'] = extract_services(transcript)
    memo['emergency_definition'] = extract_emergencies(transcript)

    phones = extract_phone_numbers(transcript)
    if phones:
        memo['emergency_routing_rules']['primary_contact'] = phones[0]
        if len(phones) > 1:
            memo['emergency_routing_rules']['order'] = phones

    memo['integration_constraints'] = extract_integration_constraints(transcript)

    # Flag unknowns
    unknowns = []
    bh = memo['business_hours']
    if not bh['days']:
        unknowns.append("Business days not specified")
    if not bh['start'] or not bh['end']:
        unknowns.append("Business hours (start/end times) not specified")
    if not bh['timezone']:
        unknowns.append("Timezone not specified")
    if not memo['emergency_definition']:
        unknowns.append("Emergency triggers not defined")
    if not memo['emergency_routing_rules']['primary_contact']:
        unknowns.append("Emergency contact phone number not provided")
    if not memo['company_name']:
        unknowns.append("Company name unclear from transcript")

    memo['questions_or_unknowns'] = unknowns
    return memo


# ─────────────────────────────────────────────
# LLM-ENHANCED EXTRACTION (uses Claude API)
# ─────────────────────────────────────────────

def llm_extract(transcript: str, account_id: str, api_key: str) -> dict:
    """Uses Claude API for richer extraction"""
    import urllib.request

    system_prompt = """You are a configuration extraction assistant for Clara Answers, an AI voice agent platform.
Extract structured operational data from call transcripts. 
Return ONLY valid JSON matching this exact schema. Do not hallucinate. Leave fields null if not mentioned.

Schema:
{
  "company_name": string or null,
  "business_hours": {"days": [list], "start": "HH:MM" or null, "end": "HH:MM" or null, "timezone": "IANA string" or null},
  "office_address": string or null,
  "services_supported": [list of strings],
  "emergency_definition": [list of trigger descriptions],
  "emergency_routing_rules": {"primary_contact": string or null, "phone_tree": string or null, "order": [list], "fallback": string or null, "timeout_seconds": number or null},
  "non_emergency_routing_rules": {"during_hours": string or null, "after_hours": string or null},
  "call_transfer_rules": {"timeout_seconds": number or null, "retries": number or null, "on_fail_message": string or null},
  "integration_constraints": [list of strings],
  "after_hours_flow_summary": string or null,
  "office_hours_flow_summary": string or null,
  "questions_or_unknowns": [list of strings - only truly missing info],
  "notes": string
}"""

    payload = json.dumps({
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 2000,
        "system": system_prompt,
        "messages": [{"role": "user", "content": f"Extract data from this call transcript:\n\n{transcript}"}]
    }).encode()

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01"
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            raw = data['content'][0]['text']
            # Strip markdown fences if present
            raw = re.sub(r'^```json\s*', '', raw.strip())
            raw = re.sub(r'```$', '', raw.strip())
            extracted = json.loads(raw)

            memo = empty_account_memo(account_id)
            for key in extracted:
                if key in memo:
                    memo[key] = extracted[key]
            return memo
    except Exception as e:
        print(f"[WARN] LLM extraction failed: {e}. Falling back to rule-based.")
        return rule_based_extract(transcript, account_id)


# ─────────────────────────────────────────────
# MAIN EXTRACTION ENTRY POINT
# ─────────────────────────────────────────────

def extract_from_transcript(transcript: str, account_id: str, api_key: str = None) -> dict:
    if api_key:
        return llm_extract(transcript, account_id, api_key)
    return rule_based_extract(transcript, account_id)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python extractor.py <transcript_file> <account_id> [api_key]")
        sys.exit(1)

    transcript_path = sys.argv[1]
    account_id = sys.argv[2]
    api_key = sys.argv[3] if len(sys.argv) > 3 else os.environ.get("ANTHROPIC_API_KEY")

    with open(transcript_path) as f:
        transcript = f.read()

    result = extract_from_transcript(transcript, account_id, api_key)
    print(json.dumps(result, indent=2))
