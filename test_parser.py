from ledger_parser import parse_utterance


def rows(text, memory=None):
    return [(r.key or r.heard, r.qty, r.unit, r.amount) for r in parse_utterance(text, memory).rows]


def test_digits_hinglish():
    assert rows("2 kilo chawal 100 rupaye, 3 litre tel 450 rupaye aur 1 packet biscuit 10 rupaye") == [
        ("rice", 2, "kg", 100), ("oil", 3, "L", 450), ("biscuit", 1, "packet", 10)]


def test_devanagari_and_digits():
    assert rows("2 किलो आटा 80 रुपये, 1 लीटर दूध 60 रुपये") == [("atta", 2, "kg", 80), ("milk", 1, "L", 60)]
    assert rows("२ किलो आटा ९० रुपये") == [("atta", 2, "kg", 90)]


def test_number_words():
    assert rows("do kilo chawal dedh sau rupaye") == [("rice", 2, "kg", 150)]
    assert rows("ek sau pachas rupaye ka tel") == [("oil", 1, "", 150)] or rows("ek sau pachas rupaye ka tel")[0][3] == 150
    assert rows("two kilo sugar ninety rupees") == [("sugar", 2, "kg", 90)]


def test_thousands_commas():
    assert rows("1 packet ghee 1,200 rupaye")[0][3] == 1200
    assert rows("do hazaar rupaye ka sofa")[0][3] == 2000


def test_rupee_symbol_no_qty():
    assert rows("sugar ₹45, tea 120 rs") == [("sugar", 1, "kg", 45), ("tea", 1, "packet", 120)]


def test_per_unit_rate():
    assert rows("2 kilo chawal 55 rupaye kilo") == [("rice", 2, "kg", 110)]
    assert rows("3 kg sugar 45 per kg") == [("sugar", 3, "kg", 135)]


def test_missing_price_uses_memory_then_catalog():
    assert rows("2 kilo chawal", {"rice": 60}) == [("rice", 2, "kg", 120)]
    r = parse_utterance("2 kilo chawal").rows[0]
    assert r.amount == 110 and r.est and r.as_dict()["Check"] == "≈ estimate"


def test_unknown_item_unpriced_flagged():
    r = parse_utterance("3 piece toy").rows[0]
    assert r.key is None and r.amount is None and r.as_dict()["Check"] == "⚠️ add price"


def test_fuzzy_item_autocorrect():
    assert rows("1 kilo chaawl 50 rupaye")[0][0] == "rice"
    assert rows("1 kilo shakkr 45 rupaye")[0][0] == "sugar"


def test_customer_and_mode():
    p = parse_utterance("Ramesh ko udhaar 2 kilo chawal 100 rupaye")
    assert p.customer == "Ramesh" and p.mode == "Udhaar"
    assert [(r.key, r.amount) for r in p.rows] == [("rice", 100)]
    p = parse_utterance("रमेश को उधार 1 लीटर दूध 60 रुपये")
    assert p.customer == "रमेश" and p.mode == "Udhaar" and p.rows[0].key == "milk"
    p = parse_utterance("sunita ke naam 1 kilo atta 45 rupaye")
    assert p.customer == "Sunita" and p.rows[0].key == "atta"
    p = parse_utterance("upi 1 packet biscuit 10 rupaye")
    assert p.mode == "UPI" and p.customer is None and p.rows[0].key == "biscuit"


def test_empty_and_noise():
    assert parse_utterance("").rows == []
    assert parse_utterance("namaste").rows == []
