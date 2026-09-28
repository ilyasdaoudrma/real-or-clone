# The Real or Clone? dataset

English and French speech, **real vs AI-cloned**, every clip turned into a WhatsApp-style voice note.
It trained and tested the detector published at
[`IlyasDaoud/real-or-clone-xlsr`](https://huggingface.co/IlyasDaoud/real-or-clone-xlsr).

> **Why there is no audio download.** The dataset is made of clips from four public datasets (two of them gated or
> non-commercial) plus our own clones, and it lived on the hackathon GPU box, which has since been deleted.
> What is published here is the exact **recipe**: every choice is seeded, so the scripts below select the same source
> clips, the same speaker and generator splits and the same voice-note effects again. Only our Chatterbox clones come
> out slightly different, because voice generation is random by nature.

## What's inside (run C)

| | Real | Clone | Total |
|---|---:|---:|---:|
| **Train** | 24,670 | 26,344 | **51,014** |
| **Test** (held out) | 4,120 | 6,002 | **10,122** |

Languages: **English and French only**. Labels: `0` = real, `1` = clone.

| Source | Label | What we took | Licence |
|---|---|---|---|
| [FLEURS](https://huggingface.co/datasets/google/fleurs) | real | `en_us` + `fr_fr`, all splits (read speech) | CC-BY-4.0 |
| [VoxPopuli](https://huggingface.co/datasets/facebook/voxpopuli) | real | 4,000 clips per language (parliament speech, many speakers and mics) | CC0 |
| [In-the-Wild](https://huggingface.co/datasets/mueller91/In-The-Wild) | real + clone | English celebrity and politician speech, real and deepfaked | CC-BY-SA-4.0 |
| [MLAAD](https://huggingface.co/datasets/mueller91/MLAAD) | clone | 150 French and 120 English files **per generator** (180+ TTS systems) | CC-BY-NC-4.0, gated |
| **Our clones** ([`generate/clone.py`](generate/clone.py)) | clone | 1,619 Chatterbox Multilingual clones of FLEURS speakers, scam-style texts | same as FLEURS + non-commercial use |

Real voices come from several sources on purpose: with FLEURS alone, run A learned "sounds like FLEURS = real"
(see the README's *Results*).

## Splits: nothing in the test set was seen in training

| Source | How it is split |
|---|---|
| FLEURS | its own train + dev → train, its test → test |
| VoxPopuli | by **speaker**: 20% of speakers test-only |
| In-the-Wild | by **speaker**: 30% of speakers test-only |
| MLAAD | by **generator**: every commercial API (ElevenLabs, OpenAI, Gemini, Cartesia, MiniMax, Hume, Resemble…) plus ~20% of the others are test-only |
| Our clones | by **reference speaker**: 20% test-only |

## The voice-note simulation

Every clip, real **and** fake, goes through the same recipe, so audio quality can't reveal the label
([`augment/voicenote.py`](augment/voicenote.py)):

16 kHz mono → trim edge silence → random 8 s crop → random loudness → one condition, picked from a hash of the file path
(never from the label): **clean**, **Opus 16 kbps**, **phone** (300–3400 Hz band, 8 kHz, Opus 12 kbps),
**noise + Opus** or **reverb + Opus**.

## Layout

```
$DATA_DIR/                     (default ~/roc_data)
  fleurs/<lang>/<split>/*.wav      itw/release_in_the_wild/*.wav + meta.csv
  mlaad/fake/<lang>/<generator>/   voxpopuli/<lang>/*.wav
  clones/*.wav                     manifest.csv      (every source clip: path, label, source, generator, lang, split)
  vn/<hash>.wav                    manifest_vn.csv   (the voice-note versions the model trains and tests on)
```

## Rebuild it

On a Linux box with an NVIDIA GPU (the clones need one; we used an L40S on NVIDIA Brev, a few hours in total)
and about 60 GB of disk. MLAAD is gated: accept its terms on Hugging Face first and put a read token in `.env`.

```bash
git clone https://github.com/ilyasdaoudrma/real-or-clone && cd real-or-clone
sudo apt-get install -y ffmpeg
python3 -m venv ~/venv-main && source ~/venv-main/bin/activate && pip install -r requirements.txt
cp .env.example .env                       # HF_TOKEN=<read token with MLAAD access>

python data/download.py                    # FLEURS, In-the-Wild (8.2 GB zip), MLAAD FR/EN, VoxPopuli
python3 -m venv ~/venv-tts && ~/venv-tts/bin/pip install chatterbox-tts "setuptools<81"
for i in 0 1 2 3 4 5; do ~/venv-tts/bin/python generate/clone.py --n 500 --shard $i --num-shards 6 & done; wait
python data/build_manifest.py              # -> manifest.csv with the splits above
python augment/voicenote.py                # -> vn/*.wav + manifest_vn.csv
```

Smoke test on a laptop, a few files per source: `python data/download.py --tiny`.

The selection is identical as long as the source datasets are unchanged; MLAAD keeps adding generators, so a rebuild
done much later can pick up new ones.

## Use and ethics

Research and non-commercial use only (MLAAD is CC-BY-NC-4.0, In-the-Wild is share-alike). Our clones are synthetic
copies of FLEURS speakers' voices, made only to train a detector; don't use them to impersonate anyone.
