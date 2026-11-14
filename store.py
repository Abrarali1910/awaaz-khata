"""Bills, udhaar (credit) balances, payments, price memory, reports and demo data.

State is a plain dict kept in Streamlit's session_state, so every visitor gets a
private ledger. It can be exported / restored as JSON.
"""
from __future__ import annotations

import json
import random
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

from catalog import CATALOG, display

IST = timezone(timedelta(hours=5, minutes=30))
MODES = ("Cash", "UPI", "Udhaar")


def now_iso() -> str:
    return datetime.now(IST).isoformat(timespec="seconds")


def new_state() -> dict:
    return {"bills": [], "payments": [], "prices": {}, "phones": {}}


def add_bill(state: dict, rows: list[dict], customer: str = "", mode: str = "Cash", ts: str | None = None) -> dict:
    items, total = [], 0.0
    for r in rows:
        qty = float(r.get("qty") or 1)
        amt = float(r.get("amount") or 0)
        items.append({"item": str(r["item"]), "qty": qty, "unit": r.get("unit") or "",
                      "amount": amt, "key": r.get("key") or ""})
        total += amt
        if r.get("key") and amt > 0 and qty > 0:
            state["prices"][r["key"]] = round(amt / qty, 2)  # remember unit price
    bill = {
        "id": max((b["id"] for b in state["bills"]), default=0) + 1,
        "ts": ts or now_iso(),
        "customer": (customer or "").strip(),
        "mode": mode if mode in MODES else "Cash",
        "total": round(total, 2),
        "items": items,
    }
    state["bills"].append(bill)
    return bill


def add_payment(state: dict, customer: str, amount: float, ts: str | None = None) -> dict:
    p = {"ts": ts or now_iso(), "customer": customer.strip(), "amount": float(amount)}
    state["payments"].append(p)
    return p


def balances(state: dict) -> dict[str, float]:
    """Outstanding udhaar per customer (credit given minus payments), > 0 only."""
    bal: dict[str, float] = defaultdict(float)
    for b in state["bills"]:
        if b["mode"] == "Udhaar" and b["customer"]:
            bal[b["customer"]] += b["total"]
    for p in state["payments"]:
        bal[p["customer"]] -= p["amount"]
    return dict(sorted(((k, round(v, 2)) for k, v in bal.items() if v > 0.009),
                       key=lambda kv: -kv[1]))


def _d(ts: str) -> date:
    return datetime.fromisoformat(ts).date()


def bills_on(state: dict, day: date) -> list[dict]:
    return [b for b in state["bills"] if _d(b["ts"]) == day]


def today_summary(state: dict, today: date) -> dict:
    todays = bills_on(state, today)
    sales = sum(b["total"] for b in todays)
    n = len(todays)
    return {
        "sales": round(sales, 2),
        "bills": n,
        "avg": round(sales / n, 2) if n else 0.0,
        "pending": round(sum(balances(state).values()), 2),
    }


def daily_totals(state: dict, today: date, days: int = 7) -> list[tuple[date, float]]:
    out = []
    for k in range(days - 1, -1, -1):
        d = today - timedelta(days=k)
        out.append((d, round(sum(b["total"] for b in bills_on(state, d)), 2)))
    return out


def top_items(state: dict, n: int = 6) -> list[tuple[str, float]]:
    agg: dict[str, float] = defaultdict(float)
    for b in state["bills"]:
        for it in b["items"]:
            agg[it["item"]] += it["amount"]
    return sorted(agg.items(), key=lambda kv: -kv[1])[:n]


def mode_split(state: dict) -> dict[str, float]:
    agg = {m: 0.0 for m in MODES}
    for b in state["bills"]:
        agg[b["mode"]] += b["total"]
    return agg


def fmt_qty(q: float) -> str:
    return str(int(q)) if float(q).is_integer() else f"{q:g}"


def bill_text(bill: dict, shop: str = "My Shop") -> str:
    when = datetime.fromisoformat(bill["ts"]).strftime("%d %b %Y, %I:%M %p")
    lines = [f"*{shop}*", f"Bill #{bill['id']} · {when}"]
    if bill["customer"]:
        lines.append(f"Customer: {bill['customer']}")
    lines.append("-" * 22)
    for it in bill["items"]:
        unit = f" {it['unit']}" if it["unit"] else ""
        lines.append(f"{it['item']} × {fmt_qty(it['qty'])}{unit} = ₹{it['amount']:.0f}")
    lines.append("-" * 22)
    lines.append(f"*Total: ₹{bill['total']:.0f}* ({bill['mode']})")
    lines.append("Thank you! 🙏 धन्यवाद!")
    return "\n".join(lines)


def reminder_text(shop: str, customer: str, amount: float) -> str:
    return (f"Namaste {customer} ji 🙏\nYour pending udhaar at {shop} is ₹{amount:.0f}. "
            f"Please pay when convenient.\nधन्यवाद!")


def bills_rows(state: dict) -> list[dict]:
    """Flat rows (one per item) for CSV export."""
    rows = []
    for b in state["bills"]:
        for it in b["items"]:
            rows.append({"bill_id": b["id"], "time": b["ts"], "customer": b["customer"],
                         "payment": b["mode"], "item": it["item"], "qty": it["qty"],
                         "unit": it["unit"], "amount": it["amount"], "bill_total": b["total"]})
    return rows


def export_json(state: dict) -> str:
    return json.dumps(state, ensure_ascii=False, indent=1)


def load_json(text: str) -> dict:
    data = json.loads(text)
    if not isinstance(data, dict) or "bills" not in data:
        raise ValueError("Not an Awaaz Khata backup file.")
    base = new_state()
    base.update({k: data.get(k, base[k]) for k in base})
    return base


def demo_state(now: datetime | None = None) -> dict:
    """A week of realistic sample data so dashboards look alive."""
    rnd = random.Random(42)
    now = now or datetime.now(IST)
    state = new_state()
    customers = ["Ramesh", "Sunita", "Mohan", "Priya", "Imran"]
    keys = list(CATALOG)
    for back in range(6, -1, -1):
        day = (now - timedelta(days=back)).replace(minute=0, second=0, microsecond=0)
        for _ in range(rnd.randint(4, 8)):
            rows = []
            for k in rnd.sample(keys, rnd.randint(2, 4)):
                e = CATALOG[k]
                qty = rnd.choice([0.5, 1, 1, 2, 2, 3, 5]) if e["unit"] in ("kg", "L") else rnd.randint(1, 4)
                price = e["price"] * rnd.uniform(0.95, 1.08)
                rows.append({"item": display(k), "qty": qty, "unit": e["unit"],
                             "amount": round(price * qty), "key": k})
            mode = rnd.choices(MODES, weights=[5, 3, 2])[0]
            cust = rnd.choice(customers) if mode == "Udhaar" or rnd.random() < 0.3 else ""
            when = day.replace(hour=rnd.randint(8, 20), minute=rnd.randint(0, 59))
            add_bill(state, rows, cust, mode, ts=when.isoformat(timespec="seconds"))
    for c, amt in list(balances(state).items())[:2]:
        add_payment(state, c, round(amt * 0.4), ts=now.isoformat(timespec="seconds"))
    state["phones"] = {}
    return state
