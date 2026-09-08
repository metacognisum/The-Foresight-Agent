# Foresight: mechanism and evaluation

## Candidate contribution

Predict an evidence transition and an explicit belief transition, then check whether
the proposed subsequent decision is warranted. A discrepancy should select a
specific intervention rather than a generic reflection prompt.

The kernel implements the checking boundary with supplied forecasts. It does not
yet implement a learned forecast generator or execute the recommended intervention.
This distinction is essential: a hand-authored successful example does not show that
an LLM can forecast its own mistakes.

## Interfaces

- `State`: immutable observed evidence with source references.
- `Requirement`: application-owned claim/value and authority/freshness conditions.
- `Forecast`: candidate action, expected evidence, predicted beliefs with citations,
  next decision, tool-success probability, and estimated action cost.
- `Controller.assess`: checks evidence support and downstream decision requirements.
- `Controller.choose`: ranks supplied candidates; the executor must obey the returned
  intervention, rather than execute an unsafe candidate solely because it ranks first.
- `observe`: records executor-supplied evidence and identifies forecast discrepancy.
- `Controller.complete`: checks requirements against observed state only.

`success_probability` is explicitly the probability of tool execution success.
Its Brier score must not be interpreted as calibration of evidence truth, belief
correctness, or final task completion. Future predictors should assign separate
probabilities to those distinct events. Unexecuted candidates have no observed
counterfactual outcome and cannot be scored as though they did.

The current source-support rules use exact structured facts. They cannot establish
natural-language entailment or source authenticity. Conflicting authoritative,
current records block completion until an application resolves them. There is no
retraction mechanism in this version.

## Closest prior work

- [RAP (2023)](https://arxiv.org/abs/2305.14992): language models as world models for planning.
- [Reflexion (2023)](https://arxiv.org/abs/2303.11366): verbal feedback and episodic memory.
- [LATS (2023/2024)](https://arxiv.org/abs/2310.04406): search, acting and reflection.
- [WorldEvolver (2026)](https://arxiv.org/abs/2606.30639): predicted action consequences,
  real transitions, mismatch-derived rules and selective foresight.
- [Epistemic calibration in planning (2026)](https://arxiv.org/abs/2605.23414): agents
  misjudging what they know can cause planning failures despite correct execution.
- [From internal models toward metacognitive AI (2021)](https://pmc.ncbi.nlm.nih.gov/articles/PMC8551129/):
  direct neuroscience-to-AI antecedent.

The literature has overlapping mechanisms. This repository makes no priority claim.

## Experimental protocol before product claims

Use held-out tasks with externally checkable outcomes and controlled evidence:
stale documents, conflicting sources, incomplete data, tool failures, and clean
tasks where no intervention is necessary. Include at least document decisions,
structured data tasks, and code tasks before claiming generality.

Compare five variants with the same model, tools, task set and total budget:

1. Basic action/observation loop.
2. The same loop with post-action reflection.
3. Outcome prediction without predicted-belief checking.
4. Foresight's evidence/belief/next-decision checking.
5. A deterministic controller with the same evidence rules but no forecasting.

Variant 5 tests whether any improvement comes entirely from ordinary validation.
Also compare always-verify against selective intervention to test the control policy.
Count prediction and verification tokens in the budget. Report multiple runs and
paired uncertainty intervals, with model versions and seeds where supported.

Measure verified completion, unsupported decisions, false completion, unnecessary
interventions, recovery after contradictions, tool calls, latency and token cost.
For probabilistic events, record forecasts before execution and compute calibration
only against the corresponding observed outcomes. Do not use the predictor as the
sole judge of its own correctness.

## Falsification criteria

The mechanism is not justified if equal-budget checks without forecasting perform
as well; if previewed beliefs fail to predict the agent's actual subsequent explicit
beliefs; if intervention suppresses useful actions without improving correctness;
or if the cost exceeds the value of prevented failures.

## Implementation sequence

1. Current: typed control kernel, scripted demo, invariants, scientific rationale.
2. Next: structured model adapter and executor with application-owned evidence checks.
3. Add a shadow mode: record forecasts before actions without influencing selection,
   then compare predicted and realized belief/decision records.
4. Implement intervention dispatch, bounded execution, cancellation and persistent traces.
5. Run held-out equal-budget experiments, then decide which mechanisms merit a release.

Shadow mode is needed to test whether the belief predictor predicts actual behavior
before letting its own interventions alter the behavior being measured.
