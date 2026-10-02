# SplitSnap

SplitSnap reads a receipt photo with Google Gemini, lets you correct the extracted items, and splits the total between people. You can split evenly or assign each item to the people who shared it. The app can optionally email the result and lets you save receipts to a session history that can be downloaded as CSV.

## Requirements

- Windows 10/11 with PowerShell, or macOS/Linux with a terminal
- Python 3.9 or newer
- A Gemini API key from [Google AI Studio](https://aistudio.google.com/)
- Optional: a Gmail account with 2-Step Verification enabled and a Gmail App Password, if you want to email splits

## 1. Open the project folder

Open PowerShell (Windows) or a terminal (macOS/Linux), then move into the folder containing `app.py`:

```powershell
cd path\to\SplitSnap
```

## 2. Create a virtual environment

Windows PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
python3 -m venv venv
source venv/bin/activate
```

If PowerShell blocks activation because of its execution policy, open a PowerShell session where script activation is permitted, then run the activation command again. You can also run the environment's executables directly, for example `venv\Scripts\python.exe -m pip install -r requirements.txt` and `venv\Scripts\streamlit.exe run app.py` on Windows.

## 3. Install the Python packages

With the virtual environment active, run:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## 4. Create the Streamlit secrets file

The Gemini key is required to read receipts. The Gmail settings are optional and only needed for sending email.

Create `.streamlit/secrets.toml` in the project folder. If the `.streamlit` directory does not exist, create it first. Put your own values in the file:

```toml
GEMINI_API_KEY = "your-google-ai-studio-api-key"
GEMINI_MODEL = "gemini-3.5-flash"

# Optional: include both settings to enable email sending.
GMAIL_ADDRESS = "you@gmail.com"
GMAIL_APP_PASSWORD = "your-16-character-gmail-app-password"
```

Use a Gemini model name available for your API key. If you omit `GEMINI_MODEL`, SplitSnap uses `gemini-3.5-flash` by default.

To make a Gmail App Password, enable 2-Step Verification on your Google account and create an App Password in your Google Account security settings. Use the App Password, not your normal Gmail password. If Gmail settings are omitted, you can still copy the split summary from the app.

**Keep secrets private.** Do not paste API keys or passwords into source code, commit `.streamlit/secrets.toml`, or share it publicly. The `.gitignore` file should exclude this file; verify that before pushing the project to a public repository.

## 5. Start SplitSnap

With the virtual environment active and secrets configured, run:

```bash
streamlit run app.py
```

Streamlit prints a local address, usually `http://localhost:8501`. Open that address in your browser. Stop the app with `Ctrl+C` in the terminal.

## 6. Read and review a receipt

1. Choose a JPG, JPEG, PNG, or WEBP photo of a receipt.
2. Select **Read receipt**.
3. Review the merchant, currency, items, quantities, line totals, and bill total. Edit any incorrect values. You can add or remove item rows.
4. Compare the item subtotal with the full bill total. The difference is shown as tax, tip, and fees.

A clear, well-lit image with all receipt text visible generally works best. Receipt images are sent to Google's Gemini API for extraction.

## 7. Split the bill

1. Enter the people sharing the bill, separated by commas. The initial names are `Me, Friend`.
2. Choose **Evenly** to divide the total equally, or **By item** to select who shared each item.
3. For an item split, mark the people sharing each row. Tax, tip, and fees are split proportionally to each person's item subtotal.
4. Review the calculated amounts. The app calculates in cents so the shares sum to the bill total.

## 8. Email or copy the result

The result is displayed as text with a copy button. If Gmail is configured, enter up to five comma-separated email addresses and select **Send email**. Sending is limited to three emails per app session.

## 9. Save and export spending history

1. Select a category and enter the receipt date.
2. Select **Save to history**.
3. Use the sidebar to view the saved receipts and category chart.
4. Select **Download CSV** to keep a copy.

History is kept only in the current browser session. It is not a permanent database and will be lost when the session ends, so download the CSV if you need to keep it.

## Troubleshooting

- **Receipt reading is disabled:** add a non-empty `GEMINI_API_KEY` to `.streamlit/secrets.toml`, save the file, and restart Streamlit.
- **Receipt processing fails:** expand **Technical details** below the error. Check that the API key is valid, that the selected model is available to your account, and that your internet connection works.
- **The image cannot be prepared:** use a valid JPG, JPEG, PNG, or WEBP image and try exporting or taking the photo again.
- **Gemini says the image is not a receipt:** upload a clearer photo showing the complete receipt. Avoid glare, blur, shadows, and cropped edges.
- **Email is unavailable:** add both `GMAIL_ADDRESS` and `GMAIL_APP_PASSWORD`. Email is optional; the on-screen summary can still be copied.
- **Gmail authentication fails:** verify the address, create a new App Password, and confirm 2-Step Verification is enabled. Do not use your normal account password.

## Deploying to Streamlit Community Cloud (optional)

1. Push the project to a GitHub repository. Check that `.streamlit/secrets.toml` is not tracked or committed.
2. In Streamlit Community Cloud, create a new app and select the repository, branch, and `app.py` entry point.
3. In the app's settings, add the required `GEMINI_API_KEY` and optional `GEMINI_MODEL`, `GMAIL_ADDRESS`, and `GMAIL_APP_PASSWORD` as secrets using TOML syntax.
4. Deploy the app and test it with a receipt. Rotate any credentials immediately if they are accidentally exposed.
5. Remember that deployed users can send email through the configured Gmail account. Keep the account dedicated to the app and only configure email if the deployment is intended to send messages.
