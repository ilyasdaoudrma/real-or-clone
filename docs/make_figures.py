"""Figures + confusion matrices for the report and video.

    python docs/make_figures.py   -> docs/figures/*.png + docs/figures/metrics.md

Numbers are copied verbatim from eval_a.log / eval_b.log / eval_c.log (Brev, 27 Sept 2026, ~15:40),
all three runs scored on the SAME held-out test set at threshold 0.5. Confusion-matrix counts are
rebuilt from those rates x test sizes (rounded to whole clips).
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

OUT = Path(__file__).parent / "figures"
RUNS = {"a": "Run A\npublic data", "b": "Run B\n+ our clones", "c": "Run C\n+ varied real voices"}
COLORS = {"a": "#9a948a", "b": "#d98c3a", "c": "#1f7a4d"}
N = {"fleurs": 1323, "vox": 695, "itw_real": 2102, "itw_fake": 1736, "mlaad": 3956, "clones": 310}
# per run: EER per test set, false-alarm rate per real source, miss rate per fake source
R = {
    "a": {"eer": {"mlaad": .0109, "itw": .3063, "clones": .2178},
          "fa": {"fleurs": .0877, "vox": .9885, "itw_real": .9543},
          "miss": {"mlaad": .0025, "itw_fake": .0127, "clones": .3774}},
    "b": {"eer": {"mlaad": .0146, "itw": .2640, "clones": .0585},
          "fa": {"fleurs": .1738, "vox": .9986, "itw_real": .9581},
          "miss": {"mlaad": .0003, "itw_fake": .0035, "clones": .0194}},
    "c": {"eer": {"mlaad": .0244, "itw": .0341, "clones": .0515},
          "fa": {"fleurs": .0794, "vox": .0691, "itw_real": .0676},
          "miss": {"mlaad": .0144, "itw_fake": .0161, "clones": .0419}},
}


def style(ax, title: str) -> None:
    ax.set_title(title, loc="left", fontsize=13, fontweight="bold")
    ax.spines[["top", "right"]].set_visible(False)
    ax.yaxis.grid(True, alpha=.3)
    ax.set_axisbelow(True)


def grouped_bars(metric: str, groups: dict[str, str], title: str, fname: str) -> None:
    fig, ax = plt.subplots(figsize=(9, 4.8), dpi=150)
    x = np.arange(len(groups))
    w = 0.26
    for i, run in enumerate(RUNS):
        vals = [R[run][metric][g] * 100 + 1e-9 for g in groups]  # round half up like the tables
        bars = ax.bar(x + (i - 1) * w, vals, w, label=RUNS[run].replace("\n", " — "), color=COLORS[run])
        ax.bar_label(bars, fmt="%.1f%%", fontsize=8, padding=2)
    ax.set_xticks(x, list(groups.values()))
    ax.set_ylabel("% (lower is better)")
    style(ax, title)
    ax.legend(frameon=False, fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT / fname)
    plt.close(fig)


def confusion(run: str) -> np.ndarray:
    real = sum(N[s] for s in R[run]["fa"])
    fake = sum(N[s] for s in R[run]["miss"])
    fp = round(sum(N[s] * r for s, r in R[run]["fa"].items()))
    fn = round(sum(N[s] * r for s, r in R[run]["miss"].items()))
    return np.array([[real - fp, fp], [fn, fake - fn]])


def plot_confusions() -> None:
    fig, axes = plt.subplots(1, 3, figsize=(12, 4), dpi=150)
    for ax, run in zip(axes, RUNS):
        cm = confusion(run)
        ax.imshow(cm / cm.sum(1, keepdims=True), cmap="Greens" if run == "c" else "Greys", vmin=0, vmax=1)
        for (i, j), v in np.ndenumerate(cm):
            pct = v / cm[i].sum() * 100
            ax.text(j, i, f"{v:,}\n{pct:.1f}%", ha="center", va="center", fontsize=10,
                    color="white" if pct > 60 else "black")
        ax.set_xticks([0, 1], ["said REAL", "said CLONE"])
        ax.set_yticks([0, 1], ["truly REAL", "truly CLONE"])
        ax.set_title(RUNS[run].replace("\n", " — "), fontsize=11, fontweight="bold")
    fig.suptitle("Confusion matrices — all held-out test clips, threshold 0.5", fontsize=13, fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT / "confusion_matrices.png")
    plt.close(fig)


def metrics_table() -> str:
    lines = ["| Run | Accuracy | Precision (clone) | Recall (clone) | F1 | False alarms on real | TN / FP / FN / TP |",
             "|---|---|---|---|---|---|---|"]
    for run in RUNS:
        (tn, fp), (fn, tp) = confusion(run)
        acc = (tn + tp) / (tn + fp + fn + tp)
        prec, rec = tp / (tp + fp), tp / (tp + fn)
        f1 = 2 * prec * rec / (prec + rec)
        lines.append(f"| {RUNS[run].replace(chr(10), ' — ')} | {acc:.1%} | {prec:.1%} | {rec:.1%} | {f1:.3f} | "
                     f"{fp / (tn + fp):.1%} | {tn:,} / {fp:,} / {fn:,} / {tp:,} |")
    return "\n".join(lines)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    grouped_bars("eer", {"mlaad": "Unseen TTS generators\n(ElevenLabs, OpenAI…)", "clones": "Our clones of\nunseen speakers",
                         "itw": "In-the-Wild\n(unseen speakers)"}, "Equal error rate by test set", "eer_by_run.png")
    grouped_bars("fa", {"fleurs": "FLEURS\n(read speech)", "vox": "VoxPopuli\n(parliament)",
                        "itw_real": "In-the-Wild\n(internet videos)"},
                 "Real voices wrongly flagged as clones", "false_alarms_by_run.png")
    plot_confusions()
    table = metrics_table()
    (OUT / "metrics.md").write_text("# Overall metrics (all held-out test clips, threshold 0.5)\n\n"
                                    f"Real test clips: {sum(N[s] for s in ('fleurs', 'vox', 'itw_real')):,} · "
                                    f"clone test clips: {sum(N[s] for s in ('mlaad', 'itw_fake', 'clones')):,}\n\n"
                                    + table + "\n", encoding="utf-8")
    print(table)


if __name__ == "__main__":
    main()
