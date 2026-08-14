"""Field, grain, business-rule, and cross-file checks."""
import hashlib, re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

@dataclass(frozen=True)
class Issue:
    code: str
    column: str
    message: str

def validate_row(row, schema):
    issues = []
    for name, rule in schema.columns.items():
        value = row.get(name, "")
        if not value:
            if not rule.nullable: issues.append(Issue("NULL_REQUIRED", name, "required value is blank"))
            continue
        if rule.max_length and len(value) > rule.max_length:
            issues.append(Issue("MAX_LENGTH", name, f"length exceeds {rule.max_length}"))
        if rule.pattern and not re.fullmatch(rule.pattern, value):
            issues.append(Issue("FORMAT", name, "value does not match CMS format"))
        if rule.domain and value.upper() not in rule.domain:
            issues.append(Issue("DOMAIN", name, f"value not in {sorted(rule.domain)}"))
        try:
            if rule.kind == "integer" and Decimal(value) != Decimal(value).to_integral_value():
                raise InvalidOperation
            if rule.kind == "decimal": Decimal(value)
        except InvalidOperation:
            issues.append(Issue("TYPE", name, f"expected {rule.kind}"))
    for name in sorted(set(row) - set(schema.columns)):
        issues.append(Issue("UNEXPECTED_COLUMN", name, "not in the 2026 layout"))
    return issues

def business_rules(dataset, row):
    issues = []
    if dataset in {"basic_drugs_formulary", "excluded_drugs_formulary"}:
        flag = row.get("quantity_limit_yn", "").upper()
        if flag in {"Y","1"} and not row.get("quantity_limit_amount"):
            issues.append(Issue("QL_CONSISTENCY", "quantity_limit_amount", "required when QL is yes"))
        if flag in {"N","0"} and (row.get("quantity_limit_amount") or row.get("quantity_limit_days")):
            issues.append(Issue("QL_CONSISTENCY", "quantity_limit_yn", "QL values present when flag is no"))
    return issues

def grain_digest(row, grain):
    return hashlib.blake2b("\x1f".join(row.get(c, "") for c in grain).encode(), digest_size=16).digest()

def linkage_issues(dataset, row, refs):
    result = []
    if dataset == "basic_drugs_formulary" and row.get("formulary_id") not in refs["formulary_ids"]:
        result.append(Issue("ORPHAN_FORMULARY", "formulary_id", "not in plan information"))
    if dataset in {"beneficiary_cost","insulin_beneficiary_cost"}:
        key = tuple(row.get(c, "") for c in ("contract_id","plan_id","segment_id"))
        if key not in refs["plan_keys"]: result.append(Issue("ORPHAN_PLAN", "plan key", "not in plan information"))
    if dataset in {"excluded_drugs_formulary","indication_based_coverage"}:
        key = (row.get("contract_id", ""), row.get("plan_id", ""))
        if key not in refs["contract_plan_keys"]: result.append(Issue("ORPHAN_PLAN", "plan key", "not in plan information"))
    if dataset == "plan_information" and row.get("county_code") and row["county_code"] not in refs["county_codes"]:
        result.append(Issue("ORPHAN_COUNTY", "county_code", "not in geographic locator"))
    return result
