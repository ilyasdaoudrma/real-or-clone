"""Clone ONE consenting person's voice for the live demo.

    ~/venv-tts/bin/python generate/demo_clone.py --ref sample.ogg --lang fr --takes 4 \
        --text "Maman, j'ai eu un accident, envoie-moi 2000 dirhams vite."
    -> demo_clone_1.wav ... demo_clone_4.wav  (listen, keep the most convincing)

--ref: 10-20 s of that person's voice. Needs written consent. Best: phone voice-recorder app
(not a WhatsApp note), quiet room. Lower --cfg (0.3) usually sticks closer to the reference voice.
"""
import argparse
import subprocess
import tempfile

import torchaudio as ta


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", required=True)
    ap.add_argument("--text", required=True)
    ap.add_argument("--lang", choices=["en", "fr"], default="fr")
    ap.add_argument("--takes", type=int, default=4)
    ap.add_argument("--cfg", type=float, default=0.3, help="cfg_weight; lower = closer to the reference voice")
    ap.add_argument("--exag", type=float, default=0.6, help="exaggeration; higher = more emotional")
    ap.add_argument("--out", default="demo_clone")
    args = ap.parse_args()

    from chatterbox.mtl_tts import ChatterboxMultilingualTTS
    model = ChatterboxMultilingualTTS.from_pretrained(device="cuda")
    with tempfile.NamedTemporaryFile(suffix=".wav") as ref:
        # mono 24 kHz, edge silence removed, max 20 s, loudness-normalised
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-nostdin", "-i", args.ref, "-t", "20",
                        "-af", "silenceremove=start_periods=1:start_threshold=-45dB,loudnorm",
                        "-ac", "1", "-ar", "24000", ref.name], check=True)
        for k in range(1, args.takes + 1):
            wav = model.generate(args.text, language_id=args.lang, audio_prompt_path=ref.name,
                                 cfg_weight=args.cfg, exaggeration=args.exag)
            out = f"{args.out}_{k}.wav"
            ta.save(out, wav.cpu(), model.sr)
            print(f"saved {out} ({wav.shape[-1] / model.sr:.1f} s)", flush=True)


if __name__ == "__main__":
    main()
