Clara Pipeline
Zero-cost automation: Demo Call → Retell Agent Draft → Onboarding Updates → Agent v2

What This Is
A two-stage pipeline that converts raw call transcripts into deployable Retell AI voice agent configurations.

Demo Transcript  →  [Pipeline A]  →  Account Memo v1  +  Agent Spec v1
Onboarding Input →  [Pipeline B]  →  Account Memo v2  +  Agent Spec v2  +  Changelog
Architecture
clara-pipeline/
├── scripts/
│   ├── extractor.py          # Transcript → structured Account Memo JSON
│   ├── prompt_generator.py   # Account Memo → Retell Agent Spec + system prompt
│   ├── version_manager.py    # v1 → v2 patch, diff, conflict detection
│   └── pipeline.py           # Main orchestrator (CLI + batch runner)
├── workflows/
│   ├── pipeline_a_demo_to_v1.json     # n8n workflow export
│   └── pipeline_b_onboarding_to_v2.json
├── data/
│   ├── transcripts/          # Input transcripts (demo + onboarding)
│   └── dataset_manifest.json # Batch runner config
├── outputs/
│   └── accounts/
│       └── <account_id>/
│           ├── v1/
│           │   ├── account_memo.json
│           │   ├── agent_spec.json
│           │   └── transcript.txt
│           └── v2/
│               ├── account_memo.json
│               └── agent_spec.json
├── changelog/
│   ├── <account_id>_changes.json
│   └── <account_id>_changes.md
├── dashboard.html            # Visual diff viewer + account explorer
└── README.md
Quick Start
Prerequisites
Python 3.11+
(Optional) Anthropic API key for LLM-enhanced extraction
Run a single account
# Pipeline A: Demo call → v1
python3 scripts/pipeline.py demo data/transcripts/acct_001_demo.txt acct_001

# Pipeline B: Onboarding → v2
python3 scripts/pipeline.py onboard data/transcripts/acct_001_onboarding.txt acct_001

# With LLM enhancement (optional, uses Claude API)
export ANTHROPIC_API_KEY=your_key_here
python3 scripts/pipeline.py demo data/transcripts/acct_001_demo.txt acct_001 --api-key $ANTHROPIC_API_KEY
Run the full batch (all 5 accounts)
python3 scripts/pipeline.py batch data/dataset_manifest.json
Onboarding form input (structured JSON)
python3 scripts/pipeline.py onboard data/forms/acct_001_form.json acct_001 --source onboarding_form
Data Flow
Pipeline A (Demo Call → v1)
Ingest: Read transcript from .txt or .json
Normalize: Assign account_id, detect format
Extract: Rule-based extraction (zero-cost) or LLM via Claude API
Extracts: business hours, emergency definitions, routing rules, integration constraints
Flags unknowns explicitly — never hallucinated
Generate: Build system prompt + Retell Agent Spec JSON
Store: Save v1/account_memo.json and v1/agent_spec.json
Log: Report unknowns, warnings
Pipeline B (Onboarding → v2)
Load: Read existing v1 memo for the account
Parse: Detect if input is structured form or transcript
Extract: Pull configuration updates
Merge: Smart merge (patch wins, null doesn't overwrite existing data)
Conflict detection: Flags contradictions (e.g., timezone changed)
Resolve unknowns: Checks if v2 data resolves v1 unknowns
Generate: Rebuild agent spec at v2
Changelog: JSON + Markdown diff files
Extraction Logic
The extractor uses two modes:

Mode 1: Rule-based (Zero Cost)
Pure regex + keyword matching. No API calls needed. Works well for:

Business hours (day patterns, time patterns)
Timezone detection
Emergency keywords
Phone number extraction
Integration constraint patterns
Mode 2: LLM-enhanced (Claude API)
When ANTHROPIC_API_KEY is set, uses claude-sonnet-4-20250514 with a structured extraction prompt. Falls back to rule-based if API fails.

The system never hallucinate missing data. All unknown fields are:

Left as null in the memo
Listed in questions_or_unknowns
Output Formats
Account Memo JSON
{
  "account_id": "acct_001",
  "company_name": "Patriot Fire Protection",
  "version": "v1",
  "business_hours": { "days": [...], "start": "07:00", "end": "17:00", "timezone": "America/New_York" },
  "emergency_definition": ["active sprinkler flow", "fire alarm activation"],
  "emergency_routing_rules": { "primary_contact": null, "order": [], "timeout_seconds": 60 },
  "integration_constraints": ["Never create sprinkler jobs in ServiceTrade automatically"],
  "questions_or_unknowns": ["Emergency contact phone number not provided"],
  ...
}
Agent Spec JSON (Retell-ready)
{
  "agent_name": "Patriot Fire Protection - Clara Agent",
  "version": "v1",
  "voice_style": { "voice_id": "elevenlabs-rachel", "speed": 1.0 },
  "system_prompt": "...",
  "key_variables": { "timezone": "America/New_York", ... },
  "call_transfer_protocol": { "timeout_seconds": 60, ... },
  "fallback_protocol": { "trigger": "transfer_fails", "script": "..." }
}
Changelog (Markdown)
See changelog/<account_id>_changes.md — human-readable diff with:

Field-level changes
Conflict resolutions
Unknowns resolved vs. remaining
n8n Workflow Setup
Option 1: Local Docker
docker run -it --rm \
  -p 5678:5678 \
  -e N8N_BASIC_AUTH_ACTIVE=true \
  -v ~/.n8n:/home/node/.n8n \
  n8nio/n8n
Option 2: n8n Cloud (free tier)
Sign up at n8n.io — free tier supports the workflow.

Import workflows
Open n8n UI at http://localhost:5678
Click Import → upload workflows/pipeline_a_demo_to_v1.json
Set environment variable: ANTHROPIC_API_KEY
Activate workflow
Webhook endpoints (n8n)
Pipeline A: POST /webhook/clara/demo-call — body: { account_id, transcript }
Pipeline B: POST /webhook/clara/onboarding — body: { account_id, transcript } or structured form
Retell Integration
If Retell free tier allows API access:
curl -X POST https://api.retellai.com/create-agent \
  -H "Authorization: Bearer YOUR_RETELL_KEY" \
  -H "Content-Type: application/json" \
  -d @outputs/accounts/acct_001/v2/agent_spec.json
Manual import steps (if API not available on free tier):
Open app.retellai.com
Create New Agent
Copy system_prompt from agent_spec.json → paste into "System Prompt" field
Set voice to match voice_style.voice_id
Configure call transfer numbers from key_variables
Set timeout from call_transfer_protocol.timeout_seconds
Dashboard
Open dashboard.html in any browser (no server needed).

Features:

Account overview with v1/v2 status
Toggle between v1 and v2 configurations
Full system prompt viewer with copy button
Visual diff viewer (v1 → v2 changes)
Unknown fields highlighted per version
Integration constraint warnings
Dataset Manifest
To run on your own dataset, edit data/dataset_manifest.json:

{
  "accounts": [
    {
      "account_id": "your_acct_id",
      "demo_transcript": "path/to/demo.txt",
      "onboarding_input": "path/to/onboarding.txt",
      "onboarding_source": "onboarding_call"
    }
  ]
}
Accepted onboarding_source values: onboarding_call, onboarding_form

For form submissions, the JSON must contain at least one of: business_hours, emergency_definition, company_name.

Idempotency
Running the pipeline twice on the same account:

Pipeline A: Overwrites v1 outputs with identical result (no duplication)
Pipeline B: Overwrites v2 outputs with latest patch applied
Changelog is regenerated each time, timestamped
Known Limitations
Rule-based extraction accuracy: Without LLM, complex phrasing may be missed. Explicit named fields are captured reliably; implicit logic (e.g., conditional routing rules) may need manual review.
Phone number extraction: Captured from transcript text; if numbers are spoken word-by-word ("four-oh-four...") they may not be captured by the regex.
No audio transcription built-in: The pipeline assumes text transcripts as input. For audio files, run Whisper locally (free) first.
n8n file storage: Local Docker n8n uses /tmp for file I/O. For production, replace file nodes with Supabase or S3 nodes.
What I Would Improve with Production Access
Retell API integration: Auto-create/update agents via API instead of manual copy-paste
Supabase storage: Replace local JSON files with a proper database for account lookup, history, and search
Audio transcription: Integrate Whisper as a preprocessing step for audio files
Async batch processing: Queue-based batch processing with progress tracking
Human review UI: Flag accounts with unresolved unknowns for review before agent activation
A/B testing support: Deploy v1 and v2 in parallel, compare performance metrics
Webhook callbacks: Notify client systems when v2 agent is deployed
Evaluation Compliance
Requirement	Status
Pipeline A: demo → v1	✅
Pipeline B: onboarding → v2	✅
5 demo + 5 onboarding pairs processed	✅
Zero spend	✅ Rule-based by default; LLM optional with own key
Account Memo JSON schema	✅ All required fields
Retell Agent Spec JSON	✅ With system prompt, key variables, transfer/fallback
Versioning + changelog	✅ JSON + Markdown
n8n workflow export	✅ Both pipelines
No hallucination	✅ Explicit unknowns, null for missing
Business hours + after-hours flows	✅ In every generated prompt
Idempotent	✅
Dashboard / diff viewer	✅
