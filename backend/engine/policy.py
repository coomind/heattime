from decimal import Decimal, ROUND_HALF_UP
from functools import lru_cache
from pathlib import Path
import yaml


@lru_cache
def policies():
    return yaml.safe_load((Path(__file__).parents[1] / "config/policies.yaml").read_text(encoding="utf-8"))


def classify(value: float, policy_id="general") -> int:
    policy = policies()[policy_id]
    if policy_id == "football":
        return 4 if value > policy["postpone_above"] else 2 if value > policy["cooling_above"] else 0
    return sum(value >= boundary for boundary in policy["boundaries"])


def round_decision(value: float) -> float:
    """Displayed precision (0.1℃, half-up) is the value that is classified.

    Rounding to 6 places first removes binary float noise so the frontend's
    identical rule always shows the same digit that decided the stage.
    """
    return float(Decimal(f"{value:.6f}").quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def risk_level(central, high, age_group, policy_id="general", escalate=False):
    conservative = age_group in policies()["age"]["upper_bound_groups"]
    value = round_decision(high if conservative else central)
    level = classify(value, policy_id)
    return min(4, level + int(escalate and conservative)), value
