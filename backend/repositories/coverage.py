"""Database queries for the Service Area + Plan + Drug workflow."""

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from database.models import (
    BeneficiaryCost,
    DrugLookup,
    ExcludedDrug,
    FormularyDrug,
    IndicationCoverage,
    InsulinCost,
    Plan,
    PlanServiceArea,
)


AREA_COLUMNS = {
    "county": PlanServiceArea.county_code,
    "ma_region": PlanServiceArea.ma_region_code,
    "pdp_region": PlanServiceArea.pdp_region_code,
}


def get_plan_in_service_area(
    session: Session,
    area_type: str,
    area_code: str,
    contract_id: str,
    plan_id: str,
    segment_id: str,
):
    column = AREA_COLUMNS.get(area_type)

    if column is None:
        raise ValueError(
            f"Unsupported service-area type: {area_type}"
        )

    statement = (
        select(Plan)
        .join(
            PlanServiceArea,
            and_(
                Plan.contract_id
                == PlanServiceArea.contract_id,
                Plan.plan_id == PlanServiceArea.plan_id,
                Plan.segment_id
                == PlanServiceArea.segment_id,
            ),
        )
        .where(
            column == area_code,
            Plan.contract_id == contract_id,
            Plan.plan_id == plan_id,
            Plan.segment_id == segment_id,
            Plan.plan_suppressed_yn.notin_(("Y", "1")),
        )
        .limit(1)
    )

    return session.scalars(statement).first()


def get_drug_name(
    session: Session,
    rxcui: str,
):
    """Return drug identity plus verified RxNorm enrichment fields."""

    statement = (
        select(
            DrugLookup.rxcui,
            DrugLookup.drug_display_name,
            DrugLookup.ingredient,
            DrugLookup.ingredient_rxcuis,
            DrugLookup.brand_name,
            DrugLookup.strength,
            DrugLookup.dose_form,
            DrugLookup.is_insulin,
            DrugLookup.insulin_match_reason,
            DrugLookup.enrichment_status,
            DrugLookup.lookup_status,
        )
        .where(DrugLookup.rxcui == rxcui)
    )

    row = session.execute(statement).mappings().first()
    return dict(row) if row else None


def get_formulary_products(
    session: Session,
    formulary_id: str,
    rxcui: str,
    ndc: str | None = None,
):
    statement = select(FormularyDrug).where(
        FormularyDrug.formulary_id == formulary_id,
        FormularyDrug.rxcui == rxcui,
    )

    if ndc:
        statement = statement.where(
            FormularyDrug.ndc == ndc
        )

    return list(
        session.scalars(
            statement.order_by(FormularyDrug.ndc)
        )
    )


def get_cost_rule(
    session: Session,
    plan: Plan,
    tier: int,
    coverage_level: int,
    days_supply: int,
):
    return session.get(
        BeneficiaryCost,
        (
            plan.contract_id,
            plan.plan_id,
            plan.segment_id,
            coverage_level,
            tier,
            days_supply,
        ),
    )


def get_available_cost_contexts(
    session: Session,
    plan: Plan,
    tier: int,
):
    statement = (
        select(
            BeneficiaryCost.coverage_level,
            BeneficiaryCost.days_supply,
        )
        .where(
            BeneficiaryCost.contract_id
            == plan.contract_id,
            BeneficiaryCost.plan_id == plan.plan_id,
            BeneficiaryCost.segment_id
            == plan.segment_id,
            BeneficiaryCost.tier == tier,
        )
        .distinct()
        .order_by(
            BeneficiaryCost.coverage_level,
            BeneficiaryCost.days_supply,
        )
    )

    return [
        {
            "coverage_level": row.coverage_level,
            "days_supply": row.days_supply,
        }
        for row in session.execute(statement)
    ]


def get_indications(
    session: Session,
    plan: Plan,
    rxcui: str,
):
    statement = (
        select(IndicationCoverage)
        .where(
            IndicationCoverage.contract_id
            == plan.contract_id,
            IndicationCoverage.plan_id == plan.plan_id,
            IndicationCoverage.rxcui == rxcui,
        )
        .order_by(IndicationCoverage.disease)
    )

    return list(session.scalars(statement))


def get_excluded_drugs(
    session: Session,
    plan: Plan,
    rxcui: str,
):
    statement = select(ExcludedDrug).where(
        ExcludedDrug.contract_id == plan.contract_id,
        ExcludedDrug.plan_id == plan.plan_id,
        ExcludedDrug.rxcui == rxcui,
    )

    return list(session.scalars(statement))


def get_insulin_rule(
    session: Session,
    plan: Plan,
    tier: int,
    days_supply: int,
):
    """Return exact-tier insulin rule, falling back to a tier-null rule."""

    statement = (
        select(InsulinCost)
        .where(
            InsulinCost.contract_id == plan.contract_id,
            InsulinCost.plan_id == plan.plan_id,
            InsulinCost.segment_id == plan.segment_id,
            InsulinCost.days_supply == days_supply,
            or_(
                InsulinCost.tier == tier,
                InsulinCost.tier.is_(None),
            ),
        )
        # False sorts before True in MySQL, so exact tier wins.
        .order_by(
            InsulinCost.tier.is_(None),
            InsulinCost.id,
        )
        .limit(1)
    )

    return session.scalars(statement).first()
