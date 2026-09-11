# Using Foresight

[Back to the README](../README.md)

## Installation

From a clone of this repository, using Python 3.10 or newer:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .
foresight
```

On Windows, use `py` instead of `python3` and activate with
`.venv\Scripts\Activate.ps1` in PowerShell. For development, use
`python -m pip install -e .`.

Installation may download build requirements. Running `python3 -m foresight.demo`
directly from the checkout requires no installation or network connection.
The CLI runs the scripted demo; it does not accept arbitrary tasks.
The new `foresight-evaluate` command runs the bounded document-agent comparison;
see [agent integration](agent.md) for custom tools and requirements.

The distribution name is `metacognisum-foresight`; the import and CLI name is
`foresight`. The package has not been published to PyPI.

## Python API

```python
from foresight import (
    Belief, Controller, Evidence, Forecast, Requirement, State, observe,
)

controller = Controller((Requirement("eligible", "yes"),))
state = State()

expected = Evidence(
    id="policy-result", claim="eligible", value="yes",
    source="current-policy", authoritative=True, current=True,
)
forecast = Forecast(
    action="check_policy",
    evidence=(expected,),
    beliefs=(Belief("eligible", "yes", ("policy-result",)),),
    next_decision="complete",
    success_probability=0.8,
)

assessment = controller.choose(state, (forecast,))
assert assessment.intervention == "execute_then_check"
assert controller.complete(state) is False  # A forecast is not an observation.

# Illustrative observation; a real application must obtain this from its executor.
actual = Evidence(
    id="observed-result", claim="eligible", value="no",
    source="current-policy", authoritative=True, current=True,
)
transition = observe(state, forecast, (actual,), action_succeeded=True)
assert transition.intervention == "revise_belief"
assert controller.complete(transition.state) is False
```

`success_probability` refers to **tool execution success**. Its Brier score does
not measure belief truth or final task success. Candidate scores are documented
heuristics, not learned weights.

| Interface | Responsibility |
| --- | --- |
| `Evidence` / `State` | Preserve source-linked observations |
| `Belief` / `Forecast` | Describe anticipated claims and action consequences |
| `Requirement` | Define application-owned evidence conditions |
| `Controller.assess()` | Identify unsupported beliefs and decision gaps |
| `Controller.choose()` | Rank candidate forecasts and return a recommendation |
| `observe()` | Record observations and flag prediction mismatches |
| `Controller.complete()` | Check actual evidence against completion requirements |


## Integration boundaries

- The application supplies source authority, freshness, and actual tool outcomes.
  The kernel cannot authenticate a source or prevent fabricated observations.
- Evidence matching uses exact structured predicates, not natural-language entailment.
- A supported belief can contradict the desired outcome while remaining justified.
- Conflicting qualifying evidence blocks completion. Records cannot be overwritten;
  source retraction and supersession are not yet supported.
- Applications must enforce intervention recommendations, including when every
  candidate requires verification. Selecting a candidate does not authorize execution.
- The bounded runtime supports a JSON model adapter, local document reads and
  persistent traces. It has no sandbox or permission system. Register only trusted,
  read-only executors. Neither example performs external approvals.

## Verification

From the repository root:

```bash
python3 -m unittest discover -v
python3 -m foresight.demo
git diff --check
```
