import csv, tempfile, unittest
from pathlib import Path
from preprocessing.pipeline import PipelineError, run
from preprocessing.schemas import SCHEMAS
from preprocessing.readers import detect_source, rows

class PipelineTest(unittest.TestCase):
    def row(self,name):
        values={c:"1" for c in SCHEMAS[name].columns}
        values.update(contract_id="H1234",plan_id="001",segment_id="000",formulary_id="00000001",
          contract_name="Contract",plan_name="Plan",premium="1.00",deductible="0.00",
          ma_region_code="",pdp_region_code="",state="CA",county_code="06001",snp="0",
          plan_suppressed_yn="N",statename="California",county="Alameda",ma_region="",pdp_region="",
          formulary_version="00001",contract_year="2026",rxcui="12345678",ndc="00000000001",
          tier_level_value="1",quantity_limit_yn="N",quantity_limit_amount="",quantity_limit_days="",
          prior_authorization_yn="N",step_therapy_yn="N",selected_drug_yn="N",tier="1",
          prior_auth_yn="N",capped_benefit_yn="N",disease="Disease",coverage_level="1",
          days_supply="1",tier_specialty_yn="N",ded_applies_yn="N")
        return {c:values[c] for c in SCHEMAS[name].columns}

    def test_all_seven_files_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); raw=root/"raw"; raw.mkdir()
            for name,schema in SCHEMAS.items():
                with (raw/schema.filename).open("w",newline="",encoding="utf-8") as handle:
                    writer=csv.DictWriter(handle,fieldnames=list(schema.columns),delimiter="|")
                    writer.writeheader(); writer.writerow(self.row(name))
            report=run(raw,root/"processed",root/"reports",root/"quarantine",strict=True)
            self.assertEqual("PASS",report["status"]); self.assertEqual(7,report["totals"]["accepted_rows"])

    def test_missing_files_fail_cleanly(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); (root/"raw").mkdir()
            with self.assertRaises(PipelineError): run(root/"raw",root/"processed",root/"reports",root/"quarantine")

    def test_ascii_prefix_with_late_cp1252_character(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"source.txt"
            path.write_bytes(b"name|description\n" + b"A"*70000 + b"|CMS \xd3text\n")
            source=detect_source(path)
            self.assertEqual("cp1252",source.encoding)
            self.assertIn("Ó",next(rows(source))["description"])

if __name__ == "__main__": unittest.main()
