# CMS 2026 preprocessing and validation

This layer prepares the seven CMS sources for:

`State/County -> Plan -> Drug -> Days supply/Coverage phase -> Tier + PA/ST/QL + Cost sharing`

It deliberately excludes pharmacy-network, member, and prescriber data and a ZIP
crosswalk. It creates no database.

## Folders and scripts

- `data/raw`: the seven original `.txt` files; never modified.
- `data/processed`: validated UTF-8 CSVs with fixed columns and LF endings.
- `data/quarantine`: rejected rows as JSONL, including source row and all issues.
- `data/reports`: `validation_report.json` and `row_counts.csv`.
- `schemas.py`: official 2026 columns, types, code domains, nullability, and grains.
- `readers.py`: encoding/delimiter detection and streaming reads.
- `normalize.py`: snake-case headers and stable number formatting.
- `validation.py`: null, format, domain, duplicate, consistency, and linkage rules.
- `pipeline.py`: orchestration, hashes/provenance, and atomic output replacement.
- `cli.py`: one command for the full pre-load gate.

Identifiers (contract, plan, segment, formulary, county, RxCUI, and NDC) remain
strings, preserving leading zeroes.

## Required raw names

`basic_drugs_formulary_file.txt`, `beneficiary_cost_file.txt`,
`excluded_drugs_formulary_file.txt`, `geographic_locator_file.txt`,
`Indication_Based_Coverage_Formulary_File.txt`,
`insulin_beneficiary_cost_file.txt`, and `plan_information_file.txt`.

Run from the project root:

```powershell
python -m preprocessing validate
```

Use the database-loading gate in CI:

```powershell
python -m preprocessing validate --strict
```

The validator checks file/header presence; required values; identifier formats;
numeric types; CMS code domains; quantity-limit consistency; natural-grain
duplicates; formulary-to-plan, child-to-plan, and plan-to-county linkages.

`PASS_WITH_QUARANTINE` produces valid cleaned rows but requires review. `--strict`
returns a failure until every rejected row is resolved. Reports include input and
output SHA-256 hashes, sizes, detected format, row/issue counts, runtime and schema
versions, and UTC run time.

Outputs are deterministic: source order is preserved, column order is fixed,
numeric formatting is canonical, and run timestamps are kept out of processed
data. Do not build tables until a strict run returns `PASS`.

## Cross-file semantic gate

After row validation passes, run the second pre-database gate:

```powershell
python -m preprocessing cross-validate --strict
```

This checks plan geography by contract type, plan-to-formulary availability,
plan-to-beneficiary-cost coverage, formulary tiers against cost tiers, initial
30-day contexts, insulin plan/tier linkage, and indication RxCUIs against the
applicable plan formulary. It writes `cross_validation_report.json` and
`cross_validation_summary.csv` under `data/reports` and never changes cleaned
data. Errors block loading; warnings identify reviewable benefit-design exceptions.
