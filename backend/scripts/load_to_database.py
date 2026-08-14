from pathlib import Path
import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, URL, text


BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"

# Load database configuration
load_dotenv(BASE_DIR / ".env")


DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")


# Build SQLAlchemy URL safely.
# URL.create handles special characters in passwords correctly.
DATABASE_URL = URL.create(
    drivername="mysql+pymysql",
    username=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=int(DB_PORT),
    database=DB_NAME,
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)


def test_database_connection():
    """
    Verify that Python can connect to MySQL before attempting
    to load the CSV datasets.
    """
    try:
        with engine.connect() as connection:
            database_name = connection.execute(
                text("SELECT DATABASE();")
            ).scalar()

        print("Database connection successful.")
        print("Connected to:", database_name)

        return True

    except Exception as error:
        print("Database connection failed.")
        print(error)

        return False


def load_plans():
    plans = pd.read_csv(
        PROCESSED_DATA_DIR / "plans_clean.csv",
        dtype=str,
    )

    plans = plans.rename(
        columns={
            "CONTRACT_ID": "contract_id",
            "PLAN_ID": "plan_id",
            "SEGMENT_ID": "segment_id",
            "PLAN_NAME": "plan_name",
            "FORMULARY_ID": "formulary_id",
        }
    )

    print("\nLoading plans...")

    plans.to_sql(
        "plans",
        con=engine,
        if_exists="append",
        index=False,
        chunksize=1000,
    )

    print(f"Plans loaded: {len(plans)}")


def load_formulary_drugs():
    formulary = pd.read_csv(
        PROCESSED_DATA_DIR / "formulary_clean.csv",
        dtype=str,
    )

    formulary = formulary.rename(
        columns={
            "FORMULARY_ID": "formulary_id",
            "FORMULARY_VERSION": "formulary_version",
            "CONTRACT_YEAR": "contract_year",
            "RXCUI": "rxcui",
            "NDC": "ndc",
            "TIER_LEVEL_VALUE": "tier",
            "QUANTITY_LIMIT_YN": "quantity_limit_yn",
            "QUANTITY_LIMIT_AMOUNT": "quantity_limit_amount",
            "QUANTITY_LIMIT_DAYS": "quantity_limit_days",
            "PRIOR_AUTHORIZATION_YN": "prior_authorization_yn",
            "STEP_THERAPY_YN": "step_therapy_yn",
        }
    )

    print("\nLoading formulary drugs...")

    formulary.to_sql(
        "formulary_drugs",
        con=engine,
        if_exists="append",
        index=False,
        chunksize=5000,
    )

    print(f"Formulary rows loaded: {len(formulary)}")


def load_beneficiary_costs():
    costs = pd.read_csv(
        PROCESSED_DATA_DIR / "beneficiary_cost_clean.csv",
        dtype=str,
    )

    costs = costs.rename(
        columns={
            "CONTRACT_ID": "contract_id",
            "PLAN_ID": "plan_id",
            "SEGMENT_ID": "segment_id",
            "COVERAGE_LEVEL": "coverage_level",
            "TIER": "tier",
            "DAYS_SUPPLY": "days_supply",
            "COST_TYPE_PREF": "cost_type_pref",
            "COST_AMT_PREF": "cost_amt_pref",
            "COST_TYPE_NONPREF": "cost_type_nonpref",
            "COST_AMT_NONPREF": "cost_amt_nonpref",
            "COST_TYPE_MAIL_PREF": "cost_type_mail_pref",
            "COST_AMT_MAIL_PREF": "cost_amt_mail_pref",
            "COST_TYPE_MAIL_NONPREF": "cost_type_mail_nonpref",
            "COST_AMT_MAIL_NONPREF": "cost_amt_mail_nonpref",
            "TIER_SPECIALTY_YN": "tier_specialty_yn",
            "DED_APPLIES_YN": "ded_applies_yn",
        }
    )

    print("\nLoading beneficiary costs...")

    costs.to_sql(
        "beneficiary_costs",
        con=engine,
        if_exists="append",
        index=False,
        chunksize=5000,
    )

    print(f"Beneficiary cost rows loaded: {len(costs)}")


if __name__ == "__main__":
    # Optional diagnostics without exposing the password
    print("DB_HOST:", DB_HOST)
    print("DB_PORT:", DB_PORT)
    print("DB_USER:", DB_USER)
    print("DB_NAME:", DB_NAME)
    print("Password loaded:", DB_PASSWORD is not None)

    if not test_database_connection():
        raise SystemExit(
            "Stopping because the database connection failed."
        )

    load_plans()
    load_formulary_drugs()
    load_beneficiary_costs()

    print("\nDatabase loading completed successfully.")