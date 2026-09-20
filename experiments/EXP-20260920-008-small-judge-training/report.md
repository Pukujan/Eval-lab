# EXP-20260920-008-small-judge-training

## Student and protocol

The pilot selected a compact TF-IDF plus logistic-regression student for single-answer correctness. It uses deterministic objective labels, retains teacher augmentation as training metadata, and excludes pairwise records from the student scope.

Arms A-D were fit on train-split records only. Arm A uses objective labels; B adds rubric criterion paraphrases; C adds verified TASK-0008 hard negatives; D adds both. The arm with the lowest dev NLL, then highest dev accuracy, was selected without consulting test labels. Arm E applies scalar temperature calibration fit only on the calibration split.

Selected arm: **D**. Calibration records: **6**. Test records: **12**.

## Ablation metrics

| Arm | Train rows | Dev accuracy | Dev NLL | Test accuracy | Test balanced accuracy | Test macro F1 | Test Brier | Test ECE |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A | 33 | 0.6667 | 0.6667 | 0.5833 | 0.5000 | 0.4958 | 0.4728 | 0.0567 |
| B | 66 | 0.6667 | 0.6507 | 0.5833 | 0.5000 | 0.4958 | 0.4593 | 0.0391 |
| C | 36 | 0.7143 | 0.6667 | 0.6667 | 0.6250 | 0.6250 | 0.4721 | 0.1349 |
| D | 72 | 0.6667 | 0.6500 | 0.6667 | 0.6250 | 0.6250 | 0.4582 | 0.1154 |
| E | 72 | 0.6667 | 0.6702 | 0.6667 | 0.6250 | 0.6250 | 0.5778 | 0.3204 |

## Calibration and validity

Temperature fit used `6` calibration records and produced a positive scalar artifact. Raw selected-arm calibration NLL was `0.6066`; calibrated arm E calibration NLL was `0.3097`.

The runner verifies that no training source family overlaps the test split, that test labels do not select the arm, and that test labels do not fit calibration. Every hard negative carries deterministic-verifier provenance; teacher rationales and rubric text remain weak augmentation metadata.

## Limitations

This is a small synthetic pilot with 33 objective train records, 21 dev records, 6 calibration records, and 12 frozen test records. The linear student is a feasibility choice rather than evidence that a transformer encoder would perform the same way. Pairwise, ARC, memory, and live provider behavior are outside this student run; inference latency is retained per prediction, while no OS-level memory claim is made.
