from mnemograph.lifecycle.confidence import (
    ConfidenceInputs,
    confidence_band,
    compute_confidence,
)


def test_component_level_clamping_avoids_zero_product_collapse():
    score = compute_confidence(
        ConfidenceInputs(
            trust=1.0,
            evidence=1.0,
            extraction=0.0,
            recency=1.0,
            contradiction=1.0,
            confirmation=1.0,
        )
    )

    assert score > 0.05
    assert score < 1.0


def test_confidence_band_monotonicity_on_controlled_fixtures():
    low = compute_confidence(
        ConfidenceInputs(
            trust=0.2,
            evidence=0.2,
            extraction=0.2,
            recency=0.2,
            contradiction=0.8,
            confirmation=0.1,
        )
    )
    medium = compute_confidence(
        ConfidenceInputs(
            trust=0.6,
            evidence=0.6,
            extraction=0.6,
            recency=0.6,
            contradiction=0.9,
            confirmation=0.4,
        )
    )
    high = compute_confidence(
        ConfidenceInputs(
            trust=0.95,
            evidence=0.9,
            extraction=0.9,
            recency=0.85,
            contradiction=1.0,
            confirmation=0.9,
        )
    )

    assert low < medium < high
    assert confidence_band(low) == "low"
    assert confidence_band(medium) == "medium"
    assert confidence_band(high) == "high"
