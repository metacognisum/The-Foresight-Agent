"""Scripted policy-source scenario. Demonstrates control, not LLM performance."""
from dataclasses import asdict
import json
from .core import Belief, Controller, Evidence, Forecast, Requirement, State, observe


def run():
    controller = Controller((Requirement("eligible", "yes"),), {"approve": ("eligible",)})
    state = State()
    old = Evidence("old", "eligible", "yes", "policy-2022", True, False)
    current = Evidence("current", "eligible", "yes", "policy-current", True, True)
    fast = Forecast("read_old_policy", (old,), (Belief("eligible", "yes", ("old",)),),
                    "approve", 0.99, 0.1)
    checked = Forecast("check_current_policy", (current,),
                       (Belief("eligible", "yes", ("current",)),), "approve", 0.85, 1)
    selection = controller.choose(state, (fast, checked))
    # Real observation contradicts the selected forecast: user is ineligible.
    actual = Evidence("observed", "eligible", "no", "policy-current", True, True)
    transition = observe(state, checked, (actual,), action_succeeded=True)
    return {
        "scenario": "Illustrative, hand-authored forecasts and observations",
        "candidates": [asdict(controller.assess(state, f)) for f in (fast, checked)],
        "selected": asdict(selection),
        "transition": asdict(transition),
        "completion_allowed": controller.complete(transition.state),
        "result": "Approval withheld; observed policy contradicts eligibility",
    }


def main():
    print(json.dumps(run(), indent=2))


if __name__ == "__main__":
    main()
