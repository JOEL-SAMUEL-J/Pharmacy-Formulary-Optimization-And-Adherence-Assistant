"""Seven-file streaming orchestrator with atomic reproducible outputs."""
import csv, hashlib, json, os, platform
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from .normalize import canonical_value, column_name, normalize_row
from .readers import detect_source, raw_headers, rows
from .schemas import PROCESSING_ORDER, SCHEMAS
from .validation import Issue, business_rules, grain_digest, linkage_issues, validate_row

class PipelineError(RuntimeError): pass

def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024*1024), b""): digest.update(chunk)
    return digest.hexdigest()

def build_references(raw_dir):
    refs = {"plan_keys":set(), "contract_plan_keys":set(), "formulary_ids":set(), "county_codes":set()}
    for name in ("plan_information", "geographic_locator"):
        schema, path = SCHEMAS[name], raw_dir / SCHEMAS[name].filename
        if not path.exists(): continue
        for raw in rows(detect_source(path)):
            row = normalize_row(raw, schema.aliases)
            if name == "plan_information":
                refs["plan_keys"].add(tuple(row.get(c,"") for c in ("contract_id","plan_id","segment_id")))
                refs["contract_plan_keys"].add((row.get("contract_id",""),row.get("plan_id","")))
                refs["formulary_ids"].add(row.get("formulary_id",""))
            else: refs["county_codes"].add(row.get("county_code",""))
    return refs

def run(raw_dir: Path, processed_dir: Path, reports_dir: Path, quarantine_dir: Path, strict=False):
    for directory in (processed_dir,reports_dir,quarantine_dir): directory.mkdir(parents=True,exist_ok=True)
    missing = [SCHEMAS[n].filename for n in PROCESSING_ORDER if not (raw_dir/SCHEMAS[n].filename).exists()]
    if missing: raise PipelineError("Missing required raw files: " + ", ".join(missing))
    refs = build_references(raw_dir)
    report = {"pipeline_version":"1.0.0", "schema_version":"CMS-2026",
              "generated_at_utc":datetime.now(timezone.utc).isoformat(),
              "python_version":platform.python_version(), "datasets":{}}
    for name in PROCESSING_ORDER:
        schema, path = SCHEMAS[name], raw_dir/SCHEMAS[name].filename
        source = detect_source(path)
        actual = {column_name(h) for h in raw_headers(source)}
        missing_cols = sorted(set(schema.columns)-actual)
        if missing_cols: raise PipelineError(f"{schema.filename}: missing columns {missing_cols}")
        output, bad = processed_dir/f"{name}.csv", quarantine_dir/f"{name}.jsonl"
        out_tmp, bad_tmp = output.with_suffix(".csv.tmp"), bad.with_suffix(".jsonl.tmp")
        counts, issue_counts, seen = Counter(), Counter(), set()
        with out_tmp.open("w",encoding="utf-8",newline="") as good, bad_tmp.open("w",encoding="utf-8",newline="") as reject:
            writer = csv.DictWriter(good,fieldnames=list(schema.columns),lineterminator="\n")
            writer.writeheader()
            for line, raw in enumerate(rows(source),start=2):
                counts["raw_rows"] += 1
                original = normalize_row(raw,schema.aliases)
                # CMS uses a single period as the missing numeric sentinel.
                # The 2026 insulin layout specifically permits a missing tier
                # for defined-standard plans. Convert it only where the schema
                # declares a nullable numeric field.
                for column, rule in schema.columns.items():
                    if rule.nullable and rule.kind in {"integer", "decimal"} and original.get(column) == ".":
                        original[column] = ""
                row = {c:canonical_value(original.get(c,""),rule.kind) for c,rule in schema.columns.items()}
                issues = validate_row(original,schema)+business_rules(name,row)
                digest = grain_digest(row,schema.grain)
                if digest in seen: issues.append(Issue("DUPLICATE_GRAIN",",".join(schema.grain),"duplicate natural key"))
                else: seen.add(digest)
                issues += linkage_issues(name,row,refs)
                if issues:
                    counts["quarantined_rows"] += 1
                    issue_counts.update(i.code for i in issues)
                    reject.write(json.dumps({"source_file":schema.filename,"source_row_number":line,
                        "issues":[i.__dict__ for i in issues],"row":row},sort_keys=True)+"\n")
                else:
                    writer.writerow(row); counts["accepted_rows"] += 1
        os.replace(out_tmp,output); os.replace(bad_tmp,bad)
        report["datasets"][name] = {"source_file":schema.filename,"source_sha256":sha256(path),
            "source_bytes":path.stat().st_size,"encoding":source.encoding,
            "delimiter":{"\t":"TAB"}.get(source.delimiter,source.delimiter),"grain":list(schema.grain),
            "raw_rows":counts["raw_rows"], "accepted_rows":counts["accepted_rows"],
            "quarantined_rows":counts["quarantined_rows"],
            "issue_counts":dict(sorted(issue_counts.items())),"processed_file":output.name,
            "processed_sha256":sha256(output),"quarantine_file":bad.name}
    report["totals"] = {k:sum(v.get(k,0) for v in report["datasets"].values())
                        for k in ("raw_rows","accepted_rows","quarantined_rows")}
    report["status"] = "PASS" if not report["totals"]["quarantined_rows"] else "PASS_WITH_QUARANTINE"
    (reports_dir/"validation_report.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    with (reports_dir/"row_counts.csv").open("w",encoding="utf-8",newline="") as handle:
        writer=csv.writer(handle,lineterminator="\n"); writer.writerow(("dataset","raw_rows","accepted_rows","quarantined_rows","status"))
        for name,data in report["datasets"].items():
            writer.writerow((name,data["raw_rows"],data["accepted_rows"],data["quarantined_rows"],
                             "PASS" if not data["quarantined_rows"] else "QUARANTINE"))
    if strict and report["totals"]["quarantined_rows"]:
        raise PipelineError(f"Strict validation failed: {report['totals']['quarantined_rows']} rows quarantined")
    return report
