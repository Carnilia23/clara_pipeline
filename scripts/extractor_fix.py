"""Post-processor to clean up extraction issues"""
import json
import re
from pathlib import Path

# CHANGED: Updated to relative path for Windows/Universal compatibility
BASE = Path("outputs/accounts")

def clean_integration_constraints(constraints: list) -> list:
    """Remove raw transcript lines, keep only clean rules"""
    cleaned = []
    for c in constraints:
        # Skip lines that look like raw transcript
        if '\n\n[' in c or c.strip().startswith('['):
            continue
        # Clean up partial sentences
        c = c.strip()
        if len(c) > 20:  # meaningful constraint
            cleaned.append(c)
    return cleaned

def extract_address_from_transcript(transcript_path: str) -> str | None:
    """Try to find address in transcript"""
    try:
        with open(transcript_path, encoding='utf-8') as f:
            text = f.read()
        # Look for address patterns
        pattern = re.compile(r'\d{3,5}\s+[A-Z][a-z]+(?:\s+[A-Za-z]+){1,4},\s*(?:Suite\s*\d+,\s*)?[A-Z][a-z]+,\s*[A-Z]{2}\s*\d{5}')
        m = pattern.search(text)
        if m:
            return m.group(0).strip()
    except:
        pass
    return None

# Process all v2 memos
if not BASE.exists():
    print(f"Error: Directory {BASE} not found. Ensure you are running from the project root.")
else:
    for acct_dir in sorted(BASE.iterdir()):
        # Skip files, only process account directories
        if not acct_dir.is_dir():
            continue
            
        v2_path = acct_dir / "v2" / "account_memo.json"
        if not v2_path.exists():
            continue
        
        with open(v2_path, encoding='utf-8') as f:
            memo = json.load(f)
        
        changed = False
        
        # Fix integration constraints [cite: 78]
        old_constraints = memo.get('integration_constraints', [])
        new_constraints = clean_integration_constraints(old_constraints)
        if new_constraints != old_constraints:
            memo['integration_constraints'] = new_constraints
            changed = True
            print(f"[{acct_dir.name}] Cleaned constraints: {len(old_constraints)} -> {len(new_constraints)}")
        
        # Fix office address if null [cite: 72]
        if not memo.get('office_address'):
            # CHANGED: Updated to relative path for Windows/Universal compatibility
            onboard_path = Path(f"data/transcripts/{acct_dir.name}_onboarding.txt")
            addr = extract_address_from_transcript(str(onboard_path))
            if addr:
                memo['office_address'] = addr
                changed = True
                print(f"[{acct_dir.name}] Found address: {addr}")
        
        # Add flow summaries if missing [cite: 79-80]
        if not memo.get('office_hours_flow_summary'):
            bh = memo.get('business_hours', {})
            memo['office_hours_flow_summary'] = f"Greet caller, identify purpose, collect name and callback number, transfer to appropriate team during {bh.get('start','08:00')}–{bh.get('end','17:00')} {bh.get('timezone','local time')}. If transfer fails, confirm 30-min callback."
            changed = True
        
        if not memo.get('after_hours_flow_summary'):
            memo['after_hours_flow_summary'] = f"Greet caller, state business hours, confirm if emergency. If emergency: collect name, number, address, attempt transfer to on-call. If transfer fails, assure 15-min callback. If non-emergency: collect details, confirm next-business-day followup."
            changed = True
        
        if changed:
            with open(v2_path, 'w', encoding='utf-8') as f:
                json.dump(memo, f, indent=2)
            print(f"[{acct_dir.name}] v2 memo updated")

    print("\nDone!")