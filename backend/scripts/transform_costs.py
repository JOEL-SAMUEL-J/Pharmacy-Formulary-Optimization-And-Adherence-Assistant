def interpret_cost(cost_type, cost_amount):
    if cost_type == "0":
        return {
            "type": "not_offered",
            "value": None,
            "display": "Not offered",
        }

    if cost_type == "1":
        amount = float(cost_amount)

        return {
            "type": "copay",
            "value": amount,
            "display": f"${amount:.2f}",
        }

    if cost_type == "2":
        percentage = float(cost_amount) * 100

        return {
            "type": "coinsurance",
            "value": percentage,
            "display": f"{percentage:g}%",
        }

    return {
        "type": "unknown",
        "value": None,
        "display": "Unknown",
    }


def interpret_coverage_level(value):
    coverage_levels = {
        "0": "Pre-deductible",
        "1": "Initial coverage",
        "3": "Catastrophic",
    }

    return coverage_levels.get(value, "Unknown")


def interpret_days_supply(value):
    days_supply = {
        "1": "30 days",
        "2": "90 days",
        "3": "Other",
        "4": "60 days",
    }

    return days_supply.get(value, "Unknown")


def transform_cost_record(record):
    return {
        "coverage_level": {
            "code": record["COVERAGE_LEVEL"],
            "display": interpret_coverage_level(
                record["COVERAGE_LEVEL"]
            ),
        },

        "days_supply": {
            "code": record["DAYS_SUPPLY"],
            "display": interpret_days_supply(
                record["DAYS_SUPPLY"]
            ),
        },

        "preferred_retail": interpret_cost(
            record["COST_TYPE_PREF"],
            record["COST_AMT_PREF"],
        ),

        "standard_retail": interpret_cost(
            record["COST_TYPE_NONPREF"],
            record["COST_AMT_NONPREF"],
        ),

        "preferred_mail": interpret_cost(
            record["COST_TYPE_MAIL_PREF"],
            record["COST_AMT_MAIL_PREF"],
        ),

        "standard_mail": interpret_cost(
            record["COST_TYPE_MAIL_NONPREF"],
            record["COST_AMT_MAIL_NONPREF"],
        ),

        "specialty_tier":
            record["TIER_SPECIALTY_YN"] == "Y",

        "deductible_applies":
            record["DED_APPLIES_YN"] == "Y",
    }


def transform_cost_records(cost_rows):
    return [
        transform_cost_record(record)
        for record in cost_rows.to_dict(orient="records")
    ]

def get_initial_coverage_records(transformed_records):
    return [
        record
        for record in transformed_records
        if record["coverage_level"]["code"] == "1"
    ]