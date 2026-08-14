"""2026 CMS PUF source contracts. All identifiers remain strings."""
from dataclasses import dataclass, field
from typing import Mapping

@dataclass(frozen=True)
class Column:
    required: bool = True
    nullable: bool = False
    kind: str = "string"
    max_length: int | None = None
    domain: frozenset[str] | None = None
    pattern: str | None = None

@dataclass(frozen=True)
class FileSchema:
    filename: str
    columns: Mapping[str, Column]
    grain: tuple[str, ...]
    description: str
    aliases: Mapping[str, str] = field(default_factory=dict)

def s(length=None, nullable=False, pattern=None, domain=None):
    return Column(nullable=nullable, max_length=length, pattern=pattern,
                  domain=frozenset(domain) if domain else None)
def i(nullable=False, domain=None):
    return Column(nullable=nullable, kind="integer",
                  domain=frozenset(str(x) for x in domain) if domain else None)
def d(nullable=False): return Column(nullable=nullable, kind="decimal")

YN = {"Y", "N", "0", "1"}
PLAN_KEY = ("contract_id", "plan_id", "segment_id")
plan_id_cols = {"contract_id": s(5, pattern=r"[HRS][0-9]{4}"),
                "plan_id": s(3, pattern=r"[0-9]{3}"),
                "segment_id": s(3, pattern=r"[0-9]{3}")}
cost_fields = {}
for suffix in ("pref", "nonpref", "mail_pref", "mail_nonpref"):
    cost_fields[f"cost_type_{suffix}"] = i(domain={0, 1, 2})
    cost_fields[f"cost_amt_{suffix}"] = d(nullable=True)
    cost_fields[f"cost_min_amt_{suffix}"] = s(12, nullable=True)
    cost_fields[f"cost_max_amt_{suffix}"] = d(nullable=True)

SCHEMAS = {
"plan_information": FileSchema("plan_information_file.txt", {
    **plan_id_cols, "contract_name": s(80), "plan_name": s(80), "formulary_id": s(8),
    "premium": d(), "deductible": d(), "ma_region_code": s(2, nullable=True),
    "pdp_region_code": s(2, nullable=True), "state": s(2, nullable=True, pattern=r"[A-Z]{2}"),
    "county_code": s(5, nullable=True, pattern=r"[0-9]{5}"),
    "snp": i(domain={0,1,2,3}), "plan_suppressed_yn": s(1, domain=YN)},
    PLAN_KEY + ("ma_region_code", "pdp_region_code", "state", "county_code"),
    "Plan, formulary, and service area"),
"geographic_locator": FileSchema("geographic_locator_file.txt", {
    "county_code": s(5, pattern=r"[0-9]{5}"), "statename": s(30), "county": s(50),
    "ma_region_code": s(2, nullable=True), "ma_region": s(150, nullable=True),
    "pdp_region_code": s(2, nullable=True), "pdp_region": s(150, nullable=True)},
    ("county_code",), "County and region lookup"),
"basic_drugs_formulary": FileSchema("basic_drugs_formulary_file.txt", {
    "formulary_id": s(8), "formulary_version": s(5),
    "contract_year": s(4, pattern=r"[0-9]{4}"), "rxcui": s(8, pattern=r"[0-9]+"),
    "ndc": s(11, pattern=r"[0-9]{11}"), "tier_level_value": i(),
    "quantity_limit_yn": s(1, domain=YN), "quantity_limit_amount": s(7, nullable=True),
    "quantity_limit_days": s(3, nullable=True), "prior_authorization_yn": s(1, domain=YN),
    "step_therapy_yn": s(1, domain=YN), "selected_drug_yn": s(1, domain=YN)},
    ("formulary_id","formulary_version","contract_year","ndc"), "Drug tiers and restrictions"),
"excluded_drugs_formulary": FileSchema("excluded_drugs_formulary_file.txt", {
    "contract_id": plan_id_cols["contract_id"], "plan_id": plan_id_cols["plan_id"],
    "rxcui": s(8, pattern=r"[0-9]+"), "tier": i(), "quantity_limit_yn": s(1, domain=YN),
    "quantity_limit_amount": s(8, nullable=True), "quantity_limit_days": s(3, nullable=True),
    "prior_auth_yn": s(1, domain=YN), "step_therapy_yn": s(1, domain=YN),
    "capped_benefit_yn": s(1, domain=YN)},
    ("contract_id","plan_id","rxcui"), "Covered excluded drugs"),
"indication_based_coverage": FileSchema("Indication_Based_Coverage_Formulary_File.txt", {
    "contract_id": plan_id_cols["contract_id"], "plan_id": plan_id_cols["plan_id"],
    "rxcui": s(8, pattern=r"[0-9]+"), "disease": s(100)},
    ("contract_id","plan_id","rxcui","disease"), "Indication-specific coverage"),
"beneficiary_cost": FileSchema("beneficiary_cost_file.txt", {
    **plan_id_cols, "coverage_level": i(domain={0,1,3}), "tier": i(),
    "days_supply": i(domain={1,2,3,4}), **cost_fields,
    "tier_specialty_yn": s(1, domain=YN), "ded_applies_yn": s(1, domain=YN)},
    PLAN_KEY + ("coverage_level","tier","days_supply"), "Cost sharing by phase/tier/supply"),
"insulin_beneficiary_cost": FileSchema("insulin_beneficiary_cost_file.txt", {
    **plan_id_cols, "tier": i(nullable=True), "days_supply": i(domain={1,2,3,4}),
    **{f"{kind}_amt_{channel}_insln": d(nullable=True) for kind in ("copay","coin")
       for channel in ("pref","nonpref","mail_pref","mail_nonpref")}},
    PLAN_KEY + ("tier","days_supply"), "Insulin cost sharing")}

PROCESSING_ORDER = ("plan_information","geographic_locator","basic_drugs_formulary",
                    "beneficiary_cost","excluded_drugs_formulary",
                    "indication_based_coverage","insulin_beneficiary_cost")
