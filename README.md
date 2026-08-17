# Debrup & Jayashree Motilal — SWP Dashboard

A Streamlit dashboard tracking:
- **Motilal Oswal Midcap Fund** — Debrup's and Jayashree's holdings combined into one number
- **Invesco India Midcap Fund**

Pick a month from the dropdown and see every day's fund return (₹ and %, colour-coded green/red), plus that month's total return in ₹ and %.

## Files
```
app.py               → the Streamlit app
requirements.txt     → Python packages needed
data/motilal_nav.csv → daily NAV history, Motilal Oswal Midcap
data/invesco_nav.csv → daily NAV history, Invesco India Midcap
data/units_events.csv→ units held after each purchase/SWP withdrawal, per person
```

The app reads these CSVs, forward-fills units held on every NAV date, and computes
`daily return (₹) = (today's NAV − yesterday's NAV) × units held at start of day`
so SWP withdrawal cashflows don't distort the "did the market go up or down" number.

---

## Part 1 — Put this on GitHub

1. Go to **github.com**, log in (or create a free account).
2. Click the **+** in the top right → **New repository**.
   - Name it e.g. `swp-dashboard`
   - Keep it **Public** (Streamlit Cloud's free tier needs this, unless you pay for private)
   - Don't add a README/gitignore (we already have files) → click **Create repository**.
3. On the new repo's page, click **uploading an existing file** (or **Add file → Upload files**).
4. Drag in these 5 files/folders from this download: `app.py`, `requirements.txt`, and the whole `data` folder (with its 3 CSVs).
5. Scroll down, click **Commit changes**.

That's it — your code is now on GitHub.

*(If you prefer the command line instead of the browser upload):*
```bash
git init
git add .
git commit -m "Initial SWP dashboard"
git branch -M main
git remote add origin https://github.com/<your-username>/swp-dashboard.git
git push -u origin main
```

---

## Part 2 — Deploy it as a website with Streamlit Community Cloud (free)

1. Go to **share.streamlit.io** and sign in with your GitHub account.
2. Click **Create app** → **"Deploy a public app from GitHub"**.
3. Fill in:
   - **Repository**: `<your-username>/swp-dashboard`
   - **Branch**: `main`
   - **Main file path**: `app.py`
4. Click **Deploy**.
5. Wait 1–2 minutes while it installs `pandas` and `streamlit` from `requirements.txt`. Your app will then be live at a URL like:
   `https://swp-dashboard-<random>.streamlit.app`

Bookmark that link — that's your website. Anyone with the link can open it (make the repo private + app "private" in Streamlit settings if you don't want that).

---

## Updating with new NAV data later

Whenever you download fresh NAV history or record a new SWP withdrawal:
1. Replace the relevant CSV in the `data` folder with updated numbers (same 2–3 column format).
2. Commit/push the change on GitHub (or use "Upload files" again on the repo page).
3. Streamlit Cloud auto-redeploys within a minute or two — no other steps needed.

## Running it on your own computer first (optional, to preview)

```bash
pip install -r requirements.txt
streamlit run app.py
```
This opens the dashboard at `http://localhost:8501`.
