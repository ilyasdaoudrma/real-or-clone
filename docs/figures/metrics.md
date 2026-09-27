# Overall metrics (all held-out test clips, threshold 0.5)

Real test clips: 4,120 · clone test clips: 6,002

| Run | Accuracy | Precision (clone) | Recall (clone) | F1 | False alarms on real | TN / FP / FN / TP |
|---|---|---|---|---|---|---|
| Run A — public data | 70.8% | 67.6% | 97.5% | 0.798 | 68.2% | 1,311 / 2,809 / 149 / 5,853 |
| Run B — + our clones | 70.8% | 67.1% | 99.8% | 0.802 | 71.3% | 1,182 / 2,938 / 13 / 5,989 |
| Run C — + varied real voices | 96.1% | 95.2% | 98.4% | 0.968 | 7.2% | 3,825 / 295 / 98 / 5,904 |
