# Remaining task list

This list reflects the completed work recorded in `LOG1.md`, `LOG2.md`, and
`LOG3.md`. Keep Tier 0 stable before starting optional or gated work.

## Tier 0 completion

- [x] Curate the `crop_facts` knowledge-base data from the staged source PDFs:
  crop seasons, allowed soil and water classes, and climate ranges for the five
  supported crops. Cite each source.
- [x] Feed those cited facts into `crop_scorer` so season/soil/water exclusions,
  Agronomic Fit, and Climate Fit become available; retain honest degradation for
  any missing evidence.
- [x] Build the sourced season-plan calendar only after the crop facts are
  curated; do not invent dates or pest checkpoints.
- [x] Run an end-to-end chat turn through the API after the current
  unit-contract fix, including trace, provenance, and the budget replan path.
- [x] Audit every rendered number for provenance, then run the required finance,
  units, scorer, and trace-redactor tests before the next merge.

## Demo hardening

- [x] Rehearse the seeded Rajshahi Rabi farm flow twice, including geocode
  confirmation, a live bigha-area change, the reduced-budget recovery, and the
  simulator insufficient-balance path.
- [x] Confirm the README and demo use the actual five-crop universe
  (boro rice, aman rice, potato, mustard, lentil), not the superseded six-crop
  plan.
- [ ] Tag `tier0-stable` only when the end-to-end flow is green.

## Deferred / requires an explicit scope decision

- [ ] Consider reintroducing wheat only if its crop.db data, facts, costs, and
  tests are curated together. Maize remains excluded because its available data
  is corrupt.
- [ ] Start any gated Tier 1 work only after `tier0-stable` exists and main is
  green.
