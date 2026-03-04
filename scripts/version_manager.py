"""
Clara Pipeline - Version Manager
Handles v1 -> v2 patching, change logging, conflict detection
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from copy import deepcopy


# ─────────────────────────────────────────────
# DEEP DIFF
# ─────────────────────────────────────────────

def deep_diff(old: dict, new: dict, path: str = "") -> list:
    """Returns list of change records"""
    changes = []
    all_keys = set(list(old.keys()) + list(new.keys()))

    for key in all_keys:
        current_path = f"{path}.{key}" if path else key
        old_val = old.get(key)
        new_val = new.get(key)

        if old_val == new_val:
            continue

        if isinstance(old_val, dict) and isinstance(new_val, dict):
            changes.extend(deep_diff(old_val, new_val, current_path))
        elif isinstance(old_val, list) and isinstance(new_val, list):
            if set(str(x) for x in old_val) != set(str(x) for x in new_val):
                changes.append({
                    "field": current_path,
                    "old": old_val,
                    "new": new_val,
                    "type": "list_updated"
                })
        else:
            if old_val is None and new_val is not None:
                change_type = "field_added"
            elif old_val is not None and new_val is None:
                change_type = "field_cleared"
            else:
                change_type = "field_updated"

            changes.append({
                "field": current_path,
                "old": old_val,
                "new": new_val,
                "type": change_type
            })

    return changes


# ─────────────────────────────────────────────
# CONFLICT DETECTOR
# ─────────────────────────────────────────────

def detect_conflicts(v1_memo: dict, patch_data: dict) -> list:
    """Flags cases where onboarding data contradicts demo data"""
    conflicts = []

    # Check business hours conflict
    if patch_data.get("business_hours") and v1_memo.get("business_hours"):
        old_tz = v1_memo["business_hours"].get("timezone")
        new_tz = patch_data["business_hours"].get("timezone")
        if old_tz and new_tz and old_tz != new_tz:
            conflicts.append({
                "field": "business_hours.timezone",
                "demo_value": old_tz,
                "onboarding_value": new_tz,
                "resolution": "onboarding_wins",
                "note": "Onboarding data takes precedence over demo assumptions"
            })

    return conflicts


# ─────────────────────────────────────────────
# SMART MERGE
# ─────────────────────────────────────────────

def smart_merge(base: dict, patch: dict) -> dict:
    """Deep merge - patch wins on conflicts, lists are replaced not appended"""
    result = deepcopy(base)

    for key, val in patch.items():
        if val is None:
            continue  # Don't overwrite existing data with null
        if isinstance(val, dict) and isinstance(result.get(key), dict):
            result[key] = smart_merge(result[key], val)
        elif isinstance(val, list):
            if val:  # Only replace if new list is non-empty
                result[key] = val
        else:
            result[key] = val

    return result


# ─────────────────────────────────────────────
# APPLY PATCH (v1 -> v2)
# ─────────────────────────────────────────────

def apply_patch(v1_memo: dict, onboarding_data: dict, source: str = "onboarding_call") -> tuple[dict, dict]:
    """
    Returns (v2_memo, changelog)
    """
    conflicts = detect_conflicts(v1_memo, onboarding_data)
    v2_memo = smart_merge(v1_memo, onboarding_data)

    # Metadata
    v2_memo["version"] = "v2"
    v2_memo["updated_at"] = datetime.utcnow().isoformat() + "Z"

    # Merge unknowns - remove any that are now resolved
    old_unknowns = set(v1_memo.get("questions_or_unknowns", []))
    new_unknowns = set(onboarding_data.get("questions_or_unknowns", []))

    # Check which old unknowns are resolved by new data
    resolved = []
    still_open = []
    for u in old_unknowns:
        resolved_flag = False
        if "timezone" in u.lower() and v2_memo.get("business_hours", {}).get("timezone"):
            resolved_flag = True
        elif "business hour" in u.lower() and v2_memo.get("business_hours", {}).get("start"):
            resolved_flag = True
        elif "emergency" in u.lower() and v2_memo.get("emergency_definition"):
            resolved_flag = True
        elif "phone" in u.lower() or "contact" in u.lower():
            if v2_memo.get("emergency_routing_rules", {}).get("primary_contact"):
                resolved_flag = True
        elif "company" in u.lower() and v2_memo.get("company_name"):
            resolved_flag = True

        if resolved_flag:
            resolved.append(u)
        else:
            still_open.append(u)

    v2_memo["questions_or_unknowns"] = list(set(still_open) | (new_unknowns - old_unknowns))

    # Build changelog
    changes = deep_diff(
        {k: v for k, v in v1_memo.items() if k not in ("updated_at", "version")},
        {k: v for k, v in v2_memo.items() if k not in ("updated_at", "version")}
    )

    changelog = {
        "account_id": v1_memo.get("account_id"),
        "from_version": "v1",
        "to_version": "v2",
        "patch_source": source,
        "applied_at": datetime.utcnow().isoformat() + "Z",
        "summary": f"{len(changes)} field(s) changed, {len(resolved)} unknown(s) resolved, {len(conflicts)} conflict(s) detected",
        "changes": changes,
        "conflicts": conflicts,
        "unknowns_resolved": resolved,
        "unknowns_remaining": v2_memo["questions_or_unknowns"]
    }

    return v2_memo, changelog


# ─────────────────────────────────────────────
# CHANGELOG MARKDOWN WRITER
# ─────────────────────────────────────────────

def write_changelog_md(changelog: dict, path: Path):
    lines = [
        f"# Changelog: {changelog.get('account_id')}",
        f"",
        f"**Transition:** v1 -> v2",
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
            lines.append(f"- **{c.get('field')}**: Demo said `{c.get('demo_value')}`, onboarding said `{c.get('onboarding_value')}` -> Resolution: {c.get('resolution')}")
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
            lines.append(f"- [RESOLVED] {r}")
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
            lines.append(f"- [OPEN] {r}")
    else:
        lines.append("_All unknowns resolved!_")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python version_manager.py <v1_memo.json> <patch_data.json>")
        sys.exit(1)

    with open(sys.argv[1]) as f:
        v1 = json.load(f)
    with open(sys.argv[2]) as f:
        patch = json.load(f)

    v2, changelog = apply_patch(v1, patch)
    print("=== V2 MEMO ===")
    print(json.dumps(v2, indent=2))
    print("\n=== CHANGELOG ===")
    print(json.dumps(changelog, indent=2))
