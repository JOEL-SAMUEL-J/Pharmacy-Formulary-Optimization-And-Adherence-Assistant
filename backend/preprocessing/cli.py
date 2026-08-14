"""Command-line entry point."""
import argparse, json
from pathlib import Path
from .pipeline import PipelineError, run
from .cross_validation import CrossValidationError, run_cross_validation

def main(argv=None):
    parser=argparse.ArgumentParser(description="Validate and clean CMS 2026 Part D PUF files")
    sub=parser.add_subparsers(dest="command",required=True)
    cmd=sub.add_parser("validate",help="validate all seven raw files")
    cmd.add_argument("--raw-dir",type=Path,default=Path("data/raw"))
    cmd.add_argument("--processed-dir",type=Path,default=Path("data/processed"))
    cmd.add_argument("--reports-dir",type=Path,default=Path("data/reports"))
    cmd.add_argument("--quarantine-dir",type=Path,default=Path("data/quarantine"))
    cmd.add_argument("--strict",action="store_true",help="fail when any row is quarantined")
    cross=sub.add_parser("cross-validate",help="verify semantic linkage across cleaned files")
    cross.add_argument("--processed-dir",type=Path,default=Path("data/processed"))
    cross.add_argument("--reports-dir",type=Path,default=Path("data/reports"))
    cross.add_argument("--strict",action="store_true",help="fail when cross-file errors exist")
    args=parser.parse_args(argv)
    try:
        if args.command == "cross-validate":
            report=run_cross_validation(args.processed_dir,args.reports_dir,args.strict)
            print(json.dumps({"status":report["status"],"error_count":report["error_count"],
                              "warning_count":report["warning_count"]},indent=2)); return 0
        report=run(args.raw_dir,args.processed_dir,args.reports_dir,args.quarantine_dir,args.strict)
    except (PipelineError,CrossValidationError,OSError,ValueError) as exc:
        print(f"VALIDATION FAILED: {exc}"); return 1
    print(json.dumps({"status":report["status"],**report["totals"]},indent=2)); return 0
