# API contract (web app codes against this; mock in web/mock_response.json)

`POST /analyze` — multipart form: `file` (any audio: ogg/opus/m4a/mp3/wav/webm, max 60 s), `lang` (`ar` | `fr` | `en`, language of the TIPS)

Response 200:
```json
{
  "verdict": "likely_clone",          // "likely_real" | "likely_clone" | "uncertain"
  "p_fake": 0.87,                      // 0..1, mean over windows
  "confidence": 0.74,                  // |p_fake - 0.5| * 2
  "duration": 9.4,
  "windows": [ {"start": 0.0, "end": 4.0, "p_fake": 0.91}, {"start": 2.0, "end": 6.0, "p_fake": 0.83} ],
  "tips": ["...", "...", "..."],       // 3 tips in `lang`, written by the LLM FROM the verdict, never changing it
  "tips_source": "nim",                // "nim" | "template" (fallback)
  "latency_ms": 640,
  "model": "run_b"
}
```
Errors: 400 `{"error": "too_short" | "too_long" | "bad_audio"}`. Audio is deleted right after scoring; nothing is stored.
`GET /health` -> `{"ok": true, "model": "run_b", "device": "cuda"}`
