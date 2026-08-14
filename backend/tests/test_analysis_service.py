import unittest
from types import SimpleNamespace as NS
from unittest.mock import ANY,patch
from services.analysis import (AmbiguousDrugProduct,AnalysisInput,CostRuleNotFound,
    PlanNotInServiceArea,analyze)

def plan(contract="H0028",plan_id="007",name="Test Plan",formulary="00026408"):
    return NS(contract_id=contract,plan_id=plan_id,segment_id="000",plan_name=name,
              formulary_id=formulary,premium=35.60,deductible=615)

def product(tier=3,ndc="00002143380",pa="Y",st="N",ql="Y"):
    return NS(ndc=ndc,tier_level_value=tier,quantity_limit_yn=ql,
        quantity_limit_amount="2" if ql=="Y" else None,
        quantity_limit_days="28" if ql=="Y" else None,
        prior_authorization_yn=pa,step_therapy_yn=st,selected_drug_yn="N")

def cost(kind=2,amount=0.25,coverage=1,days=1,tier=3,deductible="Y"):
    return NS(contract_id="present",coverage_level=coverage,days_supply=days,
        tier=tier,tier_specialty_yn="N",ded_applies_yn=deductible,
        cost_type_pref=0,cost_amt_pref=0,
        cost_type_nonpref=kind,cost_amt_nonpref=amount,
        cost_type_mail_pref=kind,cost_amt_mail_pref=amount,
        cost_type_mail_nonpref=kind,cost_amt_mail_nonpref=amount)

def drug(insulin="N"):
    return {"rxcui":"1551300","drug_display_name":"Trulicity",
        "ingredient":None,"brand_name":None,"strength":None,"dose_form":None,
        "is_insulin":insulin,"lookup_status":"success"}

def configure(repo,resolved_plan=None,resolved_product=None,resolved_cost=None):
    repo.get_plan_in_service_area.return_value=resolved_plan or plan()
    repo.get_drug_name.return_value=drug()
    repo.get_formulary_products.return_value=[resolved_product or product()]
    repo.get_cost_rule.return_value=resolved_cost or cost()
    repo.get_indications.return_value=[]
    repo.get_excluded_drugs.return_value=[]
    repo.get_insulin_rule.return_value=None

class AnalysisServiceTest(unittest.TestCase):
    @patch("services.analysis.repo")
    def test_county_coinsurance_analysis(self,repo):
        configure(repo)
        request=AnalysisInput("county","28100","H0028","007","000",
                              "1551300",1,1,"00002143380")
        result=analyze(object(),request)
        channel=result["cost_sharing"]["channels"]["standard_retail"]
        self.assertEqual(("coinsurance",0.25),(channel["type"],channel["amount"]))
        self.assertTrue(result["coverage"]["restrictions"]["prior_authorization"])
        self.assertEqual("high",result["optimization_opportunity"]["overall_opportunity"]["level"])

    @patch("services.analysis.repo")
    def test_ma_region_copay_analysis(self,repo):
        configure(repo,plan("R0110","003","Humana Full Access","00026408"),
                  product(),cost(1,47))
        request=AnalysisInput("ma_region","16","R0110","003","000",
                              "1551300",1,1,"00002143380")
        result=analyze(object(),request)
        self.assertEqual("copay",result["cost_sharing"]["channels"]["standard_retail"]["type"])
        self.assertEqual(47.0,result["cost_sharing"]["channels"]["standard_retail"]["amount"])
        repo.get_plan_in_service_area.assert_called_once_with(
            ANY,"ma_region","16","R0110","003","000")

    @patch("services.analysis.repo")
    def test_pdp_region_copay_analysis(self,repo):
        configure(repo,plan("S1030","001","BlueRx Enhanced Plus","00026207"),
                  product(),cost(1,47))
        request=AnalysisInput("pdp_region","12","S1030","001","000",
                              "1551300",1,1,"00002143380")
        result=analyze(object(),request)
        self.assertEqual("BlueRx Enhanced Plus",result["plan"]["plan_name"])
        self.assertEqual("copay",result["cost_sharing"]["channels"]["standard_mail"]["type"])

    @patch("services.analysis.repo")
    def test_sixty_day_coinsurance(self,repo):
        configure(repo,plan("H0029","007","Wellcare Dual Liberty","00026330"),
                  product(),cost(2,0.25,days=4))
        request=AnalysisInput("county","50000","H0029","007","000",
                              "1551300",1,4,"00002143380")
        result=analyze(object(),request)
        self.assertEqual("60 days",result["cost_sharing"]["days_supply_label"])
        self.assertEqual(0.25,result["cost_sharing"]["channels"]["preferred_mail"]["amount"])

    @patch("services.analysis.repo")
    def test_missing_cost_rule_returns_available_contexts(self,repo):
        configure(repo);repo.get_cost_rule.return_value=None
        repo.get_available_cost_contexts.return_value=[
            {"coverage_level":1,"days_supply":1},{"coverage_level":1,"days_supply":2}]
        request=AnalysisInput("pdp_region","12","S1030","001","000",
                              "1551300",1,4,"00002143380")
        with self.assertRaises(CostRuleNotFound) as caught:analyze(object(),request)
        self.assertEqual(2,len(caught.exception.details["available_contexts"]))

    @patch("services.analysis.repo")
    def test_plan_outside_service_area_is_rejected(self,repo):
        repo.get_plan_in_service_area.return_value=None
        request=AnalysisInput("county","99999","H0028","007","000",
                              "1551300",1,1,"00002143380")
        with self.assertRaises(PlanNotInServiceArea):analyze(object(),request)
        repo.get_formulary_products.assert_not_called()

    @patch("services.analysis.repo")
    def test_ambiguous_ndc_outcomes_require_product_selection(self,repo):
        configure(repo);repo.get_formulary_products.return_value=[
            product(3,"00002143380"),product(4,"00002143480",pa="N")]
        request=AnalysisInput("county","28100","H0028","007","000",
                              "1551300",1,1,None)
        with self.assertRaises(AmbiguousDrugProduct) as caught:analyze(object(),request)
        self.assertEqual(2,len(caught.exception.details["candidate_ndcs"]))

    @patch("services.analysis.repo")
    def test_indication_based_coverage_is_access_signal(self,repo):
        configure(repo);repo.get_indications.return_value=[NS(disease="Type 2 diabetes mellitus")]
        request=AnalysisInput("county","28100","H0028","007","000",
                              "1551300",1,1,"00002143380")
        result=analyze(object(),request)
        self.assertEqual(["Type 2 diabetes mellitus"],result["coverage"]["indications"])
        self.assertIn("Coverage depends on an approved indication",
                      result["optimization_opportunity"]["access_barriers"]["reasons"])

    @patch("services.analysis.repo")
    def test_supplemental_excluded_drug_coverage(self,repo):
        configure(repo);repo.get_formulary_products.return_value=[]
        repo.get_excluded_drugs.return_value=[NS(tier=6,quantity_limit_yn="N",
            quantity_limit_amount=None,quantity_limit_days=None,prior_auth_yn="N",
            step_therapy_yn="N",capped_benefit_yn="Y")]
        repo.get_cost_rule.return_value=cost(1,20,tier=6)
        request=AnalysisInput("county","28100","H0028","007","000",
                              "999999",1,1,None)
        result=analyze(object(),request)
        self.assertEqual("supplemental_excluded_drug",result["coverage"]["status"])
        self.assertTrue(result["coverage"]["restrictions"]["capped_benefit"])

    @patch("services.analysis.repo")
    def test_insulin_specific_rule_is_returned_separately(self,repo):
        configure(repo);repo.get_drug_name.return_value=drug("Y")
        repo.get_insulin_rule.return_value=NS(tier=3,days_supply=1,
            copay_amt_pref_insln=35,copay_amt_nonpref_insln=35,
            copay_amt_mail_pref_insln=35,copay_amt_mail_nonpref_insln=35,
            coin_amt_pref_insln=0.25,coin_amt_nonpref_insln=0.25,
            coin_amt_mail_pref_insln=0.25,coin_amt_mail_nonpref_insln=0.25)
        request=AnalysisInput("county","28100","H0028","007","000",
                              "1551300",1,1,"00002143380")
        result=analyze(object(),request)
        self.assertEqual(35.0,result["cost_sharing"]["insulin_rule"]["copay_amt_pref_insln"])
        repo.get_insulin_rule.assert_called_once()

if __name__=="__main__":unittest.main()
