# Deploy SplitSnap to Streamlit Community Cloud

This guide covers publishing SplitSnap to GitHub and deploying it with Streamlit Community Cloud.

## What you need

- A GitHub account with access to [the SplitSnap repository](https://github.com/saikiranketha/SplitSnap).
- A [Streamlit Community Cloud](https://share.streamlit.io/) account connected to GitHub.
- A Gemini API key from [Google AI Studio](https://aistudio.google.com/). Receipt reading will not work without it.
- Optionally, a Gmail account with 2-Step Verification and a Gmail App Password, if you want to send split summaries by email.

## 1. Check the project files

The app entry point and dependency file are at the repository root. Keep `app.py`, `prompts.py`, and `requirements.txt` in the repository. Community Cloud installs the packages listed in `requirements.txt`.

The local secrets file belongs at `.streamlit/secrets.toml`. It is excluded by `.gitignore`; do not force-add it or put real credentials in source files, GitHub, or this guide.

## 2. Commit and push to GitHub

Open PowerShell in the SplitSnap project folder and review the changes before staging:

```powershell
git status --short
git diff -- app.py
```

Stage only the project files you intend to publish. For the current app and deployment-guide changes:

```powershell
git add app.py deploy.md
git diff --cached
git diff --cached --check
git commit -m "Document Streamlit Cloud deployment"
git push origin main
```

If you also changed other app files, such as `prompts.py` or `requirements.txt`, review and stage those explicitly. Avoid `git add .` if there is any chance local credentials or unrelated files are present. Confirm the push on the repository's `main` branch before deploying.

## 3. Create the Community Cloud app

1. Sign in at [share.streamlit.io](https://share.streamlit.io/) and authorize access to the GitHub repository if prompted.
2. Select **Create app**, then **Yup, I have an app**.
3. Choose repository `saikiranketha/SplitSnap`, branch `main`, and main file path `app.py`.
4. In **Advanced settings**, use Python 3.12 (or another supported version you have tested) and add the secrets in the next section.
5. Select **Deploy** and wait for the build to finish. Community Cloud reads dependencies from the root `requirements.txt`.

## 4. Configure app secrets

In the deployment's **Advanced settings** or, after deployment, the app's **Settings**, paste TOML-formatted values into the **Secrets** field. Replace the example API key with your own:

```toml
GEMINI_API_KEY = "your-google-ai-studio-api-key"
GEMINI_MODEL = "gemini-3.8-flash"

# Optional: include both settings to enable email sending.
GMAIL_ADDRESS = "you@gmail.com"
GMAIL_APP_PASSWORD = "your-gmail-app-password"
```

`GEMINI_API_KEY` is required for receipt reading. `GEMINI_MODEL` is optional; the app currently defaults to `gemini-3.8-flash` when it is omitted. Use a model that is available to your Google AI Studio account. Email is optional; omit both Gmail settings to disable sending while keeping the on-screen copyable summary.

To create a Gmail App Password, enable 2-Step Verification on the Google account and create an App Password in its security settings. Use the App Password, not the normal Gmail password. Keep credentials private and rotate them immediately if exposed.

## 5. Verify the deployment

Open the deployed `streamlit.app` URL and check that:

1. SplitSnap loads without a build or runtime error.
2. You can upload a clear receipt photo and select **Read receipt**.
3. The extracted receipt can be reviewed and split between people.
4. Saving a receipt and downloading the CSV work. History lasts only for the current app session; it is not a permanent database.
5. If Gmail secrets were configured, test sending only to an address you control.

Receipt images are sent to Google's Gemini API for extraction. Protect your API key and review your provider quotas and usage. Configure email only if you intend the deployed app to send through that Gmail account.

## 6. Publish future changes

After reviewing a change, stage the intended files, commit, and push to the connected branch. For example:

```powershell
git status --short
git add app.py prompts.py
git diff --cached
git diff --cached --check
git commit -m "Describe the change"
git push origin main
```

Community Cloud normally rebuilds the app when new commits are pushed to its configured branch. Update secrets in Community Cloud settings, not in GitHub.

## Troubleshooting

- **Build fails:** Open the app's Community Cloud logs and check the first dependency or Python error. Confirm `requirements.txt` is at the repository root and includes the packages the app imports.
- **Receipt reading is disabled:** Add a non-empty `GEMINI_API_KEY` in the app's secrets and restart or reboot the app.
- **Gemini request fails:** Check the key, account access to the configured model, quota, and the app logs.
- **Email is unavailable:** Add both `GMAIL_ADDRESS` and `GMAIL_APP_PASSWORD` to the app's secrets.
- **Email authentication fails:** Create a fresh Gmail App Password and verify 2-Step Verification is enabled. Never use the normal Gmail password.
- **The deployed version looks old:** Confirm the latest intended commit is on the branch selected by the Cloud app, then check the deployment status and logs.

## Official documentation

- [Deploy an app](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy)
- [App dependencies](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies)
- [Secrets management](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management)