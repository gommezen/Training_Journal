from typing import Final, Dict, List


# ---------------------------------------------------------------------
# Session energy / readiness
# ---------------------------------------------------------------------

ENERGY_MAP: Final[Dict[str, int]] = {
    "Very tired": 1,
    "Tired": 2,
    "OK": 3,
    "Good": 4,
    "Sharp": 5,
}

ENERGY_LABELS: Final[List[str]] = list(ENERGY_MAP.keys())


# ---------------------------------------------------------------------
# Activity types
# ---------------------------------------------------------------------

ACTIVITIES: Final[List[str]] = [
    "karate",
    "weights",
    "run",
    "rowing",
    "cardio",
    "rest",
]


# ---------------------------------------------------------------------
# Session emphasis
# ---------------------------------------------------------------------

SESSION_EMPHASIS: Final[List[str]] = [
    "technical",
    "physical",
    "mixed",
]
