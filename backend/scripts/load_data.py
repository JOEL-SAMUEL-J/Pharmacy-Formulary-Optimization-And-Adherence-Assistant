from pathlib import Path
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent

RAW_DATA_DIR = BASE_DIR / "data" / "raw"


def load_plan_data():
    return pd.read_csv(
        RAW_DATA_DIR / "plan_information_file.txt",
        sep="|",
        dtype=str,
        encoding="cp1252"
    )


def load_formulary_data():
    return pd.read_csv(
        RAW_DATA_DIR / "basic_drugs_formulary_file.txt",
        sep="|",
        dtype=str,
        encoding="cp1252"
    )


def load_beneficiary_cost_data():
    return pd.read_csv(
        RAW_DATA_DIR / "beneficiary_cost_file.txt",
        sep="|",
        dtype=str,
        encoding="cp1252"
    )


if __name__ == "__main__":
    plans = load_plan_data()
    formulary = load_formulary_data()
    costs = load_beneficiary_cost_data()

    print("Plans:", plans.shape)
    print("Formulary:", formulary.shape)
    print("Beneficiary Costs:", costs.shape)

    print("\nPLAN COLUMNS")
    print(plans.columns.tolist())

    print("\nFORMULARY COLUMNS")
    print(formulary.columns.tolist())

    print("\nBENEFICIARY COST COLUMNS")
    print(costs.columns.tolist())

    print("\nPLAN SAMPLE")
    print(plans.head())

    print("\nFORMULARY SAMPLE")
    print(formulary.head())

    print("\nBENEFICIARY COST SAMPLE")
    print(costs.head())

    print("\nPLAN DTYPES")
    print(plans.dtypes)

    print("\nFORMULARY DTYPES")
    print(formulary.dtypes)

    print("\nBENEFICIARY COST DTYPES")
    print(costs.dtypes)