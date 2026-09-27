"""FastAPI: voice note in -> verdict + timeline + 3 tips. Also serves the web app at /.

    CKPT=checkpoints/run_b uvicorn api.main:app --host 0.0.0.0 --port 8000

Contract: api/CONTRACT.md. The LLM (Groq, gpt-oss-120b) only WRITES tips from the verdict JSON;
the verdict comes from the detector alone and is never sent back through the LLM.
Login (Clerk) is required to analyse. Each check saves the audio + result to that user's private,
deletable history (SQLite + files, see api/store.py).
"""
import asyncio
import json
import os
import tempfile
import time
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool
from openai import OpenAI
import torch

from augment.voicenote import SR, load
from api import auth, limits, store
from train.detector import Detector

load_dotenv()
CKPT = os.environ.get("CKPT", "checkpoints/run_c")          # our fine-tuned model
BASE_MODEL = "facebook/wav2vec2-xls-r-300m"
# The app compares the model BEFORE fine-tuning (XLS-R 300M, untrained real/fake head, fixed seed so it is
# reproducible) with our fine-tuned model AFTER, on the same voice note.
MODEL_LABELS = {"base": "XLS-R 300M · before fine-tuning", "ours": "Fine-tuned · ours"}
MAX_BYTES = 10 * 1024 * 1024
MAX_BODY = MAX_BYTES + 256 * 1024       # multipart overhead
MIN_S, MAX_S = 1.0, 60.0
CLONE_AT, REAL_AT = 0.65, 0.35          # between the two -> "uncertain"
HEAVY_SLOTS = 2                         # analyses running at once; the rest queue
QUEUE_WAIT_S = 30
_heavy = asyncio.Semaphore(HEAVY_SLOTS)
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
torch.manual_seed(0)
detectors = {"base": Detector(BASE_MODEL), "ours": Detector(CKPT)}
DEFAULT = "ours"
LLM_MODEL = os.environ.get("LLM_MODEL", "openai/gpt-oss-120b")
llm = OpenAI(base_url=os.environ.get("LLM_BASE_URL", "https://api.groq.com/openai/v1"),
             api_key=os.environ["LLM_API_KEY"], timeout=8.0) if os.environ.get("LLM_API_KEY") else None


def verdict_of(p_fake: float) -> str:
    if p_fake >= CLONE_AT:
        return "likely_clone"
    if p_fake <= REAL_AT:
        return "likely_real"
    return "uncertain"


GUIDANCE = {
    "likely_clone": "The voice is most likely AI-cloned. Give urgent, concrete protective actions "
                    "(do not pay or reply, hang up, contact the real person another way, warn family, report it).",
    "likely_real": "The voice is most likely real, but detectors can be wrong and real people can be coerced. "
                   "Reassure calmly while still suggesting one light verification before sending any money.",
    "uncertain": "The detector cannot decide. Explain simply how the listener can verify the caller themselves "
                 "(personal questions, call-back, a trusted third person) before acting.",
}


def write_tips(verdict: dict, lang: str) -> tuple[list[str], str]:
    """3 tips from the LLM, or fixed templates if the LLM is missing, slow or malformed."""
    if llm is None:
        return TEMPLATES[lang], "template"
    prompt = (f"A voice-clone detector analysed a voice note. Its result is final; never contradict it or "
              f"state another verdict or probability:\n{json.dumps(verdict)}\n"
              f"Situation: {GUIDANCE[verdict['verdict']]}\n"
              f"Write exactly 3 short, concrete, varied tips (max 25 words each) in {LANG_NAME[lang]} for the person "
              f"who received this voice note, written for a non-technical family member. If useful, mention the "
              f"most suspicious seconds. Answer ONLY with JSON: {{\"tips\": [\"...\", \"...\", \"...\"]}}")
    extra = {"reasoning_effort": "low"} if "gpt-oss" in LLM_MODEL else {}
    for attempt in range(2):  # one retry: an occasional malformed JSON answer should not cost the user
        try:
            res = llm.chat.completions.create(model=LLM_MODEL, messages=[{"role": "user", "content": prompt}],
                                              temperature=0.8, max_tokens=800, extra_body=extra)
            text = res.choices[0].message.content or ""
            tips = json.loads(text[text.index("{"):text.rindex("}") + 1])["tips"]
            if isinstance(tips, list) and len(tips) == 3 and all(isinstance(t, str) and t.strip() for t in tips):
                return [t.strip() for t in tips], "llm"
            print(f"llm attempt {attempt + 1}: bad shape", flush=True)
        except Exception as e:  # network, timeout, bad JSON -> retry once, then fixed tips
            print(f"llm attempt {attempt + 1} failed: {type(e).__name__}: {e}", flush=True)
    return TEMPLATES[lang], "template"


class GuardAnalyze:
    """Checks login and size BEFORE the multipart body is parsed (Starlette spools uploads to disk
    with no size limit), so anonymous or oversized requests never reach the disk."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["path"] != "/analyze" or scope["method"] != "POST":
            await self.app(scope, receive, send)
            return
        request = Request(scope)
        try:
            uid = auth.user_id(request)
        except HTTPException:
            uid = None
        if auth.PUBLISHABLE_KEY and uid is None:
            await JSONResponse({"detail": "login_required"}, status_code=401)(scope, receive, send)
            return
        length = request.headers.get("content-length")
        if length is not None and (not length.isdigit() or int(length) > MAX_BODY):
            await JSONResponse({"error": "too_long"}, status_code=413)(scope, receive, send)
            return
        received = 0

        async def limited_receive():
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > MAX_BODY:  # chunked bodies without Content-Length
                    raise HTTPException(413, "too_long")
            return message

        await self.app(scope, limited_receive, send)


FAPI = auth.frontend_api()
CSP = "; ".join([
    "default-src 'self'",
    f"script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://{FAPI} https://challenges.cloudflare.com",
    f"connect-src 'self' https://{FAPI} https://clerk-telemetry.com https://cdn.jsdelivr.net",
    "img-src 'self' data: blob: https://img.clerk.com",
    "media-src 'self' blob:",
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
    "font-src 'self' https://fonts.gstatic.com",
    "frame-src https://challenges.cloudflare.com",
    "worker-src 'self' blob:",
    "frame-ancestors 'none'", "base-uri 'self'", "form-action 'self'", "object-src 'none'",
]).encode()


class SecurityHeaders:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                message.setdefault("headers", [])
                message["headers"] += [(b"x-content-type-options", b"nosniff"), (b"x-frame-options", b"DENY"),
                                       (b"referrer-policy", b"strict-origin-when-cross-origin"),
                                       (b"permissions-policy", b"camera=(), geolocation=(), microphone=(self)"),
                                       (b"content-security-policy", CSP)]
            await send(message)
        await self.app(scope, receive, send_with_headers if scope["type"] == "http" else send)


app.add_middleware(GuardAnalyze)
app.add_middleware(GZipMiddleware, minimum_size=1024)
app.add_middleware(SecurityHeaders)


store.init()


@app.get("/config")
def config() -> dict:
    return {"clerk_publishable_key": auth.PUBLISHABLE_KEY, "clerk_frontend_api": auth.frontend_api()}


def reader(request: Request) -> str:
    uid = auth.require_user(request)
    limits.hit("read_user_min", uid)
    return uid


@app.get("/history")
def history(request: Request, limit: int = 50) -> dict:
    return {"items": store.list_checks(reader(request), limit)}


@app.get("/history/{check_id}/audio")
def history_audio(check_id: str, request: Request):
    path = store.audio_path(reader(request), check_id)
    if path is None or not path.exists():
        raise HTTPException(404, "not_found")
    return FileResponse(path)


@app.delete("/history/{check_id}")
def history_delete(check_id: str, request: Request) -> dict:
    if not store.delete(reader(request), check_id):
        raise HTTPException(404, "not_found")
    return {"deleted": check_id}


@app.get("/stats")
def user_stats(request: Request) -> dict:
    return store.stats(reader(request))


@app.get("/health")
def health() -> dict:
    return {"ok": True, "model": DEFAULT, "checkpoint": Path(CKPT).name, "models": MODEL_LABELS,
            "device": detectors[DEFAULT].device, "tips": LLM_MODEL if llm else "template"}


def run_analysis(data: bytes, model: str, lang: str) -> dict:
    """Blocking work (ffmpeg, model, LLM): runs in a worker thread so the event loop stays free."""
    t0 = time.perf_counter()
    fd, tmp_path = tempfile.mkstemp(suffix=".upload")   # never the uploader's extension (it steers ffmpeg probing)
    try:
        with os.fdopen(fd, "wb") as tmp:
            tmp.write(data)
        x = load(tmp_path)
    except Exception:
        return {"error": "bad_audio"}
    finally:
        os.remove(tmp_path)
    dur = len(x) / SR
    if dur < MIN_S:
        return {"error": "too_short"}
    if dur > MAX_S:
        return {"error": "too_long"}
    res = detectors[model].score_array(x)
    p = res["p_fake"]
    core = {"verdict": verdict_of(p), "p_fake": round(p, 4), "confidence": round(abs(p - 0.5) * 2, 4),
            "duration": res["duration"], "windows": res["windows"]}
    worst = max(res["windows"], key=lambda w: w["p_fake"])
    facts = {"verdict": core["verdict"], "confidence": core["confidence"], "duration_s": core["duration"]}
    if core["verdict"] != "likely_real":  # pointing at "suspicious seconds" of a real voice would confuse
        facts["most_suspicious_seconds"] = f"{worst['start']:.0f}-{worst['end']:.0f}"
    tips, source = write_tips(facts, lang)
    return {**core, "tips": tips, "tips_source": source, "latency_ms": round((time.perf_counter() - t0) * 1000),
            "model": model, "model_label": MODEL_LABELS[model]}


@app.post("/analyze")
async def analyze(request: Request, file: UploadFile = File(...), lang: str = Form("en"),
                  model: str = Form("")):
    # Login required when Clerk is configured: every check belongs to a user and goes to their history.
    uid = auth.require_user(request) if auth.PUBLISHABLE_KEY else auth.user_id(request)
    key = uid or (request.client.host if request.client else "?")
    limits.hit("analyze_global_min", "*")
    limits.hit("analyze_user_min", key)
    limits.hit("analyze_user_day", key)
    lang = lang if lang in LANGS else "en"
    model = model if model in detectors else DEFAULT
    data = await file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        return JSONResponse({"error": "too_long"}, status_code=400)
    if uid and (quota := await run_in_threadpool(store.quota_error, uid, len(data))):
        return JSONResponse({"error": quota}, status_code=507 if quota == "storage_full" else 409)
    try:
        await asyncio.wait_for(_heavy.acquire(), QUEUE_WAIT_S)
    except asyncio.TimeoutError:
        return JSONResponse({"error": "busy"}, status_code=503)
    try:
        result = await run_in_threadpool(run_analysis, data, model, lang)
    finally:
        _heavy.release()
    if "error" in result:
        return JSONResponse(result, status_code=400)
    result["saved_id"] = (await run_in_threadpool(store.save, uid, result, file.filename or "voice note", data, lang)
                          if uid else None)
    return result


web_dir = Path(__file__).resolve().parent.parent / "web"
if (web_dir / "index.html").exists():
    app.mount("/", StaticFiles(directory=web_dir, html=True), name="web")
