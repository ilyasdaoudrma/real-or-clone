"""Generate fresh voice clones with Chatterbox Multilingual (EN + FR).

Runs in its own venv because chatterbox-tts pins its own torch version:
    python3 -m venv ~/venv-tts && ~/venv-tts/bin/pip install chatterbox-tts python-dotenv

Smoke test (2 clips):   ~/venv-tts/bin/python generate/clone.py --n 2
Parallel on one GPU (4 processes, 1250 clips each):
    for i in 0 1 2 3; do nohup ~/venv-tts/bin/python generate/clone.py --n 1250 --shard $i --num-shards 4 > gen$i.log 2>&1 & done

Each clip copies the voice of a real FLEURS speaker (reference clip). References from the
FLEURS *train* split -> split=train, from *test* -> split=test, so train and test never
share a cloned speaker. Output: $DATA_DIR/clones/<lang>/*.wav + clones_shard<i>.csv
"""
import argparse
import csv
import os
import random
import time
from pathlib import Path

import torchaudio as ta
from dotenv import load_dotenv

load_dotenv()
DATA_DIR = Path(os.environ.get("DATA_DIR", "~/roc_data")).expanduser()
LANGS = {"en": "en_us", "fr": "fr_fr"}
TEST_FRACTION = 0.2
REF_MIN_S, REF_MAX_S = 5.0, 15.0
FLEURS_SR = 16000

NAMES = {"en": ["Mom", "Dad", "Sarah", "Adam", "Grandma", "Yasmine", "Karim"],
         "fr": ["Maman", "Papa", "Sarah", "Adam", "Mamie", "Yasmine", "Karim"]}
AMOUNTS = {"en": ["500", "800", "1,200", "2,000", "300"],
           "fr": ["500", "800", "1 200", "2 000", "300"]}
SCAM = {
    "en": [
        "{name}, it's me. I had an accident and I need {amt} dollars right now, please send it.",
        "{name}, please don't tell anyone, I'm in trouble. Can you transfer {amt} euros today?",
        "Hi {name}, I lost my phone, this is my new number. I need {amt} for the hospital.",
        "{name}, I'm at the police station, they need {amt} for bail. Please hurry.",
        "It's me, {name}. My card is blocked, can you send {amt} to this account quickly?",
        "{name}, I can't talk long. Send {amt} by mobile money, I'll explain later.",
        "Hey {name}, the landlord wants {amt} today or he kicks me out. Can you help me?",
        "{name}, I'm stuck at the airport and I need {amt} for a new ticket, please.",
    ],
    "fr": [
        "{name}, c'est moi. J'ai eu un accident, j'ai besoin de {amt} euros tout de suite.",
        "{name}, ne dis rien à personne, j'ai un problème. Tu peux m'envoyer {amt} aujourd'hui ?",
        "Allô {name}, j'ai perdu mon téléphone, c'est mon nouveau numéro. Il me faut {amt} pour l'hôpital.",
        "{name}, je suis au commissariat, ils demandent {amt} pour la caution. Fais vite s'il te plaît.",
        "C'est moi, {name}. Ma carte est bloquée, tu peux virer {amt} sur ce compte rapidement ?",
        "{name}, je ne peux pas parler longtemps. Envoie {amt} par transfert, je t'explique après.",
        "Salut {name}, le propriétaire veut {amt} aujourd'hui sinon il me met dehors. Tu peux m'aider ?",
        "{name}, je suis bloqué à l'aéroport, il me faut {amt} pour un nouveau billet.",
    ],
}


def load_fleurs(lang_code: str, split: str) -> list[dict]:
    """Rows of a FLEURS tsv: id, file_name, raw_transcription, transcription, ..., num_samples, gender."""
    root = DATA_DIR / "fleurs" / lang_code
    rows = []
    with open(root / f"{split}.tsv", encoding="utf-8") as f:
        for r in csv.reader(f, delimiter="\t", quoting=csv.QUOTE_NONE):
            path = root / split / r[1]
            dur = int(r[-2]) / FLEURS_SR
            if path.exists() and REF_MIN_S <= dur <= REF_MAX_S:
                rows.append({"path": str(path), "text": r[2], "dur": dur})
    return rows


def build_jobs(n: int, rng: random.Random) -> list[dict]:
    jobs = []
    for i in range(n):
        lang = "en" if i % 2 == 0 else "fr"
        split = "test" if rng.random() < TEST_FRACTION else "train"
        jobs.append({"idx": i, "lang": lang, "split": split})
    return jobs


def pick_text(lang: str, texts: list[str], rng: random.Random) -> str:
    if rng.random() < 0.5:
        return rng.choice(SCAM[lang]).format(name=rng.choice(NAMES[lang]), amt=rng.choice(AMOUNTS[lang]))
    return rng.choice(texts)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=2, help="clips for THIS shard")
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--num-shards", type=int, default=1)
    args = ap.parse_args()

    from chatterbox.mtl_tts import ChatterboxMultilingualTTS  # heavy import after arg parsing
    model = ChatterboxMultilingualTTS.from_pretrained(device="cuda")

    rng = random.Random(1000 + args.shard)
    refs = {(lang, split): load_fleurs(code, split) for lang, code in LANGS.items() for split in ("train", "test")}
    texts = {lang: [r["text"] for r in refs[(lang, "train")]] for lang in LANGS}
    out_dir = DATA_DIR / "clones"
    manifest = DATA_DIR / f"clones_shard{args.shard}.csv"
    is_new = not manifest.exists()

    with open(manifest, "a", newline="", encoding="utf-8") as mf:
        w = csv.writer(mf)
        if is_new:
            w.writerow(["path", "lang", "split", "ref_path", "text", "seconds_to_generate"])
        for job in build_jobs(args.n, rng):
            out = out_dir / job["lang"] / f"s{args.shard}_{job['idx']:05d}.wav"
            if out.exists():
                continue
            out.parent.mkdir(parents=True, exist_ok=True)
            ref = rng.choice(refs[(job["lang"], job["split"])])
            text = pick_text(job["lang"], texts[job["lang"]], rng)
            t0 = time.time()
            try:
                wav = model.generate(text, language_id=job["lang"], audio_prompt_path=ref["path"])
            except Exception as e:  # one bad reference must not kill a 1-hour run
                print(f"skip {out.name}: {e}", flush=True)
                continue
            ta.save(str(out), wav.cpu(), model.sr)
            took = time.time() - t0
            w.writerow([str(out), job["lang"], job["split"], ref["path"], text, f"{took:.2f}"])
            mf.flush()
            print(f"{out.name} {job['lang']} {job['split']} {took:.1f}s", flush=True)


if __name__ == "__main__":
    main()
