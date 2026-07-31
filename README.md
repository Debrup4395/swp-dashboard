# SWP & Investment Dashboard

A Streamlit web app that visualizes **Investment (purchase)** and **SWP
(Systematic Withdrawal Plan)** data from a Motilal Oswal-style Excel
workbook — one sheet per investor.

## Features
- Upload your own `.xlsx` workbook, or use the bundled sample
- Auto-detects every investor sheet in the workbook
- Key metrics: total invested, total withdrawn, current balance,
  remaining units, net capital gain/loss
- Interactive charts: balance over time, capital gain/loss per
  withdrawal, investment amounts, NAV trend, remaining units
- Downloadable cleaned CSVs for both Investment and SWP data

## Project structure
```
swp_app/
├── app.py                          # Streamlit application
├── requirements.txt                # Python dependencies
├── data/
│   └── sample_swp_workbook.xlsx    # Bundled sample data
└── README.md
```

## 1. Run locally

```bash
# clone your repo
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>

# (recommended) create a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# install dependencies
pip install -r requirements.txt

# run the app
streamlit run app.py
```
The app opens at `http://localhost:8501`.

## 2. Push to GitHub

```bash
git init
git add .
git commit -m "Initial commit: SWP dashboard"
git branch -M main
git remote add origin https://github.com/<your-username>/<your-repo>.git
git push -u origin main
```

## 3. Deploy for free on Streamlit Community Cloud
1. Go to https://share.streamlit.io and sign in with GitHub.
2. Click **New app**, pick your repo/branch, and set the main file
   path to `app.py`.
3. Click **Deploy** — Streamlit Cloud installs `requirements.txt`
   automatically and gives you a public URL.

## Notes on your data
- Excel workbook structure expected per sheet:
  - Columns A–D (rows from row 4 onward): `Date, Units, NAV,
    Investement` — your purchase/SIP history.
  - Columns I–O (rows from row 4 onward): `Date, Units, Remaining
    Units, NAV, Cashflow, Capital Gain/Loss, Balance` — your SWP
    withdrawal history.
- Any extra sheets that are blank (like `Sheet3`) are ignored
  automatically.
- To use your own data instead of the sample, either replace
  `data/sample_swp_workbook.xlsx` before deploying, or simply upload
  your file from the app's sidebar at runtime (no code change or
  redeploy needed).

## Disclaimer
This tool is for personal portfolio tracking/visualization only and
is not financial advice.
