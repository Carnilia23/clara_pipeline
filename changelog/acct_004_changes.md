# Changelog: acct_004

**Transition:** v1 → v2
**Source:** onboarding_call
**Applied:** 2026-03-03T11:52:05.836445Z
**Summary:** 7 field(s) changed, 1 unknown(s) resolved, 0 conflict(s) detected

## Changes

- **business_hours.start** [field_updated]
  - Before: `02:00`
  - After: `07:30`
- **business_hours.end** [field_updated]
  - Before: `07:30`
  - After: `16:30`
- **questions_or_unknowns** [list_updated]
  - Before: `['Emergency triggers not defined', 'Emergency contact phone number not provided']`
  - After: `['Emergency triggers not defined']`
- **created_at** [field_updated]
  - Before: `2026-03-03T11:52:05.803322Z`
  - After: `2026-03-03T11:52:05.836079Z`
- **emergency_routing_rules.primary_contact** [field_added]
  - Before: `None`
  - After: `312-555-0163`
- **emergency_routing_rules.order** [list_updated]
  - Before: `[]`
  - After: `['312-555-0163', '312-555-0177']`
- **integration_constraints** [list_updated]
  - Before: `['[SALES REP]: Any integrations?\n\n[DIANE]: We use our own dispatch software, not ServiceTrade']`
  - After: `['Any system integration rules?\n\n[DIANE]: Do not create records in any external system']`

## Conflicts

_No conflicts detected._

## Unknowns Resolved

- ✅ Emergency contact phone number not provided

## Unknowns Remaining

- ❓ Emergency triggers not defined