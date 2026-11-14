"""Spoken-readback messages in several Indian languages (digits are spoken by TTS)."""
from __future__ import annotations

TTS_LANGS = {
    "Auto (match what I spoke)": "auto",
    "Hindi": "hi-IN",
    "English (India)": "en-IN",
    "Tamil": "ta-IN",
    "Telugu": "te-IN",
    "Kannada": "kn-IN",
    "Bengali": "bn-IN",
    "Marathi": "mr-IN",
    "Gujarati": "gu-IN",
    "Malayalam": "ml-IN",
}

TOTAL = {
    "hi-IN": "कुल {n} चीज़ें। कुल रकम {t} रुपये।",
    "en-IN": "{n} items. Total {t} rupees.",
    "ta-IN": "மொத்தம் {n} பொருட்கள். மொத்த தொகை {t} ரூபாய்.",
    "te-IN": "మొత్తం {n} వస్తువులు. మొత్తం ధర {t} రూపాయలు.",
    "kn-IN": "ಒಟ್ಟು {n} ವಸ್ತುಗಳು. ಒಟ್ಟು ಮೊತ್ತ {t} ರೂಪಾಯಿ.",
    "bn-IN": "মোট {n}টি জিনিস। মোট {t} টাকা।",
    "mr-IN": "एकूण {n} वस्तू. एकूण रक्कम {t} रुपये.",
    "gu-IN": "કુલ {n} વસ્તુઓ. કુલ રકમ {t} રૂપિયા.",
    "ml-IN": "ആകെ {n} സാധനങ്ങൾ. ആകെ തുക {t} രൂപ.",
}

SUMMARY = {
    "hi-IN": "आज की बिक्री {s} रुपये, {b} बिल। बाकी उधार {u} रुपये।",
    "en-IN": "Today's sales are {s} rupees from {b} bills. Pending credit is {u} rupees.",
}


def lang_from_detected(code: str | None) -> str:
    """Map a detected STT language code to a supported readback language."""
    if code:
        prefix = code.split("-")[0].lower()
        for full in TOTAL:
            if full.split("-")[0] == prefix:
                return full
    return "hi-IN"


def total_message(lang: str, n: int, total: float) -> str:
    tpl = TOTAL.get(lang, TOTAL["hi-IN"])
    return tpl.format(n=n, t=f"{total:.0f}")


def summary_message(lang: str, sales: float, bills: int, pending: float) -> str:
    tpl = SUMMARY.get(lang, SUMMARY["hi-IN"])
    return tpl.format(s=f"{sales:.0f}", b=bills, u=f"{pending:.0f}")
