# Changelog

## 0.2.0a1 — Unreleased

- Bounded forecast/action/observation loop with explicit observed belief updates.
- Application-owned read-only action registry and local JSON document executor.
- Strict JSON predictor interface and opt-in Ollama transport.
- Pre-execution forecast traces, mismatch feedback and step/tool-cost limits.
- Reproducible comparison against cheapest-first reads with identical evidence gates.
- Examples include a misleading forecast that wastes a read and fails at a tighter budget.

Live-model efficacy is not established. The default experiment is scripted; there
is no sandbox, source retraction or equal-total-token-budget benchmark.

## 0.1.0a1 — Unreleased

Initial research preview:

- Structured observed evidence, predicted beliefs and downstream decisions.
- Candidate ranking with evidence and decision checks.
- Prediction/observation discrepancy reporting and intervention recommendations.
- Independent completion checks over observed evidence.
- Offline policy-check demo and regression tests.
- Neuroscience rationale, prior work, and an evaluation protocol.

The preview uses scripted forecasts. It does not execute external tools or provide
a live model adapter, learned predictor, or production agent runtime.
