"""Optional read-only integration tests against the populated MySQL database."""
import os,unittest
from database.session import create_session_factory
from services.analysis import AnalysisInput,analyze

@unittest.skipUnless(os.getenv("RUN_LIVE_DB_TESTS")=="1" and os.getenv("DATABASE_URL"),
                     "set RUN_LIVE_DB_TESTS=1 and DATABASE_URL to run MySQL tests")
class LiveMySQLAnalysisTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.Session=create_session_factory()

    def run_case(self,request):
        with self.Session() as session:return analyze(session,request)

    def test_county_path(self):
        result=self.run_case(AnalysisInput("county","28100","H0028","007","000",
            "1551300",1,1,"00002143380"))
        channel=result["cost_sharing"]["channels"]["standard_retail"]
        self.assertEqual(("coinsurance",0.25),(channel["type"],channel["amount"]))

    def test_ma_region_path(self):
        result=self.run_case(AnalysisInput("ma_region","16","R0110","003","000",
            "1551300",1,1,"00002143380"))
        channel=result["cost_sharing"]["channels"]["standard_retail"]
        self.assertEqual(("copay",47.0),(channel["type"],channel["amount"]))

    def test_pdp_region_path(self):
        result=self.run_case(AnalysisInput("pdp_region","12","S1030","001","000",
            "1551300",1,1,"00002143380"))
        channel=result["cost_sharing"]["channels"]["standard_retail"]
        self.assertEqual(("copay",47.0),(channel["type"],channel["amount"]))

    def test_sixty_day_path(self):
        result=self.run_case(AnalysisInput("county","50000","H0029","007","000",
            "1551300",1,4,"00002143380"))
        self.assertEqual("60 days",result["cost_sharing"]["days_supply_label"])
        self.assertEqual(0.25,result["cost_sharing"]["channels"]["preferred_mail"]["amount"])

if __name__=="__main__":unittest.main()
