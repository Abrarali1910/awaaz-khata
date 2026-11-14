import io
import struct
import wave
from datetime import date, datetime

import audio_utils
import i18n
import store
from gnani_client import GnaniError
from listen import listen


def _wav(samples, rate=16000):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(struct.pack(f"<{len(samples)}h", *samples))
    return buf.getvalue()


def test_normalize_boosts_quiet_audio():
    quiet = _wav([int(500 * ((i % 40) - 20) / 20) for i in range(8000)])
    out = audio_utils.normalize_wav(quiet)
    with wave.open(io.BytesIO(out)) as w:
        data = struct.unpack(f"<{w.getnframes()}h", w.readframes(w.getnframes()))
    assert max(abs(x) for x in data) > 3000
    assert audio_utils.wav_duration(out) == 0.5


def test_normalize_leaves_silence_and_non_wav():
    silent = _wav([0] * 1000)
    assert audio_utils.normalize_wav(silent) == silent
    assert audio_utils.normalize_wav(b"not a wav") == b"not a wav"


def test_store_bills_balances_payments():
    s = store.new_state()
    rows = [{"item": "Rice · चावल", "qty": 2, "unit": "kg", "amount": 110, "key": "rice"}]
    b = store.add_bill(s, rows, "Ramesh", "Udhaar", ts="2026-11-14T10:00:00+05:30")
    assert b["id"] == 1 and b["total"] == 110 and s["prices"]["rice"] == 55
    store.add_bill(s, rows, "", "Cash", ts="2026-11-14T11:00:00+05:30")
    assert store.balances(s) == {"Ramesh": 110}
    store.add_payment(s, "Ramesh", 40)
    assert store.balances(s) == {"Ramesh": 70}
    summ = store.today_summary(s, date(2026, 11, 14))
    assert summ["sales"] == 220 and summ["bills"] == 2 and summ["pending"] == 70
    assert store.mode_split(s)["Udhaar"] == 110
    assert "Total: ₹110" in store.bill_text(b, "Test Shop")


def test_json_roundtrip_and_demo():
    d = store.demo_state(datetime(2026, 11, 14, 12, 0, tzinfo=store.IST))
    assert len(d["bills"]) >= 28
    again = store.load_json(store.export_json(d))
    assert again["bills"] == d["bills"]
    totals = store.daily_totals(d, date(2026, 11, 14), 7)
    assert len(totals) == 7 and sum(t for _, t in totals) > 0
    assert store.top_items(d, 3) and store.balances(d)


def test_i18n():
    assert i18n.lang_from_detected("ta-IN") == "ta-IN"
    assert i18n.lang_from_detected("xx-YY") == "hi-IN"
    assert "560" in i18n.total_message("en-IN", 3, 560)
    assert "560" in i18n.summary_message("hi-IN", 560, 3, 0)


def test_listen_retries_until_it_understands():
    calls = []

    def fake(key, audio, filename, mime, language_code, model):
        calls.append((model, language_code))
        if len(calls) == 1:
            return {"transcript": "", "detected_language_code": "hi-IN"}
        return {"transcript": "2 kilo chawal 100 rupaye", "detected_language_code": "hi-IN"}

    out = listen("k", b"x", transcribe_fn=fake)
    assert out["text"] == "2 kilo chawal 100 rupaye" and len(calls) == 2
    assert calls[1][1] == "indic-auto"


def test_listen_stops_after_first_good_result_and_raises_on_bad_key():
    n = []

    def good(*a, **k):
        n.append(1)
        return {"transcript": "1 kilo atta 45 rupaye"}

    listen("k", b"x", transcribe_fn=good)
    assert len(n) == 1

    def bad(*a, **k):
        raise GnaniError("Invalid or missing Gnani API key (401).")

    try:
        listen("k", b"x", transcribe_fn=bad)
        raise AssertionError("should raise")
    except GnaniError:
        pass
