# Changelog: acct_003

**Transition:** v1 → v2
**Source:** onboarding_call
**Applied:** 2026-03-03T11:52:05.788426Z
**Summary:** 7 field(s) changed, 1 unknown(s) resolved, 0 conflict(s) detected

## Changes

- **business_hours.start** [field_updated]
  - Before: `02:00`
  - After: `08:00`
- **business_hours.end** [field_updated]
  - Before: `08:00`
  - After: `17:00`
- **questions_or_unknowns** [list_updated]
  - Before: `['Emergency contact phone number not provided']`
  - After: `['Emergency triggers not defined']`
- **created_at** [field_updated]
  - Before: `2026-03-03T11:52:05.765819Z`
  - After: `2026-03-03T11:52:05.787724Z`
- **emergency_routing_rules.primary_contact** [field_added]
  - Before: `None`
  - After: `619-555-0173`
- **emergency_routing_rules.order** [list_updated]
  - Before: `[]`
  - After: `['619-555-0173', '619-555-0191', '619-555-0200']`
- **services_supported** [list_updated]
  - Before: `['fire alarm']`
  - After: `['monitoring']`

## Conflicts

_No conflicts detected._

## Unknowns Resolved

- ✅ Emergency contact phone number not provided

## Unknowns Remaining

- ❓ Emergency triggers not defined