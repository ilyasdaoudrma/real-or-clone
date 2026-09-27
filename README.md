# Real or Clone? — حقيقي أم مستنسخ؟

Detects AI voice-clone scams in voice notes. Upload or record a note and get a verdict
(likely real / likely clone), a confidence score, a timeline of suspicious 2-second windows,
and 3 safety tips in Arabic, French or English. The LLM only writes the tips from the verdict
JSON and can never change the verdict. Nothing is stored; audio is deleted after analysis.
The detector is trained and tested on English and French speech; the interface and tips are in AR/FR/EN.

GOMYCODE "Come Build with AI" hackathon, 27 Sept 2026. Team: Ilyas Daoud (lead), Oualid Karmoun, Ayoub El Mouhib.

## Layout
| Folder | What |
|---|---|
| `data/` | download public datasets, build manifests and train/test splits |
| `generate/` | fresh voice clones with Chatterbox Multilingual |
| `augment/` | voice-note simulation (Opus 16 kbps, 8 kHz band, noise, reverb) on real AND fake |
| `train/` | XLS-R 300M fine-tune (real/fake head) |
| `eval/` | EER, false alarms on held-out generators and African-language speech |
| `api/` | FastAPI inference endpoint + NIM tips |
| `web/` | mobile-first web app |

## Run on Brev (Jupyter → File → New → Terminal)
```bash
git clone https://github.com/ilyasdaoudrma/real-or-clone && cd real-or-clone
pip install -r requirements.txt
cp .env.example .env   # then fill it in
nohup python data/download.py > download.log 2>&1 &
tail -f download.log
```

## Models, datasets and APIs (with licences)
| Item | Source | Licence | Role |
|---|---|---|---|
| XLS-R 300M | HF `facebook/wav2vec2-xls-r-300m` | Apache-2.0 | detector backbone (fine-tuned by us) |
| Chatterbox Multilingual v3 | HF `ResembleAI/chatterbox` | MIT | generates fresh clones for training/test |
| Llama 3.3 70B Instruct via NVIDIA NIM | `integrate.api.nvidia.com` | Llama 3.3 Community | writes safety tips from the verdict JSON |
| FLEURS | HF `google/fleurs` | CC-BY-4.0 | real speech (fr_fr, en_us); fairness test (ha_ng, wo_sn, yo_ng, am_et) |
| In-the-Wild | HF `mueller91/In-The-Wild` | CC-BY-SA-4.0 | real + fake, held-out test |
| MLAAD (FR/EN subset) | HF `mueller91/MLAAD` | CC-BY-NC-4.0 | fake speech from many TTS generators |
| NVIDIA Brev | brev.nvidia.com | — | GPU (training, generation, serving) |

Team voices are used as clone references only with written consent.
