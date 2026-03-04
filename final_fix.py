import json

fixes = {
    "acct_001": {
        "office_address": "4821 Peachtree Industrial Blvd, Suite 200, Atlanta, GA 30341",
        "integration_constraints": [
            "Never automatically create a job in ServiceTrade for sprinkler-related calls - human tech review required",
            "After-hours inspection calls may be logged in ServiceTrade as pending"
        ]
    },
    "acct_002": {
        "integration_constraints": [
            "Never auto-create ServiceTrade jobs for electrical fire calls - supervisor approval required",
            "Flag hospital or medical power outages as Priority 1 before any record creation"
        ]
    },
    "acct_003": {
        "office_address": "3252 Holiday Court, Suite 208, La Jolla, CA 92037",
        "integration_constraints": [
            "Do not interact with proprietary monitoring software",
            "UL compliance required - log every call with timestamp, caller name, number, location, alarm type, and disposition"
        ]
    },
    "acct_004": {
        "office_address": "2340 S River Rd, Des Plaines, IL 60018",
        "integration_constraints": [
            "Do not create records in any external system - collect and route only, all data entry handled internally"
        ]
    },
    "acct_005": {
        "integration_constraints": [
            "Never create, modify, or delete any record in Salesforce",
            "No Salesforce integration permitted - government data security requirement"
        ]
    }
}

for acct_id, patch in fixes.items():
    path = f"outputs/accounts/{acct_id}/v2/account_memo.json"
    with open(path, encoding="utf-8") as f:
        memo = json.load(f)
    memo.update(patch)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(memo, f, indent=2)
    print(f"{acct_id} - fixed!")

print("\nAll done! Run check.py to verify.")
