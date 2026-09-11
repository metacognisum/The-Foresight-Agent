# Bounded document agent

The runner joins forecasting to actual file reads. Only an executor's observed
evidence can update the state. Realized beliefs are derived by deterministic
evidence rules, not by asking the same model to judge its own predictions.

## Offline comparison

```bash
python3 -m foresight.experiment --output runs/offline-01
python3 -m foresight.experiment --max-steps 1 --output runs/one-step-01
```

The output contains ten JSONL files (five cases, two modes) and `summary.json`.
Existing output directories are rejected. `start` records requirements, source
metadata and budgets; `forecast` records all candidates and assessments;
`selected` is written before execution; `observed` contains actual evidence,
derived beliefs, decision and prediction mismatches; `finished` records the stop
reason. A truncated trace without `finished` is an interrupted/failed run, not a
completed one. Traces contain document claims and model predictions: choose an
appropriate local output path for your data.

The fixtures live in `foresight/experiment.py`. Outcome files are materialized in
a temporary directory and read by `DocumentExecutor`; the predictor receives only
action descriptors, fallible previews, observations and prior events. It cannot
read the outcome files. The default `HintPredictor` is hand-authored and does not
learn; the model adapter receives discrepancies for replanning. No counterfactual
outcomes are scored for actions that were not executed.

## Model forecasts

With an Ollama server and a model you have already installed:

```bash
python3 -m foresight.experiment --model YOUR_LOCAL_MODEL --output runs/model-01
```

The transport uses [`/api/generate`](https://docs.ollama.com/api/introduction)
with `format: "json"`, `stream: false`, temperature zero, a 4096-token output
limit and a 60-second request timeout. `--base-url` selects a server explicitly;
the default is `http://localhost:11434`. Nothing connects to a model server unless
`--model` is supplied. Selecting a remote server sends the prompt and observed
claims to that server. No model is downloaded by this project.

`JsonPredictor(completion_callable)` also accepts another provider: the callable
takes a prompt string and returns a JSON string. The required shape is:

```json
{"forecasts":[{"action":"read_policy","evidence":[{"id":"prediction-1","claim":"eligible","value":"yes"}],"beliefs":[{"claim":"eligible","value":"yes","evidence_ids":["prediction-1"]}],"next_decision":"complete","success_probability":0.9}]}
```

Return exactly one forecast per available action. Unknown actions, missing fields,
invalid probabilities, and extra fields are rejected. The model cannot assign
source authority, freshness or action cost. The registry supplies these fields.
Predictions still may be wrong, and the model may ignore prompts: validation and
the observed-evidence completion gate remain separate from model output.

Malformed output or transport failure stops with `forecast_error` before the next
read. The experiment command exits nonzero if any model run has that stop reason.
Previously completed reads remain in the trace. There are no hidden model retries.

## Use your own document

Create `policy.json` containing:

```json
[{"claim":"eligible","value":"yes"}]
```

Then run this Python code from its directory:

```python
from pathlib import Path
from foresight import Controller, Requirement
from foresight.experiment import DocumentExecutor
from foresight.models import JsonPredictor, OllamaCompletion
from foresight.runtime import Action, JsonlTrace, run_agent

action = Action("read_policy", "Read the current eligibility policy",
                "policy-register", authoritative=True, current=True, cost=1)
executor = DocumentExecutor({action.id: Path("policy.json")})
controller = Controller((Requirement("eligible", "yes"),))
predictor = JsonPredictor(OllamaCompletion("YOUR_LOCAL_MODEL"))
result = run_agent(controller, (action,), executor, predictor,
                   max_steps=2, max_cost=2, trace=JsonlTrace("policy-run.jsonl"))
print(result["completed"], result["beliefs"])
```

The application is responsible for deciding whether a source is authoritative and
current. Document content is restricted to claim/value records and cannot override
that metadata. Set `predictor=None` for the deterministic cheapest-first baseline.
Other domains can register `Action` objects and implement `Executor.execute`,
returning `Observation` with validated `Evidence`. Only trusted read-only tools
belong in this runner. A protocol is not a sandbox and cannot prevent arbitrary
code in an application-provided executor.

## Bounds and intervention behavior

- Each action executes at most once. A failed read consumes its step and tool cost.
- Only affordable actions are forecast. Model calls occur at most once per step.
- `verify_evidence` dispatches the registered read to verify the proposed claim;
  it never authorizes a write, approval, or publication.
- Mismatch and tool failure are recorded and fed into the next forecast request.
  The next iteration selects among remaining reads; it does not retry indefinitely.
- Beliefs are rebuilt from observed evidence after every read. Conflicting qualifying
  records remove the corresponding supported belief and block completion.
- `complete` means all goal predicates have support in the observed state. The
  runner does not exhaust all sources before stopping or prove global truth.
- Custom executors must enforce their own timeouts. There is no wall-clock deadline,
  cancellation API, automatic source supersession, or persistent run resumption.

## Interpretation

The five-case comparison is a mechanism regression suite, not a held-out benchmark.
Both modes use the same evidence gate, tool budgets and documents. The baseline
has no model calls; model tokens and latency are not equalized or included in tool
cost. A benefit may come from source filtering alone. Belief matching measures the
set of explicit claim/value pairs against deterministic derived beliefs, not an
LLM's internal state. Brier scores refer only to tool execution success. See the
[research plan](research-plan.md) for stronger baselines and falsification tests.
