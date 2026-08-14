from pathlib import Path
import pandas as pd


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


def show_required_nulls(plans, formulary, costs):
    print("\n=== REQUIRED KEY NULL COUNTS ===")

    print("\nPlans")
    print(
        plans[
            [
                "CONTRACT_ID",
                "PLAN_ID",
                "SEGMENT_ID",
                "FORMULARY_ID",
            ]
        ].isna().sum()
    )

    print("\nFormulary")
    print(
        formulary[
            [
                "FORMULARY_ID",
                "RXCUI",
                "NDC",
                "TIER_LEVEL_VALUE",
            ]
        ].isna().sum()
    )

    print("\nBeneficiary Cost")
    print(
        costs[
            [
                "CONTRACT_ID",
                "PLAN_ID",
                "SEGMENT_ID",
                "TIER",
            ]
        ].isna().sum()
    )


def show_duplicate_counts(plans, formulary, costs):
    print("\n=== DUPLICATE COUNTS ===")

    plan_duplicates = plans.duplicated(
        subset=[
            "CONTRACT_ID",
            "PLAN_ID",
            "SEGMENT_ID",
            "FORMULARY_ID",
        ]
    ).sum()

    formulary_duplicates = formulary.duplicated(
        subset=[
            "FORMULARY_ID",
            "RXCUI",
            "NDC",
            "TIER_LEVEL_VALUE",
        ]
    ).sum()

    cost_duplicates = costs.duplicated(
        subset=[
            "CONTRACT_ID",
            "PLAN_ID",
            "SEGMENT_ID",
            "TIER",
            "COVERAGE_LEVEL",
            "DAYS_SUPPLY",
        ]
    ).sum()

    print("Plan duplicates:", plan_duplicates)
    print("Formulary duplicates:", formulary_duplicates)
    print("Beneficiary cost duplicates:", cost_duplicates)


def validate_plan_uniqueness(plans):
    print("\n=== PLAN KEY UNIQUENESS ===")

    plan_key = [
        "CONTRACT_ID",
        "PLAN_ID",
        "SEGMENT_ID",
    ]

    duplicate_plan_keys = plans.duplicated(
        subset=plan_key,
        keep=False
    )

    duplicate_rows = plans[duplicate_plan_keys]

    print(
        "Plan keys appearing more than once:",
        duplicate_rows[plan_key].drop_duplicates().shape[0]
    )

    if not duplicate_rows.empty:
        print("\nSample duplicate plan keys:")
        print(
            duplicate_rows[
                plan_key + ["PLAN_NAME", "FORMULARY_ID"]
            ].head(10)
        )


def validate_plan_formulary_mapping(plans):
    print("\n=== PLAN → FORMULARY MAPPING ===")

    plan_key = [
        "CONTRACT_ID",
        "PLAN_ID",
        "SEGMENT_ID",
    ]

    mappings = (
        plans
        .groupby(plan_key)["FORMULARY_ID"]
        .nunique()
    )

    multiple_formularies = mappings[mappings > 1]

    print(
        "Plan keys mapped to multiple formularies:",
        len(multiple_formularies)
    )

    if not multiple_formularies.empty:
        print("\nSample ambiguous plan mappings:")
        print(multiple_formularies.head(10))


def show_category_values(formulary, costs):
    print("\n=== CATEGORY VALUES ===")

    print("\nFormulary tiers:")
    print(
        sorted(
            formulary["TIER_LEVEL_VALUE"]
            .dropna()
            .unique()
        )
    )

    print("\nCost tiers:")
    print(
        sorted(
            costs["TIER"]
            .dropna()
            .unique()
        )
    )

    print("\nPrior Authorization:")
    print(
        formulary[
            "PRIOR_AUTHORIZATION_YN"
        ].value_counts(dropna=False)
    )

    print("\nStep Therapy:")
    print(
        formulary[
            "STEP_THERAPY_YN"
        ].value_counts(dropna=False)
    )

    print("\nQuantity Limit:")
    print(
        formulary[
            "QUANTITY_LIMIT_YN"
        ].value_counts(dropna=False)
    )

    print("\nDeductible Applies:")
    print(
        costs[
            "DED_APPLIES_YN"
        ].value_counts(dropna=False)
    )

    print("\nSpecialty Tier:")
    print(
        costs[
            "TIER_SPECIALTY_YN"
        ].value_counts(dropna=False)
    )


def validate_plan_formulary_join(plans, formulary):
    print("\n=== PLAN → FORMULARY JOIN VALIDATION ===")

    plan_formulary_ids = set(
        plans["FORMULARY_ID"].dropna().unique()
    )

    formulary_ids = set(
        formulary["FORMULARY_ID"].dropna().unique()
    )

    unmatched = plan_formulary_ids - formulary_ids

    total = len(plan_formulary_ids)
    matched = total - len(unmatched)

    match_rate = (
        matched / total * 100
        if total > 0
        else 0
    )

    print("Unique plan formulary IDs:", total)
    print("Matched formulary IDs:", matched)
    print("Unmatched plan formulary IDs:", len(unmatched))
    print(f"Formulary match rate: {match_rate:.2f}%")

    if unmatched:
        print("\nSample unmatched IDs:")
        print(sorted(unmatched)[:10])


def validate_plan_cost_join(plans, costs):
    print("\n=== PLAN → BENEFICIARY COST JOIN VALIDATION ===")

    join_keys = [
        "CONTRACT_ID",
        "PLAN_ID",
        "SEGMENT_ID",
    ]

    plan_keys = plans[
        join_keys
    ].drop_duplicates()

    cost_keys = costs[
        join_keys
    ].drop_duplicates()

    merged = plan_keys.merge(
        cost_keys,
        on=join_keys,
        how="left",
        indicator=True,
    )

    matched_count = (
        merged["_merge"] == "both"
    ).sum()

    unmatched = merged[
        merged["_merge"] == "left_only"
    ]

    total = len(plan_keys)

    match_rate = (
        matched_count / total * 100
        if total > 0
        else 0
    )

    print("Unique plan keys:", total)
    print("Matched plan keys:", matched_count)
    print("Unmatched plan keys:", len(unmatched))
    print(f"Beneficiary cost match rate: {match_rate:.2f}%")

    if not unmatched.empty:
        print("\nSample unmatched plan keys:")
        print(
            unmatched[
                join_keys
            ].head(10)
        )


if __name__ == "__main__":
    plans, formulary, costs = load_processed_data()

    print("Plans:", plans.shape)
    print("Formulary:", formulary.shape)
    print("Beneficiary Costs:", costs.shape)

    show_required_nulls(
        plans,
        formulary,
        costs
    )

    show_duplicate_counts(
        plans,
        formulary,
        costs
    )

    validate_plan_uniqueness(
        plans
    )

    validate_plan_formulary_mapping(
        plans
    )

    show_category_values(
        formulary,
        costs
    )

    validate_plan_formulary_join(
        plans,
        formulary
    )

    validate_plan_cost_join(
        plans,
        costs
    )