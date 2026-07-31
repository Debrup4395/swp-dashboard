"""
Motilal Oswal SWP Dashboard
---------------------------
A Streamlit web app to visualize Investment (purchase / SIP) and
SWP (Systematic Withdrawal Plan) data stored in an Excel workbook.

Expected workbook layout (one sheet per investor):
    Row 1 : Section labels ("INVESTMENT" in col B, "SWP" in col J roughly)
    Row 3 : Column headers
        Investment block -> Date | Units | NAV | Investement
        SWP block        -> Date | Units | Remaining Units | NAV | Cashflow | Capital Gain/Loss | Balance
    Row 4+: Data rows

The app auto-detects every sheet in the workbook (except helper/blank
sheets) and treats each one as a separate investor / portfolio.
"""

import io
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# --------------------------------------------------------------------------
# Page config
# --------------------------------------------------------------------------
st.set_page_config(
    page_title="SWP Dashboard",
    page_icon="📈",
    layout="wide",
)

DEFAULT_FILE_PATH = "data/sample_swp_workbook.xlsx"

INVESTMENT_COLS = ["Date", "Units", "NAV", "Investement"]
SWP_RENAME = {
    "Date.1": "Date",
    "Units.1": "Units",
    "Remaining Units": "Remaining Units",
    "NAV.1": "NAV",
    "Cashflow": "Cashflow",
    "Capital Gain/Loss": "Capital Gain/Loss",
    "Balance": "Balance",
}


# --------------------------------------------------------------------------
# Data loading & parsing
# --------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def get_sheet_names(file_bytes: bytes) -> list[str]:
    xl = pd.ExcelFile(io.BytesIO(file_bytes))
    # Ignore obviously empty helper sheets (e.g. "Sheet3")
    valid = []
    for name in xl.sheet_names:
        df = pd.read_excel(xl, sheet_name=name, header=None, nrows=3)
        if df.dropna(how="all").empty:
            continue
        valid.append(name)
    return valid


@st.cache_data(show_spinner=False)
def parse_sheet(file_bytes: bytes, sheet_name: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (investment_df, swp_df) cleaned and typed for one investor sheet."""
    raw = pd.read_excel(io.BytesIO(file_bytes), sheet_name=sheet_name, header=2)

    # ---- Investment block (first 4 columns) ----
    inv_cols = [c for c in raw.columns if c in INVESTMENT_COLS]
    inv = raw[inv_cols].copy()
    inv["Date"] = pd.to_datetime(inv["Date"], errors="coerce")
    inv["Units"] = pd.to_numeric(inv["Units"], errors="coerce")
    inv["NAV"] = pd.to_numeric(inv["NAV"], errors="coerce")
    inv["Investement"] = pd.to_numeric(inv["Investement"], errors="coerce")
    inv = inv.dropna(subset=["Date", "Units"]).sort_values("Date").reset_index(drop=True)
    inv = inv.rename(columns={"Investement": "Investment Amount"})

    # ---- SWP block (the ".1" suffixed / uniquely named columns) ----
    swp_cols = [c for c in SWP_RENAME if c in raw.columns]
    swp = raw[swp_cols].rename(columns=SWP_RENAME).copy()
    swp["Date"] = pd.to_datetime(swp["Date"], errors="coerce")
    for col in ["Units", "Remaining Units", "NAV", "Cashflow", "Capital Gain/Loss", "Balance"]:
        if col in swp.columns:
            swp[col] = pd.to_numeric(swp[col], errors="coerce")
    swp = swp.dropna(subset=["Date"]).sort_values("Date").reset_index(drop=True)

    return inv, swp


def format_inr(value: float) -> str:
    if pd.isna(value):
        return "-"
    return f"₹{value:,.2f}"


# --------------------------------------------------------------------------
# Sidebar - data source selection
# --------------------------------------------------------------------------
st.sidebar.title("📂 Data Source")

uploaded_file = st.sidebar.file_uploader(
    "Upload your SWP workbook (.xlsx)", type=["xlsx"]
)

if uploaded_file is not None:
    file_bytes = uploaded_file.read()
    source_label = uploaded_file.name
else:
    with open(DEFAULT_FILE_PATH, "rb") as f:
        file_bytes = f.read()
    source_label = "Sample workbook (bundled)"

st.sidebar.caption(f"Using: **{source_label}**")

sheet_names = get_sheet_names(file_bytes)

if not sheet_names:
    st.error("No usable sheets found in this workbook.")
    st.stop()

investor = st.sidebar.selectbox("Select investor / sheet", sheet_names)

inv_df, swp_df = parse_sheet(file_bytes, investor)

# --------------------------------------------------------------------------
# Header
# --------------------------------------------------------------------------
st.title("📈 SWP & Investment Dashboard")
st.caption(f"Investor: **{investor}**")

# --------------------------------------------------------------------------
# Key metrics
# --------------------------------------------------------------------------
total_invested = inv_df["Investment Amount"].sum()
total_units_bought = inv_df["Units"].sum()
avg_buy_nav = (
    (inv_df["Investment Amount"].sum() / inv_df["Units"].sum())
    if inv_df["Units"].sum()
    else float("nan")
)

total_withdrawn = swp_df["Cashflow"].sum() if "Cashflow" in swp_df else float("nan")
current_balance = swp_df["Balance"].dropna().iloc[-1] if not swp_df["Balance"].dropna().empty else float("nan")
current_units = (
    swp_df["Remaining Units"].dropna().iloc[-1]
    if "Remaining Units" in swp_df and not swp_df["Remaining Units"].dropna().empty
    else float("nan")
)
total_gain_loss = swp_df["Capital Gain/Loss"].sum() if "Capital Gain/Loss" in swp_df else float("nan")

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total Invested", format_inr(total_invested))
c2.metric("Total Withdrawn (SWP)", format_inr(total_withdrawn))
c3.metric("Current Balance", format_inr(current_balance))
c4.metric("Remaining Units", f"{current_units:,.2f}" if pd.notna(current_units) else "-")
c5.metric(
    "Net Capital Gain/Loss",
    format_inr(total_gain_loss),
    delta=None if pd.isna(total_gain_loss) else round(total_gain_loss, 2),
)

st.divider()

# --------------------------------------------------------------------------
# Tabs
# --------------------------------------------------------------------------
tab_overview, tab_investment, tab_swp, tab_data = st.tabs(
    ["📊 Overview", "💰 Investment", "🔻 SWP Withdrawals", "🗂️ Raw Data"]
)

# ---- Overview tab: balance trend + cashflow ----
with tab_overview:
    col1, col2 = st.columns(2)

    with col1:
        if not swp_df.empty:
            fig = px.line(
                swp_df,
                x="Date",
                y="Balance",
                markers=True,
                title="Portfolio Balance Over Time (SWP phase)",
            )
            fig.update_layout(yaxis_title="Balance (₹)", xaxis_title="Date")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No SWP data available for this sheet.")

    with col2:
        if not swp_df.empty and "Capital Gain/Loss" in swp_df:
            colors = ["#2ecc71" if v >= 0 else "#e74c3c" for v in swp_df["Capital Gain/Loss"]]
            fig = go.Figure(
                go.Bar(
                    x=swp_df["Date"],
                    y=swp_df["Capital Gain/Loss"],
                    marker_color=colors,
                )
            )
            fig.update_layout(
                title="Capital Gain / Loss per Withdrawal",
                xaxis_title="Date",
                yaxis_title="Capital Gain/Loss (₹)",
            )
            st.plotly_chart(fig, use_container_width=True)

    if not inv_df.empty:
        fig = px.bar(
            inv_df,
            x="Date",
            y="Investment Amount",
            title="Investment / Purchase Amounts Over Time",
        )
        fig.update_layout(yaxis_title="Amount (₹)", xaxis_title="Date")
        st.plotly_chart(fig, use_container_width=True)

# ---- Investment tab ----
with tab_investment:
    st.subheader("Investment (Purchase) Transactions")
    if inv_df.empty:
        st.info("No investment data found.")
    else:
        st.dataframe(
            inv_df.style.format(
                {
                    "Units": "{:,.4f}",
                    "NAV": "{:,.2f}",
                    "Investment Amount": "₹{:,.2f}",
                    "Date": lambda d: d.strftime("%d-%b-%Y") if pd.notna(d) else "",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

        m1, m2, m3 = st.columns(3)
        m1.metric("Total Invested", format_inr(total_invested))
        m2.metric("Total Units Purchased", f"{total_units_bought:,.4f}")
        m3.metric("Average Buy NAV", f"₹{avg_buy_nav:,.2f}" if pd.notna(avg_buy_nav) else "-")

        fig = px.line(inv_df, x="Date", y="NAV", markers=True, title="NAV at Purchase")
        st.plotly_chart(fig, use_container_width=True)

# ---- SWP tab ----
with tab_swp:
    st.subheader("SWP (Systematic Withdrawal Plan) Transactions")
    if swp_df.empty:
        st.info("No SWP data found.")
    else:
        st.dataframe(
            swp_df.style.format(
                {
                    "Units": "{:,.4f}",
                    "Remaining Units": "{:,.4f}",
                    "NAV": "{:,.2f}",
                    "Cashflow": "₹{:,.2f}",
                    "Capital Gain/Loss": "₹{:,.2f}",
                    "Balance": "₹{:,.2f}",
                    "Date": lambda d: d.strftime("%d-%b-%Y") if pd.notna(d) else "",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

        fig = px.area(
            swp_df, x="Date", y="Remaining Units", title="Remaining Units Over Time"
        )
        st.plotly_chart(fig, use_container_width=True)

        fig2 = px.bar(swp_df, x="Date", y="Cashflow", title="SWP Withdrawal (Cashflow) per Period")
        st.plotly_chart(fig2, use_container_width=True)

# ---- Raw data tab ----
with tab_data:
    st.subheader("Download parsed data")
    csv_inv = inv_df.to_csv(index=False).encode("utf-8")
    csv_swp = swp_df.to_csv(index=False).encode("utf-8")
    d1, d2 = st.columns(2)
    d1.download_button(
        "⬇️ Download Investment CSV", csv_inv, f"{investor}_investment.csv", "text/csv"
    )
    d2.download_button(
        "⬇️ Download SWP CSV", csv_swp, f"{investor}_swp.csv", "text/csv"
    )
    st.write("Investment (raw parsed):")
    st.dataframe(inv_df, use_container_width=True)
    st.write("SWP (raw parsed):")
    st.dataframe(swp_df, use_container_width=True)

st.sidebar.divider()
st.sidebar.caption(f"App loaded at {datetime.now().strftime('%d-%b-%Y %H:%M')}")
