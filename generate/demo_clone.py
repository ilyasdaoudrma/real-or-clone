"""Clone ONE consenting person's voice for the live demo.

    ~/venv-tts/bin/python generate/demo_clone.py --ref sample.ogg --lang fr \
        --text "Maman, j'ai eu un accident, envoie-moi 2000 dirhams vite." --out demo_clone.wav

--ref: ~10 s of that person's voice (WhatsApp .ogg/.opus/.m4a all fine). Needs written consent.
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
    ap.add_argument("--out", default="demo_clone.wav")
    args = ap.parse_args()

    from chatterbox.mtl_tts import ChatterboxMultilingualTTS
    model = ChatterboxMultilingualTTS.from_pretrained(device="cuda")
    with tempfile.NamedTemporaryFile(suffix=".wav") as ref:
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", args.ref, "-ac", "1", "-ar", "24000", ref.name],
                       check=True)
        wav = model.generate(args.text, language_id=args.lang, audio_prompt_path=ref.name)
    ta.save(args.out, wav.cpu(), model.sr)
    print(f"saved {args.out}")


if __name__ == "__main__":
    main()
