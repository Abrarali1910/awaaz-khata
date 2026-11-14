"""Turn a spoken-sales transcript into bill rows. Pure Python, no API needed.

Understands:
  * digits (Gnani returns digits with format=transcribe), Devanagari digits, "1,200"
  * Hindi / Hinglish / English number words ("dedh sau", "do hazaar", "ninety")
  * units (kilo, litre, packet...), currency words (rupaye, रुपये, ₹, rs)
  * per-unit rates:  "2 kilo chawal 55 rupaye kilo"  -> amount 110
  * missing price:   "2 kilo chawal" -> estimated from remembered / typical price
  * customer + payment mode:  "Ramesh ko udhaar 2 kilo chawal 100 rupaye"
Convention: an amount is the TOTAL for that line unless a per-unit rate is spoken.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from catalog import CATALOG, display, match_item

NUMBER_WORDS = {
    # Hinglish
    "ek": 1, "do": 2, "teen": 3, "char": 4, "chaar": 4, "paanch": 5, "panch": 5,
    "chhe": 6, "chhah": 6, "che": 6, "saat": 7, "aath": 8, "nau": 9, "das": 10, "dus": 10,
    "gyarah": 11, "barah": 12, "terah": 13, "chaudah": 14, "pandrah": 15, "solah": 16,
    "satrah": 17, "atharah": 18, "unnis": 19, "bees": 20, "pachis": 25, "tees": 30,
    "chalis": 40, "pachas": 50, "saath": 60, "sattar": 70, "assi": 80, "nabbe": 90,
    "adha": 0.5, "aadha": 0.5, "dedh": 1.5, "dhai": 2.5, "dhaai": 2.5,
    # Devanagari
    "एक": 1, "दो": 2, "तीन": 3, "चार": 4, "पांच": 5, "पाँच": 5, "छह": 6, "छः": 6,
    "सात": 7, "आठ": 8, "नौ": 9, "दस": 10, "ग्यारह": 11, "बारह": 12, "तेरह": 13,
    "चौदह": 14, "पंद्रह": 15, "सोलह": 16, "सत्रह": 17, "अठारह": 18, "उन्नीस": 19,
    "बीस": 20, "पच्चीस": 25, "तीस": 30, "चालीस": 40, "पचास": 50, "साठ": 60,
    "सत्तर": 70, "अस्सी": 80, "नब्बे": 90, "आधा": 0.5, "डेढ़": 1.5, "ढाई": 2.5,
    # English
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "twenty": 20, "thirty": 30, "forty": 40,
    "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90, "half": 0.5,
}
MULTIPLIERS = {"sau": 100, "सौ": 100, "hundred": 100, "hazaar": 1000, "hazar": 1000,
               "हज़ार": 1000, "हजार": 1000, "thousand": 1000}

UNITS = {
    "kilo": "kg", "kg": "kg", "किलो": "kg", "किलोग्राम": "kg", "kilogram": "kg", "kilos": "kg",
    "gram": "g", "gm": "g", "ग्राम": "g", "grams": "g",
    "litre": "L", "liter": "L", "ltr": "L", "लीटर": "L", "litres": "L", "liters": "L",
    "packet": "packet", "पैकेट": "packet", "packets": "packet",
    "piece": "pc", "pieces": "pc", "pcs": "pc", "pc": "pc", "पीस": "pc", "नग": "pc",
    "dozen": "dozen", "दर्जन": "dozen",
    "bottle": "bottle", "बोतल": "bottle", "bottles": "bottle",
}
CURRENCY = {"rupaye", "rupees", "rupee", "rupya", "rupay", "rs", "inr",
            "रुपये", "रुपए", "रुपया", "रु", "रू", "रुपे", "₹"}
RATE_WORDS = {"per", "prati", "प्रति", "ka", "ke", "ki", "का", "के", "की", "rate", "रेट"}
CONJ = {"aur", "and", "और", "phir", "फिर", "then"}
FILLER = {
    "ka", "ki", "ke", "of", "का", "की", "के", "the", "ne", "ko", "for", "per", "prati", "प्रति",
    "rate", "रेट", "hisab", "हिसाब", "se", "से", "wala", "wali", "mein", "में", "me", "dena",
    "dedo", "dijiye", "chahiye", "चाहिए", "diya", "दिया", "liya", "लिया", "becha", "बेचा",
    "sold", "sale", "add", "bill", "price", "amount", "total", "rupaye", "plus", "a", "an",
}

UDHAAR_WORDS = {"udhaar", "udhar", "uddhar", "उधार", "उधारी", "credit", "baaki", "baki", "बाकी"}
UPI_WORDS = {"upi", "gpay", "phonepe", "paytm", "online", "qr", "यूपीआई", "फोनपे", "गूगलपे", "पेटीएम", "ऑनलाइन"}
CASH_WORDS = {"cash", "नकद", "कैश"}
MODE_WORDS = UDHAAR_WORDS | UPI_WORDS | CASH_WORDS

_W = r"[\wऀ-ॿ]+"
CUSTOMER_PATTERNS = [
    rf"(?P<n>{_W})\s+(?:ko|को)\s+(?:udhaar|udhar|uddhar|उधार|उधारी|credit)",
    rf"(?P<n>{_W})\s+(?:ke|के)\s+(?:naam|nam|नाम|khate|khata|खाते|खाता)(?:\s+(?:me|mein|mai|में|par|पर))?",
    rf"(?:customer|grahak|ग्राहक)\s+(?P<n>{_W})",
]

_DEV_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")


@dataclass
class Row:
    heard: str
    item: str
    key: str | None
    qty: float
    unit: str
    amount: float | None
    est: bool = False

    def as_dict(self) -> dict:
        if self.amount and not self.est:
            check = "✅"
        elif self.est:
            check = "≈ estimate"
        else:
            check = "⚠️ add price"
        return {
            "Item": self.item,
            "Qty": self.qty,
            "Unit": self.unit,
            "Amount (₹)": self.amount or 0,
            "Check": check,
            "_key": self.key or "",
        }


@dataclass
class ParsedBill:
    rows: list[Row] = field(default_factory=list)
    customer: str | None = None
    mode: str | None = None
    cleaned: str = ""


def _fmt(x: float):
    return int(x) if float(x).is_integer() else round(x, 2)


def _prep(text: str) -> str:
    text = (text or "").translate(_DEV_DIGITS)
    return re.sub(r"(?<=\d),(?=\d{3}(?!\d))", "", text)


def _tokens(segment: str) -> list[str]:
    segment = segment.replace("₹", " ₹ ")
    segment = re.sub(r"(?<=\d)(?=[^\W\d_])", " ", segment)  # 100rs -> 100 rs
    return [t for t in segment.lower().split() if t]


def _is_num_token(t: str) -> bool:
    return bool(re.fullmatch(r"\d+(?:\.\d+)?", t))


def _merge_numbers(tokens: list[str]) -> list:
    """Collapse number words / digits into ('num', value); other tokens stay strings."""
    out: list = []
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if _is_num_token(t):
            val = float(t)
            if i + 1 < len(tokens) and tokens[i + 1] in MULTIPLIERS:
                val *= MULTIPLIERS[tokens[i + 1]]
                i += 1
            out.append(("num", val))
            i += 1
        elif t in NUMBER_WORDS or t in MULTIPLIERS:
            total, cur, seen = 0.0, 0.0, False
            while i < len(tokens):
                w = tokens[i]
                if w in MULTIPLIERS:
                    total += (cur or 1) * MULTIPLIERS[w]
                    cur = 0.0
                elif w in NUMBER_WORDS:
                    cur += NUMBER_WORDS[w]
                else:
                    break
                seen = True
                i += 1
            if seen:
                out.append(("num", total + cur))
        else:
            out.append(t)
            i += 1
    return out


def _split_segments(text: str) -> list[list[str]]:
    parts = re.split(r"[,;\n।]|\.(?:\s|$)", text)
    segments: list[list[str]] = []
    for part in parts:
        cur: list[str] = []
        for tok in part.split():
            if tok.lower() in CONJ:
                if cur:
                    segments.append(cur)
                cur = []
            else:
                cur.append(tok)
        if cur:
            segments.append(cur)
    return segments


def _is_num(x) -> bool:
    return isinstance(x, tuple)


def parse_segment(tokens: list[str]) -> Row | None:
    items = _merge_numbers(_tokens(" ".join(tokens)))
    nums = [(i, v[1]) for i, v in enumerate(items) if _is_num(v)]
    if not nums:
        return None

    def nxt(i):
        return items[i + 1] if i + 1 < len(items) else None

    def prv(i):
        return items[i - 1] if i > 0 else None

    # --- which number is the price? ---
    cur_idx = [i for i, _ in nums
               if (isinstance(nxt(i), str) and nxt(i) in CURRENCY)
               or (isinstance(prv(i), str) and prv(i) in CURRENCY)]
    if cur_idx:
        price_idx = cur_idx[-1]
    elif len(nums) >= 2:
        price_idx = nums[-1][0]
    else:  # single number: a quantity if a unit follows, else a price
        i0 = nums[0][0]
        price_idx = None if (isinstance(nxt(i0), str) and nxt(i0) in UNITS) else i0
    price = dict(nums).get(price_idx) if price_idx is not None else None

    # --- quantity & unit ---
    qty, unit, qty_idx = 1.0, "", None
    for i, v in nums:
        if i != price_idx and isinstance(nxt(i), str) and nxt(i) in UNITS:
            qty, unit, qty_idx = v, UNITS[nxt(i)], i
            break
    if qty_idx is None:
        for i, v in nums:
            if i != price_idx:
                qty, qty_idx = v, i
                break
    if not unit:
        for w in items:
            if isinstance(w, str) and w in UNITS:
                unit = UNITS[w]
                break

    # --- per-unit rate:  "55 rupaye kilo" / "55 per kilo" ---
    amount = price
    if price is not None and price_idx is not None:
        j = price_idx + 1
        while j < len(items) and isinstance(items[j], str) and (items[j] in CURRENCY or items[j] in RATE_WORDS):
            j += 1
        if j < len(items) and isinstance(items[j], str) and items[j] in UNITS:
            amount = price * qty
            unit = unit or UNITS[items[j]]

    name_words = [
        w for w in items
        if isinstance(w, str) and w not in CURRENCY and w not in UNITS
        and w not in FILLER and not re.fullmatch(r"[^\w₹]+", w)
    ]
    heard = " ".join(name_words).strip()
    if not heard:
        return None
    key = match_item(heard)
    return Row(
        heard=heard,
        item=display(key) if key else heard.title(),
        key=key,
        qty=_fmt(qty),
        unit=unit,
        amount=_fmt(amount) if amount is not None else None,
    )


def apply_prices(rows: list[Row], memory: dict | None = None) -> None:
    """Fill missing units/amounts from remembered unit prices, else typical prices."""
    memory = memory or {}
    for r in rows:
        if r.key and not r.unit:
            r.unit = CATALOG[r.key]["unit"]
        if r.amount is None:
            unit_price = memory.get(r.key) if r.key else None
            if not unit_price and r.key:
                unit_price = CATALOG[r.key]["price"]
            if unit_price:
                r.amount = _fmt(float(unit_price) * float(r.qty))
                r.est = True


def _extract_context(text: str):
    mode = None
    words = {w.lower() for w in re.findall(_W, text)}
    if words & UDHAAR_WORDS:
        mode = "Udhaar"
    elif words & UPI_WORDS:
        mode = "UPI"
    elif words & CASH_WORDS:
        mode = "Cash"

    customer = None
    for pat in CUSTOMER_PATTERNS:
        m = re.search(pat, text, re.I)
        if not m:
            continue
        name = m.group("n")
        low = name.lower()
        bad = (low in NUMBER_WORDS or low in UNITS or low in CURRENCY or low in CONJ
               or low in FILLER or low in MODE_WORDS or len(low) < 2 or low.isdigit()
               or match_item(low))
        if bad:
            continue
        customer = name.title()
        text = text[:m.start()] + " " + text[m.end():]
        break

    cleaned = re.sub(_W, lambda m: "" if m.group().lower() in MODE_WORDS else m.group(), text)
    return customer, mode, cleaned


def parse_utterance(text: str, price_memory: dict | None = None) -> ParsedBill:
    text = _prep(text)
    customer, mode, cleaned = _extract_context(text)
    rows = []
    for seg in _split_segments(cleaned):
        row = parse_segment(seg)
        if row:
            rows.append(row)
    apply_prices(rows, price_memory)
    return ParsedBill(rows=rows, customer=customer, mode=mode, cleaned=cleaned.strip())


def parse_transcript(text: str, price_memory: dict | None = None) -> list[Row]:
    return parse_utterance(text, price_memory).rows
