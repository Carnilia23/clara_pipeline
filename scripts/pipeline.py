"""
Clara Pipeline - Main Orchestrator
Runs Pipeline A (Demo -> v1) and Pipeline B (Onboarding -> v2)
Batch-capable, idempotent, logged
"""

import json
import os
import sys
import shutil
import logging
from pathlib import Path
from datetime import datetime

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent))
from extractor import extract_from_transcript
from prompt_generator import build_agent_spec
from version_manager import apply_patch

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

BASE_DIR = Path(__file__).parent.parent
OUTPUTS_DIR = BASE_DIR / "outputs" / "accounts"
LOGS_DIR = BASE_DIR / "outputs" / "logs"
CHANGELOG_DIR = BASE_DIR / "changelog"

for d in [OUTPUTS_DIR, LOGS_DIR, CHANGELOG_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ─────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOGS_DIR / f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    ]
)
log = logging.getLogger("clara")


# ─────────────────────────────────────────────
# FILE I/O HELPERS
# ─────────────────────────────────────────────

def read_transcript(file_path: str) -> str:
    """Read transcript from .txt or .json file"""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Transcript not found: {file_path}")

    if path.suffix == ".json":
        with open(path) as f:
            data = json.load(f)
        # Accept {"transcript": "..."} or {"text": "..."} or raw string
        if isinstance(data, dict):
            return data.get("transcript") or data.get("text") or json.dumps(data)
        return str(data)
    else:
        with open(path) as f:
            return f.read()


def save_json(data: dict, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    log.info(f"Saved: {path}")


def load_json(path: Path) -> dict | None:
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return None


# ─────────────────────────────────────────────
# PIPELINE A: Demo Call -> v1 Assets
# ─────────────────────────────────────────────

def pipeline_a(transcript_file: str, account_id: str, api_key: str = None) -> dict:
    """
    Input: Demo call transcript
    Output: v1 account memo + v1 agent spec
    Idempotent: re-running overwrites with same result
    """
    log.info(f"[Pipeline A] Starting for account: {account_id}")

    # Read transcript
    transcript = read_transcript(transcript_file)
    log.info(f"[Pipeline A] Transcript loaded ({len(transcript)} chars)")

    # Extract structured memo
    memo = extract_from_transcript(transcript, account_id, api_key)
    memo["version"] = "v1"
    memo["_pipeline"] = "demo_call"
    memo["_source_file"] = str(transcript_file)

    # Generate agent spec
    spec = build_agent_spec(memo, "v1")

    # Save outputs
    out_dir = OUTPUTS_DIR / account_id / "v1"
    save_json(memo, out_dir / "account_memo.json")
    save_json(spec, out_dir / "agent_spec.json")

    # Save transcript copy
    shutil.copy2(transcript_file, out_dir / "transcript.txt")

    log.info(f"[Pipeline A] Complete. Output: {out_dir}")

    # Print summary
    unknowns = memo.get("questions_or_unknowns", [])
    if unknowns:
        log.warning(f"[Pipeline A] {len(unknowns)} unknowns flagged:")
        for u in unknowns:
            log.warning(f"  ? {u}")

    return {"memo": memo, "spec": spec, "output_dir": str(out_dir)}


# ─────────────────────────────────────────────
# PIPELINE B: Onboarding -> v2 Assets
# ─────────────────────────────────────────────

def pipeline_b(onboarding_input: str, account_id: str, api_key: str = None, source: str = "onboarding_call") -> dict:
    """
    Input: Onboarding call transcript or form JSON
    Output: v2 account memo + v2 agent spec + changelog
    """
    log.info(f"[Pipeline B] Starting for account: {account_id}")

    # Load existing v1 memo
    v1_path = OUTPUTS_DIR / account_id / "v1" / "account_memo.json"
    v1_memo = load_json(v1_path)
    if not v1_memo:
        raise FileNotFoundError(
            f"No v1 memo found for account {account_id}. Run Pipeline A first."
        )
    log.info("[Pipeline B] v1 memo loaded")

    # Determine input type: transcript or structured form?
    input_path = Path(onboarding_input)
    if input_path.suffix == ".json":
        # Check if it looks like a structured form vs a transcript JSON
        with open(input_path) as f:
            raw = json.load(f)
        if isinstance(raw, dict) and any(k in raw for k in ["business_hours", "emergency_definition", "company_name"]):
            # Structured form submission - use directly as patch
            log.info("[Pipeline B] Input detected as structured onboarding form")
            patch_data = raw
        else:
            # JSON-wrapped transcript
            log.info("[Pipeline B] Input detected as transcript JSON")
            transcript = raw.get("transcript") or raw.get("text") or json.dumps(raw)
            patch_data = extract_from_transcript(transcript, account_id, api_key)
    else:
        # Plain text transcript
        log.info("[Pipeline B] Input detected as plain transcript")
        transcript = read_transcript(onboarding_input)
        patch_data = extract_from_transcript(transcript, account_id, api_key)

    # Apply patch v1 -> v2
    v2_memo, changelog = apply_patch(v1_memo, patch_data, source=source)
    v2_spec = build_agent_spec(v2_memo, "v2")

    # Save outputs
    out_dir = OUTPUTS_DIR / account_id / "v2"
    save_json(v2_memo, out_dir / "account_memo.json")
    save_json(v2_spec, out_dir / "agent_spec.json")

    # Save changelog
    changelog_path = CHANGELOG_DIR / f"{account_id}_changes.json"
    save_json(changelog, changelog_path)

    # Also save a human-readable markdown changelog
    md_path = CHANGELOG_DIR / f"{account_id}_changes.md"
    write_changelog_md(changelog, md_path)

    log.info(f"[Pipeline B] Complete. Output: {out_dir}")
    log.info(f"[Pipeline B] Changelog: {changelog_path}")

    return {
        "v2_memo": v2_memo,
        "v2_spec": v2_spec,
        "changelog": changelog,
        "output_dir": str(out_dir)
    }


# ─────────────────────────────────────────────
# CHANGELOG MARKDOWN WRITER
# ─────────────────────────────────────────────

def write_changelog_md(changelog: dict, path: Path):
    lines = [
        f"# Changelog: {changelog.get('account_id')}",
        f"",
        f"**Transition:** {changelog.get('from_version')} → {changelog.get('to_version')}",
        f"**Source:** {changelog.get('patch_source')}",
        f"**Applied:** {changelog.get('applied_at')}",
        f"**Summary:** {changelog.get('summary')}",
        f"",
        f"## Changes",
        f"",
    ]

    changes = changelog.get("changes", [])
    if changes:
        for c in changes:
            field = c.get("field")
            old = c.get("old")
            new = c.get("new")
            ctype = c.get("type", "updated")
            lines.append(f"- **{field}** [{ctype}]")
            lines.append(f"  - Before: `{old}`")
            lines.append(f"  - After: `{new}`")
    else:
        lines.append("_No changes detected._")

    lines.extend([
        "",
        "## Conflicts",
        "",
    ])
    conflicts = changelog.get("conflicts", [])
    if conflicts:
        for c in conflicts:
            lines.append(f"- **{c.get('field')}**: Demo said `{c.get('demo_value')}`, onboarding said `{c.get('onboarding_value')}` → Resolution: {c.get('resolution')}")
    else:
        lines.append("_No conflicts detected._")

    lines.extend([
        "",
        "## Unknowns Resolved",
        "",
    ])
    resolved = changelog.get("unknowns_resolved", [])
    if resolved:
        for r in resolved:
            lines.append(f"- ✅ {r}")
    else:
        lines.append("_None resolved in this update._")

    lines.extend([
        "",
        "## Unknowns Remaining",
        "",
    ])
    remaining = changelog.get("unknowns_remaining", [])
    if remaining:
        for r in remaining:
            lines.append(f"- ❓ {r}")
    else:
        lines.append("_All unknowns resolved!_")

    with open(path, "w") as f:
        f.write("\n".join(lines))
    log.info(f"Saved markdown changelog: {path}")


# ─────────────────────────────────────────────
# BATCH RUNNER
# ─────────────────────────────────────────────

def run_batch(dataset_file: str, api_key: str = None):
    """
    Runs both pipelines over a dataset manifest JSON.
    
    Dataset format:
    {
      "accounts": [
        {
          "account_id": "acct_001",
          "demo_transcript": "path/to/demo.txt",
          "onboarding_input": "path/to/onboarding.txt"   // optional
        }
      ]
    }
    """
    with open(dataset_file) as f:
        dataset = json.load(f)

    results = []
    for account in dataset.get("accounts", []):
        account_id = account["account_id"]
        result = {"account_id": account_id, "status": {}}

        # Pipeline A
        demo_file = account.get("demo_transcript")
        if demo_file:
            try:
                pipeline_a(demo_file, account_id, api_key)
                result["status"]["pipeline_a"] = "success"
            except Exception as e:
                log.error(f"[Batch] Pipeline A failed for {account_id}: {e}")
                result["status"]["pipeline_a"] = f"failed: {e}"

        # Pipeline B
        onboarding_file = account.get("onboarding_input")
        if onboarding_file:
            try:
                source = account.get("onboarding_source", "onboarding_call")
                pipeline_b(onboarding_file, account_id, api_key, source)
                result["status"]["pipeline_b"] = "success"
            except Exception as e:
                log.error(f"[Batch] Pipeline B failed for {account_id}: {e}")
                result["status"]["pipeline_b"] = f"failed: {e}"

        results.append(result)

    # Save batch summary
    summary = {
        "run_at": datetime.utcnow().isoformat() + "Z",
        "total_accounts": len(results),
        "results": results
    }
    save_json(summary, LOGS_DIR / "batch_summary.json")
    log.info(f"[Batch] Complete. {len(results)} accounts processed.")
    return summary


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Clara Pipeline Orchestrator")
    subparsers = parser.add_subparsers(dest="command")

    # Pipeline A
    pa = subparsers.add_parser("demo", help="Run Pipeline A: Demo transcript -> v1")
    pa.add_argument("transcript", help="Path to demo call transcript")
    pa.add_argument("account_id", help="Account identifier")
    pa.add_argument("--api-key", default=os.environ.get("ANTHROPIC_API_KEY"))

    # Pipeline B
    pb = subparsers.add_parser("onboard", help="Run Pipeline B: Onboarding -> v2")
    pb.add_argument("input", help="Path to onboarding transcript or form JSON")
    pb.add_argument("account_id", help="Account identifier")
    pb.add_argument("--source", default="onboarding_call", choices=["onboarding_call", "onboarding_form"])
    pb.add_argument("--api-key", default=os.environ.get("ANTHROPIC_API_KEY"))

    # Batch
    pc = subparsers.add_parser("batch", help="Run batch over dataset manifest")
    pc.add_argument("dataset", help="Path to dataset manifest JSON")
    pc.add_argument("--api-key", default=os.environ.get("ANTHROPIC_API_KEY"))

    args = parser.parse_args()

    if args.command == "demo":
        result = pipeline_a(args.transcript, args.account_id, args.api_key)
        print(f"\n✅ Pipeline A complete. Outputs saved to: {result['output_dir']}")
    elif args.command == "onboard":
        result = pipeline_b(args.input, args.account_id, args.api_key, args.source)
        print(f"\n✅ Pipeline B complete. Outputs saved to: {result['output_dir']}")
    elif args.command == "batch":
        result = run_batch(args.dataset, args.api_key)
        print(f"\n✅ Batch complete. {result['total_accounts']} accounts processed.")
    else:
        parser.print_help()
