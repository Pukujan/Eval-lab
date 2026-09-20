# Eval Lab Report

- Total predictions: 20
- Successful predictions: 20
- Failure count: 0

## Aggregate metrics

| Metric | Value |
| --- | ---: |
| accuracy | 0.45 |
| balanced_accuracy | 0.525 |
| macro_f1 | 0.3181818181818182 |
| brier | 0.8265485329815269 |
| nll | 1.269123964251841 |
| ece | 0.41255129356979847 |

## Calibration

- Fit records: 6 synthetic single-label records on `split=calibration`.
- Applied records: 9 eligible single-label records in the held-out 20-record slice.
- Fitted scalar temperature: `20.09618943455915`.
- Raw NLL/Brier/ECE: `1.269123964251841` / `0.8265485329815269` / `0.41255129356979847`.
- Calibrated NLL/Brier/ECE: `1.03955085928192` / `0.651196287033591` / `0.306242807193657`.

## Limitations

This is a 20-record feasibility slice, not generalization evidence. Pairwise predictions were left unchanged because the calibration artifact was fit for the single-label `pass`/`fail` class set. Jev comparison is unavailable because the provider smoke was rate limited.
