"""Split-safe post-hoc calibration for frozen judge predictions."""

from eval_lab.calibration.artifact import CalibrationArtifact
from eval_lab.calibration.temperature import (
    apply_calibration,
    apply_platt_scaling,
    apply_temperature_scaling,
    fit_platt_scaling,
    fit_temperature_scaling,
)

__all__ = [
    "CalibrationArtifact",
    "apply_calibration",
    "apply_platt_scaling",
    "apply_temperature_scaling",
    "fit_platt_scaling",
    "fit_temperature_scaling",
]
