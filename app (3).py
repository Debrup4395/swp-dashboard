import calendar
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Motilal & Invesco SWP Dashboard", page_icon="📈", layout="wide")

DATA_DIR = Path(__file__).parent

# ----------------------------- Data loading -----------------------------


def _parse_dates(series: pd.Series) -> pd.Series:
    """Parse a date column robustly. Tries ISO first, then day-first, then month-first."""
    s = series.astype(str).str.strip()
    for kwargs in ({"format": "%Y-%m-%d"}, {"dayfirst": True}, {"dayfirst": False}):
        parsed = pd.to_datetime(s, errors="coerce", **kwargs)
        # accept the first strategy that parses (almost) everything
        if parsed.notna().mean() >= 0.95:
            return parsed
    return pd.to_datetime(s, errors="coerce")


@st.cache_data
def load_nav(filename: str) -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / filename)
    df.columns = [c.strip().lower() for c in df.columns]

    df["date"] = _parse_dates(df["date"])
    df["nav"] = pd.to_numeric(df["nav"], errors="coerce")

    bad = int(df["date"].isna().sum() + df["nav"].isna().sum())
    df = df.dropna(subset=["date", "nav"])
    if bad:
        st.warning(f"{filename}: ignored {bad} row(s) with unreadable date or NAV.")

    df = df.drop_duplicates(subset="date", keep="last")
    return df.sort_values("date").reset_index(drop=True)


@st.cache_data
def load_units_events() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "units_events.csv")
    df.columns = [c.strip().lower() for c in df.columns]

    df["date"] = _parse_dates(df["date"])
    df["holder"] = df["holder"].astype(str).str.strip()
    df["units_remaining"] = pd.to_numeric(df["units_remaining"], errors="coerce")
    return df.dropna(subset=["date", "units_remaining"])


def units_daily_series(nav_dates: pd.Series, events_df: pd.DataFrame, holder: str) -> pd.Series:
    """Units held by `holder` on each NAV date (carried forward from the latest event on/before that date)."""
    nav_idx = pd.DatetimeIndex(nav_dates)
    ev = events_df[events_df["holder"] == holder].sort_values("date")
    if ev.empty:
        return pd.Series(0.0, index=nav_idx)

    # one value per date (last event of the day wins)
    ev_series = ev.drop_duplicates(subset="date", keep="last").set_index("date")["units_remaining"]

    # union of dates so events falling on non-NAV days (weekends/holidays) still carry forward
    full_idx = nav_idx.union(ev_series.index)
    units = ev_series.reindex(full_idx).ffill().fillna(0.0)
    return units.reindex(nav_idx)


def build_fund_df(nav_df: pd.DataFrame, events_df: pd.DataFrame, holders: list, fund_label: str) -> pd.DataFrame:
    dates = nav_df["date"]
    total_units = pd.Series(0.0, index=pd.DatetimeIndex(dates))
    for h in holders:
        total_units = total_units + units_daily_series(dates, events_df, h)

    df = pd.DataFrame(
        {
            "date": dates.values,
            "nav": nav_df["nav"].values,
            "units": total_units.values,
        }
    )
    df["value"] = df["nav"] * df["units"]

    # Day-over-day change uses units held at the START of the day (previous day's units),
    # so it reflects pure market movement and excludes that day's SWP cashflow.
    df["prev_units"] = df["units"].shift(1)
    df["prev_nav"] = df["nav"].shift(1)
    df["prev_value"] = df["prev_units"] * df["prev_nav"]
    df["change_rs"] = (df["nav"] - df["prev_nav"]) * df["prev_units"]
    df["change_pct"] = (df["nav"] / df["prev_nav"] - 1) * 100
    df["fund"] = fund_label
    return df


motilal_nav = load_nav("motilal_nav.csv")
invesco_nav = load_nav("invesco_nav.csv")
events = load_units_events()

if motilal_nav.empty or invesco_nav.empty:
    st.error("One of the NAV files has no usable rows. Please check the CSV files.")
    st.stop()

motilal_df = build_fund_df(motilal_nav, events, ["Debrup", "Jayashree"], "Motilal Oswal Midcap (Combined)")
invesco_df = build_fund_df(invesco_nav, events, ["Invesco"], "Invesco India Midcap")

# ----------------------------- Header -----------------------------

st.title("📈 Debrup & Jayashree Motilal — SWP Investment Dashboard")
st.caption(
    "Combined Motilal Oswal Midcap holdings (Debrup + Jayashree) and Invesco India Midcap, tracked from daily NAV."
)

latest_motilal = motilal_df.iloc[-1]
latest_invesco = invesco_df.iloc[-1]

col1, col2, col3 = st.columns(3)
col1.metric(
    "Motilal Oswal Midcap — Current Value",
    f"₹{latest_motilal['value']:,.0f}",
    f"{latest_motilal['units']:,.2f} units",
)
col2.metric(
    "Invesco Midcap — Current Value",
    f"₹{latest_invesco['value']:,.0f}",
    f"{latest_invesco['units']:,.2f} units",
)
col3.metric("Combined Portfolio Value", f"₹{latest_motilal['value'] + latest_invesco['value']:,.0f}")

st.divider()

# ----------------------------- Helpers -----------------------------


def period_options(df: pd.DataFrame, freq: str) -> dict:
    """freq: 'M' for calendar month, 'W' for week (Mon-Sun)."""
    periods = sorted(df["date"].dt.to_period(freq).unique())
    if freq == "M":
        return {f"{calendar.month_name[p.month]} {p.year}": p for p in periods}
    return {f"{p.start_time.strftime('%d-%b-%Y')} to {p.end_time.strftime('%d-%b-%Y')}": p for p in periods}


def style_returns(val):
    if pd.isna(val):
        return ""
    color = "#1a7f37" if val >= 0 else "#d1242f"
    return f"color: {color}; font-weight: 600;"


def signed(x: float, fmt: str) -> str:
    return f"{'+' if x >= 0 else ''}{format(x, fmt)}"


def select_period(df: pd.DataFrame, key_prefix: str, label: str):
    """Renders the Month/Week toggle + dropdown. Returns (period_df, selected_label)."""
    granularity = st.radio("View by", ["Month", "Week"], horizontal=True, key=f"{key_prefix}_granularity")
    freq = "M" if granularity == "Month" else "W"

    opts = period_options(df, freq)
    selected_label = st.selectbox(
        f"Select {granularity.lower()} — {label}",
        list(opts.keys()),
        index=len(opts) - 1,
        key=f"{key_prefix}_{freq}_select",
    )
    period_df = df[df["date"].dt.to_period(freq) == opts[selected_label]].copy()
    return period_df, selected_label


def show_returns_table(display_df: pd.DataFrame):
    styled = display_df.style.map(
        style_returns, subset=["Daily Return (₹)", "Daily Return (%)"]
    ).format({"Daily Return (₹)": "{:+,.0f}", "Daily Return (%)": "{:+.2f}%"}, na_rep="—")
    st.dataframe(styled, width="stretch", hide_index=True)


# ----------------------------- Per-fund tabs -----------------------------


def render_fund_tab(df: pd.DataFrame, fund_name: str):
    period_df, selected_label = select_period(df, fund_name, fund_name)
    if period_df.empty:
        st.info("No data for this period.")
        return

    period_df["Date"] = period_df["date"].dt.strftime("%d-%b-%Y")
    period_df["NAV"] = period_df["nav"].map(lambda x: f"{x:,.2f}")
    period_df["Units Held"] = period_df["units"].map(lambda x: f"{x:,.2f}")
    period_df["Value (₹)"] = period_df["value"].map(lambda x: f"{x:,.0f}")
    period_df["Daily Return (₹)"] = period_df["change_rs"]
    period_df["Daily Return (%)"] = period_df["change_pct"]

    show_returns_table(
        period_df[["Date", "Daily Return (%)", "Daily Return (₹)", "NAV", "Units Held", "Value (₹)"]].reset_index(drop=True)
    )

    total_rs = period_df["change_rs"].sum()  # NaN (first ever row) is skipped by sum()
    end_value = period_df["value"].iloc[-1]

    # NAV return over the period, measured from the day before the period started when available
    first = period_df.iloc[0]
    base_nav = first["prev_nav"] if pd.notna(first["prev_nav"]) else first["nav"]
    nav_return_pct = (period_df["nav"].iloc[-1] / base_nav - 1) * 100

    m1, m2, m3 = st.columns(3)
    m1.metric(f"{selected_label} — Total Return (₹)", signed(total_rs, ",.0f"))
    m2.metric(f"{selected_label} — NAV Return (%)", signed(nav_return_pct, ".2f") + "%")
    m3.metric(f"{selected_label} — End Value", f"₹{end_value:,.0f}")


# ----------------------------- Combined portfolio -----------------------------


def build_combined(a: pd.DataFrame, b: pd.DataFrame) -> pd.DataFrame:
    cols = ["value", "prev_value", "change_rs"]
    a = a.set_index("date")[cols].add_prefix("a_")
    b = b.set_index("date")[cols].add_prefix("b_")
    m = a.join(b, how="outer").sort_index()

    # A fund may have no NAV on a day the other does (holidays): carry its value forward, zero change.
    for c in ("a_value", "b_value", "a_prev_value", "b_prev_value"):
        m[c] = m[c].ffill()
    m = m.fillna({"a_change_rs": 0.0, "b_change_rs": 0.0}).fillna(0.0)

    out = pd.DataFrame(index=m.index)
    out["value"] = m["a_value"] + m["b_value"]
    out["prev_value"] = m["a_prev_value"] + m["b_prev_value"]
    out["change_rs"] = m["a_change_rs"] + m["b_change_rs"]
    out["change_pct"] = (out["change_rs"] / out["prev_value"].where(out["prev_value"] > 0)) * 100
    return out.reset_index()


def render_combined_tab():
    merged = build_combined(motilal_df, invesco_df)
    period_df, selected_label = select_period(merged, "combined", "Combined Portfolio")
    if period_df.empty:
        st.info("No data for this period.")
        return

    period_df["Date"] = period_df["date"].dt.strftime("%d-%b-%Y")
    period_df["Portfolio Value (₹)"] = period_df["value"].map(lambda x: f"{x:,.0f}")
    display_df = period_df[["Date", "change_pct", "change_rs", "Portfolio Value (₹)"]].rename(
        columns={"change_rs": "Daily Return (₹)", "change_pct": "Daily Return (%)"}
    ).reset_index(drop=True)
    show_returns_table(display_df)

    total_rs = period_df["change_rs"].sum()
    end_value = period_df["value"].iloc[-1]
    start_value = period_df["prev_value"].iloc[0]
    total_pct = (total_rs / start_value * 100) if start_value else float("nan")

    c1, c2, c3 = st.columns(3)
    c1.metric(f"{selected_label} — Combined Total Return (₹)", signed(total_rs, ",.0f"))
    c2.metric(
        f"{selected_label} — Combined Return (%)",
        "—" if pd.isna(total_pct) else signed(total_pct, ".2f") + "%",
    )
    c3.metric(f"{selected_label} — Combined End Value", f"₹{end_value:,.0f}")


# ----------------------------- Layout -----------------------------

tab1, tab2, tab3 = st.tabs(
    ["🏦 Motilal Oswal Midcap (Combined)", "🏦 Invesco India Midcap", "📊 Combined Portfolio"]
)

with tab1:
    render_fund_tab(motilal_df, "Motilal Oswal Midcap")
with tab2:
    render_fund_tab(invesco_df, "Invesco India Midcap")
with tab3:
    render_combined_tab()

st.divider()
st.caption(
    "Data source: Motilal Oswal & Invesco daily NAV history, plus your SWP investment/withdrawal records. "
    "Daily return = change in NAV × units held at the start of the day (pure market movement, excluding that day's SWP cashflow). "
    "Use the 'View by' toggle to switch between monthly and weekly (Mon–Sun) breakdowns. "
    "Update motilal_nav.csv, invesco_nav.csv and units_events.csv (same folder as this app) to refresh the data."
)
