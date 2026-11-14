"""Audio helpers (stdlib only): loudness normalisation + duration for 16-bit PCM WAV.

Quiet phone/laptop mics are a top cause of bad speech recognition; boosting a
quiet recording to a healthy level before sending it to STT helps.
"""
from __future__ import annotations

import io
import sys
import wave
from array import array


def _is_wav(data: bytes) -> bool:
    return len(data) > 12 and data[:4] == b"RIFF" and data[8:12] == b"WAVE"


def wav_duration(data: bytes) -> float | None:
    if not _is_wav(data):
        return None
    try:
        with wave.open(io.BytesIO(data), "rb") as w:
            return w.getnframes() / float(w.getframerate() or 1)
    except (wave.Error, EOFError):
        return None


def normalize_wav(data: bytes, target_peak: float = 0.9, max_gain: float = 8.0) -> bytes:
    """Scale a 16-bit PCM WAV so its peak is ~target_peak of full scale.

    Returns the input unchanged for anything it can't safely process.
    """
    if not _is_wav(data):
        return data
    try:
        with wave.open(io.BytesIO(data), "rb") as w:
            params = w.getparams()
            if params.sampwidth != 2 or params.comptype != "NONE":
                return data
            frames = w.readframes(params.nframes)
        samples = array("h")
        samples.frombytes(frames)
        if sys.byteorder == "big":
            samples.byteswap()
        if not samples:
            return data
        peak = max(max(samples), -min(samples))
        if peak < 50:  # basically silence: don't amplify noise
            return data
        gain = min(max_gain, (32767 * target_peak) / peak)
        if gain <= 1.05:
            return data
        scaled = array("h", (max(-32768, min(32767, int(s * gain))) for s in samples))
        if sys.byteorder == "big":
            scaled.byteswap()
        out = io.BytesIO()
        with wave.open(out, "wb") as w:
            w.setparams(params)
            w.writeframes(scaled.tobytes())
        return out.getvalue()
    except (wave.Error, EOFError, ValueError):
        return data
