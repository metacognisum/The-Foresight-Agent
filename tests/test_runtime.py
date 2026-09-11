from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from foresight import Belief, Controller, Evidence, Forecast, Requirement, State
from foresight.experiment import DocumentExecutor, HintPredictor, compare, make_scenario
from foresight.models import JsonPredictor, OllamaCompletion
from foresight.runtime import Action, JsonlTrace, Observation, realized_beliefs, run_agent


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def scenario(self, name):
        return make_scenario(name, self.root / name)

    def test_real_file_read_controls_completion_not_preview(self):
        c, actions, executor = self.scenario("contradiction")
        result = run_agent(c, actions, executor, HintPredictor())
        self.assertFalse(result["completed"])
        self.assertEqual(result["beliefs"][0]["value"], "no")
        observed = next(e for e in result["events"] if e["event"] == "observed")
        self.assertEqual(observed["comparison"]["intervention"], "revise_belief")
        self.assertFalse(observed["belief_prediction_match"])
        self.assertEqual(result["state"]["evidence"][0]["id"], "observed:current:0")

    def test_failure_replans_and_receives_history(self):
        c, actions, executor = self.scenario("tool_failure")
        histories = []
        class Recording(HintPredictor):
            def forecast(self, state, actions, controller, history):
                histories.append(history)
                return super().forecast(state, actions, controller, history)
        result = run_agent(c, actions, executor, Recording())
        self.assertTrue(result["completed"])
        self.assertEqual(result["steps"], 2)
        self.assertTrue(any(e.get("comparison", {}).get("intervention") == "inspect_tool_failure"
                            for e in histories[1] if e["event"] == "observed"))

    def test_selected_forecast_is_persisted_before_execution(self):
        c, actions, executor = self.scenario("clean")
        path = self.root / "trace.jsonl"
        sink = JsonlTrace(path)
        class Inspecting:
            def execute(inner, action):
                events = [json.loads(line) for line in path.read_text().splitlines()]
                self.assertEqual(events[-1]["event"], "selected")
                self.assertEqual(events[-2]["event"], "forecast")
                return executor.execute(action)
        result = run_agent(c, actions, Inspecting(), HintPredictor(), trace=sink)
        self.assertEqual(json.loads(path.read_text().splitlines()[-1])["completed"], result["completed"])
        with self.assertRaises(FileExistsError):
            JsonlTrace(path)

    def test_budgets_and_no_repeated_actions(self):
        c, actions, executor = self.scenario("stale_source")
        result = run_agent(c, actions, executor, max_steps=1)
        self.assertEqual(result["reason"], "step_budget")
        result = run_agent(c, actions, executor, max_cost=.4)
        self.assertEqual(result["steps"], 0)
        self.assertEqual(result["reason"], "cost_budget")
        result = run_agent(c, actions, executor)
        self.assertEqual(result["steps"], 2)
        for cost in (float("nan"), float("inf"), 0, True):
            with self.assertRaises(ValueError):
                run_agent(c, actions, executor, max_cost=cost)

    def test_all_unsupported_candidates_dispatch_read_verification(self):
        c, actions, executor = self.scenario("stale_source")
        result = run_agent(c, actions[:1], executor, HintPredictor())
        selected = next(e for e in result["events"] if e["event"] == "selected")
        self.assertEqual(selected["dispatch"], "verify_evidence")
        self.assertFalse(result["completed"])

    def test_forecast_error_executes_nothing(self):
        c, actions, executor = self.scenario("clean")
        with patch.object(executor, "execute") as execute:
            result = run_agent(c, actions, executor, JsonPredictor(lambda prompt: "not JSON"))
        execute.assert_not_called()
        self.assertEqual(result["reason"], "forecast_error")

    def test_forged_predictor_provenance_rejected(self):
        c, actions, executor = self.scenario("stale_source")
        class Forged(HintPredictor):
            def forecast(self, state, actions, controller, history):
                forecasts = super().forecast(state, actions, controller, history)
                return tuple(replace(f, evidence=tuple(replace(e, current=True) for e in f.evidence))
                             for f in forecasts)
        result = run_agent(c, actions, executor, Forged())
        self.assertEqual(result["reason"], "forecast_error")
        self.assertEqual(result["steps"], 0)

    def test_executor_cannot_promote_stale_source(self):
        c, actions, _ = self.scenario("stale_source")
        class Forged:
            def execute(self, a):
                return Observation((Evidence("x", "eligible", "yes", a.source, True, True),), True)
        with self.assertRaises(ValueError):
            run_agent(c, actions[:1], Forged())

    def test_malformed_document_never_partially_enters_state(self):
        c, actions, executor = self.scenario("clean")
        executor.documents["current"].write_text('[{"claim":"eligible","value":"yes"}, {}]')
        result = run_agent(c, actions, executor)
        self.assertFalse(result["completed"])
        self.assertEqual(result["state"]["evidence"], ())

    def test_conflicting_observations_retract_derived_belief(self):
        c = Controller((Requirement("eligible", "yes"),))
        state = State((Evidence("a", "eligible", "yes", "a", True, True),
                       Evidence("b", "eligible", "no", "b", True, True)))
        self.assertEqual(realized_beliefs(state, c), ())
        self.assertFalse(c.complete(state))

    def test_comparison_includes_benefit_and_failure(self):
        rows = {(r["scenario"], r["mode"]): r for r in compare()["results"]}
        self.assertEqual(rows["stale_source", "baseline"]["steps"], 2)
        self.assertEqual(rows["stale_source", "foresight"]["steps"], 1)
        self.assertTrue(rows["misleading_preview", "baseline"]["completed"])
        self.assertTrue(rows["misleading_preview", "foresight"]["completed"])
        self.assertEqual(rows["misleading_preview", "foresight"]["steps"], 2)
        self.assertEqual(rows["misleading_preview", "baseline"]["steps"], 1)
        limited = {(r["scenario"], r["mode"]): r for r in compare(max_steps=1)["results"]}
        self.assertFalse(limited["misleading_preview", "foresight"]["completed"])
        self.assertTrue(limited["misleading_preview", "baseline"]["completed"])
        self.assertFalse(rows["contradiction", "foresight"]["completed"])


class ModelTests(unittest.TestCase):
    def setUp(self):
        self.c = Controller((Requirement("eligible", "yes"),))
        self.a = (Action("read", "hint", "registered", True, False, .5),)
        self.item = {"action": "read", "evidence": [{"id": "p", "claim": "eligible", "value": "yes"}],
                     "beliefs": [{"claim": "eligible", "value": "yes", "evidence_ids": ["p"]}],
                     "next_decision": "complete", "success_probability": .9}

    def parse(self, items):
        return JsonPredictor(lambda prompt: json.dumps({"forecasts": items})).forecast(
            State(), self.a, self.c, ())

    def test_valid_model_output_inherits_trusted_metadata(self):
        forecast = self.parse([self.item])[0]
        self.assertEqual(forecast.cost, .5)
        self.assertFalse(forecast.evidence[0].current)
        self.assertEqual(forecast.evidence[0].source, "registered")
        self.assertEqual(self.c.assess(State(), forecast).intervention, "verify_evidence")

    def test_unknown_missing_duplicate_actions_rejected(self):
        for items in ([], [self.item, self.item], [{**self.item, "action": "shell"}]):
            with self.assertRaises(ValueError):
                self.parse(items)

    def test_schema_and_probability_validation(self):
        for changes in ({"success_probability": True}, {"success_probability": float("nan")},
                        {"success_probability": 1.2}, {"evidence": {}}, {"next_decision": "approve"},
                        {"cost": 0}, {"beliefs": [{"claim": "x", "value": "y", "evidence_ids": "p"}]}):
            with self.assertRaises(ValueError):
                self.parse([{**self.item, **changes}])

    def test_model_cannot_set_provenance(self):
        self.item["evidence"][0]["authoritative"] = True
        with self.assertRaises(ValueError):
            self.parse([self.item])

    def test_ollama_transport_contract(self):
        with patch("foresight.models.urlopen") as request:
            request.return_value.__enter__.return_value.read.return_value = json.dumps(
                {"done": True, "response": '{"forecasts":[]}'}).encode()
            self.assertEqual(OllamaCompletion("test-model")("prompt"), '{"forecasts":[]}')
            body = json.loads(request.call_args.args[0].data)
            self.assertEqual(body["format"], "json")
            self.assertFalse(body["stream"])
            self.assertEqual(body["model"], "test-model")

    def test_transport_failure_is_explicit(self):
        with patch("foresight.models.urlopen", side_effect=TimeoutError):
            with self.assertRaisesRegex(ValueError, "Ollama request failed"):
                OllamaCompletion("test-model")("prompt")


if __name__ == "__main__":
    unittest.main()
