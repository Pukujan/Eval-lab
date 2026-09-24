"""Render the data-first figures used by the consolidated judge paper and web page.

The script reads committed experiment artifacts instead of keeping parallel
hand-entered result tables.  The two headline figures read the EXP-029
consolidated analysis (``scripts/analyze_judge_comparison.py``); the Grok
ablation and calibration-appendix figures read EXP-025 and EXP-019.  Figures
that the paper no longer references are deleted so the directory mirrors the
paper.

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
    "analysis": ROOT
    / "experiments"
    / "EXP-20260924-029-consolidated-judge-analysis"
    / "results.json",
    "grok": ROOT / "experiments" / "EXP-20260922-025-grok-protocol-ablation" / "results.json",
    "calibration": ROOT
    / "experiments"
    / "EXP-20260921-019-calibrated-judge-study"
    / "results.json",
}

SHORT = {
    "jev_exp014": "Jev (014)",
    "qwen_flash_exp013": "Qwen Flash, thinking off (013)",
    "grok46_exp015": "Grok 4.6 (015)",
    "qwen_flash_exp015": "Qwen Flash one pass (015)",
    "qwen_flash_exp015_016": "Qwen Flash 015+016 merge",
    "grok46_exp022": "Grok 4.6 (022)",
    "grok47_exp022": "Grok 4.7 (022)",
    "qwen_flash_exp022": "Qwen Flash (022)",
    "jev_exp022": "Jev (022)",
    "ali_qwen38_flash_exp024": "Qwen3.8 Flash (024)",
    "ali_qwen38_max_exp024": "Qwen 3.8 Max (024)",
    "ali_glm52_exp024": "GLM 5.2 (024)",
    "ali_kimi_k27_code_exp024": "Kimi K2.7 Code (024)",
    "cbcn_deepseek_v4_flash_exp024": "DeepSeek V4 Flash (024)",
    "cb_deepseek_v41_flash_exp024": "DeepSeek V4.1 Flash (024)",
    "cbcn_glm53_flash_exp024": "GLM 5.3 Flash (024)",
    "cbcn_minimax_m3_exp024": "MiniMax M3 (024)",
    "grok46_exp025": "Grok 4.6 rerun (025)",
    "qwen3_4b_exp017": "Qwen3-4B local (017)",
    "kev_4b_exp027": "Kev-4B (027)",
    "semif_qwen35_4b_exp027": "SemIf 4B (027)",
    "verdict_14_exp027": "Verdict 1.4 (027)",
    "verdict_original_exp027": "Verdict pre-v1.4 (027)",
    "kev_08b_exp027": "Kev-0.8B (027)",
    "laya_421m_exp027": "Laya 421M (027)",
    "majority_exp014": "Majority label",
}


def arm_color(key: str, arm: dict[str, Any]) -> str:
    if arm["family"] == "baseline":
        return GRAY
    if arm["family"] == "local":
        return PLUM
    if key.startswith("grok"):
        return CORAL
    if key.startswith("jev"):
        return GOLD
    return TEAL


# Fixed SVG ids and no timestamp keep regenerated SVGs byte-stable.
plt.rcParams["svg.hashsalt"] = "eval-lab-benchmark-figures"


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def sha256(path: Path) -> str:
    """SHA-256 of LF-normalized bytes so Windows CRLF checkouts hash identically."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


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


def spread(values: list[float], gap: float) -> list[float]:
    """Push sorted label positions apart by at least ``gap`` (deterministic)."""
    placed: list[float] = []
    for value in values:
        placed.append(value if not placed else max(value, placed[-1] + gap))
    shift = (placed[-1] - values[-1]) / 2 if placed else 0.0
    return [value - shift for value in placed]


def plot_accuracy_vs_coverage(payload: dict[str, Any]) -> list[str]:
    arms = payload["arms"]
    keys = list(arms)
    fig, ax = plt.subplots(figsize=(14, 9.2))
    fig.patch.set_facecolor(BG)
    add_title(
        fig,
        "Accuracy among answered records vs. share of records answered",
        "760 blind records \u00b7 every arm on the same typed decisions \u00b7 dotted curves: "
        "all-record accuracy (unanswered earns no credit)",
    )
    ax.set_facecolor(BG)
    for level in (40, 50, 60, 70, 80, 90):
        xs = np.linspace(max(level, 50), 100, 200)
        ax.plot(xs, level * 100 / xs, color=GRID, linestyle=":", linewidth=1.1, zorder=1)
        x_label = max(50.6, level * 100 / 101.5)
        ax.text(
            x_label,
            level * 100 / x_label,
            f"{level}% of all records",
            color=MUTED,
            fontsize=7.5,
            va="bottom",
            rotation=-18,
        )
    for key in keys:
        arm = arms[key]
        ax.scatter(
            arm["coverage"] * 100,
            arm["conditional_accuracy"] * 100,
            s=70,
            color=arm_color(key, arm),
            edgecolor="white",
            linewidth=0.8,
            zorder=3,
        )
    right = sorted(
        (k for k in keys if arms[k]["coverage"] >= 0.9),
        key=lambda k: (arms[k]["conditional_accuracy"], k),
    )
    left = sorted(
        (k for k in keys if arms[k]["coverage"] < 0.9),
        key=lambda k: (arms[k]["conditional_accuracy"], k),
    )
    for group, x_text, align in ((right, 108.5, "left"), (left, None, "left")):
        ys = spread([arms[k]["conditional_accuracy"] * 100 for k in group], 2.05)
        for key, y_text in zip(group, ys):
            arm = arms[key]
            x, y = arm["coverage"] * 100, arm["conditional_accuracy"] * 100
            tx = x_text if x_text is not None else x + 2.2
            ax.annotate(
                SHORT[key],
                (x, y),
                xytext=(tx, y_text),
                textcoords="data",
                fontsize=8.6,
                color=INK,
                ha=align,
                va="center",
                arrowprops={"arrowstyle": "-", "color": GRID, "linewidth": 0.8},
                annotation_clip=False,
            )
    ax.set_xlim(50, 102)
    ax.set_ylim(28, 103)
    ax.grid(color=GRID, linewidth=0.7)
    ax.set_axisbelow(True)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(colors=MUTED, labelsize=10, length=0)
    ax.set_xlabel("Coverage: records with a legal label (%)", color=MUTED, fontsize=10)
    ax.set_ylabel("Conditional accuracy: correct / answered (%)", color=MUTED, fontsize=10)
    handles = [
        plt.Line2D([], [], marker="o", linestyle="", color=c, markersize=8, label=t)
        for c, t in (
            (TEAL, "Qwen / other API"),
            (GOLD, "Jev (API)"),
            (CORAL, "Grok Build (API)"),
            (PLUM, "Local model"),
            (GRAY, "Majority-label reference"),
        )
    ]
    ax.legend(handles=handles, loc="lower left", frameon=False, fontsize=9)
    fig.subplots_adjust(left=0.07, right=0.72, top=0.86, bottom=0.1)
    add_source(fig, "Source: EXP-20260924-029 results.json (scripts/analyze_judge_comparison.py)")
    return save_figure(fig, "blind_accuracy_vs_coverage")


def plot_conditional_vs_all_record(payload: dict[str, Any]) -> list[str]:
    arms = payload["arms"]
    order = payload["rank_by_all_record_accuracy"] + [
        k for k in arms if arms[k]["family"] == "baseline"
    ]
    y = np.arange(len(order))
    fig, ax = plt.subplots(figsize=(13, 0.42 * len(order) + 2.6))
    fig.patch.set_facecolor(BG)
    add_title(
        fig,
        "What accuracy-only reporting hides",
        "760 blind records \u00b7 hollow: accuracy among answered records \u00b7 filled: "
        "accuracy over all records \u00b7 whisker: 95% Wilson interval (all-record)",
    )
    for index, key in enumerate(order):
        arm = arms[key]
        cond = arm["conditional_accuracy"] * 100
        allr = arm["all_record_accuracy"] * 100
        low, high = (v * 100 for v in arm["all_record_accuracy_95_wilson"])
        color = arm_color(key, arm)
        ax.plot([allr, cond], [index, index], color=GRID, linewidth=2.2, zorder=1)
        ax.plot([low, high], [index, index], color=INK, linewidth=0.9, zorder=2)
        ax.scatter(cond, index, s=46, facecolor=BG, edgecolor=color, linewidth=1.6, zorder=3)
        ax.scatter(allr, index, s=46, color=color, zorder=4)
        gap = cond - allr
        note = f"{allr:.1f}%" + (f"  (\u2212{gap:.1f} pts)" if gap >= 0.5 else "")
        ax.text(101.5, index, note, va="center", fontsize=8.8, color=INK)
    apply_theme(ax, (25, 100.5))
    ax.set_yticks(y, [SHORT[k] for k in order])
    ax.tick_params(axis="y", labelcolor=INK, labelsize=9.5, pad=6)
    ax.invert_yaxis()
    ax.set_xlabel("Percent", color=MUTED, fontsize=9.5)
    fig.subplots_adjust(left=0.22, right=0.86, top=0.9, bottom=0.07)
    add_source(fig, "Source: EXP-20260924-029 results.json (scripts/analyze_judge_comparison.py)")
    return save_figure(fig, "blind_conditional_vs_all_record")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    analysis = read_json(SOURCES["analysis"])
    grok = read_json(SOURCES["grok"])
    calibration = read_json(SOURCES["calibration"])

    stems = [
        "blind_accuracy_vs_coverage",
        "blind_conditional_vs_all_record",
        "grok_protocol_ablation",
        "local_qwen_calibration",
    ]
    for stale in sorted(OUT.glob("*.png")) + sorted(OUT.glob("*.svg")):
        if stale.stem not in stems:
            stale.unlink()

    generated: list[str] = []
    generated += plot_accuracy_vs_coverage(analysis)
    generated += plot_conditional_vs_all_record(analysis)
    generated += plot_grok(grok)
    generated += plot_calibration(calibration)

    manifest = {
        "generator": "scripts/generate_benchmark_figures.py",
        "figure_policy": {
            "accuracy": "conditional accuracy = correct / resolved; all-record accuracy = "
            "correct / 760 with unresolved earning no credit",
            "coverage": "resolved fraction of the 760-record blind holdout",
            "probability_metrics": "rendered only for validated native/local probability maps",
            "pooling": "arms are separate runs on the same records; nothing is pooled except the "
            "declared EXP-015 + EXP-016 Qwen merge",
        },
        "sources": {
            key: {"path": path.relative_to(ROOT).as_posix(), "sha256": sha256(path)}
            for key, path in SOURCES.items()
        },
        "outputs": [Path(item).as_posix() for item in generated],
        "figures": stems,
    }
    with (OUT / "manifest.json").open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(manifest, handle, indent=2)
        handle.write("\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
