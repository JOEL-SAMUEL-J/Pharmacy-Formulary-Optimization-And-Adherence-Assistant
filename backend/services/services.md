# SQLAlchemy Coverage and Opportunity Service

This layer converts the validated MySQL data into the MVP workflow:

```text
Service Area + Plan + Drug + Coverage Phase + Days Supply
→ validate plan availability
→ resolve plan formulary
→ resolve drug tier and restrictions
→ resolve plan-listed cost sharing
→ produce an explainable optimization opportunity
```

It sits between the database-loading layer and the future API. It does not
create or reload CMS tables.

## Folder structure

```text
backend/
├── database/
│   ├── __init__.py
│   ├── models.py
│   └── session.py
├── repositories/
│   ├── __init__.py
│   └── coverage.py
├── services/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py
│   ├── analysis.py
│   └── barriers.py
└── tests/
    └── test_analysis_service.py
```

## Responsibilities

### `database/models.py`

Contains SQLAlchemy mappings for the existing MySQL tables. Add the following
minimal mapping for the populated `drug_lookup` table:

```python
class DrugLookup(Base):
    __tablename__ = "drug_lookup"

    rxcui: Mapped[str] = mapped_column(String(20), primary_key=True)
    drug_display_name: Mapped[str | None] = mapped_column(String(255))
    ingredient: Mapped[str | None] = mapped_column(String(255))
    brand_name: Mapped[str | None] = mapped_column(String(255))
    strength: Mapped[str | None] = mapped_column(String(100))
    dose_form: Mapped[str | None] = mapped_column(String(100))
    is_insulin: Mapped[str | None] = mapped_column(CHAR(1))
    lookup_status: Mapped[str | None] = mapped_column(String(20))
```

This model maps an existing table. It does not repopulate or replace the 6,153
drug lookup records.

### `database/session.py`

Creates the SQLAlchemy engine and session factory from `DATABASE_URL`.

### `repositories/coverage.py`

Contains database queries only:

- validate a plan within a county, MA region, or PDP region;
- retrieve the drug name by RxCUI;
- find NDC products in the selected plan formulary;
- find tier/phase/days-supply cost sharing;
- retrieve available cost contexts;
- retrieve indication-based coverage;
- retrieve supplemental excluded-drug coverage; and
- retrieve insulin-specific cost rules.

No opportunity scoring belongs in the repository.

### `services/analysis.py`

Coordinates the complete workflow and returns a structured result containing:

- selected and resolved input;
- plan and formulary identity;
- drug name, RxCUI, and NDC;
- tier, PA, ST, and QL;
- coverage phase and days supply;
- retail/mail cost-sharing channels;
- indication, excluded-drug, and insulin details; and
- the explainable optimization opportunity.

If one RxCUI has NDC products with different formulary outcomes, the service
requires an exact NDC instead of silently selecting the first product.

### `services/barriers.py`

Keeps interpretation separate from database facts:

```text
PA + ST + QL + conditional/excluded coverage
→ access barriers

Tier + deductible + copay/coinsurance + specialty tier
→ affordability barriers

Preferred/standard retail/mail differences
→ channel opportunity
```

The output is a transparent review-priority heuristic, not a clinical or
member-level adherence prediction.

Canonical statement:

> This plan-drug combination has access and affordability barriers that could
> contribute to medication adherence challenges and may warrant review.

## Configuration

Activate the backend virtual environment:

```powershell
cd "E:\Pharmacy Formulary\backend"
.\.venv\Scripts\Activate.ps1
```

Set the MySQL connection for the current terminal:

```powershell
$env:DATABASE_URL = "mysql+pymysql://USER:ENCODED_PASSWORD@localhost:3306/formulary_optimization_and_adherence_assistant_mvp?charset=utf8mb4"
```

Do not commit real credentials. URL-encode special password characters.

## Supported input values

Service-area types:

```text
county     → H contracts
ma_region  → R contracts
pdp_region → S contracts
```

Coverage phases:

```text
0 → Pre-deductible
1 → Initial coverage
3 → Catastrophic
```

Days supply:

```text
1 → 30 days
2 → 90 days
3 → Other
4 → 60 days
```

Cost types:

```text
0 → Channel not offered
1 → Copay in dollars
2 → Coinsurance as a decimal percentage
```

For example, cost type `2` with amount `0.25` means 25% coinsurance—not $0.25.

## Run a live analysis

Verified county example:

```powershell
python -m services `
  --area-type county `
  --area-code 28100 `
  --contract-id H0028 `
  --plan-id 007 `
  --segment-id 000 `
  --rxcui 1551300 `
  --ndc 00002143380 `
  --coverage-level 1 `
  --days-supply 1
```

Verified MA-region example:

```powershell
python -m services `
  --area-type ma_region `
  --area-code 16 `
  --contract-id R0110 `
  --plan-id 003 `
  --segment-id 000 `
  --rxcui 1551300 `
  --ndc 00002143380 `
  --coverage-level 1 `
  --days-supply 1
```

Verified PDP-region example:

```powershell
python -m services `
  --area-type pdp_region `
  --area-code 12 `
  --contract-id S1030 `
  --plan-id 001 `
  --segment-id 000 `
  --rxcui 1551300 `
  --ndc 00002143380 `
  --coverage-level 1 `
  --days-supply 1
```

## Expected service errors

The CLI returns structured errors rather than silently guessing:

```text
PLAN_NOT_IN_SERVICE_AREA
DRUG_NOT_COVERED
AMBIGUOUS_DRUG_PRODUCT
COST_RULE_NOT_FOUND
```

`COST_RULE_NOT_FOUND` includes the phase/days-supply combinations that are
actually available for the selected plan and tier. The UI should use those
options rather than assuming every plan offers 30-, 60-, and 90-day rules.

## Tests

Run the service tests:

```powershell
python -m unittest discover -s tests -p "test_analysis_service.py" -v
```

Recommended cases before exposing the service through an API:

- County/H-contract resolution;
- MA-region/R-contract resolution;
- PDP-region/S-contract resolution;
- 30-, 60-, and 90-day cost contexts;
- copay and coinsurance interpretation;
- unavailable days supply;
- multiple NDC outcomes;
- indication-based coverage;
- supplemental excluded-drug coverage; and
- insulin-specific cost rules.

## Next step

After the live CLI and service tests pass, expose the tested service through
FastAPI endpoints. The API should call `services.analysis.analyze()` rather than
reimplementing SQL joins or barrier rules.
