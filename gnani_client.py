"""Thin client for Gnani Vachana APIs (STT: Prisma, TTS: Timbre v2.5).

Endpoints and fields follow https://docs.gnani.ai/api/introduction/quick-start
"""
from __future__ import annotations

import time

import requests

BASE_URL = "https://api.vachana.ai"
STT_URL = f"{BASE_URL}/stt/v3"
TTS_URL = f"{BASE_URL}/api/v1/tts/inference"

MODEL_V3 = "prisma-v3.0"
MODEL_V25 = "prisma-v2.5"


class GnaniError(Exception):
    pass


def _post(url: str, retries: int = 2, **kwargs) -> requests.Response:
    """POST with a small retry on network errors and 5xx responses."""
    last: Exception | None = None
    for attempt in range(retries + 1):
        try:
            r = requests.post(url, timeout=60, **kwargs)
            if r.status_code >= 500 and attempt < retries:
                time.sleep(0.8 * (attempt + 1))
                continue
            return r
        except requests.RequestException as e:
            last = e
            if attempt < retries:
                time.sleep(0.8 * (attempt + 1))
    raise GnaniError(f"Network error calling Gnani: {last}")


def transcribe(
    api_key: str,
    audio_bytes: bytes,
    filename: str = "audio.wav",
    mime: str = "audio/wav",
    language_code: str = "indic-auto",
    model: str = MODEL_V3,
) -> dict:
    """Speech -> text. Returns the JSON dict (transcript, detected_language_code, ...).

    Prisma v3.0 accepts `indic-auto` (auto language / code-mixed) and
    `format=transcribe` (numbers as digits). Prisma v2.5 is the API default and
    needs an explicit language.
    """
    data = {"language_code": language_code}
    if model == MODEL_V3:
        data["model"] = MODEL_V3
        data["format"] = "transcribe"
    elif language_code == "indic-auto":
        data["language_code"] = "hi-IN"  # indic-auto is v3-only

    r = _post(
        STT_URL,
        headers={"X-API-Key-ID": api_key},
        files={"audio_file": (filename, audio_bytes, mime)},
        data=data,
    )
    if r.status_code == 401:
        raise GnaniError("Invalid or missing Gnani API key (401).")
    if not r.ok:
        raise GnaniError(f"Gnani STT error {r.status_code}: {r.text[:300]}")
    try:
        out = r.json()
    except ValueError as e:
        raise GnaniError(f"Gnani STT returned non-JSON: {r.text[:200]}") from e
    if "transcript" not in out:
        raise GnaniError(f"Unexpected STT response: {str(out)[:300]}")
    return out


def synthesize(
    api_key: str,
    text: str,
    language: str = "hi-IN",
    voice: str = "Nalini",
    speed: float = 1.0,
) -> bytes:
    """Text -> speech using Gnani Timbre v2.5. Returns WAV bytes."""
    payload = {
        "text": text,
        "voice": voice,
        "model": "timbre-v2.5",
        "language": language,
        "speed": speed,
        "audio_config": {
            "sample_rate": 48000,
            "num_channels": 1,
            "sample_width": 2,
            "encoding": "linear_pcm",
            "container": "wav",
        },
    }
    r = _post(
        TTS_URL,
        headers={"X-API-Key-ID": api_key, "Content-Type": "application/json"},
        json=payload,
    )
    if r.status_code == 401:
        raise GnaniError("Invalid or missing Gnani API key (401).")
    if not r.ok:
        raise GnaniError(f"Gnani TTS error {r.status_code}: {r.text[:300]}")
    return r.content
