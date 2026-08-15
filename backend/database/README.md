# MySQL + SQLAlchemy database layer

This is the third gate, after both preprocessing commands return `PASS`.
It uses SQLAlchemy 2.x declarative models and PyMySQL. The database contains only
the seven validated CMS sources needed for the lean County/Plan/Drug/Cost MVP.

## Model shape

- `plans`: one row per contract/plan/segment.
- `plan_service_areas`: repeated county or region availability, separated from plan facts.
- `geographic_locator`: county and MA/PDP region labels.
- `formulary_drugs`: NDC/RxCUI, tier, QL, PA, ST, and selected-drug flag.
- `beneficiary_cost`: plan/tier/phase/days-supply cost-sharing rules.
- `excluded_drugs`: supplemental excluded-drug coverage.
- `indication_coverage`: indication-specific RxCUI coverage.
- `insulin_cost`: insulin-specific copay and coinsurance rules.
- `load_runs`: report hashes, source row count, and load provenance.

Indexes follow the application path: county to plan, plan to formulary, formulary
to RxCUI/NDC/tier, and plan/tier to phase and days supply.

## Setup

Create a UTF-8 database in MySQL:

```sql
CREATE DATABASE formulary_optimization_and_adherence_assistant_mvp CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
```

Install dependencies in the backend virtual environment:

```powershell
python -m pip install -r requirements.txt
```

Set `DATABASE_URL` in the shell; do not commit credentials:

```powershell
$env:DATABASE_URL = "Your Connection String from env"
```

## Commands

Create empty tables and indexes:

```powershell
python -m database init
```

Create and load a fresh schema after checking report status and every processed
SHA-256 hash:

```powershell
python -m database load
```

The loader streams CSVs in 5,000-row batches, preserves identifiers as text,
separates plan service areas, verifies every source-backed table count, and only
then records a completed load. It refuses to load again when `load_runs` is not
empty, preventing accidental duplication.

Check database connectivity and completed-load provenance:

```powershell
python -m database verify
```

The MySQL database itself must already exist. The loader creates tables, not the
database or user, because those require administrator privileges.
