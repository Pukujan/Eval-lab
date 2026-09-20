"""Serializable calibration metadata and fitted parameters."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from pydantic import BaseModel, ConfigDict, Field, field_validator

from eval_lab.schema import Split


class CalibrationArtifact(BaseModel):
    """A fitted calibrator with the metadata needed for safe reuse."""

    model_config = ConfigDict(extra="forbid")

    method: str = Field(min_length=1)
    parameters: dict[str, float]
    fit_split: Split
    class_order: list[str] = Field(min_length=1)
    input_semantics: str = Field(min_length=1)
    code_version: str = Field(min_length=1)

    @field_validator("fit_split")
    @classmethod
    def calibration_split_only(cls, value: Split) -> Split:
        if value is not Split.CALIBRATION:
            raise ValueError("calibration artifacts must be fit on split=calibration")
        return value

    @field_validator("class_order")
    @classmethod
    def unique_class_order(cls, value: list[str]) -> list[str]:
        if any(not label for label in value) or len(set(value)) != len(value):
            raise ValueError("class_order must contain unique non-empty labels")
        return value

    @field_validator("parameters")
    @classmethod
    def finite_parameters(cls, value: dict[str, float]) -> dict[str, float]:
        import math

        if not value or any(not math.isfinite(float(item)) for item in value.values()):
            raise ValueError("parameters must contain finite values")
        return {str(key): float(item) for key, item in value.items()}

    @property
    def fitted_parameters(self) -> dict[str, float]:
        """Compatibility view using the terminology from the design document."""

        return dict(self.parameters)

    def validate_classes(self, classes: Sequence[str] | Mapping[str, float]) -> None:
        observed = list(classes)
        if observed != self.class_order:
            raise ValueError("prediction class order does not match calibration artifact")


__all__ = ["CalibrationArtifact"]
