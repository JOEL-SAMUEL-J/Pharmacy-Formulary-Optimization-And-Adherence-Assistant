from pathlib import Path
import pandas as pd

from load_data import (
    load_plan_data,
    load_formulary_data,
    load_beneficiary_cost_data,
)

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"

PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)


PLAN_COLUMNS = [
    "CONTRACT_ID",
    "PLAN_ID",
    "SEGMENT_ID",
    "PLAN_NAME",
    "FORMULARY_ID",
]

FORMULARY_COLUMNS = [
    "FORMULARY_ID",
    "FORMULARY_VERSION",
    "CONTRACT_YEAR",
    "RXCUI",
    "NDC",
    "TIER_LEVEL_VALUE",
    "QUANTITY_LIMIT_YN",
    "QUANTITY_LIMIT_AMOUNT",
    "QUANTITY_LIMIT_DAYS",
    "PRIOR_AUTHORIZATION_YN",
    "STEP_THERAPY_YN",
]

COST_COLUMNS = [
    "CONTRACT_ID",
    "PLAN_ID",
    "SEGMENT_ID",
    "COVERAGE_LEVEL",
    "TIER",
    "DAYS_SUPPLY",
    "COST_TYPE_PREF",
    "COST_AMT_PREF",
    "COST_TYPE_NONPREF",
    "COST_AMT_NONPREF",
    "COST_TYPE_MAIL_PREF",
    "COST_AMT_MAIL_PREF",
    "COST_TYPE_MAIL_NONPREF",
    "COST_AMT_MAIL_NONPREF",
    "TIER_SPECIALTY_YN",
    "DED_APPLIES_YN",
]


def clean_strings(df):
    """
    Strip leading and trailing whitespace from string columns.
    Missing values are preserved.
    """
    df = df.copy()

    for column in df.select_dtypes(include="str").columns:
        df[column] = df[column].str.strip()

    return df


def clean_plan_data(df):
    """
    Keep only MVP-required plan fields and remove duplicate
    plan/formulary records created by geography-level source rows.
    """
    df = df[PLAN_COLUMNS].copy()
    df = clean_strings(df)

    df = df.drop_duplicates(
        subset=[
            "CONTRACT_ID",
            "PLAN_ID",
            "SEGMENT_ID",
            "FORMULARY_ID",
        ]
    )

    return df


def clean_formulary_data(df):
    df = df[FORMULARY_COLUMNS].copy()
    df = clean_strings(df)

    return df


def clean_cost_data(df):
    df = df[COST_COLUMNS].copy()
    df = clean_strings(df)

    return df


if __name__ == "__main__":
    # Load raw source files
    plans = load_plan_data()
    formulary = load_formulary_data()
    costs = load_beneficiary_cost_data()

    # Clean and reduce to MVP-required columns
    plans_clean = clean_plan_data(plans)
    formulary_clean = clean_formulary_data(formulary)
    costs_clean = clean_cost_data(costs)

    # Display cleaned dataset shapes
    print("Clean Plans:", plans_clean.shape)
    print("Clean Formulary:", formulary_clean.shape)
    print("Clean Beneficiary Costs:", costs_clean.shape)

    # Save processed datasets
    plans_clean.to_csv(
        PROCESSED_DATA_DIR / "plans_clean.csv",
        index=False,
    )

    formulary_clean.to_csv(
        PROCESSED_DATA_DIR / "formulary_clean.csv",
        index=False,
    )

    costs_clean.to_csv(
        PROCESSED_DATA_DIR / "beneficiary_cost_clean.csv",
        index=False,
    )

    print("\nCleaned files saved successfully.")