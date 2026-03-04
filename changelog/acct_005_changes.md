# Changelog: acct_005

**Transition:** v1 → v2
**Source:** onboarding_call
**Applied:** 2026-03-03T11:52:05.870494Z
**Summary:** 5 field(s) changed, 1 unknown(s) resolved, 0 conflict(s) detected

## Changes

- **questions_or_unknowns** [list_updated]
  - Before: `['Emergency contact phone number not provided']`
  - After: `['Emergency triggers not defined']`
- **created_at** [field_updated]
  - Before: `2026-03-03T11:52:05.846557Z`
  - After: `2026-03-03T11:52:05.869750Z`
- **emergency_routing_rules.primary_contact** [field_added]
  - Before: `None`
  - After: `202-555-0156`
- **emergency_routing_rules.order** [list_updated]
  - Before: `[]`
  - After: `['202-555-0156', '202-555-0167', '1-800-555-0199']`
- **integration_constraints** [list_updated]
  - Before: `['Clara should never create records in Salesforce - our system has very specific record formats our ops team manages']`
  - After: `['[SPECIALIST]: Salesforce constraint was never create records - can you clarify?\n\n[ROBERT]: Never create, modify, or delete any record in Salesforce']`

## Conflicts

_No conflicts detected._

## Unknowns Resolved

- ✅ Emergency contact phone number not provided

## Unknowns Remaining

- ❓ Emergency triggers not defined