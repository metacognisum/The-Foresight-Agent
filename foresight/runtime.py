"""Bounded read-only agent loop. Applications own tools and source metadata."""
from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
from typing import Callable, Protocol

from .core import Belief, Controller, Evidence, Forecast, State, observe, supported, Requirement


@dataclass(frozen=True)
class Action:
    id: str
    description: str
    source: str
    authoritative: bool
    current: bool
    cost: float = 1.0

    def __post_init__(self):
        if not all(isinstance(x, str) and x for x in (self.id, self.description, self.source)):
            raise ValueError("Action ID, description and source must be nonempty strings")
        if type(self.authoritative) is not bool or type(self.current) is not bool:
            raise ValueError("Source attributes must be booleans")
        if type(self.cost) not in (int, float) or not math.isfinite(self.cost) or self.cost <= 0:
            raise ValueError("Action cost must be positive and finite")


@dataclass(frozen=True)
class Observation:
    evidence: tuple[Evidence, ...]
    succeeded: bool
    error: str | None = None


class Predictor(Protocol):
    def forecast(self, state: State, actions: tuple[Action, ...],
                 controller: Controller, history: tuple[dict, ...]) -> tuple[Forecast, ...]: ...


class Executor(Protocol):
    """Implement only application-approved, read-only actions; this is not a sandbox."""
    def execute(self, action: Action) -> Observation: ...


def realized_beliefs(state: State, controller: Controller) -> tuple[Belief, ...]:
    """Derive explicit beliefs from observations, including supported negative values."""
    beliefs = []
    for rule in controller.requirements:
        values = sorted({e.value for e in state.evidence if e.claim == rule.claim})
        for value in values:
            target = Requirement(rule.claim, value, rule.authoritative, rule.current)
            if supported(target, state.evidence):
                ids = tuple(e.id for e in state.evidence if e.claim == rule.claim
                            and (not rule.authoritative or e.authoritative)
                            and (not rule.current or e.current))
                beliefs.append(Belief(rule.claim, value, ids))
    return tuple(beliefs)


def validate_forecasts(forecasts: tuple[Forecast, ...], actions: tuple[Action, ...],
                       state: State) -> None:
    if len(forecasts) != len(actions) or {f.action for f in forecasts} != {a.id for a in actions}:
        raise ValueError("Predictor must return exactly one forecast per available action")
    by_id = {a.id: a for a in actions}
    observed_ids = {e.id for e in state.evidence}
    for forecast in forecasts:
        action = by_id[forecast.action]
        if forecast.cost != action.cost:
            raise ValueError("Forecast cannot change application-owned action cost")
        for e in forecast.evidence:
            if e.id in observed_ids:
                raise ValueError("Predictions must use fresh IDs")
            if (e.source, e.authoritative, e.current) != (
                    action.source, action.authoritative, action.current):
                raise ValueError("Forecast cannot change application-owned provenance")


class JsonlTrace:
    """Create a new trace; refuse to overwrite previous runs. Flush before execution."""
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("x", encoding="utf-8"):
            pass

    def __call__(self, event: dict) -> None:
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(event, allow_nan=False) + "\n")


def run_agent(controller: Controller, actions: tuple[Action, ...], executor: Executor,
              predictor: Predictor | None = None, *, max_steps: int = 4,
              max_cost: float = 4.0, initial_state: State = State(),
              trace: Callable[[dict], None] | None = None) -> dict:
    """Forecast-controlled reads, or cheapest-first baseline when predictor is None.

    Each action executes at most once. Verification dispatch is a read, never an
    approval. Failure/mismatch leads to replanning over the remaining reads. No
    forecast can complete the task. Executor contract violations abort the run.
    """
    if type(max_steps) is not int or max_steps < 1:
        raise ValueError("max_steps must be a positive integer")
    if type(max_cost) not in (int, float) or not math.isfinite(max_cost) or max_cost <= 0:
        raise ValueError("max_cost must be positive and finite")
    if len({a.id for a in actions}) != len(actions):
        raise ValueError("Action IDs must be unique")
    state, cost, steps = initial_state, 0.0, 0
    remaining = list(actions)
    events: list[dict] = []

    def emit(event):
        if trace:
            trace(event)
        events.append(event)

    emit({"event": "start", "mode": "foresight" if predictor else "baseline",
          "requirements": [asdict(r) for r in controller.requirements],
          "actions": [asdict(a) for a in actions], "initial_state": asdict(state),
          "max_steps": max_steps, "max_cost": max_cost})
    reason = "exhausted"
    while not controller.complete(state):
        if steps >= max_steps:
            reason = "step_budget"
            break
        available = tuple(a for a in remaining if a.cost <= max_cost - cost + 1e-12)
        if not available:
            reason = "cost_budget" if remaining else "exhausted"
            break
        forecast = None
        if predictor is not None:
            try:
                forecasts = predictor.forecast(state, available, controller, tuple(events))
                validate_forecasts(forecasts, available, state)
                selection = controller.choose(state, forecasts)
            except (ValueError, TypeError, KeyError) as error:
                emit({"event": "forecast_error", "error": str(error)})
                reason = "forecast_error"
                break
            forecast = next(f for f in forecasts if f.action == selection.action)
            action = next(a for a in available if a.id == selection.action)
            emit({"event": "forecast", "step": steps + 1,
                  "candidates": [asdict(f) for f in forecasts],
                  "assessments": [asdict(controller.assess(state, f)) for f in forecasts]})
            dispatch = selection.intervention
        else:
            action = min(available, key=lambda a: (a.cost, a.id))
            dispatch = "read_then_check"
        # Persist the forecast/selection before invoking the tool.
        emit({"event": "selected", "step": steps + 1, "action": action.id,
              "dispatch": dispatch})
        actual = executor.execute(action)
        if type(actual.succeeded) is not bool or (not actual.succeeded and actual.evidence):
            raise ValueError("Failed reads must contain no evidence; success must be boolean")
        for e in actual.evidence:
            if (e.source, e.authoritative, e.current) != (
                    action.source, action.authoritative, action.current):
                raise ValueError("Executor evidence does not match registered provenance")
        steps += 1
        cost += action.cost
        remaining.remove(action)
        if forecast is not None:
            transition = observe(state, forecast, actual.evidence, action_succeeded=actual.succeeded)
            state = transition.state
            comparison = asdict(transition)
            comparison.pop("state")
        else:
            from .core import merge
            state = merge(state, actual.evidence)
            comparison = None
        beliefs = realized_beliefs(state, controller)
        decision = "complete" if controller.complete(state) else "continue"
        emit({"event": "observed", "step": steps, "action": action.id,
              "observation": asdict(actual), "comparison": comparison,
              "beliefs": [asdict(b) for b in beliefs], "decision": decision,
              "belief_prediction_match": None if forecast is None else
              {(b.claim, b.value) for b in forecast.beliefs} == {(b.claim, b.value) for b in beliefs},
              "decision_prediction_match": None if forecast is None else forecast.next_decision == decision})
    completed = controller.complete(state)
    result = {"event": "finished", "completed": completed,
              "reason": "complete" if completed else reason, "steps": steps, "cost": cost,
              "state": asdict(state), "beliefs": [asdict(b) for b in realized_beliefs(state, controller)]}
    emit(result)
    return {**result, "events": events}
