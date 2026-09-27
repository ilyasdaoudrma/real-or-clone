"""Per-user history: SQLite for results, files on disk for the audio. Every query is scoped to user_id."""
import json
import os
import shutil
import sqlite3
import time
import uuid
from pathlib import Path

STORAGE = Path(os.environ.get("STORAGE_DIR", "storage"))
DB_PATH = STORAGE / "roc.db"
AUDIO_DIR = STORAGE / "audio"
MAX_ITEMS_PER_USER = 100
MAX_BYTES_PER_USER = 300 * 1024 * 1024
MIN_FREE_DISK = 5 * 1024 ** 3        # stop saving before the shared disk fills up
ALLOWED_EXT = {".ogg", ".opus", ".m4a", ".mp3", ".wav", ".webm", ".flac", ".aac", ".mp4"}


def _db() -> sqlite3.Connection:
    STORAGE.mkdir(parents=True, exist_ok=True)
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH, timeout=10)
    con.row_factory = sqlite3.Row
    return con


def init() -> None:
    with _db() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS checks (
            id TEXT PRIMARY KEY, user_id TEXT NOT NULL, created_at REAL NOT NULL, filename TEXT,
            verdict TEXT, p_fake REAL, confidence REAL, duration REAL, model TEXT, lang TEXT,
            tips TEXT, windows TEXT, audio_file TEXT)""")
        con.execute("CREATE INDEX IF NOT EXISTS idx_checks_user ON checks(user_id, created_at DESC)")


def quota_error(user_id: str, incoming: int) -> str | None:
    """None if this user may store `incoming` more bytes, else an error code."""
    with _db() as con:
        files = [r["audio_file"] for r in con.execute("SELECT audio_file FROM checks WHERE user_id=?", (user_id,))]
    used = sum((AUDIO_DIR / f).stat().st_size for f in files if (AUDIO_DIR / f).exists())
    if len(files) >= MAX_ITEMS_PER_USER or used + incoming > MAX_BYTES_PER_USER:
        return "history_full"
    if shutil.disk_usage(STORAGE).free - incoming < MIN_FREE_DISK:
        return "storage_full"
    return None


def save(user_id: str, result: dict, filename: str, audio: bytes, lang: str) -> str:
    check_id = uuid.uuid4().hex
    ext = Path(filename or "").suffix.lower()
    ext = ext if ext in ALLOWED_EXT else ".bin"
    audio_file = f"{check_id}{ext}"                     # server-chosen name: no path traversal
    (AUDIO_DIR / audio_file).write_bytes(audio)
    with _db() as con:
        con.execute("INSERT INTO checks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            check_id, user_id, time.time(), (filename or "voice note")[:80], result["verdict"], result["p_fake"],
            result["confidence"], result["duration"], result.get("model_label") or result.get("model"), lang,
            json.dumps(result["tips"], ensure_ascii=False), json.dumps(result["windows"]), audio_file))
    return check_id


def _public(row: sqlite3.Row) -> dict:
    d = dict(row)
    d.pop("audio_file", None)
    d.pop("user_id", None)
    d["tips"] = json.loads(d["tips"] or "[]")
    d["windows"] = json.loads(d["windows"] or "[]")
    return d


def list_checks(user_id: str, limit: int = 50) -> list[dict]:
    with _db() as con:
        rows = con.execute("SELECT * FROM checks WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
                           (user_id, max(1, min(limit, 200)))).fetchall()
    return [_public(r) for r in rows]


def audio_path(user_id: str, check_id: str) -> Path | None:
    with _db() as con:
        row = con.execute("SELECT audio_file FROM checks WHERE id=? AND user_id=?", (check_id, user_id)).fetchone()
    return AUDIO_DIR / row["audio_file"] if row else None


def delete(user_id: str, check_id: str) -> bool:
    path = audio_path(user_id, check_id)
    if path is None:
        return False
    with _db() as con:
        con.execute("DELETE FROM checks WHERE id=? AND user_id=?", (check_id, user_id))
    path.unlink(missing_ok=True)
    return True


def stats(user_id: str) -> dict:
    with _db() as con:
        rows = con.execute("SELECT verdict, COUNT(*) n, AVG(confidence) c FROM checks WHERE user_id=? GROUP BY verdict",
                           (user_id,)).fetchall()
    by = {r["verdict"]: {"count": r["n"], "avg_confidence": round(r["c"] or 0, 3)} for r in rows}
    return {"total": sum(v["count"] for v in by.values()), "by_verdict": by}
