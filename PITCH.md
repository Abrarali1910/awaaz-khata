# Awaaz Khata · आवाज़ खाता
**Voice billing and udhaar (credit) khata for India's small shopkeepers, built on Gnani Vachana.**

Live app: https://awaaz-khata.streamlit.app/
Code: https://github.com/Abrarali1910/awaaz-khata
Built by: Abrar Ali, Guru Nanak Institutions Technical Campus,Hyderabad

## The problem
Millions of kirana shops, tea stalls and vegetable sellers still keep accounts in their head or on paper. Typing English on a phone is slow and error-prone, and most billing apps are not built for how shopkeepers actually talk: in Hindi or a regional language, mixed with English. The hardest part is **udhaar**, the credit given to regular customers. It is easy to forget, so money is lost and relationships are strained.

## The solution
The shopkeeper just speaks:
> "Ramesh ko udhaar 2 kilo chawal 55 rupaye kilo, 1 packet chai 100 rupaye"

Awaaz Khata understands the items, quantities and prices, recognises the customer and payment mode (cash, UPI or udhaar), saves the bill, updates Ramesh's balance, and reads the total back aloud. A WhatsApp bill or reminder is one tap away.

## How Gnani's models are used
- **Gnani Prisma (speech-to-text):** transcribes Indian-language and code-mixed Hinglish speech, with numbers returned as digits.
- **Gnani Timbre v2.5 (text-to-speech):** reads back totals and daily summaries in 9 Indian languages, so the shopkeeper can check without looking at the screen.

## What makes it accurate and practical
- Smart retry: if nothing useful is heard, it re-listens with another language mode or model and keeps the best result.
- Quiet recordings are boosted before they reach the model.
- A bilingual kirana item catalogue corrects mishearings (chaaval becomes Rice · चावल).
- Understands number words (dedh sau), per-unit rates and Devanagari digits.
- A review step lets the user fix the transcript and bill before saving.

## Features
Voice billing · udhaar tracking with payments and WhatsApp reminders · dashboard (daily sales, top items, payment split) · CSV export and backup · one-click demo data.

## Impact and next steps
It lowers the barrier to digital record-keeping for people who are comfortable speaking but not typing, and helps them recover credit they would otherwise lose. Next: voice notes sent over WhatsApp, GST invoices, stock alerts, and reminders in the shopkeeper's own cloned voice using Gnani voice cloning.