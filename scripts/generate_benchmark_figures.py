"""Render the data-first figures used by the benchmark paper and web page.

The script deliberately reads committed experiment artifacts instead of keeping
parallel hand-entered result tables.  Accuracy is conditional on resolved
labels; coverage is the resolved fraction of each declared partition (the
760-record blind pool, or the 94-record LegalBench Hearsay test split).
Direct-provider, InferHub, and local decision-model results are rendered
separately and never pooled.

Usage:
    .venv\\Scripts\\python.exe scripts\\generate_benchmark_figures.py
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "paper" / "figures" / "benchmark"

BG = "#F5F7FB"
INK = "#132A3A"
MUTED = "#5E7185"
GRID = "#D9E3EE"
TEAL = "#20C7B1"
CYAN = "#2BB9E8"
CORAL = "#F47F70"
GOLD = "#E9B949"
PLUM = "#8176E8"
GRAY = "#94A5B8"


SOURCES = {
    "direct": ROOT
    / "experiments"
    / "EXP-20260922-022-fast-provider-wave"
    / "runs"
    / "blind-comparison-20260922"
    / "results.json",
    "inferhub": ROOT
    / "experiments"
    / "EXP-20260922-024-inferhub-recommendation-wave"
    / "runs"
    / "blind-comparison-20260922"
    / "results.json",
    "grok": ROOT / "experiments" / "EXP-20260922-025-grok-protocol-ablation" / "results.json",
    "calibration": ROOT
    / "experiments"
    / "EXP-20260921-019-calibrated-judge-study"
    / "results.json",
    "local_decision": ROOT
    / "experiments"
    / "EXP-20260924-027-local-decision-bakeoff"
    / "results.json",
    "hearsay": ROOT / "experiments" / "EXP-20260924-028-legalbench-hearsay" / "results.json",
    "hearsay_records": ROOT
    / "experiments"
    / "EXP-20260924-028-legalbench-hearsay"
    / "canonical-records.jsonl",
}

LOCAL_LABELS = {
    "kev-4b": "Kev-4B",
    "semif-qwen35-4b": "SemIf (Qwen3.5-4B)",
    "verdict-1.4": "Verdict 1.4",
    "verdict-original": "Verdict pre-v1.4",
    "kev-0.8b": "Kev-0.8B",
    "laya-421m": "Laya 421M",
}
LOCAL_FAMILY_COLORS = {"kev": TEAL, "semif": CYAN, "verdict": GOLD, "laya": PLUM}

# Fixed SVG ids and no timestamp keep regenerated SVGs byte-stable.
plt.rcParams["svg.hashsalt"] = "eval-lab-benchmark-figures"


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def direct_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    labels = {
        "grok_46": "Grok 4.6 Build",
        "grok_47": "Grok 4.7 Build",
        "qwen_flash": "Qwen Flash",
        "jev": "Jev 1.13",
    }
    return [
        {
            "key": key,
            "label": label,
            "accuracy": float(arm["accuracy"]),
            "coverage": float(arm["resolved_coverage"]),
            "resolved": int(arm["resolved_count"]),
            "record_count": int(arm["record_count"]),
        }
        for key, label in labels.items()
        for arm in [payload["arms"][key]]
    ]


def inferhub_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    labels = {
        "ali_qwen38_flash": "Qwen3.8 Flash",
        "ali_qwen38_max": "Qwen 3.8 Max",
        "ali_glm52": "GLM 5.2",
        "ali_kimi_k27_code": "Kimi K2.7 Code",
        "cbcn_deepseek_v4_flash": "DeepSeek V4 Flash",
        "cb_deepseek_v41_flash": "DeepSeek V4.1 Flash",
        "cbcn_glm53_flash": "GLM 5.3 Flash",
        "cbcn_minimax_m3": "MiniMax M3",
    }
    rows = []
    for key, label in labels.items():
        arm = payload["arms"][key]
        rows.append(
            {
                "key": key,
                "label": label,
                "accuracy": float(arm["accuracy"]),
                "coverage": float(arm["resolved_coverage"]),
                "resolved": int(arm["resolved_count"]),
                "record_count": int(arm["record_count"]),
            }
        )
    return sorted(rows, key=lambda row: (-row["coverage"], -row["accuracy"]))


def apply_theme(ax: plt.Axes, xlim: tuple[float, float]) -> None:
    ax.set_facecolor(BG)
    ax.set_xlim(*xlim)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(colors=MUTED, labelsize=10, length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)


def add_title(fig: plt.Figure, title: str, subtitle: str) -> None:
    fig.text(0.055, 0.955, title, ha="left", va="top", fontsize=20, fontweight="bold", color=INK)
    fig.text(0.055, 0.916, subtitle, ha="left", va="top", fontsize=10.5, color=MUTED)


def add_source(fig: plt.Figure, text: str) -> None:
    fig.text(0.055, 0.026, text, ha="left", va="bottom", fontsize=8.5, color=MUTED)


def save_figure(fig: plt.Figure, stem: str) -> list[str]:
    png = OUT / f"{stem}.png"
    svg = OUT / f"{stem}.svg"
    fig.savefig(png, dpi=220, facecolor=BG, bbox_inches="tight", pad_inches=0.18)
    fig.savefig(svg, facecolor=BG, bbox_inches="tight", pad_inches=0.18, metadata={"Date": None})
    plt.close(fig)
    return [str(png.relative_to(ROOT)), str(svg.relative_to(ROOT))]


def plot_comparison(
    rows: list[dict[str, Any]], stem: str, title: str, subtitle: str, source: str
) -> list[str]:
    fig, axes = plt.subplots(1, 2, figsize=(14, max(5.7, 1.03 * len(rows) + 1.3)), sharey=True)
    fig.patch.set_facecolor(BG)
    add_title(fig, title, subtitle)
    palette = [
        CORAL
        if row["label"].startswith("Grok")
        else GOLD
        if row["label"].startswith("Jev")
        else TEAL
        for row in rows
    ]
    y = np.arange(len(rows))

    for index, (ax, metric, header) in enumerate(
        zip(
            axes, ("accuracy", "coverage"), ("Accuracy among resolved labels", "Execution coverage")
        )
    ):
        values = [row[metric] * 100 for row in rows]
        bars = ax.barh(y, values, height=0.62, color=palette, edgecolor="none")
        apply_theme(ax, (0, 105))
        ax.set_title(header, loc="left", fontsize=11.5, fontweight="bold", color=INK, pad=12)
        ax.set_xlabel("Percent", color=MUTED, fontsize=9.5)
        ax.set_xticks([0, 25, 50, 75, 100])
        ax.set_xticklabels(["0", "25", "50", "75", "100"])
        if index == 0:
            ax.set_yticks(y, [row["label"] for row in rows])
            ax.tick_params(axis="y", labelcolor=INK, labelsize=10.5, pad=8)
        else:
            ax.tick_params(axis="y", left=False, labelleft=False)
        ax.invert_yaxis()
        for bar, value in zip(bars, values):
            ax.text(
                min(value + 1.2, 101.5),
                bar.get_y() + bar.get_height() / 2,
                f"{value:.2f}%",
                va="center",
                fontsize=9.5,
                color=INK,
            )

    fig.subplots_adjust(left=0.24, right=0.97, top=0.79, bottom=0.14, wspace=0.25)
    add_source(fig, source)
    return save_figure(fig, stem)


def plot_grok(payload: dict[str, Any]) -> list[str]:
    public = payload["public"]["variants"]
    order = ["explicit_schema", "semantic_schema", "typed_schema", "explicit_no_schema"]
    labels = ["Explicit schema", "Semantic schema", "Typed schema", "No schema"]
    scores = [public[key]["selection_score"] for key in order]
    coverages = [public[key]["coverage"] * 100 for key in order]
    y = np.arange(len(order))
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 6.2), sharey=True)
    fig.patch.set_facecolor(BG)
    add_title(
        fig,
        "Grok protocol ablation: no tested contract fixed the blind failure",
        "EXP-025 public selection • mode-balanced score and resolved coverage are shown separately",
    )
    score_ax, coverage_ax = axes
    score_values = [value if value is not None else 0 for value in scores]
    colors = [PLUM, PLUM, TEAL, GRAY]
    bars = score_ax.barh(y, score_values, height=0.62, color=colors, edgecolor="none")
    apply_theme(score_ax, (0, 0.35))
    score_ax.set_title(
        "Public mode-balanced score",
        loc="left",
        fontsize=11.5,
        fontweight="bold",
        color=INK,
        pad=12,
    )
    score_ax.set_xlabel("Score", color=MUTED, fontsize=9.5)
    score_ax.set_xticks([0, 0.1, 0.2, 0.3])
    score_ax.set_yticks(y, labels)
    score_ax.tick_params(axis="y", labelcolor=INK, labelsize=10.5, pad=8)
    score_ax.invert_yaxis()
    for key, bar, value in zip(order, bars, scores):
        if value is None:
            score_ax.text(
                0.012,
                bar.get_y() + bar.get_height() / 2,
                "not scored: 0 resolved",
                va="center",
                fontsize=9.5,
                color=INK,
            )
        else:
            score_ax.text(
                value + 0.008,
                bar.get_y() + bar.get_height() / 2,
                f"{value:.4f}",
                va="center",
                fontsize=9.5,
                color=INK,
            )

    bars = coverage_ax.barh(y, coverages, height=0.62, color=colors, edgecolor="none")
    apply_theme(coverage_ax, (0, 105))
    coverage_ax.set_title(
        "Public resolved coverage", loc="left", fontsize=11.5, fontweight="bold", color=INK, pad=12
    )
    coverage_ax.set_xlabel("Percent of 64 records", color=MUTED, fontsize=9.5)
    coverage_ax.set_xticks([0, 25, 50, 75, 100])
    coverage_ax.tick_params(axis="y", left=False, labelleft=False)
    for bar, value in zip(bars, coverages):
        coverage_ax.text(
            min(value + 1.3, 101.5),
            bar.get_y() + bar.get_height() / 2,
            f"{value:.2f}%",
            va="center",
            fontsize=9.5,
            color=INK,
        )

    blind = payload["blind"]
    fig.text(
        0.055,
        0.105,
        "Blind typed baseline: "
        f"{blind['selection_score']:.4f} mode-balanced • {blind['coverage'] * 100:.2f}% coverage • "
        f"{blind['single_accuracy'] * 100:.1f}% single • {blind['pairwise_accuracy'] * 100:.1f}% pairwise",
        ha="left",
        va="bottom",
        fontsize=10.5,
        color=INK,
        bbox={"boxstyle": "round,pad=0.6", "facecolor": "#E9F7F4", "edgecolor": "#B9E7DE"},
    )
    fig.subplots_adjust(left=0.23, right=0.97, top=0.79, bottom=0.23, wspace=0.25)
    add_source(
        fig,
        "Source: EXP-20260922-025 results.json • no-schema score is unavailable because no labels resolved",
    )
    return save_figure(fig, "grok_protocol_ablation")


def plot_calibration(payload: dict[str, Any]) -> list[str]:
    raw = payload["calibration"]["blind_holdout"]["raw"]
    calibrated = payload["calibration"]["blind_holdout"]["calibrated"]
    metrics = [
        ("Brier score", "brier"),
        ("Negative log likelihood", "nll"),
        ("Expected calibration error", "ece"),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(14, 5.6))
    fig.patch.set_facecolor(BG)
    add_title(
        fig,
        "Calibration changes confidence, not selected labels",
        "Local Qwen 4B blind holdout • temperature fit on a separate public calibration split",
    )
    for ax, (label, key) in zip(axes, metrics):
        values = [float(raw[key]), float(calibrated[key])]
        bars = ax.bar([0, 1], values, width=0.58, color=[GRAY, TEAL], edgecolor="none")
        ymax = max(values) * 1.35
        apply_theme(ax, (-0.6, 1.6))
        ax.set_ylim(0, ymax)
        ax.set_title(label, loc="left", fontsize=11.5, fontweight="bold", color=INK, pad=12)
        ax.set_xticks([0, 1], ["Raw", "Calibrated"])
        ax.tick_params(axis="x", labelcolor=INK, labelsize=10)
        ax.set_ylabel("Lower is better", color=MUTED, fontsize=9.5)
        for bar, value in zip(bars, values):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                value - ymax * 0.045,
                f"{value:.4f}",
                ha="center",
                va="top",
                fontsize=10,
                color="white",
                fontweight="bold",
            )

    fig.text(
        0.055,
        0.105,
        f"Accuracy is unchanged at {float(calibrated['accuracy']) * 100:.2f}% • calibration improves confidence metrics only",
        ha="left",
        va="bottom",
        fontsize=10.5,
        color=INK,
        bbox={"boxstyle": "round,pad=0.6", "facecolor": "#E9F7F4", "edgecolor": "#B9E7DE"},
    )
    fig.subplots_adjust(left=0.075, right=0.97, top=0.78, bottom=0.24, wspace=0.32)
    add_source(
        fig,
        "Source: EXP-20260921-019 results.json • Brier, NLL, and ECE are available only for validated local probabilities",
    )
    return save_figure(fig, "local_qwen_calibration")


def local_rows(arms: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for key, label in LOCAL_LABELS.items():
        arm = arms[key]
        low, high = arm["accuracy_95_wilson"]
        rows.append(
            {
                "key": key,
                "label": label,
                "accuracy": float(arm["accuracy"]),
                "low": float(low),
                "high": float(high),
                "coverage": float(arm["resolved_coverage"]),
                "resolved": int(arm["resolved_count"]),
                "record_count": int(arm["record_count"]),
            }
        )
    return rows


def majority_label_rate(path: Path) -> tuple[str, float]:
    counts: dict[str, int] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                label = json.loads(line)["gold"]["label"]
                counts[label] = counts.get(label, 0) + 1
    label = max(counts, key=lambda key: counts[key])
    return label, counts[label] / sum(counts.values())


def not_run_arms(payload: dict[str, Any]) -> list[str]:
    completed = set(payload["partitions"][payload["primary_partition"]])
    return [arm["model_id"] for key, arm in payload["model_arms"].items() if key not in completed]


def draw_accuracy_panel(
    ax: plt.Axes, rows: list[dict[str, Any]], colors: list[str], header: str
) -> None:
    y = np.arange(len(rows))
    values = [row["accuracy"] * 100 for row in rows]
    lower = [(row["accuracy"] - row["low"]) * 100 for row in rows]
    upper = [(row["high"] - row["accuracy"]) * 100 for row in rows]
    ax.barh(y, values, height=0.62, color=colors, edgecolor="none")
    ax.errorbar(values, y, xerr=[lower, upper], fmt="none", ecolor=INK, elinewidth=1.1, capsize=3)
    apply_theme(ax, (0, 105))
    ax.set_title(header, loc="left", fontsize=11.5, fontweight="bold", color=INK, pad=12)
    ax.set_xlabel("Percent (bar: accuracy; whisker: 95% Wilson interval)", color=MUTED, fontsize=9)
    ax.set_xticks([0, 25, 50, 75, 100])
    for index, row in enumerate(rows):
        ax.text(
            min(row["high"] * 100 + 1.2, 101.5),
            index,
            f"{row['accuracy'] * 100:.2f}%",
            va="center",
            fontsize=9.5,
            color=INK,
        )


def plot_local_decision(
    bakeoff: dict[str, Any], hearsay: dict[str, Any], records_path: Path
) -> tuple[list[str], dict[str, Any]]:
    blind = sorted(
        local_rows(bakeoff["partitions"][bakeoff["primary_partition"]]),
        key=lambda row: -row["accuracy"],
    )
    by_key = {row["key"]: row for row in local_rows(hearsay["arms"])}
    legal = [by_key[row["key"]] for row in blind]
    majority_label, majority_rate = majority_label_rate(records_path)
    missing = not_run_arms(bakeoff)
    colors = [
        next(
            color for prefix, color in LOCAL_FAMILY_COLORS.items() if row["key"].startswith(prefix)
        )
        for row in blind
    ]
    y = np.arange(len(blind))

    fig, axes = plt.subplots(1, 3, figsize=(17, 6.8), sharey=True)
    fig.patch.set_facecolor(BG)
    add_title(
        fig,
        "Local decision models: frozen blind pool and LegalBench Hearsay",
        "EXP-027 blind holdout (760 records, primary) and EXP-028 Hearsay test (94 records) "
        "are separate benchmarks \u00b7 accuracy is conditional on a resolved label",
    )
    blind_ax, coverage_ax, legal_ax = axes
    draw_accuracy_panel(blind_ax, blind, colors, "EXP-027 blind accuracy")
    blind_ax.set_yticks(y, [row["label"] for row in blind])
    blind_ax.tick_params(axis="y", labelcolor=INK, labelsize=10.5, pad=8)
    blind_ax.invert_yaxis()

    coverage = [row["coverage"] * 100 for row in blind]
    bars = coverage_ax.barh(y, coverage, height=0.62, color=colors, edgecolor="none")
    apply_theme(coverage_ax, (0, 125))
    coverage_ax.set_title(
        "EXP-027 blind coverage", loc="left", fontsize=11.5, fontweight="bold", color=INK, pad=12
    )
    coverage_ax.set_xlabel("Percent of 760 blind records resolved", color=MUTED, fontsize=9)
    coverage_ax.set_xticks([0, 25, 50, 75, 100])
    coverage_ax.tick_params(axis="y", left=False, labelleft=False)
    for bar, row in zip(bars, blind):
        coverage_ax.text(
            row["coverage"] * 100 + 1.2,
            bar.get_y() + bar.get_height() / 2,
            f"{row['coverage'] * 100:.2f}% ({row['resolved']}/{row['record_count']})",
            va="center",
            fontsize=9,
            color=INK,
        )

    draw_accuracy_panel(legal_ax, legal, colors, "EXP-028 Hearsay accuracy (94/94 resolved)")
    legal_ax.tick_params(axis="y", left=False, labelleft=False)
    legal_ax.axvline(majority_rate * 100, color=CORAL, linestyle="--", linewidth=1.3)
    legal_ax.set_xlabel(
        f"Percent (whisker: 95% Wilson interval; dashed: always '{majority_label}' "
        f"= {majority_rate * 100:.2f}%)",
        color=MUTED,
        fontsize=9,
    )

    fig.text(
        0.055,
        0.105,
        "Not run (pinned configuration infeasible on the 16 GiB M1 host): "
        + ", ".join(missing)
        + " \u00b7 unresolved = Verdict abstentions and Verdict 1.4/Laya context-limit skips",
        ha="left",
        va="bottom",
        fontsize=10.5,
        color=INK,
        bbox={"boxstyle": "round,pad=0.6", "facecolor": "#E9F7F4", "edgecolor": "#B9E7DE"},
    )
    fig.subplots_adjust(left=0.13, right=0.98, top=0.79, bottom=0.24, wspace=0.18)
    add_source(
        fig,
        "Source: EXP-20260924-027 and EXP-20260924-028 results.json \u00b7 Hearsay majority-class "
        "rate from canonical-records.jsonl gold labels \u00b7 public partition not plotted",
    )
    derived = {
        "hearsay_majority_label": majority_label,
        "hearsay_majority_rate": majority_rate,
        "exp027_not_run_model_ids": missing,
    }
    return save_figure(fig, "local_decision_models"), derived


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    direct = read_json(SOURCES["direct"])
    inferhub = read_json(SOURCES["inferhub"])
    grok = read_json(SOURCES["grok"])
    calibration = read_json(SOURCES["calibration"])
    local_decision = read_json(SOURCES["local_decision"])
    hearsay = read_json(SOURCES["hearsay"])

    generated: list[str] = []
    generated += plot_comparison(
        direct_rows(direct),
        "direct_wave_accuracy_coverage",
        "Direct wave: correctness and coverage tell different stories",
        "EXP-022 • same 760-record blind holdout • accuracy is conditional on a resolved label",
        "Source: EXP-20260922-022 fast-provider wave • 760 blind records",
    )
    generated += plot_comparison(
        inferhub_rows(inferhub),
        "inferhub_wave_accuracy_coverage",
        "InferHub wave: the best conditional score is not the safest default",
        "EXP-024 • same 760-record blind holdout • unresolved provider/parse states remain outside accuracy",
        "Source: EXP-20260922-024 recommendation-policy wave • 760 blind records",
    )
    generated += plot_grok(grok)
    generated += plot_calibration(calibration)
    local_outputs, local_derived = plot_local_decision(
        local_decision, hearsay, SOURCES["hearsay_records"]
    )
    generated += local_outputs

    manifest = {
        "generator": "scripts/generate_benchmark_figures.py",
        "figure_policy": {
            "accuracy": "conditional on resolved labels",
            "coverage": "resolved fraction of the declared partition (760 blind or 94 Hearsay test records)",
            "probability_metrics": "rendered only for validated native/local probability maps",
            "pooling": "direct, InferHub, and local decision-model results remain separate",
            "local_decision": "EXP-027 blind (primary) and EXP-028 Hearsay are separate panels; public partition not plotted",
        },
        "sources": {
            key: {"path": str(path.relative_to(ROOT)), "sha256": sha256(path)}
            for key, path in SOURCES.items()
        },
        "outputs": generated,
        "figures": [
            "direct_wave_accuracy_coverage",
            "inferhub_wave_accuracy_coverage",
            "grok_protocol_ablation",
            "local_qwen_calibration",
            "local_decision_models",
        ],
        "derived": {"local_decision_models": local_derived},
    }
    with (OUT / "manifest.json").open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(manifest, handle, indent=2)
        handle.write("\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
