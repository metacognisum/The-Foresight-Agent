"""Reproducible local-file experiment, not a benchmark of model intelligence."""
import argparse
import json
from pathlib import Path
import tempfile

from .core import Belief, Controller, Evidence, Forecast, Requirement
from .models import JsonPredictor, OllamaCompletion
from .runtime import Action, JsonlTrace, Observation, realized_beliefs, run_agent


class DocumentExecutor:
    """Read only explicitly mapped JSON documents. Paths are never model-generated.

    Files contain claim/value pairs only. Source trust comes from the registry.
    OSError and malformed documents are failed reads, with no partial evidence.
    """
    def __init__(self, documents: dict[str, Path]):
        self.documents = dict(documents)

    def execute(self, action: Action) -> Observation:
        if action.id not in self.documents:
            raise ValueError("Unregistered document")
        try:
            records = json.loads(self.documents[action.id].read_text(encoding="utf-8"))
            if not isinstance(records, list):
                raise ValueError("Document must contain an array")
            evidence = []
            for index, record in enumerate(records):
                if not isinstance(record, dict) or set(record) != {"claim", "value"}:
                    raise ValueError("Each document record needs only claim and value")
                evidence.append(Evidence(f"observed:{action.id}:{index}", record["claim"],
                    record["value"], action.source, action.authoritative, action.current))
            return Observation(tuple(evidence), True)
        except (OSError, UnicodeError, ValueError, TypeError) as error:
            return Observation((), False, f"{type(error).__name__}: document read failed")


class HintPredictor:
    """Deterministic fixture predictor; cannot read the outcome documents.

    Descriptions are JSON previews with a possibly incorrect claim/value hint.
    This intentionally simple predictor demonstrates both benefit and failure.
    Use JsonPredictor to replace it with model-generated forecasts.
    """
    def forecast(self, state, actions, controller, history):
        result = []
        for action in actions:
            hint = json.loads(action.description)
            e = Evidence("predicted:" + action.id, hint["claim"], hint["value"],
                         action.source, action.authoritative, action.current)
            # Intentionally optimistic belief, checked independently by Controller.
            beliefs = tuple(b for b in realized_beliefs(state, controller) if b.claim != e.claim)
            beliefs += (Belief(e.claim, e.value, (e.id,)),)
            decision = "complete" if e.value == "yes" else "continue"
            result.append(Forecast(action.id, (e,), beliefs, decision, .9, action.cost))
        return tuple(result)


# Actual value: None means unreadable, empty string means an empty document.
# id, public hint, actual document value, authority, freshness, cost
# The predictor receives only public action descriptors, never actual values.
SCENARIOS = {
    "stale_source": [("archive", "yes", "yes", True, False, .5),
                     ("current", "yes", "yes", True, True, 1.0)],
    "clean": [("current", "yes", "yes", True, True, 1.0)],
    "contradiction": [("current", "yes", "no", True, True, 1.0)],
    "tool_failure": [("primary", "yes", None, True, True, .5),
                     ("backup", "yes", "yes", True, True, 1.0)],
    "misleading_preview": [("cheap", "no", "yes", True, True, .5),
                           ("expensive", "yes", "", True, True, 1.0)],
}


def make_scenario(name: str, directory: Path):
    directory.mkdir(parents=True, exist_ok=True)
    actions, paths = [], {}
    for ident, hint, actual, authority, current, cost in SCENARIOS[name]:
        path = directory / (ident + ".json")
        paths[ident] = path
        # A malformed JSON document produces a deterministic read failure.
        path.write_text("unavailable" if actual is None else
                        json.dumps([] if actual == "" else [{"claim": "eligible", "value": actual}]),
                        encoding="utf-8")
        actions.append(Action(ident, json.dumps({"claim": "eligible", "value": hint}),
                              ident, authority, current, cost))
    return Controller((Requirement("eligible", "yes"),)), tuple(actions), DocumentExecutor(paths)


def compare(output: Path | None = None, predictor=None, *, max_steps=2, max_cost=2.0):
    rows = []
    with tempfile.TemporaryDirectory(prefix="foresight-documents-") as temp:
        for name in SCENARIOS:
            controller, actions, executor = make_scenario(name, Path(temp) / name)
            for mode in ("baseline", "foresight"):
                trace = JsonlTrace(output / f"{name}-{mode}.jsonl") if output else None
                result = run_agent(controller, actions, executor,
                    (predictor if predictor is not None else HintPredictor()) if mode == "foresight" else None,
                    max_steps=max_steps, max_cost=max_cost, trace=trace)
                observations = [e for e in result["events"] if e["event"] == "observed"]
                comparisons = [e["comparison"] for e in observations if e["comparison"] is not None]
                rows.append({"scenario": name, "mode": mode, "completed": result["completed"],
                    "reason": result["reason"], "steps": result["steps"], "tool_cost": result["cost"],
                    "actions": [e["action"] for e in observations],
                    "prediction_mismatches": sum(bool(c["missing_predictions"] or c["unexpected_observations"])
                                                 for c in comparisons) if comparisons else None,
                    "tool_success_brier": sum(c["brier_score"] for c in comparisons) / len(comparisons)
                                          if comparisons else None})
    return {"experiment": "Five hand-authored local-document mechanism cases; not a benchmark",
            "predictor": "scripted hints" if predictor is None else "model adapter",
            "baseline": "cheapest-first reads with identical observed-evidence completion gate",
            "budget": {"max_steps": max_steps, "max_tool_cost": max_cost},
            "limitations": "Tool budgets match; forecasting latency and tokens are additional and not equalized. "
                           "Both modes share the completion gate, so this does not isolate belief forecasting.",
            "results": rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="New directory for persistent JSONL traces and summary")
    parser.add_argument("--model", help="Opt in to a locally available Ollama model; otherwise offline")
    parser.add_argument("--base-url", default="http://localhost:11434")
    parser.add_argument("--max-steps", type=int, default=2)
    parser.add_argument("--max-cost", type=float, default=2.0)
    args = parser.parse_args()
    if args.output:
        args.output.mkdir(parents=True, exist_ok=False)
    predictor = JsonPredictor(OllamaCompletion(args.model, args.base_url)) if args.model else None
    report = compare(args.output, predictor, max_steps=args.max_steps, max_cost=args.max_cost)
    report["model"] = args.model
    report["base_url"] = args.base_url if args.model else None
    if args.output:
        (args.output / "summary.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if any(r["reason"] == "forecast_error" for r in report["results"]):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
