from pathlib import Path
import pandas as pd

from transform_costs import (
    transform_cost_records,
    get_initial_coverage_records,
)


BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"


def load_processed_data():
    plans = pd.read_csv(
        PROCESSED_DATA_DIR / "plans_clean.csv",
        dtype=str
    )

    formulary = pd.read_csv(
        PROCESSED_DATA_DIR / "formulary_clean.csv",
        dtype=str
    )

    costs = pd.read_csv(
        PROCESSED_DATA_DIR / "beneficiary_cost_clean.csv",
        dtype=str
    )

    return plans, formulary, costs


def resolve_plan(
    plans,
    contract_id,
    plan_id,
    segment_id,
):
    result = plans[
        (plans["CONTRACT_ID"] == contract_id)
        & (plans["PLAN_ID"] == plan_id)
        & (plans["SEGMENT_ID"] == segment_id)
    ]

    if result.empty:
        return None

    return result.iloc[0]


def resolve_drug(
    formulary,
    formulary_id,
    rxcui,
):
    result = formulary[
        (formulary["FORMULARY_ID"] == formulary_id)
        & (formulary["RXCUI"] == rxcui)
    ]

    if result.empty:
        return None

    return result


def resolve_cost(
    costs,
    contract_id,
    plan_id,
    segment_id,
    tier,
):
    result = costs[
        (costs["CONTRACT_ID"] == contract_id)
        & (costs["PLAN_ID"] == plan_id)
        & (costs["SEGMENT_ID"] == segment_id)
        & (costs["TIER"] == tier)
    ]

    return result


def resolve_drug_plan(
    plans,
    formulary,
    costs,
    contract_id,
    plan_id,
    segment_id,
    rxcui,
):
    # Step 1: Resolve selected plan
    plan = resolve_plan(
        plans,
        contract_id,
        plan_id,
        segment_id,
    )

    if plan is None:
        return {
            "status": "error",
            "message": "Plan not found."
        }

    formulary_id = plan["FORMULARY_ID"]

    # Step 2: Resolve drug inside selected formulary
    drug_rows = resolve_drug(
        formulary,
        formulary_id,
        rxcui,
    )

    if drug_rows is None:
        return {
            "status": "error",
            "message": "Drug not found in the selected plan formulary."
        }

    # Temporary MVP testing behavior:
    # Use the first matching formulary product row.
    drug = drug_rows.iloc[0]

    tier = drug["TIER_LEVEL_VALUE"]

    # Step 3: Resolve beneficiary cost using plan + tier
    cost_rows = resolve_cost(
        costs,
        contract_id,
        plan_id,
        segment_id,
        tier,
    )

    # If cost information is unavailable, return a partial result
    if cost_rows.empty:
        return {
            "status": "partial",
            "message": (
                "Drug and formulary information found, "
                "but beneficiary cost data is unavailable "
                "for this plan and tier."
            ),

            "plan": {
                "contract_id": contract_id,
                "plan_id": plan_id,
                "segment_id": segment_id,
                "plan_name": plan["PLAN_NAME"],
                "formulary_id": formulary_id,
            },

            "drug": {
                "rxcui": rxcui,
                "ndc": drug["NDC"],
                "tier": tier,
                "prior_authorization":
                    drug["PRIOR_AUTHORIZATION_YN"],
                "step_therapy":
                    drug["STEP_THERAPY_YN"],
                "quantity_limit":
                    drug["QUANTITY_LIMIT_YN"],
                "quantity_limit_amount":
                    drug["QUANTITY_LIMIT_AMOUNT"],
                "quantity_limit_days":
                    drug["QUANTITY_LIMIT_DAYS"],
            },

            "matching_formulary_rows": len(drug_rows),

            "cost_records": [],
            "analysis_cost_records": [],
        }

    # Step 4: Transform all beneficiary cost records
    transformed_costs = transform_cost_records(
        cost_rows
    )

    # Step 5: Keep Initial Coverage only for scoring/analysis
    initial_coverage_records = (
        get_initial_coverage_records(
            transformed_costs
        )
    )

    return {
        "status": "success",

        "plan": {
            "contract_id": contract_id,
            "plan_id": plan_id,
            "segment_id": segment_id,
            "plan_name": plan["PLAN_NAME"],
            "formulary_id": formulary_id,
        },

        "drug": {
            "rxcui": rxcui,
            "ndc": drug["NDC"],
            "tier": tier,
            "prior_authorization":
                drug["PRIOR_AUTHORIZATION_YN"],
            "step_therapy":
                drug["STEP_THERAPY_YN"],
            "quantity_limit":
                drug["QUANTITY_LIMIT_YN"],
            "quantity_limit_amount":
                drug["QUANTITY_LIMIT_AMOUNT"],
            "quantity_limit_days":
                drug["QUANTITY_LIMIT_DAYS"],
        },

        "matching_formulary_rows": len(drug_rows),

        # All coverage levels for UI/display
        "cost_records": transformed_costs,

        # Initial Coverage only for scoring
        "analysis_cost_records": initial_coverage_records,
    }


if __name__ == "__main__":
    plans, formulary, costs = load_processed_data()

    # Known valid test plan
    CONTRACT_ID = "H0028"
    PLAN_ID = "007"
    SEGMENT_ID = "000"

    # Known valid RXCUI from formulary 00026408
    RXCUI = "1551300"

    result = resolve_drug_plan(
        plans,
        formulary,
        costs,
        CONTRACT_ID,
        PLAN_ID,
        SEGMENT_ID,
        RXCUI,
    )

    print("\n=== DRUG + PLAN RESOLUTION RESULT ===")
    print(result)

    if result["status"] == "success":
        print("\n=== ANALYSIS COST RECORDS ===")

        for record in result["analysis_cost_records"]:
            print(record)

    # Diagnostic: inspect all matching formulary rows
    if result["status"] in {"success", "partial"}:
        formulary_id = result["plan"]["formulary_id"]

        matches = formulary[
            (formulary["FORMULARY_ID"] == formulary_id)
            & (formulary["RXCUI"] == RXCUI)
        ]

        print("\n=== MATCHING FORMULARY ROWS ===")
        print(matches)

        print(
            "\nNumber of matching formulary rows:",
            len(matches)
        )