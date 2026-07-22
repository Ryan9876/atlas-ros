# Governed Prediction and Calibration Engine

Milestone 6 adds evidence-qualified probabilistic forecasts to the Atlas ROS v5 development line.

## Contracts

- `ForecastRequest` requires a bounded probability, confidence interval, expiration horizon, assumptions, and canonical evidence references.
- `PredictionRecord` remains the immutable, integrity-bound forecast artifact.
- `OutcomeObservation` records positive, negative, or invalid resolutions without mutating the forecast.
- Valid resolutions produce `CalibrationObservation` metrics and an immutable `LearningEvent`.
- Invalid outcomes are excluded from calibration and cannot update patterns.

## Governance

Forecasts are withheld when evidence is rejected, falls below confidence requirements, or has insufficient authority-adjusted strength. Outcomes cannot predate forecasts. Calibration is computed only from valid resolved forecasts.

## Metrics

- Brier score
- Mean absolute probability error
- Confidence-interval coverage
- Expected calibration error using deterministic probability bins
- Composite predictive-quality score
- Baseline-versus-recent drift status: insufficient data, stable, warning, or drift

This capability does not create autonomous actions, change production authority, or claim measured real-world predictive performance without resolved outcomes.
