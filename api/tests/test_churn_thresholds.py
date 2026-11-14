import pytest
import pandas as pd
from services.predictor import (
    RiskPredictor,
    CHURN_VERY_HIGH_THRESHOLD,
    CHURN_HIGH_THRESHOLD,
)


def test_churn_threshold_constants():
    assert CHURN_VERY_HIGH_THRESHOLD == 20
    assert CHURN_HIGH_THRESHOLD == 10
    assert CHURN_VERY_HIGH_THRESHOLD > CHURN_HIGH_THRESHOLD


@pytest.mark.parametrize("churn,expected_level", [
    (0, "Low"),
    (5, "Low"),
    (10, "Low"),
    (10.5, "Med"),
    (11, "Med"),
    (15, "Med"),
    (20, "Med"),
    (20.1, "High"),
    (25, "High"),
    (100, "High"),
    (5000, "High"),
])
def test_churn_level_thresholds(churn, expected_level):
    predictor = RiskPredictor()
    level = predictor.get_churn_level(churn)
    assert level == expected_level


def test_churn_reason_and_level_never_contradict():
    """
    Ensure that whenever 'Very High Churn' or 'High Churn' appears in reason,
    the churn level is NEVER 'Low'.
    """
    predictor = RiskPredictor()

    test_values = [0, 1, 5, 10, 10.1, 11, 15, 20, 20.5, 21, 30, 50, 100, 500, 2000]
    for churn in test_values:
        row = pd.Series({'churn': churn})
        reason = predictor._generate_reason(row)
        level = predictor.get_churn_level(churn)

        if "Very High Churn" in reason:
            assert level == "High", f"Contradiction for churn={churn}: reason has 'Very High Churn' but level is {level}"
            assert level != "Low"
        elif "High Churn" in reason:
            assert level == "Med", f"Contradiction for churn={churn}: reason has 'High Churn' but level is {level}"
            assert level != "Low"
        else:
            assert level == "Low", f"Contradiction for churn={churn}: no high churn in reason but level is {level}"

