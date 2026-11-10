# Agribase cleaning handoff

`agribase_clean.db` is a validation-first derivative of `crops.db`. The source database is never modified.

## Safe application interface

Use only these views for farmer-facing yield and finance calculations:

- `latest_district_yields` — latest accepted observation for each crop and district.
- `recommendation_yields` — all accepted historical observations.

Do not query `crops.db` directly from the application. Do not query `crop_predictions` from either database for farmer-facing advice.

## Included crops

| Database key | Farmer-facing crop | Status |
| --- | --- | --- |
| `aman_hyv` | Aman HYV rice | enabled |
| `boro_hyv` | Boro HYV rice | enabled |
| `potato_hyv` | HYV potato | enabled |
| `lentil_masur` | Lentil (masur) | enabled |
| `mustard` | Mustard | enabled |
| `wheat` | Wheat | disabled: no literal source key in `crops.db` |

The validation bounds are deliberately broad plausibility checks, not agronomic recommendations. They are recorded in `crop_yield_bounds` and must be reviewed by an agronomy/data-source owner before a production release.

## Auditability

- Accepted values retain their original source row ID in `crop_yield_observations.source_row_id`.
- Every excluded row is preserved in `rejected_crop_rows` with a rejection reason.
- District aliases are explicit in `district_alias`; unrecognised district labels are rejected, not guessed.
- `source_registry` is deliberately marked `pending_verification`: the supplied database has no embedded publication, page/table, URL, extraction method, or license. Do not label its data as BBS-verified until those fields are completed with evidence.

## Rebuilding

From `data/` (where `crops.db`, the raw source, must sit; it is not in git), run `Get-Content -Raw ../docs/data/build_agribase_clean.sql | sqlite3 agribase_clean.db` only after deliberately removing the current generated file and reviewing any changed validation policy. The build fails safely if an existing output file would be overwritten by the normal project command.

## Required README wording

Use wording equivalent to: “District yield estimates are computed from a validated derivative of the supplied agricultural dataset. The in-database source citation is pending verification; recommendations disclose this limitation.”

Do not claim live market prices, BBS verification, or use the unsupported wheat yield until separately evidenced.
