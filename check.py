import json

for i in range(1, 6):
    with open(f'outputs/accounts/acct_00{i}/v2/account_memo.json') as f:
        d = json.load(f)
    print(f'acct_00{i}:')
    print(f'  address: {d.get("office_address")}')
    print(f'  constraints: {d.get("integration_constraints")}')
    print(f'  after_hours: {d.get("after_hours_flow_summary") is not None}')
    print()
