"""FastAPI: voice note in -> verdict + timeline + 3 tips. Also serves the web app at /.

    CKPT=checkpoints/run_b uvicorn api.main:app --host 0.0.0.0 --port 8000

Contract: api/CONTRACT.md. The LLM (NVIDIA NIM) only WRITES tips from the verdict JSON;
the verdict comes from the detector alone and is never sent back through the LLM.
Nothing is stored: the upload lives in a temp file that is deleted right after scoring.
"""
import json
import os
import tempfile
import time
from collections import defaultdict, deque
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from openai import OpenAI

from augment.voicenote import SR, load
from train.detector import Detector

load_dotenv()
CKPT = os.environ.get("CKPT", "checkpoints/run_b")
MAX_BYTES = 10 * 1024 * 1024
MIN_S, MAX_S = 1.0, 60.0
CLONE_AT, REAL_AT = 0.65, 0.35          # between the two -> "uncertain"
RATE_LIMIT, RATE_WINDOW_S = 20, 60      # requests per IP per window
LANGS = ("ar", "fr", "en")

TEMPLATES = {
    "en": ["Hang up and call the person back on the number you already have saved.",
           "Ask your family code word or a question only the real person can answer.",
           "Never send money because of a voice note alone, however urgent it sounds."],
    "fr": ["Raccrochez et rappelez la personne sur le numéro que vous avez déjà enregistré.",
           "Demandez le mot de passe familial ou une question que seule la vraie personne connaît.",
           "N'envoyez jamais d'argent à cause d'un simple message vocal, même s'il semble urgent."],
    "ar": ["أغلق الخط واتصل بالشخص على الرقم المحفوظ لديك مسبقًا.",
           "اسأل عن كلمة السر العائلية أو سؤالًا لا يعرف جوابه إلا الشخص الحقيقي.",
           "لا ترسل المال أبدًا بسبب رسالة صوتية وحدها، مهما بدت عاجلة."],
}
LANG_NAME = {"en": "English", "fr": "French", "ar": "Modern Standard Arabic"}

app = FastAPI(title="Real or Clone?")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET", "POST"], allow_headers=["*"])
detector = Detector(CKPT)
nim = OpenAI(base_url=os.environ.get("NIM_BASE_URL", "https://integrate.api.nvidia.com/v1"),
             api_key=os.environ["NVIDIA_API_KEY"], timeout=8.0) if os.environ.get("NVIDIA_API_KEY") else None
hits: dict[str, deque] = defaultdict(deque)


def verdict_of(p_fake: float) -> str:
    if p_fake >= CLONE_AT:
        return "likely_clone"
    if p_fake <= REAL_AT:
        return "likely_real"
    return "uncertain"


def write_tips(verdict: dict, lang: str) -> tuple[list[str], str]:
    """3 tips from the LLM, or fixed templates if NIM is missing, slow or malformed."""
    if nim is None:
        return TEMPLATES[lang], "template"
    prompt = (f"A voice-clone detector analysed a voice note. Its result (final, do not question it):\n"
              f"{json.dumps(verdict)}\n"
              f"Write exactly 3 short, concrete safety tips in {LANG_NAME[lang]} for the person who received "
              f"this voice note, suited to this verdict (e.g. call back on a known number, family code word, "
              f"never send money on a voice note alone). Do not state a different verdict or probability. "
              f'Answer ONLY with JSON: {{"tips": ["...", "...", "..."]}}')
    try:
        res = nim.chat.completions.create(
            model=os.environ.get("NIM_MODEL", "meta/llama-3.3-70b-instruct"),
            messages=[{"role": "user", "content": prompt}], temperature=0.3, max_tokens=300)
        text = res.choices[0].message.content
        tips = json.loads(text[text.index("{"):text.rindex("}") + 1])["tips"]
        if isinstance(tips, list) and len(tips) == 3 and all(isinstance(t, str) and t.strip() for t in tips):
            return [t.strip() for t in tips], "nim"
    except Exception as e:  # network, timeout, bad JSON -> fallback, never fail the request
        print(f"nim fallback: {type(e).__name__}: {e}", flush=True)
    return TEMPLATES[lang], "template"


def rate_limited(ip: str) -> bool:
    now, q = time.time(), hits[ip]
    while q and now - q[0] > RATE_WINDOW_S:
        q.popleft()
    q.append(now)
    return len(q) > RATE_LIMIT


@app.get("/health")
def health() -> dict:
    return {"ok": True, "model": Path(CKPT).name, "device": detector.device, "tips": "nim" if nim else "template"}


@app.post("/analyze")
async def analyze(request: Request, file: UploadFile = File(...), lang: str = Form("en")):
    if rate_limited(request.client.host if request.client else "?"):
        raise HTTPException(429, "too_many_requests")
    lang = lang if lang in LANGS else "en"
    data = await file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        return JSONResponse({"error": "too_long"}, status_code=400)
    t0 = time.perf_counter()
    fd, tmp_path = tempfile.mkstemp(suffix=Path(file.filename or "a").suffix[:8])
    try:
        with os.fdopen(fd, "wb") as tmp:
            tmp.write(data)
        x = load(tmp_path)
    except Exception:
        return JSONResponse({"error": "bad_audio"}, status_code=400)
    finally:
        os.remove(tmp_path)  # nothing is kept
    del data
    dur = len(x) / SR
    if dur < MIN_S:
        return JSONResponse({"error": "too_short"}, status_code=400)
    if dur > MAX_S:
        return JSONResponse({"error": "too_long"}, status_code=400)
    res = detector.score_array(x)
    p = res["p_fake"]
    core = {"verdict": verdict_of(p), "p_fake": round(p, 4), "confidence": round(abs(p - 0.5) * 2, 4),
            "duration": res["duration"], "windows": res["windows"]}
    tips, source = write_tips({k: core[k] for k in ("verdict", "p_fake", "confidence")}, lang)
    return {**core, "tips": tips, "tips_source": source,
            "latency_ms": round((time.perf_counter() - t0) * 1000), "model": Path(CKPT).name}


web_dir = Path(__file__).resolve().parent.parent / "web"
if (web_dir / "index.html").exists():
    app.mount("/", StaticFiles(directory=web_dir, html=True), name="web")
