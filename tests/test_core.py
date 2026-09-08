import unittest
from foresight import Belief, Controller, Evidence, Forecast, Requirement, State, observe
from foresight.demo import run


class ControlTests(unittest.TestCase):
    def setUp(self):
        self.evidence = Evidence("e", "eligible", "yes", "policy", True, True)
        self.controller = Controller((Requirement("eligible", "yes"),), {"approve": ("eligible",)})
        self.forecast = Forecast("check", (self.evidence,),
                                 (Belief("eligible", "yes", ("e",)),), "approve", .8)

    def test_predictions_never_complete_actual_state(self):
        state = State()
        self.assertEqual(self.controller.assess(state, self.forecast).unsupported_beliefs, ())
        self.assertFalse(self.controller.complete(state))

    def test_observation_can_complete(self):
        transition = observe(State(), self.forecast, (self.evidence,), action_succeeded=True)
        self.assertTrue(self.controller.complete(transition.state))
        self.assertEqual(transition.intervention, "continue")
        self.assertAlmostEqual(transition.brier_score, .04)

    def test_stale_source_does_not_support_belief(self):
        old = Evidence("e", "eligible", "yes", "policy", True, False)
        f = Forecast("check", (old,), self.forecast.beliefs, "approve", .9)
        self.assertEqual(self.controller.assess(State(), f).intervention, "verify_evidence")

    def test_missing_citation_does_not_support_belief(self):
        f = Forecast("check", (self.evidence,), (Belief("eligible", "yes", ("invented",)),), "approve", .9)
        self.assertEqual(self.controller.assess(State(), f).unsupported_beliefs, ("eligible",))

    def test_contradiction_blocks_completion(self):
        contrary = Evidence("other", "eligible", "no", "other-policy", True, True)
        state = State((self.evidence, contrary))
        self.assertFalse(self.controller.complete(state))
        self.assertTrue(self.controller.assess(state, self.forecast).unsupported_beliefs)

    def test_mismatch_triggers_revision(self):
        actual = Evidence("other", "eligible", "no", "policy", True, True)
        transition = observe(State(), self.forecast, (actual,), action_succeeded=True)
        self.assertEqual(transition.intervention, "revise_belief")
        self.assertFalse(self.controller.complete(transition.state))
        self.assertEqual(transition.state.evidence, (actual,))

    def test_failed_tool_is_distinct_from_wrong_prediction(self):
        transition = observe(State(), self.forecast, (), action_succeeded=False)
        self.assertEqual(transition.intervention, "inspect_tool_failure")
        self.assertAlmostEqual(transition.brier_score, .64)

    def test_evidence_cannot_be_overwritten(self):
        changed = Evidence("e", "eligible", "no", "policy", True, True)
        with self.assertRaises(ValueError):
            observe(State((self.evidence,)), self.forecast, (changed,), action_succeeded=True)

    def test_duplicate_ids_rejected(self):
        with self.assertRaises(ValueError):
            State((self.evidence, self.evidence))

    def test_nonfinite_probability_rejected(self):
        for p in (float("nan"), float("inf"), -.1, 1.1):
            with self.assertRaises(ValueError):
                Forecast("a", (), (), "b", p)

    def test_demo_prevents_unsupported_approval(self):
        result = run()
        self.assertEqual(result["selected"]["action"], "check_current_policy")
        self.assertFalse(result["completion_allowed"])

    def test_next_decision_requires_explicit_justified_belief(self):
        f = Forecast("check", (self.evidence,), (), "approve", .9)
        assessment = self.controller.assess(State(), f)
        self.assertEqual(assessment.decision_gaps, ("eligible",))
        self.assertEqual(assessment.intervention, "verify_evidence")

    def test_unknown_decision_cannot_bypass_gate(self):
        f = Forecast("check", (self.evidence,), self.forecast.beliefs, "publish", .9)
        self.assertEqual(self.controller.assess(State(), f).intervention, "verify_evidence")

    def test_supported_negative_belief_is_distinct_from_goal_completion(self):
        negative = Evidence("negative", "eligible", "no", "policy", True, True)
        forecast = Forecast("check", (negative,),
                            (Belief("eligible", "no", ("negative",)),), "approve", .9)
        assessment = self.controller.assess(State(), forecast)
        self.assertEqual(assessment.unsupported_beliefs, ())
        self.assertEqual(assessment.decision_gaps, ("eligible",))
        self.assertFalse(self.controller.complete(State((negative,))))


if __name__ == "__main__":
    unittest.main()
