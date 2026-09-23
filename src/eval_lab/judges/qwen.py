"""Forced-choice local Qwen scoring over canonical judge records."""

from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass
from typing import Any

from eval_lab.escalation.spec import build_decision_spec
from eval_lab.schema import ExecutionStatus, JudgePrediction, JudgeRecord, JudgmentMode


class ContextLimitError(ValueError):
    """Raised when a record cannot fit the declared context cap."""


@dataclass(frozen=True)
class QwenRuntimeConfig:
    """Reproducible local runtime settings."""

    model_id: str = "Qwen/Qwen3-0.6B"
    revision: str = "main"
    context_cap: int = 4096
    device: str | None = None
    dtype: str | None = None
    quantization: str = "none"
    gpu_memory_fraction: float | None = None
    single_labels: tuple[str, str] = ("pass", "fail")
    prompt_version: str = "qwen-legacy-v1"

    def __post_init__(self) -> None:
        if self.context_cap <= 0:
            raise ValueError("context_cap must be positive")
        if len(self.single_labels) != 2 or len(set(self.single_labels)) != 2:
            raise ValueError("single_labels must contain two distinct labels")
        if self.quantization not in {"none", "4bit", "8bit"}:
            raise ValueError("quantization must be one of: none, 4bit, 8bit")
        if self.gpu_memory_fraction is not None and not 0 < self.gpu_memory_fraction <= 1:
            raise ValueError("gpu_memory_fraction must be between 0 and 1")


_DEFAULT_CONFIG = QwenRuntimeConfig()


def legal_labels(record: JudgeRecord, config: QwenRuntimeConfig | None = None) -> list[str]:
    """Return the exact class set scored for a canonical record."""

    if record.mode is JudgmentMode.PAIRWISE:
        return ["A", "B", "TIE"]
    return list((config or QwenRuntimeConfig()).single_labels)


def format_system_one_judge_prompt(record: JudgeRecord, *, context_cap: int = 4096) -> str:
    """Format the repository-owned typed System-One payload for local scoring."""

    decision = build_decision_spec(record, context_limit=context_cap)
    payload = {"record_id": decision.record_id, **decision.provider_payload()}
    labels = ", ".join(decision.legal_labels)
    return (
        "You are a strictly typed objective evaluation judge. "
        f"Return exactly one legal verdict from [{labels}] after `Verdict:`. "
        "Use only the supplied state, question, and criteria.\n\n"
        + json.dumps(payload, sort_keys=True)
    )


def format_judge_prompt(
    record: JudgeRecord,
    *,
    prompt_version: str = "qwen-legacy-v1",
    context_cap: int = 4096,
) -> str:
    """Format a short rubric prompt whose verdict boundary is explicit."""

    if prompt_version == "eval-lab-system-one-local-v1":
        return format_system_one_judge_prompt(record, context_cap=context_cap)
    if prompt_version != "qwen-legacy-v1":
        raise ValueError(f"unsupported Qwen prompt version: {prompt_version}")

    rubric = "\n".join(f"- {criterion.description}" for criterion in record.rubric)
    candidate_b = record.candidate_b if record.candidate_b is not None else "(not applicable)"
    return (
        "You are an objective evaluation judge.\n"
        f"Question or task:\n{record.prompt}\n\n"
        f"Candidate A:\n{record.candidate_a}\n\n"
        f"Candidate B:\n{candidate_b}\n\n"
        f"Rubric:\n{rubric}\n\n"
        "Return exactly one legal verdict label after `Verdict:`."
    )


def softmax_scores(scores: dict[str, float]) -> dict[str, float]:
    """Normalize finite raw log-scores without changing their key order."""

    if not scores or any(not math.isfinite(value) for value in scores.values()):
        raise ValueError("scores must be non-empty and finite")
    maximum = max(scores.values())
    exponentials = {label: math.exp(value - maximum) for label, value in scores.items()}
    normalizer = sum(exponentials.values())
    return {label: value / normalizer for label, value in exponentials.items()}


def _token_ids(tokenizer: Any, text: str, *, add_special_tokens: bool = True) -> list[int]:
    encoded = tokenizer(text, add_special_tokens=add_special_tokens)
    input_ids = encoded["input_ids"] if isinstance(encoded, dict) else encoded.input_ids
    if hasattr(input_ids, "tolist"):
        input_ids = input_ids.tolist()
    if input_ids and isinstance(input_ids[0], list):
        input_ids = input_ids[0]
    return [int(token) for token in input_ids]


class QwenJudge:
    """A lazy-loadable Qwen causal LM forced-choice scorer."""

    def __init__(self, tokenizer: Any, model: Any, config: QwenRuntimeConfig) -> None:
        self.tokenizer = tokenizer
        self.model = model
        self.config = config
        self._torch = self._load_torch()
        resolved_revision = getattr(getattr(model, "config", None), "_commit_hash", None)
        self.runtime_revision = str(resolved_revision or config.revision)
        self.device = str(getattr(model, "device", config.device or "cpu"))
        self.dtype = str(
            getattr(getattr(model, "config", None), "torch_dtype", config.dtype or "float32")
        )

    @staticmethod
    def _load_torch() -> Any:
        try:
            import torch
        except ImportError as exc:
            raise RuntimeError("install the local extra to use the Qwen judge") from exc
        return torch

    @classmethod
    def from_pretrained(cls, config: QwenRuntimeConfig = _DEFAULT_CONFIG) -> QwenJudge:
        """Load the configured model; weights remain in the local HF cache."""

        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
        except ImportError as exc:
            raise RuntimeError("install the local extra to use the Qwen judge") from exc
        device = config.device or ("cuda" if torch.cuda.is_available() else "cpu")
        dtype_name = config.dtype or ("float16" if device.startswith("cuda") else "float32")
        dtype = getattr(torch, dtype_name)
        if device.startswith("cuda") and config.gpu_memory_fraction is not None:
            memory_device = device if ":" in device else f"{device}:0"
            torch.cuda.set_per_process_memory_fraction(
                config.gpu_memory_fraction, device=memory_device
            )
        tokenizer = AutoTokenizer.from_pretrained(config.model_id, revision=config.revision)
        load_kwargs: dict[str, Any] = {
            "revision": config.revision,
            "torch_dtype": dtype,
        }
        if config.quantization == "4bit":
            load_kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=dtype,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True,
            )
            load_kwargs["device_map"] = {"": device}
        elif config.quantization == "8bit":
            load_kwargs["quantization_config"] = BitsAndBytesConfig(load_in_8bit=True)
            load_kwargs["device_map"] = {"": device}
        model = AutoModelForCausalLM.from_pretrained(config.model_id, **load_kwargs)
        if config.quantization == "none":
            model.to(device)
        model.eval()
        return cls(tokenizer, model, config)

    def _score_label(self, prompt: str, label: str) -> tuple[float, int]:
        prefix_text = prompt + "\nVerdict:"
        prefix_ids = _token_ids(self.tokenizer, prefix_text)
        continuation_ids = _token_ids(self.tokenizer, " " + label, add_special_tokens=False)
        full_ids = prefix_ids + continuation_ids
        if len(full_ids) > self.config.context_cap:
            raise ContextLimitError(
                f"record requires {len(full_ids)} tokens, context cap is {self.config.context_cap}"
            )
        if len(full_ids) <= len(prefix_ids):
            raise RuntimeError("verdict label produced no continuation tokens")
        torch = self._torch
        input_ids = torch.tensor([full_ids], dtype=torch.long, device=self.model.device)
        with torch.inference_mode():
            logits = self.model(input_ids=input_ids).logits[0]
        log_probabilities = torch.log_softmax(logits, dim=-1)
        score = 0.0
        for position in range(len(prefix_ids), len(full_ids)):
            score += float(log_probabilities[position - 1, full_ids[position]].item())
        return score, len(full_ids)

    def _score_labels(self, prompt: str, labels: list[str]) -> dict[str, float]:
        """Score legal labels in one forward pass when their continuations align."""

        prefix_text = prompt + "\nVerdict:"
        prefix_ids = _token_ids(self.tokenizer, prefix_text)
        sequences = [
            prefix_ids + _token_ids(self.tokenizer, " " + label, add_special_tokens=False)
            for label in labels
        ]
        if any(len(sequence) > self.config.context_cap for sequence in sequences):
            raise ContextLimitError(
                f"record requires {max(len(sequence) for sequence in sequences)} tokens, "
                f"context cap is {self.config.context_cap}"
            )
        if len({len(sequence) for sequence in sequences}) != 1 or any(
            len(sequence) <= len(prefix_ids) for sequence in sequences
        ):
            return {label: self._score_label(prompt, label)[0] for label in labels}

        torch = self._torch
        input_ids = torch.tensor(sequences, dtype=torch.long, device=self.model.device)
        with torch.inference_mode():
            logits = self.model(input_ids=input_ids).logits
        log_probabilities = torch.log_softmax(logits, dim=-1)
        continuation_start = len(prefix_ids)
        return {
            label: sum(
                float(log_probabilities[row, position - 1, token_id].item())
                for position, token_id in enumerate(
                    sequence[continuation_start:], start=continuation_start
                )
            )
            for row, (label, sequence) in enumerate(zip(labels, sequences, strict=True))
        }

    def predict_one(self, record: JudgeRecord) -> JudgePrediction:
        """Score one record and emit normalized probabilities and raw log-scores."""

        started = time.perf_counter()
        prompt = format_judge_prompt(
            record,
            prompt_version=self.config.prompt_version,
            context_cap=self.config.context_cap,
        )
        labels = legal_labels(record, self.config)
        scores = self._score_labels(prompt, labels)
        probabilities = softmax_scores(scores)
        label = max(probabilities, key=lambda candidate: probabilities[candidate])
        latency_ms = (time.perf_counter() - started) * 1000.0
        return JudgePrediction(
            record_id=record.record_id,
            judge_id=self.config.model_id,
            protocol_version=self.config.prompt_version,
            label=label,
            probabilities=probabilities,
            raw_scores=scores,
            execution_status=ExecutionStatus.OK,
            latency_ms=latency_ms,
            provider_metadata={
                "model_id": self.config.model_id,
                "requested_revision": self.config.revision,
                "resolved_revision": self.runtime_revision,
                "runtime": "transformers",
                "device": self.device,
                "dtype": self.dtype,
                "context_cap": self.config.context_cap,
                "score_semantics": "sum conditional log-likelihood of legal label continuation",
                "prompt_version": self.config.prompt_version,
            },
        )

    def predict(
        self, records: list[JudgeRecord] | tuple[JudgeRecord, ...]
    ) -> list[JudgePrediction]:
        """Predict in input order, preserving record IDs and explicit runtime errors."""

        return [self.predict_one(record) for record in records]

    def release_cuda_cache(self) -> None:
        """Release unused CUDA allocator blocks between checkpointed records."""

        if self.device.startswith("cuda"):
            self._torch.cuda.empty_cache()


__all__ = [
    "ContextLimitError",
    "QwenJudge",
    "QwenRuntimeConfig",
    "format_judge_prompt",
    "format_system_one_judge_prompt",
    "legal_labels",
    "softmax_scores",
]
