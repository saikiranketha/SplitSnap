import io
import re
from datetime import date
import smtplib
from email.mime.text import MIMEText

import pandas as pd
import streamlit as st
from google import genai
from google.genai import types
from PIL import Image, ImageOps
from pydantic import BaseModel

from prompts import EXTRACT_PROMPT

st.set_page_config(page_title="SplitSnap", page_icon="🧾")

MODEL_NAME = st.secrets.get("GEMINI_MODEL", "gemini-3.5-flash")
MAX_READS, MAX_SENDS, MAX_RECIPIENTS = 10, 3, 5
CATEGORIES = ["Food", "Groceries", "Transport", "Shopping", "Bills", "Other"]
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")
gemini_ready = isinstance(GEMINI_API_KEY, str) and bool(GEMINI_API_KEY.strip())
email_ready = "GMAIL_ADDRESS" in st.secrets and "GMAIL_APP_PASSWORD" in st.secrets


class Item(BaseModel):
    name: str
    quantity: int
    price: float  # line total


class Receipt(BaseModel):
    is_receipt: bool
    merchant: str
    currency: str
    items: list[Item]
    total: float
    date: str
    category: str


@st.cache_resource
def get_gemini():
    if not gemini_ready:
        raise RuntimeError("GEMINI_API_KEY is missing from .streamlit/secrets.toml.")
    return genai.Client(api_key=GEMINI_API_KEY.strip())


def shrink(file):
    img = ImageOps.exif_transpose(Image.open(file)).convert("RGB")
    img.thumbnail((1600, 1600))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=85)
    return buf.getvalue()


def read_receipt(img_bytes):
    try:
        resp = get_gemini().models.generate_content(
            model=MODEL_NAME,
            contents=[types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"), EXTRACT_PROMPT],
            config=types.GenerateContentConfig(
                response_mime_type="application/json", response_schema=Receipt
            ),
        )
        return resp.parsed, None
    except Exception as error:
        return None, str(error)


def allocate(total, weights):
    """Split integer cents by weights; result always sums exactly to total."""
    s = sum(weights)
    if s == 0:
        weights, s = [1] * len(weights), len(weights)
    base = [total * w // s for w in weights]
    leftover = total - sum(base)
    order = sorted(range(len(weights)), key=lambda i: (total * weights[i]) % s, reverse=True)
    for i in order[:leftover]:
        base[i] += 1
    return base


def build_summary(merchant, cur, total_c, people, cents, mode):
    head = f"🧾 {merchant} - total {cur}{total_c / 100:.2f} (split {mode.lower()})"
    rows = [f"{p}: {cur}{c / 100:.2f}" for p, c in zip(people, cents)]
    return head + "\n" + "\n".join(rows)


def safe_cell(value):
    """Stop spreadsheet apps from running a cell that starts with = + - @ as a formula."""
    value = str(value)
    return "'" + value if value.startswith(("=", "+", "-", "@")) else value


def send_email(recipients, merchant, body):
    sender = st.secrets["GMAIL_ADDRESS"]
    subject = " ".join(merchant.split())[:80] or "Receipt"  # no newlines in headers
    message = MIMEText(body, _charset="utf-8")
    message["Subject"] = f"Bill split: {subject}"
    message["From"] = sender
    message["To"] = ", ".join(recipients)
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as server:
            server.login(sender, st.secrets["GMAIL_APP_PASSWORD"])
            server.send_message(message)
        return True, ""
    except smtplib.SMTPAuthenticationError:
        return False, "Gmail login failed. Check the App Password and that 2-Step Verification is on."
    except Exception as error:
        return False, str(error)


def render_history():
    with st.sidebar:
        st.header("📒 Spending history")
        rows = st.session_state.history
        if not rows:
            st.caption("Nothing saved yet. Save a receipt to start tracking.")
            return
        df = pd.DataFrame(rows)
        st.dataframe(df, hide_index=True)
        if df["currency"].nunique() == 1:
            st.bar_chart(df.groupby("category")["total"].sum())
        else:
            st.caption("Mixed currencies, so the chart is hidden.")
        st.download_button("⬇️ Download CSV", df.to_csv(index=False), "splitsnap_history.csv", "text/csv")
        st.caption("History lives in this browser session. Download the CSV to keep it.")


st.session_state.setdefault("reads", 0)
st.session_state.setdefault("history", [])
st.session_state.setdefault("saved_reads", [])
st.session_state.setdefault("sends", 0)
st.session_state.setdefault("receipt", None)

st.title("🧾 SplitSnap")
st.caption("Snap the bill. Fix any misreads. Split it. Email everyone.")
if not gemini_ready:
    st.warning("Receipt reading is disabled. Add your Gemini API key to `.streamlit/secrets.toml` and restart the app.")
    st.code('GEMINI_API_KEY = "your-gemini-api-key"', language="toml")

photo = st.file_uploader("Photo of the receipt", type=["jpg", "jpeg", "png", "webp"], accept_multiple_files=False, help="Take a clear photo of the receipt, with all items visible.")
if photo and st.button("Read receipt", type="primary", disabled=not gemini_ready):
    if st.session_state.reads >= MAX_READS:
        st.error("Read limit reached for this session. Refresh to start over.")
    else:
        try:
            with st.spinner("Reading the bill..."):
                receipt, err = read_receipt(shrink(photo))
        except Exception as error:
            receipt, err = None, f"Image preparation failed: {error}"
        if err:
            st.error("Receipt processing failed. Check the technical details for the cause.")
            with st.expander("Technical details"):
                st.code(err)
        elif receipt is None:
            st.error("Gemini returned no receipt data. Try again or check that the configured model is available.")
        elif not receipt.is_receipt or not receipt.items:
            st.warning("That doesn't look like a receipt. Try another photo.")
        else:
            st.session_state.reads += 1
            st.session_state.receipt = receipt

receipt = st.session_state.receipt
if receipt is None:
    st.stop()

n = st.session_state.reads  # keys change per read, so widgets reset for a new receipt

st.subheader("1. Check what was read")
merchant = st.text_input("Merchant", receipt.merchant, key=f"m_{n}")
cur = st.text_input("Currency", receipt.currency, key=f"c_{n}")
items_df = pd.DataFrame(
    [{"name": i.name, "quantity": i.quantity, "price": i.price} for i in receipt.items]
)
items = st.data_editor(
    items_df,
    num_rows="dynamic",
    hide_index=True,
    key=f"items_{n}",
    column_config={"price": st.column_config.NumberColumn("Line total", format="%.2f")},
)
items = items.dropna(subset=["name"]).fillna(0).reset_index(drop=True)
total = st.number_input(
    "Bill total (including tax / tip)", min_value=0.0, value=float(receipt.total), step=0.01, key=f"t_{n}"
)

item_cents = [int(round(p * 100)) for p in items["price"]]
total_c = int(round(total * 100))
extra_c = total_c - sum(item_cents)
st.caption(f"Items add up to {cur}{sum(item_cents) / 100:.2f}. Tax, tip & fees: {cur}{extra_c / 100:.2f}.")
if extra_c < 0:
    st.warning("Total is lower than the items. That's fine for a discount, but check for a misread.")

st.subheader("2. Split it")
people = list(dict.fromkeys(p.strip() for p in st.text_input("Who's splitting? (comma-separated)", "Me, Friend").split(",") if p.strip()))
if not people:
    render_history()
    st.stop()
mode = st.radio("Split", ["Evenly", "By item"], horizontal=True)

if mode == "Evenly":
    cents = allocate(total_c, [1] * len(people))
else:
    st.caption("Tick who shared each item. Tax and tip are split in proportion to what each person ordered.")
    assign = pd.DataFrame({"Item": items["name"]})
    for p in people:
        assign[p] = True
    edited = st.data_editor(
        assign, disabled=["Item"], hide_index=True, key=f"a_{n}_{'|'.join(people)}_{len(items)}"
    )
    shares = [0] * len(people)
    for i, ic in enumerate(item_cents):
        weights = [1 if edited.loc[i, p] else 0 for p in people]
        shares = [s + a for s, a in zip(shares, allocate(ic, weights))]
    cents = [s + e for s, e in zip(shares, allocate(extra_c, shares))]

st.subheader("3. Result")
for p, c in zip(people, cents):
    st.metric(p, f"{cur}{c / 100:.2f}")

summary = build_summary(merchant, cur, total_c, people, cents, mode)
st.code(summary, language=None)  # built-in copy button

if not email_ready:
    st.info("Email isn't configured, so copy the summary above. Add GMAIL_ADDRESS and GMAIL_APP_PASSWORD to enable sending.")
else:
    raw = st.text_input(
        f"Email the split to (up to {MAX_RECIPIENTS}, comma-separated)", placeholder="friend@example.com, me@example.com"
    )
    if st.button("📧 Send email"):
        recipients = list(dict.fromkeys(a.strip() for a in raw.split(",") if a.strip()))
        if not recipients or not all(EMAIL_RE.match(a) for a in recipients):
            st.warning("Enter valid email addresses, separated by commas.")
        elif len(recipients) > MAX_RECIPIENTS:
            st.warning(f"Up to {MAX_RECIPIENTS} recipients at a time.")
        elif st.session_state.sends >= MAX_SENDS:
            st.error("Send limit reached for this session.")
        else:
            ok, info = send_email(recipients, merchant, summary)
            if ok:
                st.session_state.sends += 1
                st.success("Sent! Check the inbox (and spam) 📬")
            else:
                st.error("Couldn't send the email.")
                st.caption(info)

st.subheader("4. Save to history")
default_cat = receipt.category if receipt.category in CATEGORIES else "Other"
category = st.selectbox("Category", CATEGORIES, index=CATEGORIES.index(default_cat), key=f"cat_{n}")
when = st.text_input("Date (YYYY-MM-DD)", receipt.date or date.today().isoformat(), key=f"d_{n}")
if n in st.session_state.saved_reads:
    st.success("Saved to history ✅")
elif st.button("💾 Save to history"):
    st.session_state.history.append(
        {
            "date": safe_cell(when.strip()),
            "merchant": safe_cell(merchant.strip()),
            "category": category,
            "currency": safe_cell(cur.strip()),
            "total": total,
            "people": len(people),
        }
    )
    st.session_state.saved_reads.append(n)
    st.rerun()

render_history()
