"""Focused tests for RxNorm-confirmed insulin-cost matching."""

import unittest
from types import SimpleNamespace as NS
from unittest.mock import patch

from services.analysis import AnalysisInput, analyze


def plan():
    return NS(
        contract_id="H0169",
        plan_id="001",
        segment_id="000",
        plan_name="Test Insulin Plan",
        formulary_id="00026002",
        premium=0,
        deductible=0,
    )


def product():
    return NS(
        ndc="00002775205",
        tier_level_value=3,
        quantity_limit_yn="N",
        quantity_limit_amount=None,
        quantity_limit_days=None,
        prior_authorization_yn="N",
        step_therapy_yn="N",
        selected_drug_yn="N",
    )


def beneficiary_cost():
    return NS(
        coverage_level=1,
        days_supply=1,
        tier=3,
        tier_specialty_yn="N",
        ded_applies_yn="N",
        cost_type_pref=1,
        cost_amt_pref=35,
        cost_type_nonpref=1,
        cost_amt_nonpref=35,
        cost_type_mail_pref=1,
        cost_amt_mail_pref=35,
        cost_type_mail_nonpref=1,
        cost_amt_mail_nonpref=35,
    )


def insulin_cost():
    return NS(
        tier=3,
        days_supply=1,
        copay_amt_pref_insln=35,
        copay_amt_nonpref_insln=35,
        copay_amt_mail_pref_insln=35,
        copay_amt_mail_nonpref_insln=35,
        coin_amt_pref_insln=None,
        coin_amt_nonpref_insln=None,
        coin_amt_mail_pref_insln=None,
        coin_amt_mail_nonpref_insln=None,
    )


def drug(
    *,
    is_insulin="Y",
    enrichment_status="success",
    match_reason="RXNORM_INGREDIENT",
):
    return {
        "rxcui": "1926331",
        "drug_display_name": (
            "0.5 UNIT Doses 3 ML insulin lispro "
            "100 UNT/ML Pen Injector"
        ),
        "ingredient": "insulin lispro",
        "ingredient_rxcuis": "86009",
        "brand_name": None,
        "strength": None,
        "dose_form": None,
        "is_insulin": is_insulin,
        "insulin_match_reason": match_reason,
        "enrichment_status": enrichment_status,
        "lookup_status": "success",
    }


def request():
    return AnalysisInput(
        "county",
        "00000",
        "H0169",
        "001",
        "000",
        "1926331",
        1,
        1,
        "00002775205",
    )


def configure(repo):
    repo.get_plan_in_service_area.return_value = plan()
    repo.get_formulary_products.return_value = [
        product()
    ]
    repo.get_cost_rule.return_value = (
        beneficiary_cost()
    )
    repo.get_available_cost_contexts.return_value = []
    repo.get_indications.return_value = []
    repo.get_excluded_drugs.return_value = []


class InsulinMatchingTest(unittest.TestCase):
    @patch("services.analysis.repo")
    def test_confirmed_insulin_returns_rule(
        self,
        repo,
    ):
        configure(repo)
        repo.get_drug_name.return_value = drug()
        repo.get_insulin_rule.return_value = (
            insulin_cost()
        )

        result = analyze(object(), request())
        insulin = result["cost_sharing"]["insulin"]

        self.assertTrue(insulin["is_insulin"])
        self.assertEqual(
            "RXNORM_INGREDIENT",
            insulin["match_reason"],
        )
        self.assertEqual(
            "INSULIN COST RULE FOUND",
            insulin["resolution_status"],
        )
        self.assertEqual(
            35.0,
            insulin["rule"][
                "copay_amt_pref_insln"
            ],
        )
        # Original field remains available.
        self.assertEqual(
            35.0,
            result["cost_sharing"][
                "insulin_rule"
            ]["copay_amt_pref_insln"],
        )
        repo.get_insulin_rule.assert_called_once()

    @patch("services.analysis.repo")
    def test_non_insulin_does_not_query_rule(
        self,
        repo,
    ):
        configure(repo)
        repo.get_drug_name.return_value = drug(
            is_insulin="N",
            match_reason="NOT_INSULIN",
        )

        result = analyze(object(), request())
        insulin = result["cost_sharing"]["insulin"]

        self.assertFalse(insulin["is_insulin"])
        self.assertEqual(
            "NOT AN INSULIN DRUG",
            insulin["resolution_status"],
        )
        self.assertIsNone(insulin["rule"])
        self.assertIsNone(
            result["cost_sharing"]["insulin_rule"]
        )
        repo.get_insulin_rule.assert_not_called()

    @patch("services.analysis.repo")
    def test_pending_enrichment_is_unresolved(
        self,
        repo,
    ):
        configure(repo)
        repo.get_drug_name.return_value = drug(
            is_insulin="N",
            enrichment_status="pending",
            match_reason=None,
        )

        result = analyze(object(), request())
        insulin = result["cost_sharing"]["insulin"]

        self.assertIsNone(insulin["is_insulin"])
        self.assertEqual(
            "INSULIN STATUS UNRESOLVED",
            insulin["resolution_status"],
        )
        repo.get_insulin_rule.assert_not_called()

    @patch("services.analysis.repo")
    def test_confirmed_insulin_without_cost_rule(
        self,
        repo,
    ):
        configure(repo)
        repo.get_drug_name.return_value = drug()
        repo.get_insulin_rule.return_value = None

        result = analyze(object(), request())
        insulin = result["cost_sharing"]["insulin"]

        self.assertTrue(insulin["is_insulin"])
        self.assertEqual(
            "NO MATCHING INSULIN COST RULE",
            insulin["resolution_status"],
        )
        self.assertIsNone(insulin["rule"])
        repo.get_insulin_rule.assert_called_once()


if __name__ == "__main__":
    unittest.main()
