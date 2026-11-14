"""Common kirana items with Hindi/Hinglish aliases, default units and typical prices.

Used to (1) auto-correct what speech-to-text hears ("chaaval" -> Rice),
(2) show bilingual item names, (3) estimate a price when none was spoken.
Default prices are rough estimates only; the app flags them for the user to check.
"""
from __future__ import annotations

import difflib
import re


def _e(en, hi, unit, price, aliases):
    return {"en": en, "hi": hi, "unit": unit, "price": price, "aliases": aliases}


CATALOG: dict[str, dict] = {
    "rice": _e("Rice", "चावल", "kg", 55, ["rice", "chawal", "chaval", "chaawal", "chawl", "chaaval", "chanwal", "चावल", "चांवल"]),
    "atta": _e("Atta", "आटा", "kg", 45, ["atta", "aata", "aatta", "ata", "flour", "आटा", "गेहूं का आटा"]),
    "sugar": _e("Sugar", "चीनी", "kg", 45, ["sugar", "chini", "cheeni", "shakkar", "sakkar", "shakar", "चीनी", "शक्कर", "शकर"]),
    "salt": _e("Salt", "नमक", "kg", 20, ["salt", "namak", "namck", "नमक"]),
    "oil": _e("Cooking oil", "तेल", "L", 150, ["oil", "tel", "tail", "refined oil", "sarso tel", "mustard oil", "तेल", "सरसों का तेल"]),
    "milk": _e("Milk", "दूध", "L", 60, ["milk", "doodh", "dudh", "dood", "दूध"]),
    "tea": _e("Tea", "चाय पत्ती", "packet", 100, ["tea", "chai", "chai patti", "chaipatti", "chay", "चाय", "चायपत्ती", "चाय पत्ती"]),
    "coffee": _e("Coffee", "कॉफी", "packet", 150, ["coffee", "kofi", "coffe", "कॉफी", "कॉफ़ी"]),
    "dal": _e("Dal", "दाल", "kg", 120, ["dal", "daal", "dhal", "toor dal", "arhar", "arhar dal", "moong dal", "masoor dal", "chana dal", "दाल", "अरहर", "मूंग दाल"]),
    "besan": _e("Besan", "बेसन", "kg", 90, ["besan", "baysan", "बेसन"]),
    "maida": _e("Maida", "मैदा", "kg", 40, ["maida", "maeda", "मैदा"]),
    "soap": _e("Soap", "साबुन", "pc", 40, ["soap", "sabun", "saboon", "साबुन"]),
    "biscuit": _e("Biscuit", "बिस्किट", "packet", 10, ["biscuit", "biskut", "biscut", "biscuits", "बिस्किट", "बिस्कुट"]),
    "onion": _e("Onion", "प्याज़", "kg", 40, ["onion", "pyaz", "pyaaz", "pyaj", "pyas", "प्याज", "प्याज़"]),
    "potato": _e("Potato", "आलू", "kg", 30, ["potato", "aloo", "alu", "aaloo", "आलू"]),
    "tomato": _e("Tomato", "टमाटर", "kg", 40, ["tomato", "tamatar", "tamaatar", "टमाटर"]),
    "egg": _e("Eggs", "अंडे", "dozen", 84, ["egg", "eggs", "anda", "ande", "अंडा", "अंडे"]),
    "bread": _e("Bread", "ब्रेड", "packet", 40, ["bread", "bred", "double roti", "ब्रेड"]),
    "butter": _e("Butter", "मक्खन", "packet", 58, ["butter", "makhan", "makkhan", "मक्खन", "बटर"]),
    "ghee": _e("Ghee", "घी", "kg", 600, ["ghee", "ghi", "घी"]),
    "curd": _e("Curd", "दही", "kg", 80, ["curd", "dahi", "dahee", "दही"]),
    "paneer": _e("Paneer", "पनीर", "kg", 360, ["paneer", "panir", "पनीर"]),
    "noodles": _e("Noodles", "मैगी", "packet", 14, ["noodles", "maggi", "magi", "मैगी", "नूडल्स"]),
    "chips": _e("Chips", "चिप्स", "packet", 20, ["chips", "chip", "kurkure", "lays", "चिप्स"]),
    "colddrink": _e("Cold drink", "कोल्ड ड्रिंक", "bottle", 40, ["cold drink", "colddrink", "coke", "pepsi", "thums up", "cola", "कोल्ड ड्रिंक", "कोल्डड्रिंक"]),
    "water": _e("Water bottle", "पानी बोतल", "bottle", 20, ["water", "pani", "paani", "water bottle", "पानी", "पानी बोतल"]),
}


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").lower().strip())


ALIASES: dict[str, str] = {}
for _key, _e_ in CATALOG.items():
    for _a in [*_e_["aliases"], _e_["en"], _e_["hi"]]:
        ALIASES[_norm(_a)] = _key

_SINGLE = [a for a in ALIASES if " " not in a and len(a) >= 4]


def match_item(name: str) -> str | None:
    """Return the catalog key for a spoken item name, or None."""
    n = _norm(name)
    if not n:
        return None
    if n in ALIASES:
        return ALIASES[n]
    toks = n.split()
    best, best_len = None, 0
    for alias, key in ALIASES.items():
        at = alias.split()
        size = len(at)
        if size <= len(toks) and any(toks[i:i + size] == at for i in range(len(toks) - size + 1)):
            if len(alias) > best_len:
                best, best_len = key, len(alias)
    if best:
        return best
    for t in toks:
        if len(t) >= 4:
            m = difflib.get_close_matches(t, _SINGLE, n=1, cutoff=0.8)
            if m:
                return ALIASES[m[0]]
    return None


def display(key: str) -> str:
    e = CATALOG[key]
    return f"{e['en']} · {e['hi']}"
