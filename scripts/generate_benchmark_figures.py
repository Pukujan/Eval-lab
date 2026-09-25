"""Render the paper's figures in four variants each, plus a data file per figure.

Every figure is drawn from committed results in two themes (``light``, ``dark``)
and two layouts (``wide`` for desktop, ``tall`` for phones and narrow columns):

    paper/figures/benchmark/NAME.{light,dark}.{wide,tall}.svg
    paper/figures/benchmark/NAME.data.json   # the plotted values, for interactive reuse

Sources: the EXP-029 consolidated analysis (``scripts/analyze_judge_comparison.py``),
EXP-025 (Grok ablation) and EXP-019 (calibration).  Files the paper no longer uses
are deleted so the directory mirrors the paper.  SVG output is byte-stable.

Chart style follows the writing guide: plain bars for counts and shares, no
whiskers, direct labels instead of legends, a takeaway title, and a source line a
reader can use.  TASK-0061 replaced the dumbbell chart with a stacked bar per
judge (right / wrong / skipped out of 760), the interval chart with plain bars
that grey out the judges tied with the leader, and the settings chart with two
bars for the same model under two setups.

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

DATA_LINK = "github.com/Pukujan/Eval-lab/tree/main/paper/data"
BENCHMARK_NOTE = (
    "Source: Eval Lab benchmark of 25 AI graders on 760 questions with known "
    f"answers. Data: {DATA_LINK}"
)


@dataclass(frozen=True)
class Theme:
    name: str
    bg: str
    ink: str
    muted: str
    grid: str
    top: str  # right answers / clearly above the floor
    other: str  # neutral series
    local: str
    bad: str  # wrong answers / below the floor
    skip: str  # questions the grader never answered
    tied: str  # too close to the leader to call


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
    skip="#CFC9BC",
    tied="#B4B0A6",
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
    skip="#4A4A48",
    tied="#6E6A62",
)
THEMES = (LIGHT, DARK)


@dataclass(frozen=True)
class Layout:
    name: str
    width: float  # inches
    base: float  # tick/label font size in points
    title: float
    wrap: int  # title wrap width in characters
    note_wrap: int  # wrap width for text drawn inside the axes
    label_frac: float  # share of the figure width reserved for row names


WIDE = Layout("wide", width=10.0, base=14, title=20, wrap=56, note_wrap=64, label_frac=0.34)
TALL = Layout("tall", width=4.4, base=14, title=18, wrap=26, note_wrap=38, label_frac=0.04)
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
    "qwen_flash_exp013": "Qwen3.8 Flash (thinking off)",
    "qwen_flash_exp015": "Qwen3.8 Flash (317 refused)",
    "qwen_flash_exp015_016": "Qwen3.8 Flash (retried)",
    "qwen_flash_exp022": "Qwen3.8 Flash (provider defaults)",
    "cb_deepseek_v41_flash_exp024": "DeepSeek V4.1 Flash",
    "cbcn_deepseek_v4_flash_exp024": "DeepSeek V4 Flash",
    "kev_4b_exp027": "Kev-4B (on our computer)",
    "semif_qwen35_4b_exp027": "SemIf 4B (on our computer)",
    "kev_08b_exp027": "Kev-0.8B (on our computer)",
    "laya_421m_exp027": "Laya 421M (on our computer)",
    "qwen3_4b_exp017": "Qwen3-4B (on our computer)",
    "grok46_exp015": "Grok 4.6 Build (run 1)",
    "grok46_exp022": "Grok 4.6 Build",
    "grok46_exp025": "Grok 4.6 Build (format test)",
    "grok47_exp022": "Grok 4.7 Build",
    "verdict_14_exp027": "Our grader 1.4",
    "verdict_original_exp027": "Our grader, older version",
    "majority_exp014": "Always the same answer",
}

FLOOR_SENTENCE = "A grader that always gives the same answer scores {value:.1f}%."


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
    note = data.get("source_note", BENCHMARK_NOTE)
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
    note_lines = textwrap.wrap(note, int(layout.wrap * 1.75))
    for offset, line in enumerate(reversed(note_lines)):
        fig.text(
            0.2 / layout.width,
            (0.12 + offset * layout.base * 0.72 / 72 * 1.35) / height,
            line,
            ha="left",
            va="bottom",
            fontsize=layout.base * 0.72,
            color=theme.muted,
        )
    top = (y - 0.25) / height
    bottom = (0.12 + len(note_lines) * layout.base * 0.72 / 72 * 1.35 + 0.35) / height
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


def wrap_note(text: str, layout: Layout) -> list[str]:
    return textwrap.wrap(text, layout.note_wrap)


def row_step(layout: Layout) -> float:
    """Vertical distance between bars; tall layouts leave room for the name above each bar."""
    return 1.5 if layout.name == "tall" else 1.0


def row_positions(count: int, layout: Layout) -> np.ndarray:
    return np.arange(count) * row_step(layout)


def axes_rect(layout: Layout, top: float, bottom: float) -> tuple[float, float, float, float]:
    """Plot area: row names on the left when wide, above the bars when tall."""
    left = layout.label_frac
    return (left, bottom, 0.96 - left, top - bottom)


def row_labels(ax: plt.Axes, rows: list[dict[str, Any]], theme: Theme, layout: Layout) -> None:
    """Judge names beside the bars (wide) or above them (tall)."""
    if layout.name == "tall":
        ax.set_yticks([])
        for index, row in enumerate(rows):
            label = row["label"]
            if row.get("coverage", 1.0) < 0.99:
                label += f", {row['coverage'] * 100:.0f}% answered"
            ax.text(
                0,
                index * row_step(layout) - 0.45,
                label,
                fontsize=layout.base,
                color=theme.ink,
                va="bottom",
                ha="left",
            )
    else:
        ax.set_yticks(np.arange(len(rows)), [row["label"] for row in rows])
        ax.tick_params(axis="y", labelcolor=theme.ink, labelsize=layout.base, pad=6)


def floor_line(
    ax: plt.Axes,
    theme: Theme,
    layout: Layout,
    baseline: float,
    label_y: float,
    value: float,
    rows: int,
) -> None:
    """Draw the always-same-answer line over the bars, and label it with a sentence."""
    ax.plot(
        [baseline, baseline],
        [-0.6 * row_step(layout), (rows - 1) * row_step(layout) + 0.6],
        color=theme.ink,
        linestyle="--",
        linewidth=1.3,
        zorder=1,
    )
    lines = textwrap.wrap(FLOOR_SENTENCE.format(value=value), max(16, layout.note_wrap // 2))
    ax.text(
        baseline + 2,
        label_y,
        "\n".join(lines),
        fontsize=layout.base * 0.95,
        color=theme.ink,
        va="bottom",
        ha="left",
        linespacing=1.35,
    )


def note_block(
    ax: plt.Axes,
    theme: Theme,
    layout: Layout,
    notes: list[dict[str, Any]],
    rows: list[dict[str, Any]],
    anchors: list[float],
) -> float:
    """Write wrapped annotations below the bars, each with an arrow to its bar.

    Returns the lowest y used, so the caller can size the axis.
    """
    y = (len(rows) - 1) * row_step(layout) + 1.3
    for note, anchor in zip(notes, anchors):
        lines = wrap_note(note["text"], layout)
        index = next(i for i, row in enumerate(rows) if row["key"] == note["key"])
        ax.annotate(
            "\n".join(lines),
            xy=(anchor, index * row_step(layout) + 0.5),
            xytext=(0, y),
            textcoords="data",
            fontsize=layout.base * 0.95,
            color=theme.ink,
            va="top",
            ha="left",
            linespacing=1.35,
            arrowprops={
                "arrowstyle": "-|>",
                "color": theme.muted,
                "linewidth": 1.2,
                "shrinkA": 3,
                "shrinkB": 5,
            },
        )
        y += len(lines) + 0.7
    return y


# --- Figure 1: what each grader did with all 760 questions ---------------------

SKIP_ARMS = (
    "ali_qwen38_flash_exp024",
    "ali_qwen38_max_exp024",
    "ali_kimi_k27_code_exp024",
    "cbcn_glm53_flash_exp024",
    "cbcn_minimax_m3_exp024",
    "ali_glm52_exp024",
    "jev_exp022",
    "cb_deepseek_v41_flash_exp024",
    "cbcn_deepseek_v4_flash_exp024",
    "qwen_flash_exp015",
    "verdict_14_exp027",
    "verdict_original_exp027",
)

SKIP_NOTES = {
    "cbcn_deepseek_v4_flash_exp024": (
        "DeepSeek V4 Flash was right 99.8% of the times it answered, and 80.3% of "
        "all 760. It skipped 149 questions."
    ),
    "qwen_flash_exp015": "The provider refused 317 of the 760 requests in this run.",
}


def skipped_data(analysis: dict[str, Any]) -> dict[str, Any]:
    arms = analysis["arms"]
    keys = sorted(SKIP_ARMS, key=lambda k: (-arms[k]["all_record_accuracy"], k))
    rows = []
    for key in keys:
        arm = arms[key]
        right = arm["all_record_accuracy"]
        skipped = 1 - arm["coverage"]
        rows.append(
            {
                "key": key,
                "label": PLAIN[key],
                "right": right,
                "wrong": arm["coverage"] - right,
                "skipped": skipped,
                "answered": arm["coverage"],
                "answered_accuracy": arm["conditional_accuracy"],
            }
        )
    return {
        "title": "Some AI graders look almost perfect until you count the questions they skipped",
        "subtitle": "Each bar is all 760 questions: green is right, red is wrong, grey is skipped",
        "unit": "fraction",
        "floor": {
            "label": "a grader that always gives the same answer",
            "value": arms["majority_exp014"]["all_record_accuracy"],
        },
        "annotations": [
            {"key": key, "text": text}
            for key, text in SKIP_NOTES.items()
            if key in set(keys)
        ],
        "rows": rows,
    }


def draw_skipped(data: dict[str, Any], theme: Theme, layout: Layout) -> plt.Figure:
    rows = data["rows"]
    tall = layout.name == "tall"
    notes = data["annotations"][:1] if tall else data["annotations"]
    note_lines = sum(len(wrap_note(note["text"], layout)) + 1 for note in notes)
    row_h = 0.66 if tall else 0.5
    height = 2.4 + row_h * len(rows) * row_step(layout) + 0.30 * note_lines * row_step(layout) + 0.7
    fig, top, bottom = new_figure(theme, layout, height, data)
    ax = fig.add_axes(axes_rect(layout, top, bottom))
    style_axes(ax, theme, layout)
    values = [row["right"] * 100 for row in rows]
    wrong = [row["wrong"] * 100 for row in rows]
    skipped = [row["skipped"] * 100 for row in rows]
    y = row_positions(len(rows), layout)
    ax.barh(y, values, height=0.62, color=theme.top, edgecolor="none")
    ax.barh(y, wrong, height=0.62, left=values, color=theme.bad, edgecolor="none")
    ax.barh(y, skipped, height=0.62, left=np.add(values, wrong), color=theme.skip, edgecolor="none")
    for index, row in enumerate(rows):
        ax.text(
            values[index] - 2,
            y[index],
            pct(row["right"]),
            va="center",
            ha="right",
            fontsize=layout.base,
            color=theme.bg,
            fontweight="bold",
        )
        if row["skipped"] > 0.10:
            ax.text(
                100 - skipped[index] / 2,
                y[index],
                f"skipped\n{pct(row['skipped'])}",
                va="center",
                ha="center",
                fontsize=layout.base * 0.9,
                color=theme.ink,
                linespacing=1.3,
            )
    row_labels(ax, rows, theme, layout)
    floor_line(ax, theme, layout, data["floor"]["value"] * 100, -1.7, data["floor"]["value"] * 100, len(rows))
    lowest = note_block(
        ax,
        theme,
        layout,
        notes,
        rows,
        [values[next(i for i, r in enumerate(rows) if r["key"] == note["key"])] + 1 for note in notes],
    )
    ax.set_xlim(0, 100)
    ax.set_ylim(lowest + 0.2, -2.9 * row_step(layout))
    ax.set_xticks([0, 25, 50, 75, 100])
    return fig


# --- Figure 2: the top of the field, and who is tied with the leader ------------

RANGE_ARMS = (
    "ali_qwen38_flash_exp024",
    "ali_qwen38_max_exp024",
    "ali_kimi_k27_code_exp024",
    "cbcn_glm53_flash_exp024",
    "cbcn_minimax_m3_exp024",
    "ali_glm52_exp024",
    "jev_exp022",
    "kev_4b_exp027",
    "grok46_exp022",
)


def range_data(analysis: dict[str, Any]) -> dict[str, Any]:
    arms = analysis["arms"]
    ranks = analysis["shared_ranks_all_record"]
    floor = arms["majority_exp014"]["all_record_accuracy"]
    keys = sorted(RANGE_ARMS, key=lambda k: (-arms[k]["all_record_accuracy"], k))
    rows = []
    for key in keys:
        value = arms[key]["all_record_accuracy"]
        tied = ranks[key] == 1
        rows.append(
            {
                "key": key,
                "label": PLAIN[key],
                "value": value,
                "tied_with_leader": tied,
                "below_floor": value < floor,
                "coverage": arms[key]["coverage"],
            }
        )
    return {
        "title": "Four graders are too close to call a winner",
        "subtitle": (
            "Right answers out of all 760 questions. Grey bars are too close to the "
            "leader to separate; red is below the line"
        ),
        "unit": "fraction",
        "floor": {"label": "always the same answer", "value": floor},
        "annotations": [
            {
                "key": "kev_4b_exp027",
                "text": "Kev-4B was the best grader that ran on our own computer.",
            }
        ],
        "rows": rows,
    }


def draw_range(data: dict[str, Any], theme: Theme, layout: Layout) -> plt.Figure:
    rows = data["rows"]
    tall = layout.name == "tall"
    row_h = 0.66 if tall else 0.5
    height = 2.4 + row_h * len(rows) * row_step(layout) + 1.1
    fig, top, bottom = new_figure(theme, layout, height, data)
    ax = fig.add_axes(axes_rect(layout, top, bottom))
    style_axes(ax, theme, layout)
    floor = data["floor"]["value"] * 100
    y = row_positions(len(rows), layout)
    values = [row["value"] * 100 for row in rows]
    colors = [
        theme.tied if row["tied_with_leader"] else theme.bad if row["below_floor"] else theme.top
        for row in rows
    ]
    ax.barh(y, values, height=0.62, color=colors, edgecolor="none")
    for index, (row, value) in enumerate(zip(rows, values)):
        ax.text(
            value - 2,
            y[index],
            f"{value:.1f}%",
            va="center",
            ha="right",
            fontsize=layout.base,
            color=theme.ink if row["tied_with_leader"] else theme.bg,
            fontweight="bold",
        )
    row_labels(ax, rows, theme, layout)
    floor_line(ax, theme, layout, floor, -1.7, floor, len(rows))
    note = data["annotations"][0]
    note_index = next(i for i, row in enumerate(rows) if row["key"] == note["key"])
    lowest = note_block(ax, theme, layout, data["annotations"], rows, [values[note_index] - 2])
    ax.set_xlim(0, 100)
    ax.set_ylim(lowest + 0.2, -2.9 * row_step(layout))
    ax.set_xticks([0, 25, 50, 75, 100])
    return fig


# --- Figure 3: the same model under two setups ---------------------------------

QWEN_RUNS = (
    ("qwen_flash_exp013", "Capped replies, thinking off"),
    ("qwen_flash_exp022", "The provider's own settings"),
)


def settings_data(analysis: dict[str, Any]) -> dict[str, Any]:
    arms = analysis["arms"]
    first = arms["qwen_flash_exp013"]["conditional_accuracy"]
    second = arms["qwen_flash_exp022"]["conditional_accuracy"]
    return {
        "title": f"The same model scored {pct(first)} and {pct(second)} on the same questions",
        "subtitle": "Qwen3.8 Flash, right answers when it answered, in two runs we set up differently",
        "unit": "fraction",
        "annotations": ["Answers took about nine times longer to arrive in the second run."],
        "rows": [
            {
                "key": key,
                "label": label,
                "value": arms[key]["conditional_accuracy"],
                "answered": arms[key]["coverage"],
                "median_latency_s": arms[key]["median_resolved_latency_ms"] / 1000,
            }
            for key, label in QWEN_RUNS
        ],
    }


def draw_settings(data: dict[str, Any], theme: Theme, layout: Layout) -> plt.Figure:
    rows = data["rows"]
    tall = layout.name == "tall"
    height = 6.2 if tall else 5.2
    fig, top, bottom = new_figure(theme, layout, height, data)
    ax = fig.add_axes(axes_rect(layout, top, bottom - 0.02))
    style_axes(ax, theme, layout, grid_axis="x")
    colors = (theme.bad, theme.top)
    y = row_positions(len(rows), layout)
    for index, (row, color) in enumerate(zip(rows, colors)):
        value = row["value"] * 100
        ax.barh(y[index], value, height=0.55, color=color, edgecolor="none")
        ax.text(
            value - 2,
            y[index],
            f"{value:.1f}%",
            va="center",
            ha="right",
            fontsize=layout.base,
            color=theme.bg,
            fontweight="bold",
        )
    if tall:
        ax.set_yticks([])
        for index, row in enumerate(rows):
            ax.text(
                0,
                y[index] - 0.45,
                row["label"],
                fontsize=layout.base,
                color=theme.ink,
                va="bottom",
                ha="left",
            )
    else:
        ax.set_yticks(np.arange(len(rows)), [row["label"] for row in rows])
        ax.tick_params(axis="y", labelcolor=theme.ink, labelsize=layout.base, pad=6)
    note_lines = wrap_note(data["annotations"][0], layout)
    ax.text(
        0,
        y[-1] + 1.0,
        "\n".join(note_lines),
        fontsize=layout.base * 0.95,
        color=theme.muted,
        va="top",
        ha="left",
        linespacing=1.35,
    )
    ax.set_xlim(0, 100)
    ax.set_ylim(y[-1] + 1.0 + len(note_lines) * 0.8 * row_step(layout), -0.9 * row_step(layout))
    ax.set_xticks([0, 25, 50, 75, 100])
    return fig


# --- Appendix: every grader, ranked -------------------------------------------

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
    floor = arms["majority_exp014"]["all_record_accuracy"]
    top_count = sum(1 for key in order if ranks[key] == 1)
    below = sum(1 for key in order if arms[key]["all_record_accuracy"] < floor)
    return {
        "title": f"{top_count} judges share first place; {below} score below a constant guess",
        "subtitle": (
            "Right answers out of all 760 questions. Grey bars are too close to the top "
            "judge to call a winner"
        ),
        "unit": "fraction",
        "floor": {"label": "always the same answer", "value": floor},
        "rows": [
            {
                "key": key,
                "label": PLAIN[key],
                "rank": ranks[key],
                "value": arms[key]["all_record_accuracy"],
                "coverage": arms[key]["coverage"],
                "family": arms[key]["family"],
                "highlight": key in HIGHLIGHT,
                "tied_with_leader": ranks[key] == 1,
                "below_floor": arms[key]["all_record_accuracy"] < floor,
            }
            for key in order
        ],
    }


def draw_ranked(data: dict[str, Any], theme: Theme, layout: Layout) -> plt.Figure:
    rows = data["rows"]
    tall = layout.name == "tall"
    row_h = 0.62 if tall else 0.42
    height = 2.6 + row_h * len(rows) * row_step(layout) + 0.9
    fig, top, bottom = new_figure(theme, layout, height, data)
    ax = fig.add_axes(axes_rect(layout, top, bottom))
    style_axes(ax, theme, layout)
    floor = data["floor"]["value"] * 100
    y = row_positions(len(rows), layout)
    values = [row["value"] * 100 for row in rows]
    colors = [
        theme.tied if row["tied_with_leader"] else theme.bad if row["below_floor"] else theme.top
        for row in rows
    ]
    ax.barh(y, values, height=0.62, color=colors, edgecolor="none")
    for index, (row, value) in enumerate(zip(rows, values)):
        ax.text(
            value - 2,
            y[index],
            f"{value:.1f}%",
            va="center",
            ha="right",
            fontsize=layout.base * 0.95,
            color=theme.ink if row["tied_with_leader"] else theme.bg,
        )
        if row["coverage"] < 0.99 and not tall:
            ax.text(
                103,
                y[index],
                f"{row['coverage'] * 100:.0f}% answered",
                va="center",
                ha="left",
                fontsize=layout.base * 0.85,
                color=theme.bad,
            )
    row_labels(ax, rows, theme, layout)
    floor_line(ax, theme, layout, floor, -1.7, floor, len(rows))
    ax.set_xlim(0, 130)
    ax.set_ylim((len(rows) - 1) * row_step(layout) + 0.6, -2.9 * row_step(layout))
    ax.set_xticks([0, 25, 50, 75, 100])
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
        "source_note": (
            "Source: Eval Lab request-format test on 64 public questions. "
            f"Data: {DATA_LINK}"
        ),
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
        "source_note": (
            "Source: Eval Lab local grader confidence study. "
            f"Data: {DATA_LINK}"
        ),
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
        ("finding_skipped_questions", lambda: skipped_data(analysis), draw_skipped),
        ("finding_accuracy_range", lambda: range_data(analysis), draw_range),
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
            "accuracy": "all-record accuracy = correct / 760 with unresolved earning no credit; "
            "conditional accuracy = correct / resolved",
            "coverage": "resolved fraction of the 760-record blind holdout",
            "floor": "the majority-label reference arm: 50.3% of the 760 questions",
            "tied_with_leader": "shared rank 1: the Holm-corrected all-760 McNemar test gives "
            "p >= 0.05 against the top arm",
            "chart_style": "plain bars, direct labels, no whiskers or confidence intervals",
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
