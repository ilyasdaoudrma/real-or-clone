---
license: cc-by-nc-4.0
base_model: facebook/wav2vec2-xls-r-300m
pipeline_tag: audio-classification
language: [en, fr]
tags: [audio-deepfake-detection, voice-cloning, anti-spoofing, wav2vec2]
---

# Real or Clone? — voice-clone detector (run C)

XLS-R 300M fine-tuned to tell a real voice from an AI-cloned one in phone voice notes.
This is the model behind the **Real or Clone?** app: https://github.com/ilyasdaoudrma/real-or-clone
(the app downloads it automatically; see "Run it on your computer" in that README).

- Labels: 0 = real, 1 = clone. Input: 16 kHz mono, scored in 4 s windows with a 2 s hop.
- Training: 51,014 clips (FLEURS + VoxPopuli + In-the-Wild real voices; MLAAD + In-the-Wild + 1,619 fresh Chatterbox clones),
  every clip passed through the same WhatsApp-style voice-note simulation (Opus 16 kbps, 8 kHz band, noise, reverb).
- Held-out test (10,122 clips, unseen speakers and generators): 96.1% accuracy, 2.4% EER on unseen generators
  (ElevenLabs, OpenAI, Gemini…), 5.2% EER on fresh clones, 7.2% of real voices wrongly flagged.
- Dataset (composition, splits, rebuild recipe): https://huggingface.co/datasets/IlyasDaoud/real-or-clone-data
- English and French voices only; not validated on Arabic or Darija speech.
- Non-commercial: the MLAAD training data is CC-BY-NC-4.0, so these weights are too.
- An AI can be wrong: always confirm by calling back on a number you already know.
