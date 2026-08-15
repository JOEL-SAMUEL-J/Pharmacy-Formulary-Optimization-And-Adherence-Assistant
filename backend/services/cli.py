"""Temporary CLI for exercising the service before FastAPI is added."""
import argparse,json
from database.session import create_session_factory
from .analysis import AnalysisError,AnalysisInput,analyze

def main(argv=None):
    parser=argparse.ArgumentParser(description="Analyze one plan-drug coverage context")
    parser.add_argument("--area-type",required=True,choices=("county","ma_region","pdp_region"))
    parser.add_argument("--area-code",required=True)
    parser.add_argument("--contract-id",required=True)
    parser.add_argument("--plan-id",required=True)
    parser.add_argument("--segment-id",default="000")
    parser.add_argument("--rxcui",required=True)
    parser.add_argument("--ndc")
    parser.add_argument("--coverage-level",required=True,type=int,choices=(0,1,3))
    parser.add_argument("--days-supply",required=True,type=int,choices=(1,2,3,4))
    args=parser.parse_args(argv)
    request=AnalysisInput(args.area_type,args.area_code,args.contract_id,args.plan_id,
        args.segment_id,args.rxcui,args.coverage_level,args.days_supply,args.ndc)
    try:
        with create_session_factory()() as session: result=analyze(session,request)
    except AnalysisError as exc:
        print(json.dumps({"status":"ERROR","code":exc.code,"message":str(exc),
                          "details":exc.details},indent=2));return 1
    except Exception as exc:
        print(json.dumps({"status":"ERROR","code":"INTERNAL_ERROR","message":str(exc)},indent=2));return 1
    print(json.dumps(result,indent=2,default=str));return 0
