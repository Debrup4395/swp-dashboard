import streamlit as st
import pandas as pd
import calendar
from pathlib import Path

st.set_page_config(page_title="Motilal & Invesco SWP Dashboard", page_icon="📈", layout="wide")

DATA_DIR = Path(__file__).parent

# ----------------------------- Data loading -----------------------------

@st.cache_data
def load_nav(filename):
    df = pd.read_csv(DATA_DIR / filename, parse_dates=["date"])
    return df.sort_values("date").reset_index(drop=True)

@st.cache_data
def load_units_events():
    df = pd.read_csv(DATA_DIR / "units_events.csv", parse_dates=["date"])
    return df

def units_daily_series(nav_dates, events_df, holder):
    """Forward-fill units held on each NAV date for a given holder."""
    ev = events_df[events_df["holder"] == holder].sort_values("date")
    s = pd.Series(index=nav_dates, dtype=float)
    for d, u in zip(ev["date"], ev["units_remaining"]):
        s.loc[s.index >= d] = u
    return s.ffill()

def build_fund_df(nav_df, events_df, holders, fund_label):
    dates = nav_df["date"]
    total_units = 0.0
    for h in holders:
        total_units = total_units + units_daily_series(dates, events_df, h).values
    df = pd.DataFrame({
        "date": dates.values,
        "nav": nav_df["nav"].values,
        "units": total_units,
    })
    df["value"] = df["nav"] * df["units"]
    # Day-over-day change based on units held at START of the day (previous day's units)
    df["prev_units"] = df["units"].shift(1)
    df["prev_nav"] = df["nav"].shift(1)
    df["change_rs"] = (df["nav"] - df["prev_nav"]) * df["prev_units"]
    df["change_pct"] = (df["nav"] / df["prev_nav"] - 1) * 100
    df["fund"] = fund_label
    return df

motilal_nav = load_nav("motilal_nav.csv")
invesco_nav = load_nav("invesco_nav.csv")
events = load_units_events()

motilal_df = build_fund_df(motilal_nav, events, ["Debrup", "Jayashree"], "Motilal Oswal Midcap (Combined)")
invesco_df = build_fund_df(invesco_nav, events, ["Invesco"], "Invesco India Midcap")

# ----------------------------- Header -----------------------------

st.title("📈 Debrup & Jayashree Motilal — SWP Investment Dashboard")
st.caption("Combined Motilal Oswal Midcap holdings (Debrup + Jayashree) and Invesco India Midcap, tracked from daily NAV.")

col1, col2, col3 = st.columns(3)
latest_motilal = motilal_df.iloc[-1]
latest_invesco = invesco_df.iloc[-1]
col1.metric("Motilal Oswal Midcap — Current Value", f"₹{latest_motilal['value']:,.0f}", f"{latest_motilal['units']:,.2f} units")
col2.metric("Invesco Midcap — Current Value", f"₹{latest_invesco['value']:,.0f}", f"{latest_invesco['units']:,.2f} units")
col3.metric("Combined Portfolio Value", f"₹{latest_motilal['value'] + latest_invesco['value']:,.0f}")

st.divider()

# ----------------------------- Period (Month/Week) dropdown dashboard -----------------------------

def period_options(df, freq):
    """freq: 'M' for calendar month, 'W' for week (Mon-Sun)."""
    periods = sorted(df["date"].dt.to_period(freq).unique())
    if freq == "M":
        return {f"{calendar.month_name[m.month]} {m.year}": m for m in periods}
    else:
        opts = {}
        for p in periods:
            start = p.start_time.strftime("%d-%b-%Y")
            end = p.end_time.strftime("%d-%b-%Y")
            opts[f"{start} to {end}"] = p
        return opts

def style_returns(val):
    if pd.isna(val):
        return ""
    color = "#1a7f37" if val >= 0 else "#d1242f"
    return f"color: {color}; font-weight: 600;"

def render_period_dashboard(df, fund_name, freq, freq_label):
    opts = period_options(df, freq)
    selected_label = st.selectbox(
        f"Select {freq_label.lower()} — {fund_name}",
        list(opts.keys()),
        index=len(opts) - 1,
        key=f"{fund_name}_{freq}_select",
    )
    period = opts[selected_label]

    period_df = df[df["date"].dt.to_period(freq) == period].copy()
    period_df["Date"] = period_df["date"].dt.strftime("%d-%b-%Y")
    period_df["NAV"] = period_df["nav"].map(lambda x: f"{x:,.2f}")
    period_df["Units Held"] = period_df["units"].map(lambda x: f"{x:,.2f}")
    period_df["Value (₹)"] = period_df["value"].map(lambda x: f"{x:,.0f}")
    period_df["Daily Return (₹)"] = period_df["change_rs"]
    period_df["Daily Return (%)"] = period_df["change_pct"]

    display_df = period_df[["Date", "Daily Return (%)", "Daily Return (₹)", "NAV", "Units Held", "Value (₹)"]].reset_index(drop=True)

    styled = display_df.style.map(style_returns, subset=["Daily Return (₹)", "Daily Return (%)"]) \
        .format({"Daily Return (₹)": "{:+,.0f}", "Daily Return (%)": "{:+.2f}%"}, na_rep="—")

    st.dataframe(styled, width='stretch', hide_index=True)

    # Period total return
    valid = period_df.dropna(subset=["change_rs"])
    total_rs = valid["change_rs"].sum()
    end_value = period_df["value"].iloc[-1] if not period_df.empty else 0
    start_nav = period_df["nav"].iloc[0]
    end_nav = period_df["nav"].iloc[-1]
    nav_return_pct = (end_nav / start_nav - 1) * 100

    m1, m2, m3 = st.columns(3)
    m1.metric(f"{selected_label} — Total Return (₹)", f"{'+' if total_rs>=0 else ''}{total_rs:,.0f}")
    m2.metric(f"{selected_label} — NAV Return (%)", f"{'+' if nav_return_pct>=0 else ''}{nav_return_pct:.2f}%")
    m3.metric(f"{selected_label} — End Value", f"₹{end_value:,.0f}")

def render_fund_tab(df, fund_name):
    granularity = st.radio(
        "View by",
        ["Month", "Week"],
        horizontal=True,
        key=f"{fund_name}_granularity",
    )
    if granularity == "Month":
        render_period_dashboard(df, fund_name, "M", "Month")
    else:
        render_period_dashboard(df, fund_name, "W", "Week")

tab1, tab2, tab3 = st.tabs(["🏦 Motilal Oswal Midcap (Combined)", "🏦 Invesco India Midcap", "📊 Combined Portfolio"])

with tab1:
    render_fund_tab(motilal_df, "Motilal Oswal Midcap")

with tab2:
    render_fund_tab(invesco_df, "Invesco India Midcap")

with tab3:
    combined = motilal_df[["date", "nav", "value", "change_rs"]].rename(columns={"value": "motilal_value", "change_rs": "motilal_change"})
    inv = invesco_df[["date", "value", "change_rs"]].rename(columns={"value": "invesco_value", "change_rs": "invesco_change"})
    merged = pd.merge(combined, inv, on="date", how="outer").sort_values("date")
    merged["value"] = merged["motilal_value"].fillna(0) + merged["invesco_value"].fillna(0)
    merged["change_rs"] = merged["motilal_change"].fillna(0) + merged["invesco_change"].fillna(0)
    merged["change_pct"] = merged["change_rs"] / (merged["value"] - merged["change_rs"]) * 100
    merged["units"] = 0  # placeholder, not shown
    merged["nav"] = merged["value"]  # not used in this view directly

    granularity = st.radio("View by", ["Month", "Week"], horizontal=True, key="combined_granularity")
    freq = "M" if granularity == "Month" else "W"

    opts = period_options(merged, freq)
    selected_label = st.selectbox(
        f"Select {granularity.lower()} — Combined Portfolio",
        list(opts.keys()),
        index=len(opts) - 1,
        key=f"combined_{freq}_select",
    )
    period = opts[selected_label]
    period_df = merged[merged["date"].dt.to_period(freq) == period].copy()
    period_df["Date"] = period_df["date"].dt.strftime("%d-%b-%Y")
    period_df["Portfolio Value (₹)"] = period_df["value"].map(lambda x: f"{x:,.0f}")
    display_df = period_df[["Date", "change_pct", "change_rs", "Portfolio Value (₹)"]].rename(
        columns={"change_rs": "Daily Return (₹)", "change_pct": "Daily Return (%)"}
    ).reset_index(drop=True)

    styled = display_df.style.map(style_returns, subset=["Daily Return (₹)", "Daily Return (%)"]) \
        .format({"Daily Return (₹)": "{:+,.0f}", "Daily Return (%)": "{:+.2f}%"}, na_rep="—")
    st.dataframe(styled, width='stretch', hide_index=True)

    valid = period_df.dropna(subset=["change_rs"])
    total_rs = valid["change_rs"].sum()
    end_value = period_df["value"].iloc[-1] if not period_df.empty else 0
    start_value = period_df["value"].iloc[0] - period_df["change_rs"].fillna(0).iloc[0] if not period_df.empty else 0
    total_pct = (total_rs / start_value * 100) if start_value else float("nan")
    c1, c2, c3 = st.columns(3)
    c1.metric(f"{selected_label} — Combined Total Return (₹)", f"{'+' if total_rs>=0 else ''}{total_rs:,.0f}")
    c2.metric(f"{selected_label} — Combined Return (%)", f"{'+' if total_pct>=0 else ''}{total_pct:.2f}%")
    c3.metric(f"{selected_label} — Combined End Value", f"₹{end_value:,.0f}")

st.divider()
st.caption("Data source: Motilal Oswal & Invesco daily NAV history, plus your SWP investment/withdrawal records. "
           "Daily return = change in NAV × units held at the start of the day (i.e. pure market movement, excluding that day's SWP cashflow). "
           "Use the 'View by' toggle to switch between monthly and weekly (Mon–Sun) breakdowns. "
           "Update the CSV files in the /data folder to refresh with new NAV data.")
