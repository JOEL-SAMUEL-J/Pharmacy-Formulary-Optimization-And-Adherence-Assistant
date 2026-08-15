import argparse, csv, hashlib, json, os
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import create_engine, func, insert, select
from sqlalchemy.engine import Engine
from .models import (Base, BeneficiaryCost, ExcludedDrug, FormularyDrug,
    GeographicLocator, IndicationCoverage, InsulinCost, LoadRun, Plan,
    PlanServiceArea)

FILES={
    GeographicLocator:"geographic_locator.csv", FormularyDrug:"basic_drugs_formulary.csv",
    BeneficiaryCost:"beneficiary_cost.csv", ExcludedDrug:"excluded_drugs_formulary.csv",
    IndicationCoverage:"indication_based_coverage.csv",
    InsulinCost:"insulin_beneficiary_cost.csv"}
SOURCE_NAMES={model:filename.removesuffix(".csv") for model,filename in FILES.items()}
SOURCE_NAMES[FormularyDrug]="basic_drugs_formulary"
SOURCE_NAMES[ExcludedDrug]="excluded_drugs_formulary"
SOURCE_NAMES[IndicationCoverage]="indication_based_coverage"
SOURCE_NAMES[InsulinCost]="insulin_beneficiary_cost"

class LoadError(RuntimeError): pass

def sha256(path: Path):
    digest=hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda:handle.read(1024*1024),b""): digest.update(chunk)
    return digest.hexdigest()

def read_gate(reports_dir: Path, processed_dir: Path):
    validation_path=reports_dir/"validation_report.json"
    cross_path=reports_dir/"cross_validation_report.json"
    validation=json.loads(validation_path.read_text(encoding="utf-8"))
    cross=json.loads(cross_path.read_text(encoding="utf-8"))
    if validation.get("status")!="PASS": raise LoadError("Row validation report is not PASS")
    if cross.get("status")!="PASS": raise LoadError("Cross-validation report is not PASS")
    for data in validation["datasets"].values():
        path=processed_dir/data["processed_file"]
        if not path.exists(): raise LoadError(f"Missing processed file: {path}")
        if sha256(path)!=data["processed_sha256"]: raise LoadError(f"Processed hash mismatch: {path.name}")
    return validation,validation_path,cross_path

def engine_from_env(echo=False):
    url=os.environ.get("DATABASE_URL")
    if not url: raise LoadError("DATABASE_URL is required (mysql+pymysql://...?...charset=utf8mb4)")
    if not url.startswith("mysql+"): raise LoadError("DATABASE_URL must use a MySQL SQLAlchemy dialect/driver")
    return create_engine(url,pool_pre_ping=True,echo=echo)

def clean(row): return {key:(None if value=="" else value) for key,value in row.items()}

def batches(path: Path, size: int):
    with path.open("r",encoding="utf-8",newline="") as handle:
        reader=csv.DictReader(handle); batch=[]
        for row in reader:
            batch.append(clean(row))
            if len(batch)>=size: yield batch; batch=[]
        if batch: yield batch

def insert_csv(engine: Engine, model, path: Path, batch_size: int):
    total=0
    with engine.begin() as connection:
        for batch in batches(path,batch_size):
            connection.execute(insert(model),batch); total+=len(batch)
    return total

def insert_plans(engine: Engine, path: Path, batch_size: int):
    plan_fields=("contract_id","plan_id","segment_id","contract_name","plan_name",
                 "formulary_id","premium","deductible","snp","plan_suppressed_yn")
    area_fields=("contract_id","plan_id","segment_id","ma_region_code",
                 "pdp_region_code","state","county_code")
    unique_plans={}; plan_rows=[]; area_rows=[]; area_total=0
    def flush(connection):
        nonlocal plan_rows,area_rows
        if plan_rows: connection.execute(insert(Plan),plan_rows); plan_rows=[]
        if area_rows: connection.execute(insert(PlanServiceArea),area_rows); area_rows=[]
    with path.open("r",encoding="utf-8",newline="") as handle, engine.begin() as connection:
        for raw in csv.DictReader(handle):
            key=tuple(raw[field] for field in plan_fields[:3])
            if key not in unique_plans:
                unique_plans[key]=True
                plan_rows.append({field:raw[field] for field in plan_fields})
            area_rows.append({field:raw[field] for field in area_fields}); area_total+=1
            if len(area_rows)>=batch_size: flush(connection)
        flush(connection)
    return len(unique_plans),area_total

def assert_empty(engine: Engine):
    with engine.connect() as connection:
        if connection.scalar(select(func.count()).select_from(LoadRun)):
            raise LoadError("Database already contains a completed load; use a fresh schema")

def verify_counts(engine: Engine, expected: dict):
    models=(PlanServiceArea,GeographicLocator,FormularyDrug,BeneficiaryCost,
            ExcludedDrug,IndicationCoverage,InsulinCost)
    names=("plan_information","geographic_locator","basic_drugs_formulary",
           "beneficiary_cost","excluded_drugs_formulary","indication_based_coverage",
           "insulin_beneficiary_cost")
    actual={}
    with engine.connect() as connection:
        for model,name in zip(models,names):
            count=connection.scalar(select(func.count()).select_from(model))
            wanted=expected["datasets"][name]["accepted_rows"]
            actual[model.__tablename__]=count
            if count!=wanted: raise LoadError(f"{model.__tablename__}: loaded {count}, expected {wanted}")
    return actual

def load(engine: Engine,processed_dir: Path,reports_dir: Path,batch_size=5000):
    validation,validation_path,cross_path=read_gate(reports_dir,processed_dir)
    Base.metadata.create_all(engine); assert_empty(engine)
    loaded={}
    loaded["plans"],loaded["plan_service_areas"]=insert_plans(
        engine,processed_dir/"plan_information.csv",batch_size)
    for model,filename in FILES.items():
        loaded[model.__tablename__]=insert_csv(engine,model,processed_dir/filename,batch_size)
    verified=verify_counts(engine,validation)
    with engine.begin() as connection:
        connection.execute(insert(LoadRun),{"loaded_at_utc":datetime.now(timezone.utc).replace(tzinfo=None),
            "validation_report_sha256":sha256(validation_path),
            "cross_validation_report_sha256":sha256(cross_path),
            "total_source_rows":validation["totals"]["accepted_rows"]})
    return {"status":"PASS","loaded":loaded,"verified":verified}

def main(argv=None):
    parser=argparse.ArgumentParser(description="Create and load the MySQL CMS formulary schema")
    sub=parser.add_subparsers(dest="command",required=True)
    for command in ("init","load","verify"):
        item=sub.add_parser(command)
        item.add_argument("--echo-sql",action="store_true")
        if command=="load":
            item.add_argument("--processed-dir",type=Path,default=Path("data/processed"))
            item.add_argument("--reports-dir",type=Path,default=Path("data/reports"))
            item.add_argument("--batch-size",type=int,default=5000)
    args=parser.parse_args(argv)
    try:
        engine=engine_from_env(args.echo_sql)
        if args.command=="init": Base.metadata.create_all(engine); result={"status":"SCHEMA_READY"}
        elif args.command=="load": result=load(engine,args.processed_dir,args.reports_dir,args.batch_size)
        else:
            with engine.connect() as connection:
                result={"status":"PASS","load_runs":connection.scalar(select(func.count()).select_from(LoadRun))}
    except Exception as exc:
        print(f"DATABASE STEP FAILED: {exc}"); return 1
    print(json.dumps(result,indent=2,sort_keys=True)); return 0
