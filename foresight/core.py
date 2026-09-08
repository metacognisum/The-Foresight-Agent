"""Pure control primitives; forecasts never become observed evidence automatically.

Evidence attributes must be supplied by trusted application adapters. This module
checks explicit predicates, not the truth of arbitrary natural-language claims.
"""

from dataclasses import dataclass
from typing import Mapping
import math


@dataclass(frozen=True)
class Evidence:
    id: str
    claim: str
    value: str
    source: str
    authoritative: bool = False
    current: bool = False

    def __post_init__(self):
        if not all(isinstance(x, str) and x for x in (self.id, self.claim, self.value, self.source)):
            raise ValueError("Evidence identifiers, claims, values and sources must be nonempty strings")
        if type(self.authoritative) is not bool or type(self.current) is not bool:
            raise ValueError("Evidence attributes must be booleans")


@dataclass(frozen=True)
class Requirement:
    claim: str
    value: str
    authoritative: bool = True
    current: bool = True


@dataclass(frozen=True)
class Belief:
    claim: str
    value: str
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True)
class State:
    evidence: tuple[Evidence, ...] = ()

    def __post_init__(self):
        if len({e.id for e in self.evidence}) != len(self.evidence):
            raise ValueError("Evidence IDs must be unique")


@dataclass(frozen=True)
class Forecast:
    action: str
    evidence: tuple[Evidence, ...]
    beliefs: tuple[Belief, ...]
    next_decision: str
    success_probability: float
    cost: float = 1.0

    def __post_init__(self):
        if not self.action or not self.next_decision:
            raise ValueError("Action and next decision are required")
        if not math.isfinite(self.success_probability) or not 0 <= self.success_probability <= 1:
            raise ValueError("Probability must be finite and in [0, 1]")
        if not math.isfinite(self.cost) or self.cost < 0:
            raise ValueError("Cost must be finite and nonnegative")
        State(self.evidence)


def supported(requirement: Requirement, evidence: tuple[Evidence, ...]) -> bool:
    relevant = [e for e in evidence if e.claim == requirement.claim
                and (not requirement.authoritative or e.authoritative)
                and (not requirement.current or e.current)]
    # Conflicting qualifying sources require resolution, not majority voting.
    return bool(relevant) and all(e.value == requirement.value for e in relevant)


def merge(state: State, evidence: tuple[Evidence, ...]) -> State:
    records = {e.id: e for e in state.evidence}
    for record in evidence:
        if record.id in records and records[record.id] != record:
            raise ValueError("Evidence is immutable: use a new ID for a new observation")
        records[record.id] = record
    return State(tuple(records.values()))


@dataclass(frozen=True)
class Assessment:
    action: str
    unsupported_beliefs: tuple[str, ...]
    missing_requirements: tuple[str, ...]
    decision_gaps: tuple[str, ...]
    score: float
    intervention: str


class Controller:
    """Compare forecast consequences while enforcing evidence rules independently.

    Scoring weights are explicit heuristics, not learned or neuroscience-derived.
    Terminal completion is only allowed through complete(observed_state).
    """

    def __init__(self, requirements: tuple[Requirement, ...],
                 decision_requirements: Mapping[str, tuple[str, ...]] | None = None):
        if not requirements or len({r.claim for r in requirements}) != len(requirements):
            raise ValueError("Provide nonempty requirements with unique claims")
        self.requirements = requirements
        self.decision_requirements = dict(decision_requirements or {
            "complete": tuple(r.claim for r in requirements), "continue": ()})
        known = {r.claim for r in requirements}
        if any(claim not in known for claims in self.decision_requirements.values() for claim in claims):
            raise ValueError("Decision requirements must reference configured claims")

    def assess(self, state: State, forecast: Forecast) -> Assessment:
        imagined = merge(state, forecast.evidence)
        by_id = {e.id: e for e in imagined.evidence}
        rules = {r.claim: r for r in self.requirements}
        unsupported = []
        for belief in forecast.beliefs:
            target = rules.get(belief.claim, Requirement(belief.claim, belief.value))
            # Justification concerns truth of the belief, not the desired outcome.
            rule = Requirement(belief.claim, belief.value, target.authoritative, target.current)
            cited = tuple(by_id[x] for x in belief.evidence_ids if x in by_id)
            justified = (bool(belief.evidence_ids)
                         and all(x in by_id for x in belief.evidence_ids)
                         and supported(rule, cited)
                         and supported(rule, imagined.evidence))
            if not justified:
                unsupported.append(belief.claim)
        missing = tuple(r.claim for r in self.requirements if not supported(r, imagined.evidence))
        if forecast.next_decision not in self.decision_requirements:
            decision_gaps = ("unknown_decision:" + forecast.next_decision,)
        else:
            justified_claims = {b.claim for b in forecast.beliefs if b.claim not in unsupported}
            decision_gaps = tuple(claim for claim in self.decision_requirements[forecast.next_decision]
                                  if claim not in justified_claims or claim in missing)
        before = sum(supported(r, state.evidence) for r in self.requirements)
        after = len(self.requirements) - len(missing)
        # Prediction improves ranking; unsupported belief transitions are penalized.
        score = (forecast.success_probability * (after - before) - forecast.cost * 0.05
                 - len(unsupported) * 2 - len(decision_gaps) * 2)
        intervention = "verify_evidence" if unsupported or decision_gaps else "execute_then_check"
        return Assessment(forecast.action, tuple(unsupported), missing, decision_gaps, score, intervention)

    def choose(self, state: State, forecasts: tuple[Forecast, ...]) -> Assessment:
        if not forecasts or len({f.action for f in forecasts}) != len(forecasts):
            raise ValueError("Provide candidates with unique action IDs")
        assessments = [self.assess(state, f) for f in forecasts]
        return max(assessments, key=lambda a: a.score)

    def complete(self, state: State) -> bool:
        return all(supported(r, state.evidence) for r in self.requirements)


@dataclass(frozen=True)
class Transition:
    state: State
    missing_predictions: tuple[str, ...]
    unexpected_observations: tuple[str, ...]
    brier_score: float
    intervention: str


def observe(state: State, forecast: Forecast, actual: tuple[Evidence, ...],
            *, action_succeeded: bool) -> Transition:
    """Record trusted observations; score probability of tool success, not task truth.

    Compare semantic records without IDs: adapters may assign IDs at observation.
    An unexecuted counterfactual cannot be scored by this function.
    """
    if type(action_succeeded) is not bool:
        raise ValueError("Success must be supplied as a boolean by the executor")
    State(actual)
    def signature(e):
        return (e.claim, e.value, e.source, e.authoritative, e.current)
    predicted = {signature(e) for e in forecast.evidence}
    observed = {signature(e) for e in actual}
    missing = tuple(sorted(repr(x) for x in predicted - observed))
    unexpected = tuple(sorted(repr(x) for x in observed - predicted))
    intervention = ("inspect_tool_failure" if not action_succeeded else
                    "revise_belief" if missing or unexpected else "continue")
    return Transition(merge(state, actual), missing, unexpected,
                      (forecast.success_probability - int(action_succeeded)) ** 2,
                      intervention)
