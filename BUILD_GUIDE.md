# Step-by-Step Build Guide: SplitSnap

SplitSnap is a Streamlit app that turns a photo of a bill into a fair split in about ten seconds. You photograph a receipt, Gemini reads the line items and total as **structured data**, you fix any misreads, split the bill evenly or by item, and email the breakdown to your friends. Every receipt you save also builds a small spending history you can download as a CSV.

Built with Gemini (vision + structured output) and Gmail (SMTP). No OpenCV, no OCR library, no model training.

**What you will learn**
- Getting structured data (amounts, totals) out of a photo, not just a description
- Why money math belongs in Python, not in the AI
- Turning an everyday chore into a quick automation

## What you'll need
- Python 3.9 or newer, and basic comfort with Python
- A free Google AI Studio account (Gemini API key)
- A Gmail account with 2-Step Verification on (for the App Password)

## Project structure
```
splitsnap/
├── app.py                        # the app
├── prompts.py                    # instructions for reading receipts
├── requirements.txt
├── .gitignore                    # keeps secrets.toml out of GitHub
└── .streamlit/
    └── secrets.toml.example      # copy to secrets.toml and fill in
```

## Step 1: Environment and keys
1. Make a folder, then a virtual environment: `python -m venv venv`
2. Activate it. macOS/Linux: `source venv/bin/activate`. Windows PowerShell: `.\venv\Scripts\Activate.ps1`
3. Install dependencies: `pip install -r requirements.txt`
4. Get a Gemini key at aistudio.google.com (Get API key).
5. On the sending Gmail account, turn on 2-Step Verification, then create an App Password at myaccount.google.com/apppasswords. Use that 16-character password in the app, never your real one.
6. Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and fill it in. Never commit the real file.

## Step 2: requirements.txt
```
streamlit>=1.43
google-genai
pandas
pydantic
Pillow
```

## Step 3: prompts.py, teaching Gemini to read receipts
```python
EXTRACT_PROMPT = """You read photos of receipts and restaurant bills.
Extract every purchased line item: name, quantity, and the LINE TOTAL price
(quantity x unit price, as printed). Do not include tax, tip, service charge
or discounts as items. Set `total` to the final amount payable as printed.
`currency` is the symbol or code (e.g. Rs, INR, $). `merchant` is the shop name.
`date` is the receipt date as YYYY-MM-DD, or an empty string if not visible.
`category` is one of: Food, Groceries, Transport, Shopping, Bills, Other.
If the image is not a receipt or bill, set is_receipt to false and items to [].
Never guess unreadable numbers; use 0 for them."""
```
Telling the model to use 0 instead of guessing, and to flag non-receipts, is what keeps bad photos from producing confident nonsense.

## Step 4: Structured output, the heart of the project
Instead of asking Gemini to describe the receipt, we give it a schema and get JSON back.
```python
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
```
- `response_schema=Receipt` forces the reply into that shape, and `resp.parsed` hands you a real `Receipt` object.
- This is a single call, not a chat. A receipt has no follow-up conversation.
- Before sending, `shrink()` rotates the photo using its EXIF data and resizes it to 1600px. Smaller images are faster and cheaper.

Cache the client once, as in MacroSnap:
```python
@st.cache_resource
def get_gemini():
    return genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
```
`cache_resource` creates it once per server process and shares it across users.

## Step 5: Upload, read, and fix
```python
photo = st.file_uploader("Photo of the receipt", type=["jpg", "jpeg", "png"])
if photo and st.button("Read receipt", type="primary"):
    ...
    receipt, err = read_receipt(shrink(photo))
```
The result goes into `st.session_state.receipt`, and everything below the button only shows once a receipt exists (`st.stop()` otherwise).

AI misreads happen, so the items appear in an editable table:
```python
items = st.data_editor(items_df, num_rows="dynamic", hide_index=True, key=f"items_{n}")
```
`num_rows="dynamic"` lets users add or delete rows. Widget keys include the read counter `n`, so uploading a new receipt resets every field. A caption shows `total - sum(items)` as "tax, tip and fees", which also exposes misreads instantly.

## Step 6: Splitting, with money math in Python
Never let an AI add up money. We work in integer cents and use a "largest remainder" rule so shares always add up exactly:
```python
def allocate(total, weights):
    s = sum(weights)
    if s == 0:
        weights, s = [1] * len(weights), len(weights)
    base = [total * w // s for w in weights]
    leftover = total - sum(base)
    order = sorted(range(len(weights)), key=lambda i: (total * weights[i]) % s, reverse=True)
    for i in order[:leftover]:
        base[i] += 1
    return base
```
`allocate(10000, [1, 1, 1])` gives `[3334, 3333, 3333]`, so ₹100.00 across three people never loses a paisa.

- **Evenly:** `allocate(total_cents, [1] * len(people))`
- **By item:** a checkbox grid (`st.data_editor` with one column per person) says who shared each item. Each item is allocated among its sharers, then tax and tip are allocated in proportion to each person's item subtotal.

Try it live: split a bill where one person only had a drink.

## Step 7: Emailing the breakdown
```python
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
```
- The summary is built in plain Python (`build_summary`), not by Gemini, so the numbers are exact and there is no hidden AI call.
- Up to 5 comma-separated recipients, each checked with a regex. A session cap of 3 sends stops a public deployment from becoming a spam relay.
- If Gmail secrets are missing, the app still works: the summary has a built-in copy button.

## Step 8: Spending history and CSV
After each receipt, the user picks a category and a date and clicks **Save to history**. Rows live in `st.session_state.history`, and the sidebar shows a table, a bar chart by category, and a download button:
```python
st.download_button("⬇️ Download CSV", df.to_csv(index=False), "splitsnap_history.csv", "text/csv")
```
Two decisions to point out to students:
- **Why not write to a CSV on the server?** On Streamlit Community Cloud the disk is temporary and shared. One file would mix everyone's receipts together and vanish on restart. A session list plus a download keeps each person's data their own.
- **CSV injection.** A merchant name like `=HYPERLINK(...)` can run as a formula when the CSV is opened in Excel. `safe_cell()` puts a `'` in front of any text starting with `=`, `+`, `-` or `@`.

## Full code
The complete, working `app.py` is in this project folder. Read it top to bottom after finishing the steps.

## Secrets template: `.streamlit/secrets.toml.example`
```toml
GEMINI_API_KEY = "your-gemini-api-key-here"
GEMINI_MODEL = "gemini-2.5-flash"   # check this name in AI Studio

# Optional: without these the app works as a copy-paste splitter.
GMAIL_ADDRESS = "you@gmail.com"
GMAIL_APP_PASSWORD = "your-16-char-app-password"
```

## Running it locally
```
streamlit run app.py
```
It opens at http://localhost:8501. Upload a receipt, click **Read receipt**, fix anything wrong, pick a split, and send yourself a test email. Check the spam folder.

## Deploying: Streamlit Community Cloud
1. Push to GitHub. Do not commit `.streamlit/secrets.toml`.
2. At share.streamlit.io, click **New app**, then choose the repo, branch, and `app.py`.
3. Paste your secrets into **Settings → Secrets**.
4. Deploy. Remember that anyone with the link can trigger emails from your Gmail, so keep the send limits, or leave the Gmail secrets out of a public demo.

## Gotchas to flag live
- **Test with bad photos:** a dim receipt, a crumpled one, a handwritten bill, and a non-receipt.
- **Currency and date formats vary by country.** Always show the user what was read and let them edit it.
- **Privacy:** receipt photos go to Google's API, and the summary goes through Gmail.
- **Model names get retired.** That is why `GEMINI_MODEL` lives in secrets.

## Stretch ideas
- A `st.camera_input` tab for taking the photo inside the app.
- Per-person emails, each showing only that person's amount.
- A UPI or payment link added to the email.
- Monthly totals by category with `st.line_chart`.
