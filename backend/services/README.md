# SQLAlchemy query and analysis service

## Structure

```text
database/
  models.py       # SQLAlchemy mappings
  session.py      # engine and session factory
repositories/
  coverage.py     # SQL only: plan, product, cost, indication, insulin lookups
services/
  analysis.py     # workflow orchestration and structured response
  barriers.py     # transparent access/affordability/channel heuristic
  cli.py          # pre-API command-line test entry point
tests/
  test_analysis_service.py
```

The repository contains no scoring. The service never guesses an unavailable
cost rule and never silently chooses among NDCs with different formulary
outcomes. Insulin rows are returned separately because a negotiated price is
needed for final dollar adjudication.

Run the verified county example:

```powershell
python -m services --area-type county --area-code 28100 `
  --contract-id H0028 --plan-id 007 --segment-id 000 `
  --rxcui 1551300 --ndc 00002143380 `
  --coverage-level 1 --days-supply 1
```

Run the service test:

```powershell
python -m unittest tests.test_analysis_service -v
```

Coverage codes: `0` pre-deductible, `1` initial, `3` catastrophic.
Days-supply codes: `1` 30 days, `2` 90 days, `3` other, `4` 60 days.
