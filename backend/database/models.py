from datetime import datetime
from decimal import Decimal
from sqlalchemy import (BigInteger, CHAR, DateTime, ForeignKeyConstraint, Index,
                        Integer, Numeric, PrimaryKeyConstraint, String, Text,
                        UniqueConstraint)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase): pass

class LoadRun(Base):
    __tablename__="load_runs"
    id: Mapped[int]=mapped_column(BigInteger,primary_key=True,autoincrement=True)
    loaded_at_utc: Mapped[datetime]=mapped_column(DateTime,nullable=False)
    validation_report_sha256: Mapped[str]=mapped_column(CHAR(64),nullable=False)
    cross_validation_report_sha256: Mapped[str]=mapped_column(CHAR(64),nullable=False)
    total_source_rows: Mapped[int]=mapped_column(BigInteger,nullable=False)

class Plan(Base):
    __tablename__="plans"
    contract_id: Mapped[str]=mapped_column(CHAR(5),primary_key=True)
    plan_id: Mapped[str]=mapped_column(CHAR(3),primary_key=True)
    segment_id: Mapped[str]=mapped_column(CHAR(3),primary_key=True)
    contract_name: Mapped[str]=mapped_column(String(80),nullable=False)
    plan_name: Mapped[str]=mapped_column(String(80),nullable=False)
    formulary_id: Mapped[str]=mapped_column(CHAR(8),nullable=False,index=True)
    premium: Mapped[Decimal]=mapped_column(Numeric(12,2),nullable=False)
    deductible: Mapped[Decimal]=mapped_column(Numeric(12,2),nullable=False)
    snp: Mapped[int]=mapped_column(Integer,nullable=False)
    plan_suppressed_yn: Mapped[str]=mapped_column(CHAR(1),nullable=False)

class PlanServiceArea(Base):
    __tablename__="plan_service_areas"
    contract_id: Mapped[str]=mapped_column(CHAR(5),nullable=False)
    plan_id: Mapped[str]=mapped_column(CHAR(3),nullable=False)
    segment_id: Mapped[str]=mapped_column(CHAR(3),nullable=False)
    ma_region_code: Mapped[str]=mapped_column(String(2),nullable=False,default="")
    pdp_region_code: Mapped[str]=mapped_column(String(2),nullable=False,default="")
    state: Mapped[str]=mapped_column(String(2),nullable=False,default="")
    county_code: Mapped[str]=mapped_column(String(5),nullable=False,default="")
    __table_args__=(
        PrimaryKeyConstraint("contract_id","plan_id","segment_id","ma_region_code",
                             "pdp_region_code","state","county_code"),
        ForeignKeyConstraint(("contract_id","plan_id","segment_id"),
                             ("plans.contract_id","plans.plan_id","plans.segment_id")),
        Index("ix_service_area_county","state","county_code"),)

class GeographicLocator(Base):
    __tablename__="geographic_locator"
    county_code: Mapped[str]=mapped_column(CHAR(5),primary_key=True)
    statename: Mapped[str]=mapped_column(String(30),nullable=False)
    county: Mapped[str]=mapped_column(String(50),nullable=False)
    ma_region_code: Mapped[str|None]=mapped_column(String(2))
    ma_region: Mapped[str|None]=mapped_column(String(150))
    pdp_region_code: Mapped[str|None]=mapped_column(String(2))
    pdp_region: Mapped[str|None]=mapped_column(String(150))

class FormularyDrug(Base):
    __tablename__="formulary_drugs"
    formulary_id: Mapped[str]=mapped_column(CHAR(8),primary_key=True)
    formulary_version: Mapped[str]=mapped_column(CHAR(5),primary_key=True)
    contract_year: Mapped[str]=mapped_column(CHAR(4),primary_key=True)
    ndc: Mapped[str]=mapped_column(CHAR(11),primary_key=True)
    rxcui: Mapped[str]=mapped_column(String(8),nullable=False)
    tier_level_value: Mapped[int]=mapped_column(Integer,nullable=False)
    quantity_limit_yn: Mapped[str]=mapped_column(CHAR(1),nullable=False)
    quantity_limit_amount: Mapped[str|None]=mapped_column(String(7))
    quantity_limit_days: Mapped[str|None]=mapped_column(String(3))
    prior_authorization_yn: Mapped[str]=mapped_column(CHAR(1),nullable=False)
    step_therapy_yn: Mapped[str]=mapped_column(CHAR(1),nullable=False)
    selected_drug_yn: Mapped[str]=mapped_column(CHAR(1),nullable=False)
    __table_args__=(Index("ix_formulary_rxcui","formulary_id","rxcui"),
                    Index("ix_formulary_ndc","formulary_id","ndc"),
                    Index("ix_formulary_tier","formulary_id","tier_level_value"))

class BeneficiaryCost(Base):
    __tablename__="beneficiary_cost"
    contract_id: Mapped[str]=mapped_column(CHAR(5),primary_key=True)
    plan_id: Mapped[str]=mapped_column(CHAR(3),primary_key=True)
    segment_id: Mapped[str]=mapped_column(CHAR(3),primary_key=True)
    coverage_level: Mapped[int]=mapped_column(Integer,primary_key=True)
    tier: Mapped[int]=mapped_column(Integer,primary_key=True)
    days_supply: Mapped[int]=mapped_column(Integer,primary_key=True)
    cost_type_pref: Mapped[int]=mapped_column(Integer,nullable=False)
    cost_amt_pref: Mapped[Decimal|None]=mapped_column(Numeric(12,2))
    cost_min_amt_pref: Mapped[str|None]=mapped_column(String(12))
    cost_max_amt_pref: Mapped[Decimal|None]=mapped_column(Numeric(12,2))
    cost_type_nonpref: Mapped[int]=mapped_column(Integer,nullable=False)
    cost_amt_nonpref: Mapped[Decimal|None]=mapped_column(Numeric(12,2))
    cost_min_amt_nonpref: Mapped[str|None]=mapped_column(String(12))
    cost_max_amt_nonpref: Mapped[Decimal|None]=mapped_column(Numeric(12,2))
    cost_type_mail_pref: Mapped[int]=mapped_column(Integer,nullable=False)
    cost_amt_mail_pref: Mapped[Decimal|None]=mapped_column(Numeric(12,2))
    cost_min_amt_mail_pref: Mapped[str|None]=mapped_column(String(12))
    cost_max_amt_mail_pref: Mapped[Decimal|None]=mapped_column(Numeric(12,2))
    cost_type_mail_nonpref: Mapped[int]=mapped_column(Integer,nullable=False)
    cost_amt_mail_nonpref: Mapped[Decimal|None]=mapped_column(Numeric(12,2))
    cost_min_amt_mail_nonpref: Mapped[str|None]=mapped_column(String(12))
    cost_max_amt_mail_nonpref: Mapped[Decimal|None]=mapped_column(Numeric(12,2))
    tier_specialty_yn: Mapped[str]=mapped_column(CHAR(1),nullable=False)
    ded_applies_yn: Mapped[str]=mapped_column(CHAR(1),nullable=False)
    __table_args__=(ForeignKeyConstraint(("contract_id","plan_id","segment_id"),
        ("plans.contract_id","plans.plan_id","plans.segment_id")),
        Index("ix_cost_lookup","contract_id","plan_id","segment_id","tier","days_supply","coverage_level"))

class ExcludedDrug(Base):
    __tablename__="excluded_drugs"
    contract_id: Mapped[str]=mapped_column(CHAR(5),primary_key=True)
    plan_id: Mapped[str]=mapped_column(CHAR(3),primary_key=True)
    rxcui: Mapped[str]=mapped_column(String(8),primary_key=True)
    tier: Mapped[int]=mapped_column(Integer,nullable=False)
    quantity_limit_yn: Mapped[str]=mapped_column(CHAR(1),nullable=False)
    quantity_limit_amount: Mapped[str|None]=mapped_column(String(8))
    quantity_limit_days: Mapped[str|None]=mapped_column(String(3))
    prior_auth_yn: Mapped[str]=mapped_column(CHAR(1),nullable=False)
    step_therapy_yn: Mapped[str]=mapped_column(CHAR(1),nullable=False)
    capped_benefit_yn: Mapped[str]=mapped_column(CHAR(1),nullable=False)
    __table_args__=(Index("ix_excluded_lookup","contract_id","plan_id","rxcui"),)

class IndicationCoverage(Base):
    __tablename__="indication_coverage"
    contract_id: Mapped[str]=mapped_column(CHAR(5),primary_key=True)
    plan_id: Mapped[str]=mapped_column(CHAR(3),primary_key=True)
    rxcui: Mapped[str]=mapped_column(String(8),primary_key=True)
    disease: Mapped[str]=mapped_column(String(100),primary_key=True)
    __table_args__=(Index("ix_indication_lookup","contract_id","plan_id","rxcui"),)

class InsulinCost(Base):
    __tablename__="insulin_cost"
    id: Mapped[int]=mapped_column(BigInteger,primary_key=True,autoincrement=True)
    contract_id: Mapped[str]=mapped_column(CHAR(5),nullable=False)
    plan_id: Mapped[str]=mapped_column(CHAR(3),nullable=False)
    segment_id: Mapped[str]=mapped_column(CHAR(3),nullable=False)
    tier: Mapped[int|None]=mapped_column(Integer)
    days_supply: Mapped[int]=mapped_column(Integer,nullable=False)
    copay_amt_pref_insln: Mapped[Decimal|None]=mapped_column(Numeric(12,2))
    copay_amt_nonpref_insln: Mapped[Decimal|None]=mapped_column(Numeric(12,2))
    copay_amt_mail_pref_insln: Mapped[Decimal|None]=mapped_column(Numeric(12,2))
    copay_amt_mail_nonpref_insln: Mapped[Decimal|None]=mapped_column(Numeric(12,2))
    coin_amt_pref_insln: Mapped[Decimal|None]=mapped_column(Numeric(12,2))
    coin_amt_nonpref_insln: Mapped[Decimal|None]=mapped_column(Numeric(12,2))
    coin_amt_mail_pref_insln: Mapped[Decimal|None]=mapped_column(Numeric(12,2))
    coin_amt_mail_nonpref_insln: Mapped[Decimal|None]=mapped_column(Numeric(12,2))
    __table_args__=(UniqueConstraint("contract_id","plan_id","segment_id","tier","days_supply"),
        ForeignKeyConstraint(("contract_id","plan_id","segment_id"),
            ("plans.contract_id","plans.plan_id","plans.segment_id")),
        Index("ix_insulin_lookup","contract_id","plan_id","segment_id","tier","days_supply"))
