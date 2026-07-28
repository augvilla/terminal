"""
Screen implementations.

Every screen is a function taking a single optional ticker and rendering
itself. Keep them self-contained — the router knows nothing about their
internals.
"""

from datetime import datetime

import pandas as pd
import streamlit as st
import yfinance as yf

import registry


# --------------------------------------------------------------------------
# Shared render helpers
# --------------------------------------------------------------------------

def stat_row(pairs):
    """pairs: list of (label, value, css_class). Renders one compact stat line."""
    blocks = "".join(
        f'<div class="stat-block"><div class="stat-label">{label}</div>'
        f'<div class="stat-value {cls}">{value}</div></div>'
        for label, value, cls in pairs
    )
    st.markdown(f'<div class="stat-row">{blocks}</div>', unsafe_allow_html=True)


def screen_title(text, sub=None):
    st.markdown(f'<div class="screen-title">{text}</div>', unsafe_allow_html=True)
    if sub:
        st.markdown(f'<div class="screen-sub">{sub}</div>', unsafe_allow_html=True)


# --------------------------------------------------------------------------
# SNAP — company snapshot
# --------------------------------------------------------------------------

@st.cache_data(ttl=300, show_spinner=False)
def _fetch_snapshot(ticker: str) -> dict:
    t = yf.Ticker(ticker)

    # yfinance raises assorted internal KeyErrors for symbols that do not
    # exist. Translate anything it throws into one clear message.
    try:
        info = t.info or {}
    except Exception:
        info = {}

    try:
        fi = t.fast_info
        price = fi.get("lastPrice")
        prev_close = fi.get("previousClose")
    except Exception:
        fi, price, prev_close = {}, None, None

    if not price or not prev_close:
        try:
            hist = t.history(period="5d")["Close"].dropna()
        except Exception:
            hist = None
        if hist is None or hist.empty:
            raise ValueError("no such symbol, or no price data available")
        price = float(hist.iloc[-1])
        prev_close = float(hist.iloc[-2]) if len(hist) > 1 else price

    change = price - prev_close
    change_pct = (change / prev_close * 100) if prev_close else 0.0

    return {
        "name": info.get("longName") or info.get("shortName") or ticker,
        "price": float(price),
        "change": float(change),
        "change_pct": float(change_pct),
        "currency": info.get("currency") or "USD",
        "exchange": info.get("fullExchangeName") or info.get("exchange") or "—",
        "sector": info.get("sector") or "—",
        "industry": info.get("industry") or "—",
        "country": info.get("country") or "—",
        "employees": info.get("fullTimeEmployees"),
        "website": info.get("website") or "",
        "summary": info.get("longBusinessSummary") or "",
        "market_cap": info.get("marketCap"),
        "pe": info.get("trailingPE"),
        "fwd_pe": info.get("forwardPE"),
        "eps": info.get("trailingEps"),
        "beta": info.get("beta"),
        "div_yield": info.get("dividendYield"),
        "hi52": info.get("fiftyTwoWeekHigh"),
        "lo52": info.get("fiftyTwoWeekLow"),
        "avg_vol": info.get("averageVolume"),
        "open": fi.get("open"),
        "day_high": fi.get("dayHigh"),
        "day_low": fi.get("dayLow"),
    }


def _fmt_big(n):
    if n is None:
        return "—"
    n = float(n)
    for cutoff, suffix in ((1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "K")):
        if abs(n) >= cutoff:
            return f"{n / cutoff:,.2f}{suffix}"
    return f"{n:,.0f}"


def _fmt_num(n, dp=2, suffix=""):
    if n is None:
        return "—"
    try:
        return f"{float(n):,.{dp}f}{suffix}"
    except (TypeError, ValueError):
        return "—"


def screen_snap(ticker: str):
    try:
        d = _fetch_snapshot(ticker)
    except Exception as e:
        st.error(f"COULD NOT LOAD {ticker} — {e}")
        return

    up = d["change_pct"] > 0
    down = d["change_pct"] < 0
    cls = "up" if up else ("down" if down else "")
    arrow = "\u25b2" if up else ("\u25bc" if down else "\u25ac")

    screen_title(f"{ticker} \u2014 {d['name']}", f"{d['exchange']}  |  {d['sector']}  |  {d['country']}")

    stat_row([
        ("Last", f"{d['price']:,.2f}", "accent"),
        ("Change", f"{arrow} {d['change']:+,.2f} ({d['change_pct']:+.2f}%)", cls),
        ("Market Cap", _fmt_big(d["market_cap"]), ""),
        ("Currency", d["currency"], ""),
    ])

    left, right = st.columns(2)

    with left:
        st.markdown('<div class="block-label">Session</div>', unsafe_allow_html=True)
        session = pd.DataFrame({
            "Field": ["Open", "Day High", "Day Low", "Prev Close", "52W High", "52W Low", "Avg Volume"],
            "Value": [
                _fmt_num(d["open"]), _fmt_num(d["day_high"]), _fmt_num(d["day_low"]),
                _fmt_num(d["price"] - d["change"]),
                _fmt_num(d["hi52"]), _fmt_num(d["lo52"]), _fmt_big(d["avg_vol"]),
            ],
        })
        st.dataframe(session, use_container_width=True, hide_index=True)

    with right:
        st.markdown('<div class="block-label">Valuation</div>', unsafe_allow_html=True)
        div_y = d["div_yield"]
        if div_y is not None and div_y < 1:
            div_y = div_y * 100
        val = pd.DataFrame({
            "Field": ["Trailing P/E", "Forward P/E", "EPS (ttm)", "Beta", "Dividend Yield", "Industry", "Employees"],
            "Value": [
                _fmt_num(d["pe"]), _fmt_num(d["fwd_pe"]), _fmt_num(d["eps"]),
                _fmt_num(d["beta"]), _fmt_num(div_y, suffix="%") if div_y else "—",
                d["industry"], _fmt_big(d["employees"]) if d["employees"] else "—",
            ],
        })
        st.dataframe(val, use_container_width=True, hide_index=True)

    if d["summary"]:
        st.markdown('<div class="block-label">Profile</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="profile-text">{d["summary"]}</div>', unsafe_allow_html=True)

    st.caption(f"RETRIEVED {datetime.now():%Y-%m-%d %H:%M}  |  QUOTES MAY BE DELAYED")


# --------------------------------------------------------------------------
# MENU — command index
# --------------------------------------------------------------------------

def screen_menu(ticker=None):
    screen_title("Command Index", "Every command available in this terminal")

    query = st.text_input(
        "Filter commands", key="menu_filter", placeholder="FILTER COMMANDS...",
        label_visibility="collapsed",
    ).strip().lower()

    cmds = list(registry.COMMANDS.values())
    if query:
        cmds = [
            c for c in cmds
            if query in c.code.lower() or query in c.title.lower() or query in c.description.lower()
        ]

    if not cmds:
        st.info("NO COMMANDS MATCH THAT FILTER.")
        return

    order = ["Company", "Markets", "Tools", "System"]
    by_cat = {}
    for c in cmds:
        by_cat.setdefault(c.category, []).append(c)

    for cat in order:
        group = sorted(by_cat.get(cat, []), key=lambda c: c.code)
        if not group:
            continue
        st.markdown(f'<div class="block-label">{cat}</div>', unsafe_allow_html=True)
        rows = []
        for c in group:
            usage = f"<TICKER> {c.code}" if c.needs_ticker else c.code
            rows.append({
                "CMD": c.code,
                "SCREEN": c.title,
                "USAGE": usage,
                "STATUS": "LIVE" if c.implemented else "PLANNED",
                "DESCRIPTION": c.description,
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    live = sum(1 for c in registry.COMMANDS.values() if c.implemented)
    st.caption(f"{live} OF {len(registry.COMMANDS)} COMMANDS LIVE  |  PLANNED ENTRIES ARE NOT YET BUILT")


# --------------------------------------------------------------------------
# HELP
# --------------------------------------------------------------------------

def screen_help(ticker=None):
    screen_title("Help", "How the command bar works")

    st.markdown("""
<div class="help-body">

<div class="block-label">Syntax</div>

Type a ticker, a command, or both — in either order.

<table class="help-table">
<tr><td><code>AAPL</code></td><td>Ticker alone opens its snapshot</td></tr>
<tr><td><code>AAPL BOOKS</code></td><td>Ticker plus command</td></tr>
<tr><td><code>BOOKS AAPL</code></td><td>Same thing — order does not matter</td></tr>
<tr><td><code>BOOKS</code></td><td>Command alone reuses your last ticker</td></tr>
<tr><td><code>MACRO</code></td><td>Some screens need no ticker at all</td></tr>
</table>

<div class="block-label">Finding commands</div>

Type <code>MENU</code> for the full index of screens, with a filter box.
Commands marked PLANNED exist in the vocabulary but are not built yet.

<div class="block-label">Shortcuts</div>

Crypto shorthand is expanded automatically — <code>BTC</code> becomes
<code>BTC-USD</code>. Mistyped commands will suggest the closest match.

</div>
""", unsafe_allow_html=True)


# --------------------------------------------------------------------------
# Bind handlers to the registry
# --------------------------------------------------------------------------

registry.bind("SNAP", screen_snap)
registry.bind("MENU", screen_menu)
registry.bind("HELP", screen_help)
