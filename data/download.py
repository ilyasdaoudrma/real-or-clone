"""Download all public data onto the GPU box.

    python data/download.py                 # everything (Brev)
    python data/download.py --tiny          # a few files per source (smoke test on a laptop)
    python data/download.py --only fleurs   # one source: fleurs | itw | mlaad

Output layout under $DATA_DIR (default ~/roc_data):
    fleurs/<lang>/<split>.tsv + fleurs/<lang>/<split>/*.wav
    itw/release_in_the_wild/*.wav + meta.csv
    mlaad/fake/<lang>/<generator>/*.wav   + mlaad_selected.csv
"""
import argparse
import csv
import os
import random
import tarfile
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from dotenv import load_dotenv
from huggingface_hub import HfApi, hf_hub_download
from tqdm import tqdm

load_dotenv()
DATA_DIR = Path(os.environ.get("DATA_DIR", "~/roc_data")).expanduser()
HF_TOKEN = os.environ.get("HF_TOKEN") or None

FLEURS_TRAIN_LANGS = ["fr_fr", "en_us"]          # real speech for training
MLAAD_LANGS = {"fr": 150, "en": 120}          # files per generator
SEED = 13
VOXPOPULI_PER_LANG = 4000   # varied REAL speech (many speakers/mics) so "not FLEURS" != "fake"


def _extract_tar(path: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    with tarfile.open(path) as tar:
        tar.extractall(dest, filter="data")


def download_fleurs(tiny: bool) -> None:
    jobs = [(lang, split) for lang in FLEURS_TRAIN_LANGS for split in ("train", "dev", "test")]
    if tiny:
        jobs = [("fr_fr", "dev")]
    for lang, split in tqdm(jobs, desc="fleurs"):
        out = DATA_DIR / "fleurs" / lang
        if (out / split).exists():
            continue
        tsv = hf_hub_download("google/fleurs", f"data/{lang}/{split}.tsv", repo_type="dataset")
        tgz = hf_hub_download("google/fleurs", f"data/{lang}/audio/{split}.tar.gz", repo_type="dataset")
        out.mkdir(parents=True, exist_ok=True)
        Path(out / f"{split}.tsv").write_bytes(Path(tsv).read_bytes())
        _extract_tar(Path(tgz), out)  # tar holds a <split>/ folder of wavs


def download_itw(tiny: bool) -> None:
    if tiny:
        print("itw: skipped in --tiny (single 8.2 GB zip)")
        return
    out = DATA_DIR / "itw"
    if (out / "release_in_the_wild").exists():
        return
    z = hf_hub_download("mueller91/In-The-Wild", "release_in_the_wild.zip", repo_type="dataset")
    with zipfile.ZipFile(z) as zf:
        zf.extractall(out)


def _list_generator(api: HfApi, lang: str, gen: str) -> list[str]:
    items = api.list_repo_tree("mueller91/MLAAD", path_in_repo=f"fake/{lang}/{gen}",
                               repo_type="dataset", token=HF_TOKEN)
    return sorted(i.path for i in items if i.path.endswith(".wav"))


def download_mlaad(tiny: bool) -> None:
    if not HF_TOKEN:
        raise SystemExit("mlaad: set HF_TOKEN in .env and accept the terms at "
                         "https://huggingface.co/datasets/mueller91/MLAAD first")
    api = HfApi()
    rng = random.Random(SEED)
    selected: list[tuple[str, str, str]] = []
    for lang, per_gen in MLAAD_LANGS.items():
        gens = [i.path.split("/")[-1] for i in api.list_repo_tree(
            "mueller91/MLAAD", path_in_repo=f"fake/{lang}", repo_type="dataset", token=HF_TOKEN)]
        if tiny:
            gens, per_gen = gens[:2], 3
        with ThreadPoolExecutor(8) as pool:
            listings = list(pool.map(lambda g: (g, _list_generator(api, lang, g)), gens))
        for gen, files in listings:
            pick = rng.sample(files, min(per_gen, len(files)))
            selected += [(lang, gen, f) for f in pick]
        if tiny:
            break
    print(f"mlaad: {len(selected)} files selected")

    def fetch(path: str) -> None:
        hf_hub_download("mueller91/MLAAD", path, repo_type="dataset",
                        local_dir=DATA_DIR / "mlaad", token=HF_TOKEN)

    with ThreadPoolExecutor(32) as pool:
        list(tqdm(pool.map(fetch, [s[2] for s in selected]), total=len(selected), desc="mlaad"))
    with open(DATA_DIR / "mlaad_selected.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["lang", "generator", "path"])
        w.writerows(selected)


def download_voxpopuli(tiny: bool) -> None:
    import io

    import pyarrow.parquet as pq
    import soundfile as sf
    for lang in ("fr", "en"):
        out = DATA_DIR / "voxpopuli" / lang
        meta = out / "meta.csv"
        if meta.exists():
            continue
        pqf = hf_hub_download("facebook/voxpopuli", f"{lang}/test-00000-of-00001.parquet", repo_type="dataset")
        out.mkdir(parents=True, exist_ok=True)
        cap = 5 if tiny else VOXPOPULI_PER_LANG
        rows = []
        for batch in pq.ParquetFile(pqf).iter_batches(batch_size=256, columns=["audio_id", "speaker_id", "audio"]):
            for r in batch.to_pylist():
                x, sr = sf.read(io.BytesIO(r["audio"]["bytes"]), dtype="float32")
                if len(x) < sr * 2:
                    continue
                path = out / f"{r['audio_id']}.wav"
                sf.write(path, x, sr)
                rows.append([str(path), lang, r["speaker_id"]])
                if len(rows) >= cap:
                    break
            if len(rows) >= cap:
                break
        with open(meta, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["path", "lang", "speaker"])
            w.writerows(rows)
        print(f"voxpopuli {lang}: {len(rows)} clips")


SOURCES = {"fleurs": download_fleurs, "itw": download_itw, "mlaad": download_mlaad, "voxpopuli": download_voxpopuli}

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=SOURCES)
    ap.add_argument("--tiny", action="store_true")
    args = ap.parse_args()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for name, fn in SOURCES.items():
        if args.only in (None, name):
            print(f"== {name} -> {DATA_DIR}")
            fn(args.tiny)
    print("done")
