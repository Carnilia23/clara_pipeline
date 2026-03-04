# Changelog: acct_001

**Transition:** v1 → v2
**Source:** onboarding_call
**Applied:** 2026-03-03T17:44:11.541605Z
**Summary:** 7 field(s) changed, 1 unknown(s) resolved, 0 conflict(s) detected

## Changes

- **emergency_routing_rules.primary_contact** [field_added]
  - Before: `None`
  - After: `404-555-0182`
- **emergency_routing_rules.order** [list_updated]
  - Before: `[]`
  - After: `['404-555-0182', '404-555-0219', '404-555-0100']`
- **created_at** [field_updated]
  - Before: `2026-03-03T17:41:52.745167Z`
  - After: `2026-03-03T17:44:11.540304Z`
- **integration_constraints** [list_updated]
  - Before: `['[SALES REP]: And you mentioned ServiceTrade - are you using that for your service management?\n\n[MIKE]: Yeah', "So we're very careful about not automatically creating jobs in ServiceTrade without a tech reviewing it first"]`
  - After: `['Now about ServiceTrade - you had some concerns during the demo?\n\n[MIKE]: Right', 'So the rule is: never automatically create a job in ServiceTrade for sprinkler-related calls', "[SARAH]: Also, any inspection calls that come in after hours, we do want those logged in ServiceTrade as pending, that's fine"]`
- **services_supported** [list_updated]
  - Before: `['fire protection', 'sprinkler', 'fire alarm', 'suppression', 'inspection']`
  - After: `['fire protection', 'sprinkler', 'fire alarm', 'suppression', 'inspection', 'extinguisher']`
- **questions_or_unknowns** [list_updated]
  - Before: `['Emergency contact phone number not provided']`
  - After: `[]`
- **emergency_definition** [list_updated]
  - Before: `['fire alarm', 'fire suppression']`
  - After: `['fire alarm', 'active fire', 'flooding']`

## Conflicts

_No conflicts detected._

## Unknowns Resolved

- ✅ Emergency contact phone number not provided

## Unknowns Remaining

_All unknowns resolved!_