from __future__ import annotations

from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

PALETTE = ["#1f4e79", "#9b2226", "#52796f", "#bb8c5b", "#5e548e", "#7a7a7a"]

plt.rcParams.update({
    "figure.facecolor": "#fafafa",
    "axes.facecolor": "#fafafa",
    "axes.edgecolor": "#333",
    "axes.linewidth": 0.6,
    "grid.color": "#cccccc",
    "grid.linewidth": 0.4,
    "grid.linestyle": "-",
    "axes.grid": True,
    "axes.axisbelow": True,
    "font.family": "serif",
    "font.serif": ["DejaVu Serif", "Times New Roman", "Microsoft YaHei", "SimSun", "Noto Serif CJK SC", "Noto Sans CJK SC"],
    "font.size": 10,
    "axes.titlesize": 12,
    "axes.titleweight": "normal",
    "axes.labelsize": 10,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "xtick.color": "#333",
    "ytick.color": "#333",
    "figure.dpi": 140,
    "savefig.dpi": 140,
    "axes.spines.top": False,
    "axes.spines.right": False,
})


def scatter_oi_vs_price(metrics: list[dict], out_path: str | Path) -> str:
    out_path = str(out_path)
    fig, ax = plt.subplots(figsize=(8, 6))
    xs = [m["oi_z_avg"] for m in metrics]
    ys = [m["price_z"] for m in metrics]
    ax.scatter(xs, ys, s=22, alpha=0.75, color=PALETTE[0], edgecolors="none")
    ax.axhline(0, color="#888888", linestyle="--", linewidth=0.5)
    ax.axvline(0, color="#888888", linestyle="--", linewidth=0.5)

    top = sorted(metrics, key=lambda m: abs(m["composite"]), reverse=True)[:8]
    for m in top:
        ax.annotate(
            m["symbol"].replace("USDT", ""),
            (m["oi_z_avg"], m["price_z"]),
            fontsize=7,
            xytext=(4, 4),
            textcoords="offset points",
        )

    ax.set_xlabel("OI z-score (avg 30m/1h/4h)")
    ax.set_ylabel("Price Z-Score")
    ax.set_title("OI vs Price Z-Score (cross-section)")
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)
    return out_path


def bar_top_composite(metrics: list[dict], n: int, out_path: str | Path) -> str:
    out_path = str(out_path)
    top = sorted(metrics, key=lambda m: m["composite"], reverse=True)[:n]
    top = list(reversed(top))

    labels = [m["symbol"].replace("USDT", "") for m in top]
    values = [m["composite"] for m in top]
    colors = [PALETTE[0] if v >= 0 else PALETTE[1] for v in values]

    fig, ax = plt.subplots(figsize=(8, max(4, 0.35 * len(top) + 1)))
    bars = ax.barh(labels, values, color=colors, edgecolor="none")
    for bar, v in zip(bars, values):
        x = bar.get_width()
        ax.text(
            x + (0.02 if x >= 0 else -0.02),
            bar.get_y() + bar.get_height() / 2,
            f"{v:+.2f}",
            va="center",
            ha="left" if x >= 0 else "right",
            fontsize=8,
        )
    ax.axvline(0, color="#888888", linewidth=0.5)
    ax.set_xlabel("Composite Z-Score")
    ax.set_title(f"Top {n} Composite Z-Score")
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)
    return out_path


def bar_top_oi_30m(metrics: list[dict], n: int, out_path: str | Path) -> str:
    out_path = str(out_path)
    eligible = [m for m in metrics if m.get("oi_z_30m") is not None]
    top = sorted(eligible, key=lambda m: m["oi_z_30m"], reverse=True)[:n]
    top = list(reversed(top))

    labels = [m["symbol"].replace("USDT", "") for m in top]
    values = [m["oi_z_30m"] for m in top]
    colors = [PALETTE[0] if v >= 0 else PALETTE[1] for v in values]

    fig, ax = plt.subplots(figsize=(8, max(4, 0.35 * len(top) + 1)))
    bars = ax.barh(labels, values, color=colors, edgecolor="none")
    for bar, v in zip(bars, values):
        x = bar.get_width()
        ax.text(
            x + (0.02 if x >= 0 else -0.02),
            bar.get_y() + bar.get_height() / 2,
            f"{v:+.2f}",
            va="center",
            ha="left" if x >= 0 else "right",
            fontsize=8,
        )
    ax.axvline(0, color="#888888", linewidth=0.5)
    ax.set_xlabel("30m OI Z-Score")
    ax.set_title(f"Top {n} by 30m OI z (early movers)")
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)
    return out_path
