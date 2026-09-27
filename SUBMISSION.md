# Submission — Real or Clone? (حقيقي أم مستنسخ؟)

GOMYCODE "Come Build with AI" hackathon — Morocco — 27 Sept 2026
Team: Ilyas Daoud (lead, ML), Oualid Karmoun (data, testing, slides), Ayoub El Mouhib (web app, demo video)

- **Prototype URL:** TODO (Brev secure link to the FastAPI app, port 8000)
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

| Test set | Run (a) | Run (b) | Run (c) |
|---|---|---|---|
| MLAAD generators never seen in training (incl. ElevenLabs, OpenAI, Gemini…) — EER | TODO | TODO | TODO |
| In-the-Wild, held-out speakers — EER | TODO | TODO | TODO |
| Our clones of held-out speakers — EER | TODO | TODO | TODO |
| False alarms on real VoxPopuli speakers (never seen) | TODO | TODO | TODO |
| Latency per 10 s of audio (L40S) | TODO | TODO | TODO |

**Failure mode we found and fixed:** run (a) learned a shortcut — "sounds like FLEURS = real, anything else = fake".
Spot check on unseen clips: FLEURS real 0/10 flagged, MLAAD fake 10/10 caught, but **In-the-Wild REAL 8/10 wrongly flagged**
and the team lead's own real phone voice note scored 1.00 (fake). Run (c) adds varied real voices to remove the shortcut.

## Cost and speed
GPU: 1× NVIDIA L40S 48 GB on Brev (Nebius), $2.14/h. Total GPU time: TODO h, cost: TODO $.
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
