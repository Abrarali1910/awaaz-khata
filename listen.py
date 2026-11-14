"""'Smart listen': try Gnani speech-to-text, and if nothing useful was understood,
automatically retry with another language mode / model and keep the best result.
"""
from __future__ import annotations

from gnani_client import MODEL_V3, MODEL_V25, GnaniError, transcribe
from ledger_parser import parse_utterance


def score_text(text: str, memory: dict | None = None) -> float:
    rows = parse_utterance(text, memory).rows
    return sum(1.0 if r.amount else 0.5 for r in rows)


def listen(api_key, audio, filename="audio.wav", mime="audio/wav",
           language_code="hi-IN", model=MODEL_V3, memory=None, transcribe_fn=transcribe):
    alt_lang = "indic-auto" if language_code != "indic-auto" else "hi-IN"
    other_model = MODEL_V25 if model == MODEL_V3 else MODEL_V3
    other_lang = language_code if (other_model == MODEL_V3 or language_code != "indic-auto") else "hi-IN"
    plans = [(model, language_code), (model, alt_lang), (other_model, other_lang)]

    best = None
    log: list[dict] = []
    last_error: GnaniError | None = None
    for i, (m, lang) in enumerate(plans):
        try:
            res = transcribe_fn(api_key, audio, filename=filename, mime=mime,
                                language_code=lang, model=m)
        except GnaniError as e:
            last_error = e
            log.append({"model": m, "language": lang, "heard": f"error: {e}", "score": 0})
            if i == 0 and "401" in str(e):
                raise
            continue
        text = (res.get("transcript") or "").strip()
        score = score_text(text, memory) if text else 0
        log.append({"model": m, "language": lang, "heard": text, "score": score,
                    "detected": res.get("detected_language_code")})
        if best is None or score > best[0]:
            best = (score, text, res.get("detected_language_code"))
        if text and score > 0:
            break  # understood something useful: stop spending calls

    if best is None:
        raise last_error or GnaniError("Could not transcribe the audio.")
    return {"text": best[1], "detected": best[2], "attempts": log}
