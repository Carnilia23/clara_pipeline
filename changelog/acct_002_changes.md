# Changelog: acct_002

**Transition:** v1 → v2
**Source:** onboarding_call
**Applied:** 2026-03-03T11:52:05.756435Z
**Summary:** 5 field(s) changed, 1 unknown(s) resolved, 0 conflict(s) detected

## Changes

- **questions_or_unknowns** [list_updated]
  - Before: `['Emergency triggers not defined', 'Emergency contact phone number not provided']`
  - After: `['Emergency triggers not defined']`
- **created_at** [field_updated]
  - Before: `2026-03-03T11:52:05.733587Z`
  - After: `2026-03-03T11:52:05.756084Z`
- **emergency_routing_rules.primary_contact** [field_added]
  - Before: `None`
  - After: `713-555-0144`
- **emergency_routing_rules.order** [list_updated]
  - Before: `[]`
  - After: `['713-555-0144', '713-555-0188']`
- **integration_constraints** [list_updated]
  - Before: `['[SALES REP]: Any integration systems?\n\n[JENNIFER]: We use ServiceTrade too actually']`
  - After: `['[SPECIALIST]: ServiceTrade constraints?\n\n[JENNIFER]: Never auto-create jobs for any electrical fire related calls']`

## Conflicts

_No conflicts detected._

## Unknowns Resolved

- ✅ Emergency contact phone number not provided

## Unknowns Remaining

- ❓ Emergency triggers not defined