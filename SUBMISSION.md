# Submission — Real or Clone? (حقيقي أم مستنسخ؟)

GOMYCODE "Come Build with AI" hackathon — Morocco — 27 Sept 2026
Team: Ilyas Daoud (lead, ML), Oualid Karmoun (data, testing, slides), Ayoub El Mouhib (web app, demo video)

- **Prototype URL:** https://real-or-clone-9m7lxdq0i.gobrev.dev (live on the Brev L40S, model run c)
- **90-second demo video:** TODO
- **Source code:** https://github.com/ilyasdaoudrma/real-or-clone
- **Presentation:** TODO

## Problem and user
3 seconds of audio are enough to clone a voice. Scammers send fake voice notes ("Mom, I had an accident, send money now").
McAfee survey (7,054 adults, 7 countries): 1 in 4 had faced an AI voice scam or knew a victim; 77% of victims lost money;
70% were not confident they could tell a clone from a real voice.
Users: families (especially older parents), mobile-money agents, bank/fintech call centres, fact-checkers.
The user uploads or records a voice note and gets: a verdict (likely real / likely clone / uncertain), a confidence score,
a timeline of suspicious seconds (4-s windows, 2-s hop), and 3 safety tips in Arabic, French or English.

## What we built
1. **Data** (English + French speech only): FLEURS (real), VoxPopuli FR/EN (real, many speakers/mics), MLAAD FR/EN subset
   (fake, 182 TTS generators), In-the-Wild (real + fake, split by speaker).
2. **Fresh clones:** 1,619 clips made on the GPU with Chatterbox Multilingual, each cloning a real FLEURS speaker
   (half say scam-style money requests). Train/test split by cloned speaker.
3. **Voice-note simulation** applied identically to real and fake: Opus 16 kbps, 8 kHz phone band, noise, reverb,
   edge-silence trim, random loudness. Stops "clean = fake" shortcuts.
4. **Detector:** XLS-R 300M fine-tuned with a real/fake head, bf16, balanced 50/50 sampling.
5. **App:** FastAPI + mobile web page (record/upload, verdict card, timeline, tips, AR/FR/EN with RTL).
   The LLM only writes tips from the verdict JSON; it never sees the audio and cannot change the verdict.

## Results (real numbers; EER = equal error rate, lower is better; threshold 0.5)
Three runs, all evaluated on the SAME held-out test set:
- (a) FLEURS real + MLAAD fake
- (b) (a) + our 1,619 Chatterbox clones
- (c) (b) + varied real speech (VoxPopuli) + In-the-Wild training speakers

| Test set (never seen in training) | Run (a) | Run (b) | Run (c) |
|---|---|---|---|
| MLAAD generators never seen (incl. ElevenLabs, OpenAI, Gemini, Cartesia…) — EER | **1.1%** | 1.5% | 2.4% |
| Our Chatterbox clones of held-out speakers — EER | 21.8% | 5.9% | **5.2%** |
| Our clones missed at threshold 0.5 | 37.7% | **1.9%** | 4.2% |
| In-the-Wild, held-out speakers — EER | 30.6% | 26.4% | **3.4%** |
| In-the-Wild REAL voices wrongly flagged | 95.4% | 95.8% | **6.8%** |
| VoxPopuli REAL speakers wrongly flagged | 98.9% | 99.9% | **6.9%** |
| FLEURS REAL speakers wrongly flagged | 8.8% | 17.4% | **7.9%** |
| Latency per 10 s of audio (L40S) | 35 ms | 46 ms | **30 ms** |

Test sizes: 1,323 FLEURS real, 695 VoxPopuli real, 3,956 MLAAD fake (held-out generators), 2,102 real + 1,736 fake
In-the-Wild (held-out speakers), 310 of our clones. Full JSON (incl. per-generator detection) in `results/`.

**Main results**
- Adding our fresh Chatterbox clones (a → b) cut the error on voice clones **4×** (EER 21.8% → 5.9%; misses 37.7% → 1.9%).
- Adding varied real voices (b → c) removed the shortcut: real voices wrongly flagged fell from ~96–99% to **~7%**,
  In-the-Wild EER 26.4% → **3.4%**, at a small cost on MLAAD (1.5% → 2.4%).
- **Caveat:** run (c) trains on other In-the-Wild speakers, so that test is speaker-disjoint but no longer a new domain.
- Demo check with run (c): team lead's real phone voice note → likely real (p_fake 0.17); his 5 Chatterbox clones → likely clone (1.00).


**Overall, all held-out test clips pooled (threshold 0.5)** — figures in `docs/figures/`
(`eer_by_run.png`, `false_alarms_by_run.png`, `confusion_matrices.png`; script `docs/make_figures.py`):

Real test clips: 4,120 · clone test clips: 6,002

| Run | Accuracy | Precision (clone) | Recall (clone) | F1 | False alarms on real | TN / FP / FN / TP |
|---|---|---|---|---|---|---|
| Run A — public data | 70.8% | 67.6% | 97.5% | 0.798 | 68.2% | 1,311 / 2,809 / 149 / 5,853 |
| Run B — + our clones | 70.8% | 67.1% | 99.8% | 0.802 | 71.3% | 1,182 / 2,938 / 13 / 5,989 |
| Run C — + varied real voices | 96.1% | 95.2% | 98.4% | 0.968 | 7.2% | 3,825 / 295 / 98 / 5,904 |

The live app lets the user pick run A, B or C, to compare the baseline and our improved models on the same voice note.

**Failure mode we found and fixed:** run (a) learned a shortcut — "sounds like FLEURS = real, anything else = fake".
Spot check on unseen clips: FLEURS real 0/10 flagged, MLAAD fake 10/10 caught, but **In-the-Wild REAL 8/10 wrongly flagged**
and the team lead's own real phone voice note scored 1.00 (fake). Run (c) adds varied real voices and removes the shortcut (same note: 0.17 = real).

## Cost and speed
GPU: 1× NVIDIA L40S 48 GB on Brev (Nebius), $2.14/h. Instance up since 12:01; ~3.7 h ≈ $8 at 15:40 (final figure at submission). Training: run (a) ~7 min, run (c) ~10 min.
Clone generation ~39 clips/min (6 processes on one GPU). Training run (a): 2,169 steps in ~7 min.

## Models, agents, datasets, APIs, generated assets
| Item | Source | Licence | Use |
|---|---|---|---|
| XLS-R 300M | HF `facebook/wav2vec2-xls-r-300m` | Apache-2.0 | detector backbone, fine-tuned by us |
| Chatterbox Multilingual | HF `ResembleAI/chatterbox` | MIT | fresh clones for training/test + demo clone |
| gpt-oss-120b via Groq API | `api.groq.com` | Apache-2.0 | writes the 3 safety tips from the verdict JSON |
| FLEURS | HF `google/fleurs` (fr_fr, en_us) | CC-BY-4.0 | real speech |
| VoxPopuli | HF `facebook/voxpopuli` (fr, en test) | CC0 | varied real speech |
| MLAAD | HF `mueller91/MLAAD` (fr, en) | CC-BY-NC-4.0 | fake speech |
| In-the-Wild | HF `mueller91/In-The-Wild` | CC-BY-SA-4.0 | real + fake, speaker-split |
| NVIDIA Brev | brev.nvidia.com | — | GPU for generation, training, evaluation, serving |
| Claude Code (Anthropic) | — | — | coding assistant (see disclosure) |

**Generated assets:** 1,619 Chatterbox clones (EN/FR); 1 demo clone of the team lead's voice (with his consent);
the trained detector checkpoints (runs a, b, c).

## AI disclosure
- **Stack:** XLS-R 300M fine-tuned by us (the verdict), Chatterbox (clone generation), gpt-oss-120b on Groq (tips text only).
- **Access limits:** Groq free tier (rate-limited); Brev credit $100. MLAAD is non-commercial, so this prototype is non-commercial.
- **What AI did:** Claude Code wrote most of the pipeline code (download, augmentation, training, evaluation, API, web app);
  the team chose the approach, ran every step on the GPU, listened to the clones, checked the results and caught the
  shortcut. The detector decides the verdict; the LLM only writes tips and cannot change it.
- **Fallback:** if Groq is down or slow (>8 s), fixed expert-written tips in AR/FR/EN are shown. The model also runs on CPU.
- **Limits (honest):** trained and tested on English and French only — not validated on Arabic or Darija voice notes.
  An AI can be wrong: the app always tells the user to call back on a known number.
- **Privacy:** no database; audio is deleted right after analysis; demo voices used with written consent.
