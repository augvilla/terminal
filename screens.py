"""
Screen implementations.

Every screen is a function taking a single optional ticker and rendering
itself. Keep them self-contained — the router knows nothing about their
internals.
"""

from datetime import datetime, date, timedelta

import pandas as pd
import streamlit as st
import yfinance as yf
import plotly.graph_objects as go

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
    except Exception:
        st.warning(f"INVALID COMMAND OR TICKER: {ticker}  |  TYPE MENU TO SEE WHAT'S AVAILABLE.")
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
# CHART -- price history
# --------------------------------------------------------------------------

@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_history(ticker, start, end):
    df = yf.download(ticker, start=start, end=end + timedelta(days=1),
                      progress=False, auto_adjust=True)
    if df.empty:
        return pd.Series(dtype=float)
    close = df["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]
    return close


def screen_chart(ticker):
    screen_title(f"{ticker} \u2014 Price Chart")

    default_start = date(date.today().year, 1, 1)
    default_end = date.today()
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="term-label">Start Date</div>', unsafe_allow_html=True)
        start_date = st.date_input("Start", value=default_start, max_value=default_end,
                                    key=f"chart_start_{ticker}", label_visibility="collapsed")
    with c2:
        st.markdown('<div class="term-label">End Date</div>', unsafe_allow_html=True)
        end_date = st.date_input("End", value=default_end, max_value=default_end,
                                  key=f"chart_end_{ticker}", label_visibility="collapsed")

    if start_date >= end_date:
        st.warning("START DATE MUST BE BEFORE END DATE.")
        return

    prices = _fetch_history(ticker, start_date, end_date)
    if prices.empty:
        st.warning(f"NO PRICE DATA FOR {ticker} IN THAT RANGE.")
        return

    ret_pct = (prices.iloc[-1] / prices.iloc[0] - 1) * 100
    cls = "up" if ret_pct > 0 else ("down" if ret_pct < 0 else "")
    stat_row([
        ("Start", f"{prices.iloc[0]:,.2f}", ""),
        ("End", f"{prices.iloc[-1]:,.2f}", "accent"),
        ("Range Return", f"{ret_pct:+.2f}%", cls),
        ("Trading Days", f"{len(prices):,}", ""),
    ])

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=prices.index, y=prices.values, mode="lines",
                              line=dict(color="#FF1E1E", width=2.2)))
    fig.update_layout(
        xaxis=dict(title="DATE", color="#FF8C00", gridcolor="#2a2a2a", griddash="dot",
                   showline=True, linecolor="#FF8C00"),
        yaxis=dict(title="PRICE", color="#FF8C00", gridcolor="#2a2a2a", griddash="dot",
                   showline=True, linecolor="#FF8C00"),
        showlegend=False, hovermode="x unified", height=520,
        paper_bgcolor="#000000", plot_bgcolor="#000000",
        font=dict(family="IBM Plex Mono", color="#FF8C00"),
        margin=dict(l=10, r=10, t=20, b=10),
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption("QUOTES MAY BE DELAYED  |  ADJUSTED FOR SPLITS AND DIVIDENDS")


# --------------------------------------------------------------------------
# BOOKS -- financial statements
# --------------------------------------------------------------------------

@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_financials(ticker):
    t = yf.Ticker(ticker)
    return {
        "income": t.income_stmt,
        "income_q": t.quarterly_income_stmt,
        "balance": t.balance_sheet,
        "balance_q": t.quarterly_balance_sheet,
        "cashflow": t.cashflow,
        "cashflow_q": t.quarterly_cashflow,
    }


def _format_statement(df, max_rows=25):
    if df is None or df.empty:
        return pd.DataFrame()
    out = df.iloc[:max_rows].copy()
    out.columns = [c.strftime("%Y-%m") if hasattr(c, "strftime") else str(c) for c in out.columns]
    out = out.map(lambda v: _fmt_big(v) if isinstance(v, (int, float)) else v)
    out.index.name = "Line Item"
    return out.reset_index()


def screen_books(ticker):
    screen_title(f"{ticker} \u2014 Financial Statements", "Most recent first")

    try:
        data = _fetch_financials(ticker)
    except Exception as e:
        st.warning(f"COULD NOT LOAD FINANCIALS FOR {ticker} \u2014 {e}")
        return

    period = st.radio("Period", ["Annual", "Quarterly"], horizontal=True,
                       key=f"books_period_{ticker}", label_visibility="collapsed")
    suffix = "_q" if period == "Quarterly" else ""

    tabs = st.tabs(["Income Statement", "Balance Sheet", "Cash Flow"])
    keys = [f"income{suffix}", f"balance{suffix}", f"cashflow{suffix}"]
    for tab, key in zip(tabs, keys):
        with tab:
            table = _format_statement(data.get(key))
            if table.empty:
                st.info("NO DATA AVAILABLE FOR THIS STATEMENT.")
            else:
                st.dataframe(table, use_container_width=True, hide_index=True)

    st.caption("VALUES IN REPORTING CURRENCY  |  SOURCE: YAHOO FINANCE")


# --------------------------------------------------------------------------
# DIV -- dividends
# --------------------------------------------------------------------------

@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_dividends(ticker):
    t = yf.Ticker(ticker)
    return t.dividends, (t.info or {})


def screen_div(ticker):
    screen_title(f"{ticker} \u2014 Dividends")

    try:
        divs, info = _fetch_dividends(ticker)
    except Exception as e:
        st.warning(f"COULD NOT LOAD DIVIDEND DATA FOR {ticker} \u2014 {e}")
        return

    yld = info.get("dividendYield")
    if yld is not None and yld < 1:
        yld = yld * 100
    rate = info.get("dividendRate")
    payout = info.get("payoutRatio")
    if payout is not None:
        payout = payout * 100
    ex_date = info.get("exDividendDate")
    if ex_date:
        try:
            ex_date = datetime.fromtimestamp(ex_date).strftime("%Y-%m-%d")
        except Exception:
            ex_date = "\u2014"

    stat_row([
        ("Yield", f"{yld:.2f}%" if yld else "\u2014", "accent"),
        ("Annual Rate", f"{rate:,.2f}" if rate else "\u2014", ""),
        ("Payout Ratio", f"{payout:.1f}%" if payout else "\u2014", ""),
        ("Ex-Dividend Date", ex_date or "\u2014", ""),
    ])

    if divs is None or divs.empty:
        st.info(f"{ticker} HAS NO DIVIDEND HISTORY ON RECORD.")
        return

    st.markdown('<div class="block-label">Payment History (Most Recent 20)</div>', unsafe_allow_html=True)
    recent = divs.tail(20).sort_index(ascending=False)
    table = pd.DataFrame({
        "Date": [d.strftime("%Y-%m-%d") for d in recent.index],
        "Amount": [f"{v:,.4f}" for v in recent.values],
    })
    st.dataframe(table, use_container_width=True, hide_index=True)

    fig = go.Figure()
    fig.add_trace(go.Bar(x=divs.index, y=divs.values, marker=dict(color="#FF8C00")))
    fig.update_layout(
        xaxis=dict(title="DATE", color="#FF8C00", gridcolor="#2a2a2a", showline=True, linecolor="#FF8C00"),
        yaxis=dict(title="AMOUNT", color="#FF8C00", gridcolor="#2a2a2a", showline=True, linecolor="#FF8C00"),
        showlegend=False, height=380,
        paper_bgcolor="#000000", plot_bgcolor="#000000",
        font=dict(family="IBM Plex Mono", color="#FF8C00"),
        margin=dict(l=10, r=10, t=20, b=10),
    )
    st.plotly_chart(fig, use_container_width=True)


# --------------------------------------------------------------------------
# EARN -- earnings
# --------------------------------------------------------------------------

@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_earnings(ticker):
    t = yf.Ticker(ticker)
    try:
        dates = t.earnings_dates
    except Exception:
        dates = None
    return dates


def screen_earn(ticker):
    screen_title(f"{ticker} \u2014 Earnings")

    try:
        dates = _fetch_earnings(ticker)
    except Exception as e:
        st.warning(f"COULD NOT LOAD EARNINGS DATA FOR {ticker} \u2014 {e}")
        return

    if dates is None or dates.empty:
        st.info(f"NO EARNINGS DATA AVAILABLE FOR {ticker}.")
        return

    dates = dates.sort_index(ascending=False)
    now = pd.Timestamp.now(tz=dates.index.tz) if dates.index.tz else pd.Timestamp.now()
    upcoming = dates[dates.index > now]
    past = dates[dates.index <= now]

    if not upcoming.empty:
        st.markdown('<div class="block-label">Next Earnings Date</div>', unsafe_allow_html=True)
        stat_row([("Date", upcoming.index[-1].strftime("%Y-%m-%d"), "accent")])

    st.markdown('<div class="block-label">Recent History (Last 12)</div>', unsafe_allow_html=True)
    recent = past.head(12).copy()
    if recent.empty:
        st.info("NO PAST EARNINGS ON RECORD.")
        return

    table = pd.DataFrame({"Date": [d.strftime("%Y-%m-%d") for d in recent.index]})
    for col in ["EPS Estimate", "Reported EPS", "Surprise(%)"]:
        if col in recent.columns:
            table[col] = recent[col].map(lambda v: f"{v:,.2f}" if pd.notna(v) else "\u2014")
    st.dataframe(table, use_container_width=True, hide_index=True)
    st.caption("SOURCE: YAHOO FINANCE  |  ESTIMATES CAN CHANGE UNTIL REPORTED")


# --------------------------------------------------------------------------
# STREET -- analyst view
# --------------------------------------------------------------------------

@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_street(ticker):
    t = yf.Ticker(ticker)
    info = t.info or {}
    try:
        recs = t.recommendations
    except Exception:
        recs = None
    return info, recs


def screen_street(ticker):
    screen_title(f"{ticker} \u2014 Analyst View")

    try:
        info, recs = _fetch_street(ticker)
    except Exception as e:
        st.warning(f"COULD NOT LOAD ANALYST DATA FOR {ticker} \u2014 {e}")
        return

    key = info.get("recommendationKey")
    n_analysts = info.get("numberOfAnalystOpinions")
    target_mean = info.get("targetMeanPrice")
    target_high = info.get("targetHighPrice")
    target_low = info.get("targetLowPrice")
    current = info.get("currentPrice") or info.get("regularMarketPrice")

    upside = None
    if target_mean and current:
        upside = (target_mean / current - 1) * 100

    stat_row([
        ("Consensus", (key or "\u2014").upper().replace("_", " "), "accent"),
        ("Mean Target", f"{target_mean:,.2f}" if target_mean else "\u2014", ""),
        ("Implied Upside", f"{upside:+.1f}%" if upside is not None else "\u2014",
         "up" if (upside or 0) > 0 else ("down" if (upside or 0) < 0 else "")),
        ("Analysts", f"{n_analysts:,}" if n_analysts else "\u2014", ""),
    ])

    st.markdown('<div class="block-label">Price Target Range</div>', unsafe_allow_html=True)
    rng = pd.DataFrame({
        "Field": ["Low", "Mean", "High", "Current"],
        "Value": [
            f"{target_low:,.2f}" if target_low else "\u2014",
            f"{target_mean:,.2f}" if target_mean else "\u2014",
            f"{target_high:,.2f}" if target_high else "\u2014",
            f"{current:,.2f}" if current else "\u2014",
        ],
    })
    st.dataframe(rng, use_container_width=True, hide_index=True)

    if recs is not None and not recs.empty:
        st.markdown('<div class="block-label">Recent Rating Changes</div>', unsafe_allow_html=True)
        recent = recs.tail(15).sort_index(ascending=False).reset_index()
        st.dataframe(recent, use_container_width=True, hide_index=True)
    else:
        st.caption("NO RECENT RATING-CHANGE HISTORY AVAILABLE.")


# --------------------------------------------------------------------------
# NEWS -- headlines
# --------------------------------------------------------------------------

@st.cache_data(ttl=600, show_spinner=False)
def _fetch_news(ticker):
    t = yf.Ticker(ticker)
    try:
        return t.news or []
    except Exception:
        return []


def screen_news(ticker):
    screen_title(f"{ticker} \u2014 Headlines")

    try:
        items = _fetch_news(ticker)
    except Exception as e:
        st.warning(f"COULD NOT LOAD NEWS FOR {ticker} \u2014 {e}")
        return

    if not items:
        st.info(f"NO RECENT HEADLINES FOUND FOR {ticker}.")
        return

    for item in items[:15]:
        content = item.get("content", item)
        title = content.get("title") or item.get("title") or "Untitled"
        provider = content.get("provider")
        publisher = provider.get("displayName") if isinstance(provider, dict) else item.get("publisher")
        canonical = content.get("canonicalUrl")
        link = canonical.get("url") if isinstance(canonical, dict) else item.get("link")
        pub_time = content.get("pubDate") or item.get("providerPublishTime")

        when = ""
        if isinstance(pub_time, (int, float)):
            try:
                when = datetime.fromtimestamp(pub_time).strftime("%Y-%m-%d %H:%M")
            except Exception:
                when = ""
        elif isinstance(pub_time, str):
            when = pub_time[:16].replace("T", " ")

        st.markdown(
            f'<div class="news-item">'
            f'<a href="{link or "#"}" target="_blank" class="news-title">{title}</a>'
            f'<div class="news-meta">{publisher or "\u2014"}{"  |  " + when if when else ""}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.caption("SOURCE: YAHOO FINANCE  |  HEADLINES LINK OUT TO THE ORIGINAL PUBLISHER")


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

Order is fixed — <b>ticker first, command second</b>.

<table class="help-table">
<tr><td><code>AAPL BOOKS</code></td><td>Ticker, then command</td></tr>
<tr><td><code>AAPL</code></td><td>Ticker alone opens its snapshot</td></tr>
<tr><td><code>BOOKS</code></td><td>Command alone reuses your last ticker</td></tr>
<tr><td><code>MACRO</code></td><td>Some screens need no ticker at all</td></tr>
</table>

<div class="block-label">Why the order is fixed</div>

Plenty of commands are also real ticker symbols — SNAP is Snapchat, and
DIV, EARN, PORT and HOLD are all listed securities. Position decides which
is which, so <code>SNAP SNAP</code> reads cleanly as the snapshot screen
for Snapchat.

<div class="block-label">Finding commands</div>

Type <code>MENU</code> for the full index of screens, with a filter box.
Commands marked PLANNED exist in the vocabulary but are not built yet.

<div class="block-label">Shortcuts</div>

Input is case-insensitive. Crypto shorthand expands automatically —
<code>BTC</code> becomes <code>BTC-USD</code>.

</div>
""", unsafe_allow_html=True)


# --------------------------------------------------------------------------
# Bind handlers to the registry
# --------------------------------------------------------------------------

registry.bind("SNAP", screen_snap)
registry.bind("CHART", screen_chart)
registry.bind("BOOKS", screen_books)
registry.bind("DIV", screen_div)
registry.bind("EARN", screen_earn)
registry.bind("STREET", screen_street)
registry.bind("NEWS", screen_news)
registry.bind("MENU", screen_menu)
registry.bind("HELP", screen_help)
