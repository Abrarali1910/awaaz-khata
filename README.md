# 🎙️ Awaaz Khata · आवाज़ खाता

**Voice-first billing & udhaar (credit) khata for India's shopkeepers — powered by Gnani Vachana.**

Speak a sale in your own language (even Hinglish):

> "Ramesh ko udhaar 2 kilo chawal 55 rupaye kilo, 1 packet chai 100 rupaye"

→ items, quantities and prices are extracted · customer **Ramesh** + payment mode **Udhaar** are understood ·
the bill is saved, the udhaar balance updates, a WhatsApp bill/reminder is one tap away, and the total is read back in your language.

## App gone to sleep
If the app shows “gone to sleep” (free hosting), click “Yes, get this app back up!”. It starts in about 5 to 10 seconds.

## Gnani models used
| Model | Used for |
|---|---|
| **Gnani Prisma v3.0 / v2.5** (STT, `POST /stt/v3`, `indic-auto`, `format=transcribe`) | Transcribe Indian-language & code-mixed speech, numbers as digits |
| **Gnani Timbre v2.5** (TTS, `POST /api/v1/tts/inference`) | Read back totals & daily summaries in 9 Indian languages |

## Features
- 🎙️ Voice billing with a review step (edit transcript and bill before saving)
- 📒 **Udhaar khata** — per-customer dues, record payments, WhatsApp reminders
- 📊 Dashboard — today's sales, 7-day trend, top items, payment split, CSV export
- 💬 Share bills on WhatsApp, download bill text
- 🔊 Read-back of totals/daily summary (Hindi, English, Tamil, Telugu, Kannada, Bengali, Marathi, Gujarati, Malayalam)
- ✨ One-click demo data · JSON backup/restore

## Built for accuracy
- **Smart retry** — if nothing useful is heard, re-listens with another language mode / model and keeps the best result
- **Auto-boost** of quiet recordings before sending to STT
- **Item autocorrect** via a bilingual kirana catalogue (chaaval → Rice · चावल)
- Understands number words (*dedh sau*), per-unit rates (*55 rupaye kilo*), Devanagari digits, "1,200"
- Missing price? Uses the last price you charged for that item (flagged ≈ so you can check)

## Run locally
```bash
pip install -r requirements.txt
set GNANI_API_KEY=your-key        # Windows  (use `export` on Mac/Linux)
python -m streamlit run app.py
python run_tests.py               # logic tests, no API key needed
```

## Deploy (free)
Push to GitHub → share.streamlit.io → New app → `app.py` → Advanced settings → Secrets:
```toml
GNANI_API_KEY = "your-key"
```

## Files
`app.py` UI · `gnani_client.py` Gnani STT/TTS · `listen.py` smart-retry listening · `ledger_parser.py` speech→bill ·
`catalog.py` items · `store.py` bills/udhaar/reports · `audio_utils.py` · `i18n.py` · `.streamlit/config.toml` theme
