"""Render the paper's figures in four variants each, plus a data file per figure.

Every figure is drawn from committed results in two themes (``light``, ``dark``)
and two layouts (``wide`` for desktop, ``tall`` for phones and narrow columns):

    paper/figures/benchmark/NAME.{light,dark}.{wide,tall}.svg
    paper/figures/benchmark/NAME.data.json   # the plotted values, for interactive reuse

Sources: the EXP-029 consolidated analysis (``scripts/analyze_judge_comparison.py``),
EXP-025 (Grok ablation) and EXP-019 (calibration).  Files the paper no longer uses
are deleted so the directory mirrors the paper.  SVG output is byte-stable.

Usage:
    uv run --locked python scripts/generate_benchmark_figures.py
"""

from __future__ import annotations

import hashlib
import json
import textwrap
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "paper" / "figures" / "benchmark"

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

# Fixed SVG ids and no timestamp keep regenerated SVGs byte-stable.
plt.rcParams["svg.hashsalt"] = "eval-lab-benchmark-figures"
plt.rcParams["font.family"] = "DejaVu Sans"


@dataclass(frozen=True)
class Theme:
    name: str
    bg: str
    ink: str
    muted: str
    grid: str
    top: str  # highlighted "good" series
    other: str  # neutral series
    local: str
    bad: str  # below baseline / lost
    accent: str  # secondary series


LIGHT = Theme(
    "light",
    bg="#FBFAF6",
    ink="#1A1A1A",
    muted="#5E6670",
    grid="#DDD8CC",
    top="#0F8F7E",
    other="#9AA9B8",
    local="#6F5BD6",
    bad="#D9534F",
    accent="#6F5BD6",
)
DARK = Theme(
    "dark",
    bg="#161616",
    ink="#ECEAE3",
    muted="#A7A39A",
    grid="#34363B",
    top="#3DD6BF",
    other="#6F8296",
    local="#A99BFF",
    bad="#FF8A7A",
    accent="#A99BFF",
)
THEMES = (LIGHT, DARK)


@dataclass(frozen=True)
class Layout:
    name: str
    width: float  # inches
    base: float  # tick/label font size in points
    title: float
    wrap: int  # title wrap width in characters


WIDE = Layout("wide", width=10.0, base=14, title=20, wrap=56)
TALL = Layout("tall", width=4.4, base=14, title=18, wrap=26)
LAYOUTS = (WIDE, TALL)


PLAIN = {
    "ali_qwen38_flash_exp024": "Qwen3.8 Flash",
    "ali_qwen38_max_exp024": "Qwen 3.8 Max",
    "ali_kimi_k27_code_exp024": "Kimi K2.7 Code",
    "cbcn_glm53_flash_exp024": "GLM 5.3 Flash",
    "cbcn_minimax_m3_exp024": "MiniMax M3",
    "ali_glm52_exp024": "GLM 5.2",
    "jev_exp014": "Jev 1.13 (run 1)",
    "jev_exp022": "Jev 1.13",
    "qwen_flash_exp013": "Qwen3.8 Flash, thinking off",
    "qwen_flash_exp015": "Qwen3.8 Flash, one pass",
    "qwen_flash_exp015_016": "Qwen3.8 Flash + retry",
    "qwen_flash_exp022": "Qwen3.8 Flash (defaults)",
    "cb_deepseek_v41_flash_exp024": "DeepSeek V4.1 Flash",
    "cbcn_deepseek_v4_flash_exp024": "DeepSeek V4 Flash",
    "kev_4b_exp027": "Kev-4B (local)",
    "semif_qwen35_4b_exp027": "SemIf 4B (local)",
    "kev_08b_exp027": "Kev-0.8B (local)",
    "laya_421m_exp027": "Laya 421M (local)",
    "qwen3_4b_exp017": "Qwen3-4B (local)",
    "grok46_exp015": "Grok 4.6 Build (run 1)",
    "grok46_exp022": "Grok 4.6 Build",
    "grok46_exp025": "Grok 4.6 Build (rerun)",
    "grok47_exp022": "Grok 4.7 Build",
    "verdict_14_exp027": "Verdict 1.4 (local)",
    "verdict_original_exp027": "Verdict pre-v1.4 (local)",
    "majority_exp014": "Always-same-answer baseline",
}


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def sha256(path: Path) -> str:
    """SHA-256 of LF-normalized bytes so Windows CRLF checkouts hash identically."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


# --- Shared drawing helpers ---------------------------------------------------


def new_figure(theme: Theme, layout: Layout, height: float, data: dict[str, Any]):
    """Create a figure with a wrapped title block and a source line; return (fig, top, bottom)."""
    title, subtitle = data["title"], data["subtitle"]
    source = data.get("source", "EXP-029")
    note = (
        f"Source: Eval Lab {source}"
        if layout.name == "tall"
        else f"Source: Eval Lab {source} results (scripts/generate_benchmark_figures.py)"
    )
    fig = plt.figure(figsize=(layout.width, height))
    fig.patch.set_facecolor(theme.bg)
    title_lines = textwrap.wrap(title, layout.wrap)
    sub_lines = textwrap.wrap(subtitle, int(layout.wrap * layout.title / layout.base * 0.95))
    y = height - 0.2
    for line in title_lines:
        fig.text(
            0.2 / layout.width,
            y / height,
            line,
            ha="left",
            va="top",
            fontsize=layout.title,
            fontweight="bold",
            color=theme.ink,
        )
        y -= layout.title / 72 * 1.28
    y -= 0.06
    for line in sub_lines:
        fig.text(
            0.2 / layout.width,
            y / height,
            line,
            ha="left",
            va="top",
            fontsize=layout.base,
            color=theme.muted,
        )
        y -= layout.base / 72 * 1.35
    fig.text(
        0.2 / layout.width,
        0.12 / height,
        note,
        ha="left",
        va="bottom",
        fontsize=layout.base * 0.72,
        color=theme.muted,
    )
    top = (y - 0.25) / height
    bottom = (0.12 + layout.base * 0.72 / 72 + 0.35) / height
    return fig, top, bottom


def style_axes(ax: plt.Axes, theme: Theme, layout: Layout, grid_axis: str = "x") -> None:
    ax.set_facecolor(theme.bg)
    ax.grid(axis=grid_axis, color=theme.grid, linewidth=0.9)
    ax.set_axisbelow(True)
    ax.tick_params(colors=theme.muted, labelsize=layout.base, length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)


def save_svg(fig: plt.Figure, stem: str, theme: Theme, layout: Layout) -> str:
    path = OUT / f"{stem}.{theme.name}.{layout.name}.svg"
    fig.savefig(path, facecolor=theme.bg, metadata={"Date": None})
    plt.close(fig)
    return path.relative_to(ROOT).as_posix()


def pct(value: float) -> str:
    return f"{value * 100:.1f}%"


# --- Figure 1: accuracy range -------------------------------------------------

RANGE_ARMS = (
    "ali_qwen38_flash_exp024",
    "ali_qwen38_max_exp024",
    "ali_kimi_k27_code_exp024",
    "cbcn_glm53_flash_exp024",
    "cbcn_minimax_m3_exp024",
    "jev_exp022",
    "cbcn_deepseek_v4_flash_exp024",
    "kev_4b_exp027",
    "semif_qwen35_4b_exp027",
    "grok46_exp022",
    "verdict_14_exp027",
)


def range_data(analysis: dict[str, Any]) -> dict[str, Any]:
    arms = analysis["arms"]
    majority = arms["majority_exp014"]["all_record_accuracy"]
    keys = sorted(RANGE_ARMS, key=lambda k: (-arms[k]["all_record_accuracy"], k))
    rows = []
    for key in keys:
        arm = arms[key]
        value = arm["all_record_accuracy"]
        group = (
            "below_baseline"
            if value < majority
            else "local"
            if arm["family"] == "local"
            else "top_api"
            if value >= 0.98
            else "other_api"
        )
        rows.append({"key": key, "label": PLAIN[key], "value": value, "group": group})
    return {
        "title": "Top judges get about 99% right; some do worse than a constant guess",
        "subtitle": "Share of all 760 questions answered correctly (skipped = wrong)",
        "unit": "fraction",
        "baseline": {"label": "always-same-answer baseline", "value": majority},
        "rows": rows,
    }


def draw_range(data: dict[str, Any], theme: Theme, layout: Layout) -> plt.Figure:
    rows = data["rows"]
    colors = {
        "top_api": theme.top,
        "other_api": theme.other,
        "local": theme.local,
        "below_baseline": theme.bad,
    }
    tall = layout.name == "tall"
    row_h = 0.62 if tall else 0.46
    height = 2.2 + row_h * len(rows) + (1.2 if tall else 0.9)
    fig, top, bottom = new_figure(theme, layout, height, data)
    legend_h = 0.9 / height if tall else 0
    ax = fig.add_axes(
        (0.02 if tall else 0.25, bottom + legend_h, 0.9 if tall else 0.7, top - bottom - legend_h)
    )
    style_axes(ax, theme, layout)
    baseline = data["baseline"]["value"] * 100
    y = np.arange(len(rows))
    values = [row["value"] * 100 for row in rows]
    bar_h = 0.34 if tall else 0.68
    ax.barh(y, values, height=bar_h, color=[colors[r["group"]] for r in rows], edgecolor="none")
    for index, (row, value) in enumerate(zip(rows, values)):
        if tall:
            ax.text(
                0,
                index - 0.3,
                row["label"],
                fontsize=layout.base,
                color=theme.ink,
                va="bottom",
                ha="left",
            )
        inside = value < baseline
        ax.text(
            value - 1 if inside else value + 1,
            index,
            f"{value:.1f}%",
            va="center",
            ha="right" if inside else "left",
            fontsize=layout.base,
            color=theme.bg if inside else theme.ink,
            fontweight="bold" if inside else "normal",
        )
    ax.axvline(baseline, color=theme.ink, linestyle="--", linewidth=1.3)
    ax.text(
        baseline + 1,
        -0.95 if not tall else -1.05,
        f"baseline {baseline:.1f}%",
        fontsize=layout.base * 0.92,
        color=theme.ink,
        va="center",
    )
    ax.set_xlim(0, 118)
    ax.set_ylim(len(rows) - 0.4, -1.4)
    ax.set_xticks([0, 25, 50, 75, 100])
    if tall:
        ax.set_yticks([])
    else:
        ax.set_yticks(y, [row["label"] for row in rows])
        ax.tick_params(axis="y", labelcolor=theme.ink, labelsize=layout.base, pad=6)
    handles = [
        plt.Rectangle((0, 0), 1, 1, color=colors[key], label=text)
        for key, text in (
            ("top_api", "API, 98% or more"),
            ("other_api", "other API"),
            ("local", "local, above baseline"),
            ("below_baseline", "below baseline"),
        )
    ]
    if tall:
        fig.legend(
            handles=handles,
            loc="lower left",
            bbox_to_anchor=(0.02, bottom - 0.02),
            ncol=2,
            frameon=False,
            fontsize=layout.base * 0.9,
            labelcolor=theme.ink,
        )
    else:
        ax.legend(
            handles=handles,
            loc="lower right",
            frameon=True,
            facecolor=theme.bg,
            edgecolor=theme.grid,
            fontsize=layout.base * 0.92,
            labelcolor=theme.ink,
        )
    return fig


# --- Figure 2: skipped questions ----------------------------------------------

SKIP_ARMS = (
    "cbcn_deepseek_v4_flash_exp024",
    "ali_glm52_exp024",
    "qwen_flash_exp015",
    "verdict_14_exp027",
    "verdict_original_exp027",
)


def skipped_data(analysis: dict[str, Any]) -> dict[str, Any]:
    arms = analysis["arms"]
    return {
        "title": "Scores on answered questions hide skipped ones",
        "subtitle": "Hollow: correct when it answered · filled: correct over all 760",
        "unit": "fraction",
        "baseline": {
            "label": "always-same-answer baseline",
            "value": arms["majority_exp014"]["all_record_accuracy"],
        },
        "rows": [
            {
                "key": key,
                "label": PLAIN[key],
                "answered_accuracy": arms[key]["conditional_accuracy"],
                "all_record_accuracy": arms[key]["all_record_accuracy"],
                "coverage": arms[key]["coverage"],
            }
            for key in SKIP_ARMS
        ],
    }


def draw_skipped(data: dict[str, Any], theme: Theme, layout: Layout) -> plt.Figure:
    rows = data["rows"]
    tall = layout.name == "tall"
    row_h = 0.95 if tall else 0.62
    height = 2.2 + row_h * len(rows) + 0.8
    fig, top, bottom = new_figure(theme, layout, height, data)
    ax = fig.add_axes((0.04 if tall else 0.3, bottom, 0.9 if tall else 0.66, top - bottom))
    style_axes(ax, theme, layout)
    baseline = data["baseline"]["value"] * 100
    for index, row in enumerate(rows):
        cond = row["answered_accuracy"] * 100
        allr = row["all_record_accuracy"] * 100
        ax.plot(
            [allr, cond],
            [index, index],
            color=theme.grid,
            linewidth=6,
            zorder=1,
            solid_capstyle="round",
        )
        ax.scatter(
            cond, index, s=170, facecolor=theme.bg, edgecolor=theme.top, linewidth=2.6, zorder=3
        )
        ax.scatter(allr, index, s=170, color=theme.bad, zorder=4)
        ax.text(
            cond + 3, index, f"{cond:.1f}%", va="center", fontsize=layout.base, color=theme.muted
        )
        ax.text(
            allr - 3,
            index,
            f"{allr:.1f}%",
            va="center",
            ha="right",
            fontsize=layout.base,
            color=theme.ink,
            fontweight="bold",
        )
        if tall:
            ax.text(
                8, index - 0.42, row["label"], fontsize=layout.base, color=theme.ink, va="bottom"
            )
    ax.axvline(baseline, color=theme.muted, linestyle=":", linewidth=1.2, zorder=0)
    ax.text(
        baseline,
        -0.85 if not tall else -1.0,
        f"baseline {baseline:.1f}%",
        ha="center",
        fontsize=layout.base * 0.92,
        color=theme.muted,
    )
    ax.set_xlim(5 if tall else 15, 118)
    ax.set_ylim(len(rows) - 0.4, -1.25 if tall else -1.1)
    ax.set_xticks([25, 50, 75, 100])
    if tall:
        ax.set_yticks([])
    else:
        ax.set_yticks(np.arange(len(rows)), [row["label"] for row in rows])
        ax.tick_params(axis="y", labelcolor=theme.ink, labelsize=layout.base, pad=6)
    return fig


# --- Figure 3: request settings -----------------------------------------------

QWEN_RUNS = (
    ("qwen_flash_exp013", "EXP-013", "128-token cap, thinking off"),
    ("qwen_flash_exp022", "EXP-022", "provider defaults"),
    ("ali_qwen38_flash_exp024", "EXP-024", "other route, 1,024-token cap"),
)


def settings_data(analysis: dict[str, Any]) -> dict[str, Any]:
    arms = analysis["arms"]
    first = arms["qwen_flash_exp013"]["conditional_accuracy"]
    second = arms["qwen_flash_exp022"]["conditional_accuracy"]
    return {
        "title": f"Same model, same questions: {pct(first)} vs {pct(second)}",
        "subtitle": "Qwen3.8 Flash accuracy when it answered, by request settings",
        "unit": "fraction",
        "series": [
            {"key": "overall", "label": "All questions"},
            {"key": "gsm8k", "label": "Math (GSM8K)"},
        ],
        "rows": [
            {
                "key": key,
                "label": run,
                "settings": settings,
                "overall": arms[key]["conditional_accuracy"],
                "gsm8k": arms[key]["by_source"]["GSM8K"]["accuracy"],
            }
            for key, run, settings in QWEN_RUNS
        ],
    }


def draw_settings(data: dict[str, Any], theme: Theme, layout: Layout) -> plt.Figure:
    rows = data["rows"]
    tall = layout.name == "tall"
    colors = (theme.top, theme.accent)
    if tall:
        height = 2.3 + 1.45 * len(rows) + 0.9
        fig, top, bottom = new_figure(theme, layout, height, data)
        legend_h = 0.5 / height
        ax = fig.add_axes((0.04, bottom, 0.9, top - bottom - legend_h))
        style_axes(ax, theme, layout)
        for index, row in enumerate(rows):
            base = index * 3
            ax.text(
                0,
                base - 0.75,
                f"{row['label']}: {row['settings']}",
                fontsize=layout.base,
                color=theme.ink,
                va="bottom",
            )
            for offset, (series, color) in enumerate(zip(data["series"], colors)):
                value = row[series["key"]] * 100
                ax.barh(base + offset * 0.9, value, height=0.8, color=color)
                ax.text(
                    value + 1.2,
                    base + offset * 0.9,
                    f"{value:.1f}%",
                    va="center",
                    fontsize=layout.base,
                    color=theme.ink,
                )
        ax.set_xlim(0, 120)
        ax.set_ylim(3 * len(rows) - 1.2, -1.4)
        ax.set_yticks([])
        ax.set_xticks([0, 25, 50, 75, 100])
        handles = [
            plt.Rectangle((0, 0), 1, 1, color=c, label=s["label"])
            for s, c in zip(data["series"], colors)
        ]
        fig.legend(
            handles=handles,
            loc="upper left",
            bbox_to_anchor=(0.02, top + 0.005),
            ncol=2,
            frameon=False,
            fontsize=layout.base,
            labelcolor=theme.ink,
        )
        return fig
    height = 6.4
    fig, top, bottom = new_figure(theme, layout, height, data)
    ax = fig.add_axes((0.08, bottom + 0.16, 0.9, top - bottom - 0.24))
    style_axes(ax, theme, layout, grid_axis="y")
    x = np.arange(len(rows))
    width = 0.36
    for offset, (series, color) in enumerate(zip(data["series"], colors)):
        values = [row[series["key"]] * 100 for row in rows]
        bars = ax.bar(x + (offset - 0.5) * width, values, width, color=color, label=series["label"])
        for bar in bars:
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 1.2,
                f"{bar.get_height():.1f}%",
                ha="center",
                va="bottom",
                fontsize=layout.base,
                color=theme.ink,
            )
    ax.set_ylim(0, 112)
    ax.set_yticks([0, 25, 50, 75, 100])
    ax.set_xticks(x, [f"{row['label']}\n{row['settings']}" for row in rows])
    ax.tick_params(axis="x", labelcolor=theme.ink, labelsize=layout.base)
    ax.legend(
        loc="upper left",
        bbox_to_anchor=(0, 1.13),
        ncol=2,
        frameon=False,
        fontsize=layout.base,
        labelcolor=theme.ink,
    )
    return fig


# --- Figure A1: every judge ranked ----------------------------------------------

HIGHLIGHT = {
    "ali_qwen38_flash_exp024",
    "ali_qwen38_max_exp024",
    "jev_exp022",
    "cbcn_deepseek_v4_flash_exp024",
    "qwen_flash_exp013",
    "qwen_flash_exp015",
    "kev_4b_exp027",
    "grok46_exp022",
    "verdict_14_exp027",
}


def ranked_data(analysis: dict[str, Any]) -> dict[str, Any]:
    arms = analysis["arms"]
    ranks = analysis["shared_ranks_all_record"]
    order = analysis["rank_by_all_record_accuracy"]
    majority = arms["majority_exp014"]["all_record_accuracy"]
    top_count = sum(1 for key in order if ranks[key] == 1)
    below = sum(1 for key in order if arms[key]["all_record_accuracy"] < majority)
    return {
        "title": f"{top_count} judges share first place; {below} score below the baseline",
        "subtitle": (
            "All 25 judges, correct over all 760 questions, with 95% Wilson intervals. "
            "Shared rank = not separable from the group's top judge (Holm-corrected McNemar)."
        ),
        "unit": "fraction",
        "baseline": {"label": "always-same-answer baseline", "value": majority},
        "rows": [
            {
                "key": key,
                "label": PLAIN[key],
                "rank": ranks[key],
                "value": arms[key]["all_record_accuracy"],
                "interval": arms[key]["all_record_accuracy_95_wilson"],
                "coverage": arms[key]["coverage"],
                "family": arms[key]["family"],
                "highlight": key in HIGHLIGHT,
            }
            for key in order
        ],
    }


def draw_ranked(data: dict[str, Any], theme: Theme, layout: Layout) -> plt.Figure:
    rows = data["rows"]
    tall = layout.name == "tall"
    row_h = 0.56 if tall else 0.36
    height = 2.8 + row_h * len(rows) + 0.8
    fig, top, bottom = new_figure(theme, layout, height, data)
    rect = (
        (0.04, bottom, 0.74, top - bottom - 0.02)
        if tall
        else (0.35, bottom, 0.46, top - bottom - 0.02)
    )
    ax = fig.add_axes(rect)
    style_axes(ax, theme, layout)
    axis_x = ax.get_yaxis_transform()
    baseline = data["baseline"]["value"] * 100
    fs = layout.base * (0.88 if tall else 0.95)
    for index, row in enumerate(rows):
        value = row["value"] * 100
        low, high = (v * 100 for v in row["interval"])
        color = (theme.bad if value < baseline else theme.top) if row["highlight"] else theme.other
        ax.plot([low, high], [index, index], color=color, linewidth=2.2, zorder=2)
        ax.scatter(value, index, s=55 if tall else 70, color=color, zorder=3)
        label = f"#{row['rank']}  {row['label']}"
        if tall and row["coverage"] < 0.99:
            label += f"  ({row['coverage'] * 100:.0f}% answered)"
        weight = "bold" if row["highlight"] else "normal"
        text_color = theme.ink if row["highlight"] else theme.muted
        if tall:
            ax.text(
                0.0,
                index - 0.2,
                label,
                transform=axis_x,
                fontsize=fs * 0.9,
                color=text_color,
                fontweight=weight,
                va="bottom",
            )
        else:
            ax.text(
                -0.02,
                index,
                label,
                transform=axis_x,
                fontsize=fs,
                color=text_color,
                fontweight=weight,
                va="center",
                ha="right",
            )
        ax.text(
            1.03,
            index,
            f"{value:.1f}%",
            transform=axis_x,
            fontsize=fs,
            color=text_color,
            fontweight=weight,
            va="center",
            ha="left",
        )
        if not tall:
            answered = row["coverage"] * 100
            ax.text(
                1.36,
                index,
                f"{answered:.0f}%",
                transform=axis_x,
                fontsize=fs,
                color=theme.bad if answered < 99 else theme.muted,
                va="center",
                ha="right",
            )
    ax.axvline(baseline, color=theme.muted, linestyle=":", linewidth=1.2, zorder=0)
    ax.text(
        baseline,
        -1.3,
        f"baseline {baseline:.1f}%",
        ha="center",
        fontsize=fs * 0.9,
        color=theme.muted,
        va="center",
    )
    ax.text(
        1.03,
        -1.3,
        "correct" if tall else "correct   answered",
        transform=axis_x,
        fontsize=fs * 0.85,
        color=theme.muted,
        va="center",
        ha="left",
    )
    ax.set_xlim(0 if tall else 25, 101)
    ax.set_ylim(len(rows) - 0.5, -1.9)
    ax.set_yticks([])
    ax.set_xticks([25, 50, 75, 100])
    return fig


# --- Appendix: Grok ablation ------------------------------------------------------

GROK_VARIANTS = (
    ("typed_schema", "Typed schema (baseline)"),
    ("explicit_schema", "Explicit wording + schema"),
    ("semantic_schema", "Semantic labels + schema"),
    ("explicit_no_schema", "Explicit wording, no schema"),
)


def grok_data(payload: dict[str, Any]) -> dict[str, Any]:
    variants = payload["public"]["variants"]
    blind = payload["blind"]
    return {
        "title": "No request format fixed Grok Build's failure",
        "source": "EXP-025",
        "subtitle": f"EXP-025 public diagnostic ({payload['public']['record_count']} questions)",
        "rows": [
            {
                "key": key,
                "label": label,
                "score": variants[key]["selection_score"],
                "coverage": variants[key]["coverage"],
            }
            for key, label in GROK_VARIANTS
        ],
        "blind_baseline": {
            "score": blind["selection_score"],
            "coverage": blind["coverage"],
            "single_accuracy": blind["single_accuracy"],
            "pairwise_accuracy": blind["pairwise_accuracy"],
        },
    }


def draw_grok(data: dict[str, Any], theme: Theme, layout: Layout) -> plt.Figure:
    rows = data["rows"]
    tall = layout.name == "tall"
    height = 9.6 if tall else 6.2
    fig, top, bottom = new_figure(theme, layout, height, data)
    blind = data["blind_baseline"]
    note = (
        f"Blind rerun of the baseline: score {blind['score']:.4f}, "
        f"{blind['coverage'] * 100:.1f}% answered, {blind['pairwise_accuracy'] * 100:.1f}% on "
        "pick-the-better questions"
    )
    note_lines = textwrap.wrap(note, 44 if tall else 110)
    note_h = (len(note_lines) * layout.base * 1.4 / 72 + 0.2) / height
    fig.text(
        0.2 / layout.width,
        bottom,
        "\n".join(note_lines),
        ha="left",
        va="bottom",
        fontsize=layout.base * 0.92,
        color=theme.ink,
        linespacing=1.4,
    )
    area_bottom = bottom + note_h + 0.03
    panels = (
        ("score", "Mode-balanced score", (0, 0.36), [0, 0.1, 0.2, 0.3]),
        ("coverage", "Share answered", (0, 1.25), [0, 0.5, 1.0]),
    )
    colors = [theme.top, theme.other, theme.other, theme.bad]
    y = np.arange(len(rows))
    for p_index, (key, title, xlim, ticks) in enumerate(panels):
        if tall:
            h = (top - area_bottom) / 2
            rect = (0.05, area_bottom + (1 - p_index) * h + 0.02, 0.88, h - 0.08)
        else:
            rect = (0.3 + p_index * 0.36, area_bottom + 0.02, 0.3, top - area_bottom - 0.08)
        ax = fig.add_axes(rect)
        style_axes(ax, theme, layout)
        ax.set_title(
            title, loc="left", fontsize=layout.base, fontweight="bold", color=theme.ink, pad=8
        )
        values = [row[key] if row[key] is not None else 0 for row in rows]
        ax.barh(y, values, height=0.45 if tall else 0.62, color=colors)
        for index, (row, value) in enumerate(zip(rows, values)):
            shown = (
                "no readable answers"
                if row[key] is None
                else (f"{value:.4f}" if key == "score" else f"{value * 100:.1f}%")
            )
            ax.text(
                value + xlim[1] * 0.02,
                index,
                shown,
                va="center",
                fontsize=layout.base * 0.92,
                color=theme.ink,
            )
            if tall:
                ax.text(
                    0,
                    index - 0.3,
                    row["label"],
                    fontsize=layout.base * 0.92,
                    color=theme.muted,
                    va="bottom",
                )
        ax.set_xlim(*xlim)
        ax.set_xticks(ticks, [f"{t:.1f}" if key == "score" else f"{t * 100:.0f}%" for t in ticks])
        ax.set_ylim(len(rows) - 0.5, -0.9 if tall else -0.5)
        if tall or p_index == 1:
            ax.set_yticks([])
        else:
            ax.set_yticks(y, [row["label"] for row in rows])
            ax.tick_params(axis="y", labelcolor=theme.ink, labelsize=layout.base)
    return fig


# --- Appendix: calibration ----------------------------------------------------------

CAL_METRICS = (
    ("brier", "Brier score"),
    ("nll", "Negative log likelihood"),
    ("ece", "Expected calibration error"),
)


def calibration_data(payload: dict[str, Any]) -> dict[str, Any]:
    raw = payload["calibration"]["blind_holdout"]["raw"]
    calibrated = payload["calibration"]["blind_holdout"]["calibrated"]
    return {
        "title": "Calibration made confidence more honest; answers stayed the same",
        "source": "EXP-019",
        "subtitle": (
            f"Local Qwen3-4B, blind set (accuracy {float(calibrated['accuracy']) * 100:.2f}% "
            "before and after) · lower is better"
        ),
        "rows": [
            {
                "key": key,
                "label": label,
                "raw": float(raw[key]),
                "calibrated": float(calibrated[key]),
            }
            for key, label in CAL_METRICS
        ],
    }


def draw_calibration(data: dict[str, Any], theme: Theme, layout: Layout) -> plt.Figure:
    rows = data["rows"]
    tall = layout.name == "tall"
    height = 8.6 if tall else 5.6
    fig, top, bottom = new_figure(theme, layout, height, data)
    for index, row in enumerate(rows):
        if tall:
            h = (top - bottom) / 3
            rect = (0.05, bottom + (2 - index) * h + 0.02, 0.85, h - 0.09)
        else:
            rect = (0.05 + index * 0.32, bottom + 0.02, 0.26, top - bottom - 0.1)
        ax = fig.add_axes(rect)
        style_axes(ax, theme, layout, grid_axis="x" if tall else "y")
        ax.set_title(
            row["label"],
            loc="left",
            fontsize=layout.base,
            fontweight="bold",
            color=theme.ink,
            pad=8,
        )
        values = [row["raw"], row["calibrated"]]
        colors = [theme.other, theme.top]
        labels = ["Raw", "Calibrated"]
        top_value = max(values) * 1.35
        if tall:
            ax.barh([0, 1], values, height=0.6, color=colors)
            for i, value in enumerate(values):
                ax.text(
                    value + top_value * 0.02,
                    i,
                    f"{labels[i]} {value:.4f}",
                    va="center",
                    fontsize=layout.base * 0.95,
                    color=theme.ink,
                )
            ax.set_xlim(0, top_value * 1.25)
            ax.set_ylim(1.6, -0.6)
            ax.set_yticks([])
        else:
            ax.bar([0, 1], values, width=0.58, color=colors)
            for i, value in enumerate(values):
                ax.text(
                    i,
                    value + top_value * 0.02,
                    f"{value:.4f}",
                    ha="center",
                    va="bottom",
                    fontsize=layout.base,
                    color=theme.ink,
                )
            ax.set_ylim(0, top_value)
            ax.set_xticks([0, 1], labels)
            ax.tick_params(axis="x", labelcolor=theme.ink)
    return fig


# --- Driver -------------------------------------------------------------------------

Figure = tuple[str, Callable[[], dict[str, Any]], Callable[[dict[str, Any], Theme, Layout], Any]]


def figures(analysis: dict[str, Any], grok: dict[str, Any], calibration: dict[str, Any]):
    return (
        ("finding_accuracy_range", lambda: range_data(analysis), draw_range),
        ("finding_skipped_questions", lambda: skipped_data(analysis), draw_skipped),
        ("finding_request_settings", lambda: settings_data(analysis), draw_settings),
        ("judges_ranked", lambda: ranked_data(analysis), draw_ranked),
        ("grok_protocol_ablation", lambda: grok_data(grok), draw_grok),
        ("local_qwen_calibration", lambda: calibration_data(calibration), draw_calibration),
    )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    analysis = read_json(SOURCES["analysis"])
    grok = read_json(SOURCES["grok"])
    calibration = read_json(SOURCES["calibration"])
    specs = figures(analysis, grok, calibration)
    expected = set()
    for stem, _, _ in specs:
        expected.add(f"{stem}.data.json")
        for theme in THEMES:
            for layout in LAYOUTS:
                expected.add(f"{stem}.{theme.name}.{layout.name}.svg")
    for stale in sorted(OUT.iterdir()):
        if stale.is_file() and stale.name != "manifest.json" and stale.name not in expected:
            stale.unlink()

    manifest_figures: dict[str, Any] = {}
    for stem, build_data, draw in specs:
        data = build_data()
        data_path = OUT / f"{stem}.data.json"
        with data_path.open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(data, handle, indent=2, sort_keys=True)
            handle.write("\n")
        variants = {}
        for theme in THEMES:
            for layout in LAYOUTS:
                variants[f"{theme.name}.{layout.name}"] = save_svg(
                    draw(data, theme, layout), stem, theme, layout
                )
        manifest_figures[stem] = {
            "title": data["title"],
            "data": data_path.relative_to(ROOT).as_posix(),
            "variants": variants,
        }

    manifest = {
        "generator": "scripts/generate_benchmark_figures.py",
        "naming": "NAME.{light,dark}.{wide,tall}.svg plus NAME.data.json (plotted values)",
        "figure_policy": {
            "accuracy": "conditional accuracy = correct / resolved; all-record accuracy = "
            "correct / 760 with unresolved earning no credit",
            "coverage": "resolved fraction of the 760-record blind holdout",
            "interval": "95% Wilson score interval",
            "shared_rank": "competition rank by all-record accuracy; an arm shares its group's "
            "rank when the Holm-corrected all-760 McNemar test gives p >= 0.05 against the "
            "group's top arm",
        },
        "sources": {
            key: {"path": path.relative_to(ROOT).as_posix(), "sha256": sha256(path)}
            for key, path in SOURCES.items()
        },
        "figures": manifest_figures,
    }
    with (OUT / "manifest.json").open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(manifest, handle, indent=2)
        handle.write("\n")
    print(f"wrote {len(manifest_figures)} figures x 4 variants to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
