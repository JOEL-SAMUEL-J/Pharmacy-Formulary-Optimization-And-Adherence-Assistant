"""Cross-file semantic checks for the lean County/Plan/Drug/Cost MVP."""
import csv, hashlib, json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

class CrossValidationError(RuntimeError): pass

def _rows(path):
    if not path.exists(): raise CrossValidationError(f"Missing processed file: {path}")
    with path.open("r",encoding="utf-8",newline="") as handle:
        yield from csv.DictReader(handle)

def _pair_digest(*values):
    return hashlib.blake2b("\x1f".join(values).encode(),digest_size=16).digest()

def run_cross_validation(processed_dir: Path, reports_dir: Path, strict=False, sample_limit=20):
    reports_dir.mkdir(parents=True,exist_ok=True)
    paths={name:processed_dir/f"{name}.csv" for name in (
        "plan_information","geographic_locator","basic_drugs_formulary",
        "beneficiary_cost","excluded_drugs_formulary","indication_based_coverage",
        "insulin_beneficiary_cost")}

    counties=set(); ma_regions=set(); pdp_regions=set()
    for row in _rows(paths["geographic_locator"]):
        if row["county_code"]: counties.add(row["county_code"])
        if row["ma_region_code"]: ma_regions.add(row["ma_region_code"])
        if row["pdp_region_code"]: pdp_regions.add(row["pdp_region_code"])

    plan_keys=set(); contract_plan_keys=set(); plan_formulary={}; suppressed_keys=set(); plan_geo_issues=[]
    for row in _rows(paths["plan_information"]):
        key=(row["contract_id"],row["plan_id"],row["segment_id"])
        plan_keys.add(key); contract_plan_keys.add(key[:2]); plan_formulary[key]=row["formulary_id"]
        if row["plan_suppressed_yn"].upper() in {"Y","1"}: suppressed_keys.add(key)
        prefix=row["contract_id"][:1]
        valid=(prefix=="H" and row["county_code"] in counties) or \
              (prefix=="R" and row["ma_region_code"] in ma_regions) or \
              (prefix=="S" and row["pdp_region_code"] in pdp_regions)
        if not valid and len(plan_geo_issues)<sample_limit:
            plan_geo_issues.append({"plan_key":list(key),"contract_type":prefix,
                "county_code":row["county_code"],"ma_region_code":row["ma_region_code"],
                "pdp_region_code":row["pdp_region_code"]})

    formulary_tiers=defaultdict(set); formulary_drugs=set()
    for row in _rows(paths["basic_drugs_formulary"]):
        formulary_tiers[row["formulary_id"]].add(row["tier_level_value"])
        formulary_drugs.add(_pair_digest(row["formulary_id"],row["rxcui"]))

    cost_tiers=defaultdict(set); initial_30=set()
    for row in _rows(paths["beneficiary_cost"]):
        key=(row["contract_id"],row["plan_id"],row["segment_id"])
        cost_tiers[key].add(row["tier"])
        if row["coverage_level"]=="1" and row["days_supply"]=="1": initial_30.add((key,row["tier"]))

    excluded_tiers=set()
    for row in _rows(paths["excluded_drugs_formulary"]):
        excluded_tiers.add((row["contract_id"],row["plan_id"],row["tier"]))

    checks=[]
    def add(name,severity,count,samples,description):
        checks.append({"check":name,"severity":severity,"failure_count":count,
                       "samples":samples[:sample_limit],"description":description})

    active_plan_keys=plan_keys-suppressed_keys
    active_plan_formulary={key:value for key,value in plan_formulary.items() if key in active_plan_keys}
    add("suppressed_plans_excluded","INFO",len(suppressed_keys),[list(x) for x in sorted(suppressed_keys)],
        "CMS-suppressed plans are excluded from required formulary and cost-publication checks.")
    missing_formularies=sorted(set(active_plan_formulary.values())-set(formulary_tiers))
    add("plan_formulary_has_drugs","ERROR",len(missing_formularies),missing_formularies,
        "Every formulary referenced by a plan must contain a basic-formulary drug.")
    missing_cost=sorted(active_plan_keys-set(cost_tiers))
    add("plan_has_beneficiary_cost","ERROR",len(missing_cost),[list(x) for x in missing_cost],
        "Every distinct plan key must have beneficiary-cost rows.")

    missing_tier_count=0; missing_tier_samples=[]; unused_tier_count=0; unused_tier_samples=[]
    supplemental_tier_count=0; supplemental_tier_samples=[]
    missing_context_count=0; missing_context_samples=[]
    for key,formulary in active_plan_formulary.items():
        drug_tiers=formulary_tiers.get(formulary,set()); plan_tiers=cost_tiers.get(key,set())
        for tier in sorted(drug_tiers-plan_tiers):
            missing_tier_count+=1
            if len(missing_tier_samples)<sample_limit: missing_tier_samples.append({"plan_key":list(key),"formulary_id":formulary,"tier":tier})
        for tier in sorted(plan_tiers-drug_tiers):
            sample={"plan_key":list(key),"formulary_id":formulary,"tier":tier}
            if (key[0],key[1],tier) in excluded_tiers:
                supplemental_tier_count+=1
                if len(supplemental_tier_samples)<sample_limit: supplemental_tier_samples.append(sample)
            else:
                unused_tier_count+=1
                if len(unused_tier_samples)<sample_limit: unused_tier_samples.append(sample)
        for tier in sorted(drug_tiers & plan_tiers):
            if (key,tier) not in initial_30:
                missing_context_count+=1
                if len(missing_context_samples)<sample_limit: missing_context_samples.append({"plan_key":list(key),"tier":tier})
    add("formulary_tier_has_plan_cost","ERROR",missing_tier_count,missing_tier_samples,
        "Every drug tier used by a plan's formulary must have a cost rule for that plan.")
    add("cost_tier_used_by_formulary","WARNING",unused_tier_count,unused_tier_samples,
        "Cost tiers not used by either basic or excluded-drug formularies require review.")
    add("cost_tier_used_by_excluded_drugs","INFO",supplemental_tier_count,supplemental_tier_samples,
        "Cost tier is intentionally used for supplemental coverage of excluded drugs.")
    add("tier_has_initial_30_day_context","WARNING",missing_context_count,missing_context_samples,
        "A used tier should normally have initial-coverage 30-day cost sharing.")

    insulin_orphans=0; insulin_tier_mismatch=0; insulin_samples=[]
    for row in _rows(paths["insulin_beneficiary_cost"]):
        key=(row["contract_id"],row["plan_id"],row["segment_id"])
        if key not in plan_keys: insulin_orphans+=1
        elif row["tier"] and row["tier"] not in cost_tiers.get(key,set()):
            insulin_tier_mismatch+=1
            if len(insulin_samples)<sample_limit: insulin_samples.append({"plan_key":list(key),"tier":row["tier"]})
    add("insulin_plan_exists","ERROR",insulin_orphans,[],"Every insulin-cost row must link to a plan.")
    add("insulin_tier_has_general_cost_tier","WARNING",insulin_tier_mismatch,insulin_samples,
        "A populated insulin tier should also occur in beneficiary cost.")

    indication_orphans=0; indication_mismatch=0; indication_samples=[]
    for row in _rows(paths["indication_based_coverage"]):
        cp=(row["contract_id"],row["plan_id"])
        keys=[key for key in plan_keys if key[:2]==cp]
        if not keys: indication_orphans+=1; continue
        if not any(_pair_digest(plan_formulary[key],row["rxcui"]) in formulary_drugs for key in keys):
            indication_mismatch+=1
            if len(indication_samples)<sample_limit: indication_samples.append({"contract_plan":list(cp),"rxcui":row["rxcui"]})
    add("indication_plan_exists","ERROR",indication_orphans,[],"Every indication row must link to a plan.")
    add("indication_drug_in_plan_formulary","ERROR",indication_mismatch,indication_samples,
        "Indication-covered RxCUI must occur in that plan's basic formulary.")
    add("plan_geography_matches_contract_type","ERROR",len(plan_geo_issues),plan_geo_issues,
        "H contracts use county, R contracts MA region, and S contracts PDP region.")

    errors=sum(c["failure_count"] for c in checks if c["severity"]=="ERROR")
    warnings=sum(c["failure_count"] for c in checks if c["severity"]=="WARNING")
    status="FAIL" if errors else ("PASS_WITH_WARNINGS" if warnings else "PASS")
    report={"status":status,"generated_at_utc":datetime.now(timezone.utc).isoformat(),
            "processed_dir":str(processed_dir),"error_count":errors,"warning_count":warnings,
            "checks":checks,"scope":"County/State + Plan + Drug + days supply/coverage phase"}
    (reports_dir/"cross_validation_report.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    with (reports_dir/"cross_validation_summary.csv").open("w",encoding="utf-8",newline="") as handle:
        writer=csv.writer(handle,lineterminator="\n"); writer.writerow(("check","severity","failure_count","description"))
        for check in checks: writer.writerow((check["check"],check["severity"],check["failure_count"],check["description"]))
    if strict and errors: raise CrossValidationError(f"Cross-validation failed with {errors} errors")
    return report
