"""
Clara Pipeline - Prompt Generator
Converts Account Memo JSON -> Retell Agent Draft Spec (JSON)
"""

import json
import sys
from datetime import datetime
from pathlib import Path


# ─────────────────────────────────────────────
# VOICE / STYLE DEFAULTS
# ─────────────────────────────────────────────

VOICE_STYLE = {
    "voice_id": "elevenlabs-rachel",   # Warm, professional female
    "speed": 1.0,
    "interruption_sensitivity": "medium",
    "language": "en-US"
}


# ─────────────────────────────────────────────
# PROMPT BUILDER
# ─────────────────────────────────────────────

def format_hours(bh: dict) -> str:
    days = ", ".join(bh.get("days", [])) or "Monday through Friday"
    start = bh.get("start") or "08:00"
    end = bh.get("end") or "17:00"
    tz = bh.get("timezone") or "your local time"
    return f"{days}, {start}–{end} {tz}"


def build_emergency_list(emergency_def: list) -> str:
    if not emergency_def:
        return "active sprinkler leak, fire alarm activation, fire suppression discharge, active fire, flooding, or any situation threatening life safety"
    return ", ".join(emergency_def)


def build_routing_instructions(routing: dict) -> str:
    primary = routing.get("primary_contact")
    order = routing.get("order", [])
    fallback = routing.get("fallback")
    timeout = routing.get("timeout_seconds") or 60

    lines = []
    if primary:
        lines.append(f"1. Attempt transfer to primary on-call: {primary} (wait up to {timeout} seconds)")
    if order and len(order) > 1:
        for i, contact in enumerate(order[1:], 2):
            lines.append(f"{i}. If no answer, try: {contact}")
    if fallback:
        lines.append(f"Final fallback: {fallback}")
    else:
        lines.append("Final fallback: Apologize and assure the caller that an on-call technician will call back within 15 minutes")

    return "\n".join(lines) if lines else "Attempt to transfer to the on-call technician. If unavailable, assure caller of rapid callback."


def build_system_prompt(memo: dict) -> str:
    company = memo.get("company_name") or "our company"
    bh = memo.get("business_hours", {})
    hours_str = format_hours(bh)
    emergency_list = build_emergency_list(memo.get("emergency_definition", []))
    services = ", ".join(memo.get("services_supported", [])) or "fire protection, inspection, and service requests"
    routing = memo.get("emergency_routing_rules", {})
    routing_instructions = build_routing_instructions(routing)
    transfer_timeout = memo.get("call_transfer_rules", {}).get("timeout_seconds") or 60
    on_fail_msg = (
        memo.get("call_transfer_rules", {}).get("on_fail_message") or
        "I was unable to reach the on-call technician right now, but I have logged your information and someone will call you back within 15 minutes."
    )
    integration_notes = ""
    constraints = memo.get("integration_constraints", [])
    if constraints:
        integration_notes = "\n\nSYSTEM NOTES (internal, never mention to caller):\n" + "\n".join(f"- {c}" for c in constraints)

    prompt = f"""You are Clara, a professional and empathetic AI voice assistant for {company}.
Your role is to handle inbound calls efficiently, route emergencies immediately, and ensure every caller feels heard and helped.

BUSINESS INFORMATION:
- Company: {company}
- Services: {services}
- Business Hours: {hours_str}

CRITICAL RULES:
- Never mention that you are an AI or a bot unless directly asked. If asked, confirm honestly.
- Never mention "function calls", "tool calls", "routing logic", or internal system processes to the caller.
- Do not ask unnecessary questions. Collect only what is needed for routing and dispatch.
- Always be warm, calm, and professional — especially during emergencies.
- Never put an emergency caller on hold without explanation.

═══════════════════════════════════════════
DURING BUSINESS HOURS FLOW
═══════════════════════════════════════════

Step 1 – GREETING:
Say: "Thank you for calling {company}. This is Clara. How can I help you today?"

Step 2 – UNDERSTAND PURPOSE:
Listen to why they are calling. Classify as:
  - Emergency (see emergency definition below)
  - Non-emergency service request
  - Inspection scheduling
  - General inquiry

Step 3 – COLLECT CALLER INFO:
Say: "I'd like to make sure I get you to the right person. May I have your name and the best callback number?"
Collect:
  - Full name
  - Phone number

Step 4 – ROUTE / TRANSFER:
For emergencies → Follow EMERGENCY ROUTING (see below).
For non-emergency → Transfer to the appropriate office staff or scheduler.
Say before transferring: "Let me connect you with the right person. Please hold for just a moment."

Step 5 – IF TRANSFER FAILS (after {transfer_timeout} seconds):
Say: "{on_fail_msg}"
Then log: caller name, number, call purpose, and timestamp.

Step 6 – WRAP UP:
Say: "Is there anything else I can help you with today?"
If no: "Thank you for calling {company}. Have a great day. Goodbye!"

═══════════════════════════════════════════
AFTER HOURS FLOW
═══════════════════════════════════════════

Step 1 – GREETING:
Say: "Thank you for calling {company}. You've reached us outside of our regular business hours, which are {hours_str}. This is Clara. How can I help you?"

Step 2 – UNDERSTAND PURPOSE:
Listen and classify as emergency or non-emergency.

Step 3 – CONFIRM EMERGENCY STATUS:
If the situation sounds urgent, ask: "Is this an emergency situation requiring immediate attention tonight?"

EMERGENCY DEFINITION — treat as emergency if caller describes:
{emergency_list}

Step 4A – IF EMERGENCY:
Say: "I understand — I'm going to connect you with our on-call team right away. I just need a few quick details."
Immediately collect:
  1. Full name
  2. Callback phone number
  3. Property address or location of the issue
  4. Brief description of the situation

Then attempt transfer:
{routing_instructions}

If transfer fails:
Say: "I was not able to reach the on-call technician directly, but your information has been logged as an emergency. A technician will call you back within 15 minutes. If the situation is life-threatening, please call 911 immediately."

Step 4B – IF NON-EMERGENCY:
Say: "I understand. Since this is not an emergency, I'll make sure someone from our team follows up with you during business hours."
Collect:
  - Full name
  - Phone number
  - Brief description of the issue
Confirm: "Thank you. Someone will reach out to you during our next business day. Is there a preferred time to call you back?"

Step 5 – WRAP UP:
Say: "Is there anything else I can help you with?"
If no: "Thank you for calling {company}. We'll be in touch. Stay safe. Goodbye!"{integration_notes}
"""
    return prompt.strip()


# ─────────────────────────────────────────────
# SPEC BUILDER
# ─────────────────────────────────────────────

def build_agent_spec(memo: dict, version: str = "v1") -> dict:
    company = memo.get("company_name") or "Clara Client"
    bh = memo.get("business_hours", {})

    spec = {
        "agent_name": f"{company} - Clara Agent",
        "version": version,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "source_account_id": memo.get("account_id"),
        "voice_style": VOICE_STYLE,
        "system_prompt": build_system_prompt(memo),
        "key_variables": {
            "timezone": bh.get("timezone"),
            "business_hours_start": bh.get("start"),
            "business_hours_end": bh.get("end"),
            "business_days": bh.get("days", []),
            "office_address": memo.get("office_address"),
            "emergency_routing_primary": memo.get("emergency_routing_rules", {}).get("primary_contact"),
            "emergency_routing_order": memo.get("emergency_routing_rules", {}).get("order", []),
            "transfer_timeout_seconds": memo.get("call_transfer_rules", {}).get("timeout_seconds") or 60
        },
        "tool_invocation_placeholders": {
            "_note": "These are internal tool calls. Never mention to caller.",
            "log_call": {
                "trigger": "on every call start",
                "params": ["caller_number", "timestamp", "call_type"]
            },
            "transfer_call": {
                "trigger": "when routing is needed",
                "params": ["destination_number", "caller_name", "call_purpose"]
            },
            "create_ticket": {
                "trigger": "after collecting non-emergency details",
                "params": ["caller_name", "phone", "issue_description", "priority"]
            }
        },
        "call_transfer_protocol": {
            "method": "warm_transfer",
            "announce_before_transfer": True,
            "announce_script": "Let me connect you with the right person. Please hold for just a moment.",
            "timeout_seconds": memo.get("call_transfer_rules", {}).get("timeout_seconds") or 60,
            "retries": memo.get("call_transfer_rules", {}).get("retries") or 1
        },
        "fallback_protocol": {
            "trigger": "transfer_fails",
            "action": "collect_and_assure",
            "script": memo.get("call_transfer_rules", {}).get("on_fail_message") or
                      "I was unable to reach the on-call team right now, but your information has been logged and someone will call you back within 15 minutes.",
            "log_required_fields": ["caller_name", "callback_number", "issue_description", "timestamp"]
        },
        "integration_constraints": memo.get("integration_constraints", []),
        "questions_or_unknowns": memo.get("questions_or_unknowns", [])
    }
    return spec


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python prompt_generator.py <memo_json_file> [version]")
        sys.exit(1)

    with open(sys.argv[1]) as f:
        memo = json.load(f)

    version = sys.argv[2] if len(sys.argv) > 2 else memo.get("version", "v1")
    spec = build_agent_spec(memo, version)
    print(json.dumps(spec, indent=2))
