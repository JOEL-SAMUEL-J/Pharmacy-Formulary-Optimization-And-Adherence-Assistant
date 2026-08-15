"""End-to-end plan/drug resolution and explainable opportunity output."""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from repositories import coverage as repo

from .barriers import build_opportunity


COVERAGE_LABELS = {
    0: "Pre-deductible",
    1: "Initial coverage",
    3: "Catastrophic",
}

DAYS_LABELS = {
    1: "30 days",
    2: "90 days",
    3: "Other",
    4: "60 days",
}

COST_TYPES = {
    0: "not_offered",
    1: "copay",
    2: "coinsurance",
}

CONFIRMED_INSULIN_REASONS = {
    "RXNORM_INGREDIENT",
    "RXNORM_PRECISE_INGREDIENT",
    "RXNORM_MULTI_INGREDIENT",
}


class AnalysisError(RuntimeError):
    code = "ANALYSIS_ERROR"

    def __init__(self, message, details=None):
        super().__init__(message)
        self.details = details or {}


class PlanNotInServiceArea(AnalysisError):
    code = "PLAN_NOT_IN_SERVICE_AREA"


class DrugNotCovered(AnalysisError):
    code = "DRUG_NOT_COVERED"


class AmbiguousDrugProduct(AnalysisError):
    code = "AMBIGUOUS_DRUG_PRODUCT"


class CostRuleNotFound(AnalysisError):
    code = "COST_RULE_NOT_FOUND"


@dataclass(frozen=True)
class AnalysisInput:
    service_area_type: str
    service_area_code: str
    contract_id: str
    plan_id: str
    segment_id: str
    rxcui: str
    coverage_level: int
    days_supply: int
    ndc: str | None = None


def _yes(value):
    return str(value).upper() in {"Y", "1"}


def _number(value):
    return None if value is None else float(value)


def _confirmed_insulin(drug: dict) -> bool:
    """Require completed RxNorm enrichment before treating a drug as insulin."""

    return (
        _yes(drug.get("is_insulin"))
        and drug.get("enrichment_status") == "success"
        and drug.get("insulin_match_reason")
        in CONFIRMED_INSULIN_REASONS
    )


def _channels(cost):
    result = {}

    specs = {
        "preferred_retail": (
            "cost_type_pref",
            "cost_amt_pref",
        ),
        "standard_retail": (
            "cost_type_nonpref",
            "cost_amt_nonpref",
        ),
        "preferred_mail": (
            "cost_type_mail_pref",
            "cost_amt_mail_pref",
        ),
        "standard_mail": (
            "cost_type_mail_nonpref",
            "cost_amt_mail_nonpref",
        ),
    }

    for name, (type_field, amount_field) in specs.items():
        code = getattr(cost, type_field)

        result[name] = {
            "type": COST_TYPES[code],
            "type_code": code,
            "amount": _number(
                getattr(cost, amount_field)
            ),
        }

    return result


def _restriction_signature(product):
    return (
        product.tier_level_value,
        product.quantity_limit_yn,
        product.quantity_limit_amount,
        product.quantity_limit_days,
        product.prior_authorization_yn,
        product.step_therapy_yn,
    )


def _serialize_insulin_rule(rule):
    if not rule:
        return None

    fields = (
        "copay_amt_pref_insln",
        "copay_amt_nonpref_insln",
        "copay_amt_mail_pref_insln",
        "copay_amt_mail_nonpref_insln",
        "coin_amt_pref_insln",
        "coin_amt_nonpref_insln",
        "coin_amt_mail_pref_insln",
        "coin_amt_mail_nonpref_insln",
    )

    return {
        "tier": rule.tier,
        "days_supply": rule.days_supply,
        **{
            field: _number(getattr(rule, field))
            for field in fields
        },
    }


def _insulin_resolution(
    drug: dict,
    insulin_rule,
):
    enrichment_status = drug.get(
        "enrichment_status"
    )

    match_reason = drug.get(
        "insulin_match_reason"
    )

    if enrichment_status != "success":
        return {
            "is_insulin": None,
            "match_reason": match_reason,
            "enrichment_status": enrichment_status,
            "resolution_status": (
                "INSULIN STATUS UNRESOLVED"
            ),
            "rule": None,
        }

    if not _confirmed_insulin(drug):
        return {
            "is_insulin": False,
            "match_reason": match_reason,
            "enrichment_status": enrichment_status,
            "resolution_status": (
                "NOT AN INSULIN DRUG"
            ),
            "rule": None,
        }

    serialized_rule = _serialize_insulin_rule(
        insulin_rule
    )

    if serialized_rule is None:
        return {
            "is_insulin": True,
            "match_reason": match_reason,
            "enrichment_status": enrichment_status,
            "resolution_status": (
                "NO MATCHING INSULIN COST RULE"
            ),
            "rule": None,
        }

    return {
        "is_insulin": True,
        "match_reason": match_reason,
        "enrichment_status": enrichment_status,
        "resolution_status": (
            "INSULIN COST RULE FOUND"
        ),
        "rule": serialized_rule,
    }


def analyze(
    session: Session,
    user_input: AnalysisInput,
):
    if user_input.coverage_level not in COVERAGE_LABELS:
        raise AnalysisError(
            "Unsupported coverage level",
            {"allowed": COVERAGE_LABELS},
        )

    if user_input.days_supply not in DAYS_LABELS:
        raise AnalysisError(
            "Unsupported days-supply code",
            {"allowed": DAYS_LABELS},
        )

    plan = repo.get_plan_in_service_area(
        session,
        user_input.service_area_type,
        user_input.service_area_code,
        user_input.contract_id,
        user_input.plan_id,
        user_input.segment_id,
    )

    if not plan:
        raise PlanNotInServiceArea(
            "Selected plan is not active in the "
            "selected service area"
        )

    drug = repo.get_drug_name(
        session,
        user_input.rxcui,
    ) or {
        "rxcui": user_input.rxcui,
        "drug_display_name": None,
        "ingredient": None,
        "ingredient_rxcuis": None,
        "brand_name": None,
        "strength": None,
        "dose_form": None,
        "is_insulin": "N",
        "insulin_match_reason": None,
        "enrichment_status": "missing",
        "lookup_status": "missing",
    }

    products = repo.get_formulary_products(
        session,
        plan.formulary_id,
        user_input.rxcui,
        user_input.ndc,
    )

    excluded = False

    if products:
        signatures = {
            _restriction_signature(product)
            for product in products
        }

        if (
            not user_input.ndc
            and len(signatures) > 1
        ):
            raise AmbiguousDrugProduct(
                "RxCUI has products with different "
                "formulary outcomes; select an NDC",
                {
                    "candidate_ndcs": [
                        product.ndc
                        for product in products
                    ]
                },
            )

        product = products[0]
        tier = product.tier_level_value

        restrictions = {
            "quantity_limit": _yes(
                product.quantity_limit_yn
            ),
            "quantity_limit_amount": (
                product.quantity_limit_amount
            ),
            "quantity_limit_days": (
                product.quantity_limit_days
            ),
            "prior_authorization": _yes(
                product.prior_authorization_yn
            ),
            "step_therapy": _yes(
                product.step_therapy_yn
            ),
            "selected_drug": _yes(
                product.selected_drug_yn
            ),
        }

        ndcs = [
            product.ndc
            for product in products
        ]

    else:
        excluded_rows = repo.get_excluded_drugs(
            session,
            plan,
            user_input.rxcui,
        )

        if not excluded_rows:
            raise DrugNotCovered(
                "Drug is not present in the plan "
                "formulary or supplemental "
                "excluded-drug coverage"
            )

        product = excluded_rows[0]
        excluded = True
        tier = product.tier
        ndcs = []

        restrictions = {
            "quantity_limit": _yes(
                product.quantity_limit_yn
            ),
            "quantity_limit_amount": (
                product.quantity_limit_amount
            ),
            "quantity_limit_days": (
                product.quantity_limit_days
            ),
            "prior_authorization": _yes(
                product.prior_auth_yn
            ),
            "step_therapy": _yes(
                product.step_therapy_yn
            ),
            "selected_drug": False,
            "capped_benefit": _yes(
                product.capped_benefit_yn
            ),
        }

    cost = repo.get_cost_rule(
        session,
        plan,
        tier,
        user_input.coverage_level,
        user_input.days_supply,
    )

    if not cost:
        raise CostRuleNotFound(
            "No cost rule exists for the selected "
            "phase and days supply",
            {
                "available_contexts": (
                    repo.get_available_cost_contexts(
                        session,
                        plan,
                        tier,
                    )
                )
            },
        )

    indications = [
        row.disease
        for row in repo.get_indications(
            session,
            plan,
            user_input.rxcui,
        )
    ]

    channels = _channels(cost)

    is_confirmed_insulin = _confirmed_insulin(
        drug
    )

    insulin_rule = (
        repo.get_insulin_rule(
            session,
            plan,
            tier,
            user_input.days_supply,
        )
        if is_confirmed_insulin
        else None
    )

    serialized_insulin_rule = (
        _serialize_insulin_rule(insulin_rule)
    )

    insulin = _insulin_resolution(
        drug,
        insulin_rule,
    )

    opportunity = build_opportunity(
        restrictions,
        tier,
        _yes(cost.ded_applies_yn),
        _yes(cost.tier_specialty_yn),
        channels,
        indications,
        excluded,
    )

    return {
        "input": user_input.__dict__,
        "plan": {
            "contract_id": plan.contract_id,
            "plan_id": plan.plan_id,
            "segment_id": plan.segment_id,
            "plan_name": plan.plan_name,
            "formulary_id": plan.formulary_id,
            "premium": _number(plan.premium),
            "deductible": _number(plan.deductible),
        },
        "drug": {
            **drug,
            "ndcs": ndcs,
            "selected_ndc": getattr(
                product,
                "ndc",
                None,
            ),
        },
        "coverage": {
            "status": (
                "supplemental_excluded_drug"
                if excluded
                else "formulary"
            ),
            "tier": tier,
            "restrictions": restrictions,
            "indications": indications,
        },
        "cost_sharing": {
            "coverage_level": cost.coverage_level,
            "coverage_phase": COVERAGE_LABELS[
                cost.coverage_level
            ],
            "days_supply": cost.days_supply,
            "days_supply_label": DAYS_LABELS[
                cost.days_supply
            ],
            "deductible_applies": _yes(
                cost.ded_applies_yn
            ),
            "specialty_tier": _yes(
                cost.tier_specialty_yn
            ),
            "channels": channels,
            # Keep the original field so existing callers do
            # not break during this transition.
            "insulin_rule": serialized_insulin_rule,
            # New explicit classification and resolution object.
            "insulin": insulin,
        },
        "optimization_opportunity": opportunity,
    }
