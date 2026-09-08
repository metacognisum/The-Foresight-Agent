# Contributing

Foresight is an alpha research prototype. Contributions that make its claims more
testable are especially useful: counterexamples, evidence-handling fixes, model
adapters, and controlled evaluations.

## Development

Use Python 3.10 or newer:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m unittest discover -v
python -m foresight.demo
git diff --check
```

On Windows, activate with `.venv\Scripts\Activate.ps1` in PowerShell.

## Pull requests

Describe the problem, the resulting behavior, and how you verified it. Add a focused
regression test for changes to decision or evidence handling. Keep predicted evidence
separate from executor observations, and distinguish belief correctness from goal
completion. Do not remove a failing test merely to make a patch pass.

Research claims should link to primary sources and state limitations. Hand-authored
fixtures demonstrate mechanics; they are not benchmark results. Performance claims
need the model, dataset, budget, baseline and evaluation procedure.

Do not commit credentials, private documents, or generated run data containing user
information. For ordinary bugs, open a repository issue with a minimal reproducible
example. Contributions are provided under this repository's Apache 2.0 license.
