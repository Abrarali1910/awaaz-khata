"""Awaaz Khata · आवाज़ खाता — voice-first billing & udhaar khata for India's shopkeepers.

Powered by Gnani Vachana: Prisma (speech-to-text) listens, Timbre v2.5 (text-to-speech) speaks.
"""
import hashlib
import json
import os
import urllib.parse
from datetime import datetime

import pandas as pd
import streamlit as st

import i18n
import store
from audio_utils import normalize_wav, wav_duration
from gnani_client import MODEL_V3, MODEL_V25, GnaniError, synthesize
from ledger_parser import parse_utterance
from listen import listen

st.set_page_config(page_title="Awaaz Khata · आवाज़ खाता", page_icon="🎙️",
                   layout="wide", initial_sidebar_state="expanded")

# ───────────────────────────── styling ─────────────────────────────
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&family=Noto+Sans+Devanagari:wght@400;600;700&display=swap');
html, body, .stApp, .stMarkdown, label, button, input, textarea, h1, h2, h3, h4, p, li {
  font-family: 'Poppins', 'Noto Sans Devanagari', sans-serif;
}
#MainMenu, footer {visibility: hidden;}
header[data-testid="stHeader"] {background: transparent;}
.block-container {padding-top: 1rem; max-width: 1280px;}
.tricolor {height: 5px; border-radius: 6px; margin-bottom: 14px;
  background: linear-gradient(90deg,#FF9933 0 33.3%,#ffffff 33.3% 66.6%,#138808 66.6% 100%);
  box-shadow: 0 0 0 1px #ece3d6;}
.hero {background: linear-gradient(120deg,#171a3a 0%,#2b2f6e 55%,#d9631a 135%);
  border-radius: 22px; padding: 26px 30px; color: #fff; margin-bottom: 18px;
  box-shadow: 0 14px 40px rgba(23,26,58,.28);}
.hero h1 {margin: 0; font-size: 2.3rem; font-weight: 700; letter-spacing: -.5px; color:#fff;}
.hero h1 span {color: #FFB067; font-weight: 600; margin-left: 10px;}
.hero p {margin: 6px 0 14px 0; color: #dfe3ff; font-size: 1.02rem;}
.pill {display: inline-block; padding: 5px 13px; margin: 0 8px 6px 0; border-radius: 999px;
  background: rgba(255,255,255,.14); border: 1px solid rgba(255,255,255,.22);
  color: #fff; font-size: .8rem; font-weight: 500;}
.pill.ok {background: rgba(19,136,8,.35); border-color: rgba(120,230,110,.6);}
.pill.warn {background: rgba(249,115,22,.35); border-color: rgba(255,180,120,.7);}
div[data-testid="stVerticalBlockBorderWrapper"] {border-radius: 18px;}
div[data-testid="stVerticalBlockBorderWrapper"]:has(> div > div[data-testid="stVerticalBlock"]) {
  background: #ffffff; border: 1px solid #f0e6d8; box-shadow: 0 8px 26px rgba(31,41,55,.06);}
[data-testid="stMetric"] {background: #fff; border: 1px solid #f0e6d8; border-radius: 16px;
  padding: 14px 18px; box-shadow: 0 6px 20px rgba(31,41,55,.05);}
[data-testid="stMetricValue"] {font-weight: 700; color: #171a3a;}
.stButton > button, .stDownloadButton > button, .stLinkButton > a {border-radius: 12px; font-weight: 600;}
.stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"] {
  background: linear-gradient(135deg,#F97316,#EA580C); border: none; color: #fff;}
.stTabs [data-baseweb="tab-list"] {gap: 8px;}
.stTabs [data-baseweb="tab"] {background: #fff; border: 1px solid #f0e6d8; border-radius: 12px;
  padding: 8px 18px; font-weight: 600;}
.stTabs [aria-selected="true"] {background: #171a3a !important; color: #fff !important;}
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] {display: none;}
.total-card {background: linear-gradient(135deg,#138808,#0b5d05); color: #fff; border-radius: 16px;
  padding: 16px 22px; display: flex; justify-content: space-between; align-items: center;
  box-shadow: 0 10px 26px rgba(19,136,8,.28);}
.total-card .lbl {font-size: .85rem; opacity: .85; text-transform: uppercase; letter-spacing: 1px;}
.total-card .amt {font-size: 2.3rem; font-weight: 700; line-height: 1.1;}
.total-card .meta {text-align: right; font-size: .9rem; opacity: .95;}
.step {display: inline-flex; align-items: center; justify-content: center; width: 30px; height: 30px;
  border-radius: 50%; background: #F97316; color: #fff; font-weight: 700; margin-right: 10px;}
.sec-title {font-size: 1.2rem; font-weight: 700; color: #171a3a; margin: 0 0 8px 0;}
.tip {background: #FFF4E5; border: 1px dashed #F5B26B; border-radius: 12px; padding: 10px 14px;
  font-size: .86rem; color: #5b3b10; margin-top: 6px;}
.understood {background: #EEF7ED; border: 1px solid #bfe3bb; border-radius: 12px; padding: 9px 13px;
  font-size: .88rem; color: #1c4d17; margin: 6px 0 10px 0;}
.saved {background: linear-gradient(135deg,#eef9ee,#f6fff5); border: 1px solid #b7e2b2;
  border-radius: 16px; padding: 12px 16px; margin-bottom: 10px;}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ───────────────────────────── state ─────────────────────────────
ss = st.session_state
BILL_COLS = ["Item", "Qty", "Unit", "Amount (₹)", "Check", "_key"]


def empty_df() -> pd.DataFrame:
    return pd.DataFrame({"Item": pd.Series(dtype="str"), "Qty": pd.Series(dtype="float"),
                         "Unit": pd.Series(dtype="str"), "Amount (₹)": pd.Series(dtype="float"),
                         "Check": pd.Series(dtype="str"), "_key": pd.Series(dtype="str")})


for k, v in {"db": store.new_state(), "bill_df": empty_df(), "current_df": empty_df(),
             "editor_ver": 0, "last_audio_id": None, "detected_lang": "hi-IN",
             "customer_input": "", "mode_input": "Cash", "heard_box": "",
             "last_saved": None, "heard_info": None, "flash": None, "tts_audio": None}.items():
    ss.setdefault(k, v)

if ss.pop("_reset_form", False):  # must run before the widgets below are created
    ss.customer_input, ss.mode_input, ss.heard_box = "", "Cash", ""


def today():
    return datetime.now(store.IST).date()


def get_api_key() -> str:
    typed = st.session_state.get("api_key_input", "")
    if typed:
        return typed
    try:
        if "GNANI_API_KEY" in st.secrets:
            return st.secrets["GNANI_API_KEY"]
    except Exception:
        pass
    return os.environ.get("GNANI_API_KEY", "")


def wa_link(text: str, phone: str = "") -> str:
    digits = "".join(c for c in phone if c.isdigit())
    if len(digits) == 10:
        digits = "91" + digits
    return f"https://wa.me/{digits}?text={urllib.parse.quote(text)}"


def df_to_rows(df: pd.DataFrame) -> list[dict]:
    out = []
    for rec in df.to_dict("records"):
        item = str(rec.get("Item") or "").strip()
        if not item or item == "nan":
            continue
        qty = pd.to_numeric(rec.get("Qty"), errors="coerce")
        amt = pd.to_numeric(rec.get("Amount (₹)"), errors="coerce")
        unit, key = rec.get("Unit"), rec.get("_key")
        out.append({"item": item, "qty": 1.0 if pd.isna(qty) else float(qty),
                    "unit": "" if pd.isna(unit) else str(unit),
                    "amount": 0.0 if pd.isna(amt) else float(amt),
                    "key": "" if pd.isna(key) else str(key)})
    return out


def add_text_to_bill(text: str) -> int:
    """Parse text and append to the bill. Safe to call from callbacks or before widgets render."""
    parsed = parse_utterance(text, ss.db["prices"])
    if not parsed.rows:
        return 0
    new = pd.DataFrame([r.as_dict() for r in parsed.rows], columns=BILL_COLS)
    base = ss.current_df if len(ss.current_df) else empty_df()
    ss.bill_df = pd.concat([base, new], ignore_index=True) if len(base) else new
    ss.editor_ver += 1
    if parsed.customer:
        ss.customer_input = parsed.customer
    if parsed.mode:
        ss.mode_input = parsed.mode
    return len(parsed.rows)


def cb_add():
    n = add_text_to_bill(ss.heard_box)
    if n:
        ss.heard_box = ""
        ss.flash = ("success", f"Added {n} item(s) to the bill ✅")
    else:
        ss.flash = ("warning", "I couldn't find items with prices in that text. "
                               "Try: “2 kilo chawal 100 rupaye”.")


def cb_example(text: str):
    ss.heard_box = text


def cb_clear():
    ss.bill_df = empty_df()
    ss.current_df = empty_df()
    ss.editor_ver += 1
    ss.customer_input, ss.mode_input, ss.heard_box = "", "Cash", ""


def cb_demo():
    ss.db = store.demo_state()
    ss.flash = ("success", "Loaded a week of demo data — open the Dashboard & Udhaar tabs 📊")


def cb_wipe():
    ss.db = store.new_state()
    ss.last_saved = None


def speak(api_key: str, msg_fn, lang: str, voice: str):
    """Synthesize msg_fn(lang); fall back to Hindi if that language/voice fails."""
    try:
        return synthesize(api_key, msg_fn(lang), language=lang, voice=voice)
    except GnaniError:
        if lang == "hi-IN":
            raise
        return synthesize(api_key, msg_fn("hi-IN"), language="hi-IN", voice=voice)


# ───────────────────────────── sidebar ─────────────────────────────
STT_LANGS = {
    "Hindi / Hinglish (best for mixed speech)": "hi-IN",
    "Auto-detect any Indian language": "indic-auto",
    "English (India)": "en-IN", "Telugu": "te-IN", "Tamil": "ta-IN", "Kannada": "kn-IN",
    "Bengali": "bn-IN", "Marathi": "mr-IN", "Gujarati": "gu-IN", "Malayalam": "ml-IN", "Punjabi": "pa-IN",
}
with st.sidebar:
    st.markdown("### 🎙️ Awaaz Khata")
    st.text_input("Gnani API key", type="password", key="api_key_input",
                  help="Or set GNANI_API_KEY in env / Streamlit secrets.")
    st.text_input("Shop name", value="Sharma Kirana Store", key="shop_name")

    st.markdown("#### 👂 Listening")
    stt_label = st.selectbox("I will speak in", list(STT_LANGS), index=0)
    model_label = st.selectbox("Speech model", ["Gnani Prisma v3.0 (recommended)", "Gnani Prisma v2.5"])
    quick = st.toggle("Quick mode (add items without review)", value=False)
    boost = st.toggle("Auto-boost quiet audio", value=True)

    st.markdown("#### 🔊 Speaking")
    tts_label = st.selectbox("Read-back language", list(i18n.TTS_LANGS))
    voice = st.selectbox("Voice", ["Nalini", "Karan", "Simran"])

    st.markdown("#### 💾 Data")
    st.button("✨ Load demo data", on_click=cb_demo, use_container_width=True)
    st.download_button("⬇️ Backup (JSON)", store.export_json(ss.db), "awaaz_khata_backup.json",
                       "application/json", use_container_width=True)
    restore = st.file_uploader("Restore backup", type=["json"], key="restore_file")
    if restore is not None and st.button("Restore now", use_container_width=True):
        try:
            ss.db = store.load_json(restore.getvalue().decode("utf-8"))
            st.success("Backup restored.")
        except (ValueError, json.JSONDecodeError) as e:
            st.error(f"Could not restore: {e}")
    st.button("🗑️ Erase all data", on_click=cb_wipe, use_container_width=True)
    st.caption("Your ledger lives only in this browser session. Download a backup to keep it.")

api_key = get_api_key()
stt_lang = STT_LANGS[stt_label]
stt_model = MODEL_V3 if "v3.0" in model_label else MODEL_V25
tts_choice = i18n.TTS_LANGS[tts_label]

# ───────────────────────────── hero ─────────────────────────────
status = ('<span class="pill ok">● API key connected</span>' if api_key
          else '<span class="pill warn">● Add your Gnani API key in the sidebar</span>')
st.markdown(f"""
<div class="tricolor"></div>
<div class="hero">
  <h1>Awaaz Khata<span>आवाज़ खाता</span></h1>
  <p>Bolo, hisaab ban jayega — voice billing &amp; udhaar khata for India's shopkeepers. Speak in your own language, even Hinglish.</p>
  <span class="pill">🎙️ Gnani Prisma · Speech-to-Text</span>
  <span class="pill">🔊 Gnani Timbre v2.5 · Text-to-Speech</span>
  <span class="pill">🇮🇳 10+ Indian languages</span>
  <span class="pill">🗣️ Hinglish ready</span>
  {status}
</div>
""", unsafe_allow_html=True)

tab_bill, tab_udhaar, tab_dash, tab_about = st.tabs(
    ["🎙️ New Bill", "📒 Udhaar Khata", "📊 Dashboard", "💡 About"])

# ═════════════════════════════ NEW BILL ═════════════════════════════
with tab_bill:
    if ss.flash:
        kind, msg = ss.flash
        ss.flash = None
        getattr(st, kind)(msg)

    colL, colR = st.columns([5, 6], gap="large")

    # ---------- left: speak ----------
    with colL:
        with st.container(border=True):
            st.markdown('<div class="sec-title"><span class="step">1</span>Speak your sale</div>',
                        unsafe_allow_html=True)
            try:
                audio = st.audio_input("Tap the mic, speak, tap again to stop", sample_rate=16000)
            except TypeError:  # older Streamlit without sample_rate
                audio = st.audio_input("Tap the mic, speak, tap again to stop")
            with st.expander("…or upload a recording"):
                uploaded = st.file_uploader("Audio file", type=["wav", "mp3", "m4a", "ogg", "flac", "aac"],
                                            label_visibility="collapsed")
            st.markdown(
                '<div class="tip">💡 <b>For best accuracy:</b> speak slowly in a quiet spot, say '
                '<i>item · quantity · price</i>, keep it under 30 seconds. Say '
                '<b>“Ramesh ko udhaar …”</b> for credit, or a rate like '
                '<b>“2 kilo chawal 55 rupaye kilo”</b>.</div>', unsafe_allow_html=True)

        # process new audio before the widgets that depend on it are created
        src = None
        if audio is not None:
            data = audio.getvalue()
            src = ("rec", data, "audio.wav", "audio/wav")
        elif uploaded is not None:
            data = uploaded.getvalue()
            src = ("up", data, uploaded.name, uploaded.type or "audio/wav")
        if src:
            sid = hashlib.md5(src[1]).hexdigest()
            if sid != ss.last_audio_id:
                if not api_key:
                    st.warning("Add your Gnani API key in the sidebar first.")
                else:
                    secs = wav_duration(src[1])
                    payload = normalize_wav(src[1]) if boost else src[1]
                    if secs and secs > 30:
                        st.warning(f"That recording is {secs:.0f}s — Gnani REST handles ~30s. "
                                   "Record shorter clips for best results.")
                    with st.spinner("Gnani is listening… 👂"):
                        try:
                            res = listen(api_key, payload, filename=src[2], mime=src[3],
                                         language_code=stt_lang, model=stt_model, memory=ss.db["prices"])
                            ss.last_audio_id = sid
                            ss.heard_info = res
                            ss.detected_lang = res.get("detected") or ss.detected_lang
                            ss.heard_box = res["text"]
                            if quick and res["text"]:
                                n = add_text_to_bill(res["text"])
                                ss.flash = ("success", f"Heard & added {n} item(s) ✅") if n else \
                                           ("warning", "Heard you, but found no items with prices.")
                                ss.heard_box = "" if n else res["text"]
                                st.rerun()
                        except GnaniError as e:
                            ss.last_audio_id = sid
                            st.error(str(e))

        with st.container(border=True):
            st.markdown('<div class="sec-title"><span class="step">2</span>Check what I heard</div>',
                        unsafe_allow_html=True)
            st.text_area("Transcript — fix any mistake, then add it", key="heard_box", height=96,
                         placeholder="e.g. 2 kilo chawal 100 rupaye, 1 litre doodh 60 rupaye")
            if ss.heard_box.strip():
                pb = parse_utterance(ss.heard_box, ss.db["prices"])
                if pb.rows:
                    bits = " · ".join(f"{r.item.split(' · ')[0]} ×{r.qty}{(' ' + r.unit) if r.unit else ''} "
                                      f"₹{r.amount or 0:g}" for r in pb.rows)
                    extra = ""
                    if pb.customer or pb.mode:
                        extra = f"<br>👤 {pb.customer or '—'} · 💳 {pb.mode or '—'}"
                    st.markdown(f'<div class="understood">✅ <b>I understood:</b> {bits}{extra}</div>',
                                unsafe_allow_html=True)
                else:
                    st.caption("🤔 Nothing parsed yet — add item, quantity and price.")
            st.button("➕ Add to bill", on_click=cb_add, type="primary", use_container_width=True,
                      disabled=not ss.heard_box.strip())
            st.caption("No mic? Try an example:")
            e1, e2, e3 = st.columns(3)
            e1.button("Hinglish", on_click=cb_example, use_container_width=True,
                      args=("2 kilo chawal 100 rupaye, 1 litre doodh 60 rupaye aur 1 packet biscuit 10 rupaye",))
            e2.button("Udhaar", on_click=cb_example, use_container_width=True,
                      args=("Ramesh ko udhaar 2 kilo chawal 55 rupaye kilo, 1 packet chai 100 rupaye",))
            e3.button("Number words", on_click=cb_example, use_container_width=True,
                      args=("do kilo atta dedh sau rupaye aur ek dozen anda 84 rupaye",))
            if ss.heard_info:
                with st.expander("How I listened"):
                    st.dataframe(pd.DataFrame(ss.heard_info["attempts"]), hide_index=True,
                                 use_container_width=True)
                    st.caption("If the first try understood nothing, I automatically retry with another "
                               "language mode / model and keep the best result.")

    # ---------- right: bill ----------
    with colR:
        if ss.last_saved:
            b = ss.last_saved
            txt = store.bill_text(b, ss.shop_name)
            st.markdown(f'<div class="saved">✅ <b>Bill #{b["id"]} saved</b> · ₹{b["total"]:.0f} · {b["mode"]}'
                        f'{(" · " + b["customer"]) if b["customer"] else ""}</div>', unsafe_allow_html=True)
            s1, s2, s3 = st.columns(3)
            s1.link_button("💬 WhatsApp", wa_link(txt, ss.db["phones"].get(b["customer"], "")),
                           use_container_width=True)
            s2.download_button("⬇️ Bill .txt", txt, f"bill_{b['id']}.txt", use_container_width=True)
            if s3.button("Dismiss", use_container_width=True):
                ss.last_saved = None
                st.rerun()

        with st.container(border=True):
            st.markdown('<div class="sec-title"><span class="step">3</span>Your bill</div>',
                        unsafe_allow_html=True)
            c1, c2 = st.columns([3, 4])
            c1.text_input("Customer (optional)", key="customer_input", placeholder="e.g. Ramesh")
            c2.radio("Payment", list(store.MODES), key="mode_input", horizontal=True)

            edited = st.data_editor(
                ss.bill_df, key=f"editor_{ss.editor_ver}", num_rows="dynamic", hide_index=True,
                use_container_width=True, disabled=["Check"],
                column_config={
                    "Item": st.column_config.TextColumn("Item", width="large"),
                    "Qty": st.column_config.NumberColumn("Qty", min_value=0, format="%g", width="small"),
                    "Unit": st.column_config.SelectboxColumn(
                        "Unit", options=["", "kg", "g", "L", "packet", "pc", "dozen", "bottle"], width="small"),
                    "Amount (₹)": st.column_config.NumberColumn("Amount (₹)", min_value=0, format="%g"),
                    "Check": st.column_config.TextColumn("Check", width="small"),
                    "_key": None,
                })
            ss.current_df = edited
            amounts = pd.to_numeric(edited["Amount (₹)"], errors="coerce").fillna(0)
            n_items = int((edited["Item"].fillna("").astype(str).str.strip() != "").sum())
            grand = float(amounts.sum())
            if (edited["Check"].astype(str).str.contains("estimate|add price", na=False)).any():
                st.caption("≈ rows use a remembered/typical price and ⚠️ rows have no price — "
                           "edit the Amount if needed.")
            st.markdown(f'<div class="total-card"><div><div class="lbl">Total</div>'
                        f'<div class="amt">₹{grand:,.0f}</div></div>'
                        f'<div class="meta">{n_items} item(s)<br>{ss.mode_input}'
                        f'{(" · " + ss.customer_input) if ss.customer_input else ""}</div></div>',
                        unsafe_allow_html=True)
            st.write("")
            b1, b2, b3 = st.columns([3, 3, 2])
            save = b1.button("💾 Save bill", type="primary", use_container_width=True, disabled=n_items == 0)
            say = b2.button("🔊 Read total", use_container_width=True, disabled=not (api_key and n_items))
            b3.button("Clear", on_click=cb_clear, use_container_width=True)

            if say:
                lang = i18n.lang_from_detected(ss.detected_lang) if tts_choice == "auto" else tts_choice
                try:
                    ss.tts_audio = speak(api_key, lambda L: i18n.total_message(L, n_items, grand), lang, voice)
                except GnaniError as e:
                    st.error(str(e))
            if ss.tts_audio:
                st.audio(ss.tts_audio, format="audio/wav", autoplay=True)
                ss.tts_audio = None

            if save:
                rows = df_to_rows(edited)
                cust = ss.customer_input.strip()
                if not rows:
                    st.warning("Add at least one item.")
                elif ss.mode_input == "Udhaar" and not cust:
                    st.error("Udhaar needs a customer name — type it above.")
                else:
                    ss.last_saved = store.add_bill(ss.db, rows, cust, ss.mode_input)
                    ss.bill_df = empty_df()
                    ss.current_df = empty_df()
                    ss.editor_ver += 1
                    ss._reset_form = True
                    st.rerun()

# ═════════════════════════════ UDHAAR ═════════════════════════════
with tab_udhaar:
    bal = store.balances(ss.db)
    m1, m2 = st.columns(2)
    m1.metric("Total udhaar pending", f"₹{sum(bal.values()):,.0f}")
    m2.metric("Customers with dues", len(bal))
    if not bal:
        st.info("No pending udhaar. Say “Ramesh ko udhaar …” on a bill, or load demo data from the sidebar.")
    else:
        left, right = st.columns([5, 4], gap="large")
        with left:
            with st.container(border=True):
                st.markdown('<div class="sec-title">Who owes what</div>', unsafe_allow_html=True)
                st.dataframe(pd.DataFrame({"Customer": list(bal), "Pending (₹)": list(bal.values()),
                                           "Phone": [ss.db["phones"].get(c, "") for c in bal]}),
                             hide_index=True, use_container_width=True)
        with right:
            with st.container(border=True):
                st.markdown('<div class="sec-title">Collect / remind</div>', unsafe_allow_html=True)
                who = st.selectbox("Customer", list(bal))
                st.caption(f"Pending: ₹{bal[who]:,.0f}")
                phone = st.text_input("WhatsApp number (10 digits)", value=ss.db["phones"].get(who, ""),
                                      key=f"phone_{who}")
                if phone != ss.db["phones"].get(who, ""):
                    ss.db["phones"][who] = phone
                st.link_button("💬 Send WhatsApp reminder",
                               wa_link(store.reminder_text(ss.shop_name, who, bal[who]), phone),
                               use_container_width=True)
                paid = st.number_input("Payment received (₹)", min_value=0.0, max_value=float(bal[who]),
                                       step=10.0, key=f"pay_{who}")
                if st.button("✅ Record payment", type="primary", use_container_width=True, disabled=paid <= 0):
                    store.add_payment(ss.db, who, paid)
                    ss.flash = ("success", f"Recorded ₹{paid:,.0f} from {who}")
                    st.rerun()

# ═════════════════════════════ DASHBOARD ═════════════════════════════
with tab_dash:
    if not ss.db["bills"]:
        st.info("No bills yet. Save a bill from the first tab — or load a week of demo data to preview this page.")
        st.button("✨ Load demo data", on_click=cb_demo, key="demo_dash")
    else:
        summ = store.today_summary(ss.db, today())
        d1, d2, d3, d4 = st.columns(4)
        d1.metric("Today's sales", f"₹{summ['sales']:,.0f}")
        d2.metric("Bills today", summ["bills"])
        d3.metric("Average bill", f"₹{summ['avg']:,.0f}")
        d4.metric("Udhaar pending", f"₹{summ['pending']:,.0f}")

        g1, g2 = st.columns(2, gap="large")
        with g1:
            with st.container(border=True):
                st.markdown('<div class="sec-title">Last 7 days</div>', unsafe_allow_html=True)
                days = store.daily_totals(ss.db, today(), 7)
                st.bar_chart(pd.DataFrame({"Sales (₹)": [t for _, t in days]},
                                          index=[d.strftime("%d %b") for d, _ in days]), color="#F97316")
        with g2:
            with st.container(border=True):
                st.markdown('<div class="sec-title">Top items by sales</div>', unsafe_allow_html=True)
                tops = store.top_items(ss.db, 6)
                st.bar_chart(pd.DataFrame({"Sales (₹)": [v for _, v in tops]},
                                          index=[k.split(" · ")[0] for k, _ in tops]), color="#138808")

        h1, h2 = st.columns([3, 2], gap="large")
        with h1:
            with st.container(border=True):
                st.markdown('<div class="sec-title">Recent bills</div>', unsafe_allow_html=True)
                recent = list(reversed(ss.db["bills"]))[:12]
                st.dataframe(pd.DataFrame([{
                    "#": b["id"], "When": datetime.fromisoformat(b["ts"]).strftime("%d %b %H:%M"),
                    "Customer": b["customer"] or "—", "Payment": b["mode"], "Items": len(b["items"]),
                    "Total (₹)": b["total"]} for b in recent]), hide_index=True, use_container_width=True)
        with h2:
            with st.container(border=True):
                st.markdown('<div class="sec-title">Payment split</div>', unsafe_allow_html=True)
                split = store.mode_split(ss.db)
                st.bar_chart(pd.DataFrame({"Sales (₹)": list(split.values())}, index=list(split)),
                             color="#2b2f6e")

        a1, a2 = st.columns(2)
        if a1.button("🔊 Read today's summary aloud", use_container_width=True, disabled=not api_key):
            lang = i18n.lang_from_detected(ss.detected_lang) if tts_choice == "auto" else tts_choice
            try:
                audio_bytes = speak(api_key, lambda L: i18n.summary_message(
                    L, summ["sales"], summ["bills"], summ["pending"]), lang if lang in i18n.SUMMARY else "hi-IN", voice)
                st.audio(audio_bytes, format="audio/wav", autoplay=True)
            except GnaniError as e:
                st.error(str(e))
        a2.download_button("⬇️ Download all bills (CSV)",
                           pd.DataFrame(store.bills_rows(ss.db)).to_csv(index=False).encode("utf-8-sig"),
                           "awaaz_khata_bills.csv", "text/csv", use_container_width=True)

# ═════════════════════════════ ABOUT ═════════════════════════════
with tab_about:
    c1, c2 = st.columns(2, gap="large")
    with c1:
        with st.container(border=True):
            st.markdown("### The problem")
            st.write("Millions of kirana shops, tea stalls and vegetable vendors still keep accounts in their "
                     "head or on paper. Typing English on a phone is slow — but speaking is natural, in "
                     "Hindi, Telugu, Tamil… often mixed with English. Udhaar (credit) is the heart of their "
                     "business, and it is the hardest thing to track.")
            st.markdown("### The solution")
            st.write("**Awaaz Khata** turns a spoken sentence into a bill: items, quantities and prices are "
                     "extracted, the customer and payment mode are understood, udhaar balances are tracked, "
                     "reminders go out on WhatsApp, and the total is read back in the shopkeeper's language.")
    with c2:
        with st.container(border=True):
            st.markdown("### Gnani models used")
            st.markdown("- **Gnani Prisma v3.0 / v2.5** — speech-to-text for Indian languages and code-mixed "
                        "Hinglish (`/stt/v3`, with `indic-auto` and digit formatting)\n"
                        "- **Gnani Timbre v2.5** — text-to-speech read-back of totals and daily summaries "
                        "(`/api/v1/tts/inference`) in 9 languages")
            st.markdown("### Built for accuracy")
            st.markdown("- **Smart retry:** if nothing useful is heard, re-listens with another language mode / model\n"
                        "- **Auto-boost** of quiet recordings before they reach the model\n"
                        "- **Item autocorrect** with a bilingual kirana catalogue (chaaval → Rice · चावल)\n"
                        "- Understands **number words** (dedh sau), per-unit **rates**, Devanagari digits\n"
                        "- **Review step:** edit the transcript and the bill before saving")
            st.markdown("### Roadmap")
            st.markdown("Voice-note input from WhatsApp · GST invoices · inventory alerts · "
                        "voice cloning so reminders sound like the shopkeeper (Gnani voice cloning)")
