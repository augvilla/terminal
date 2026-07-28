"""
Terminal — shell and router.

Step one: the chrome, the command bar, and dispatch. Screens live in
screens.py; the vocabulary lives in registry.py. Adding a screen means
writing a function and binding it — never editing this file.
"""

import streamlit as st

st.set_page_config(page_title="Terminal", layout="wide", initial_sidebar_state="collapsed")

import registry
import router
import screens  # noqa: F401  — importing binds handlers to the registry

# --------------------------------------------------------------------------
# Theme
# --------------------------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'IBM Plex Mono', 'Consolas', monospace !important;
    }

    .stApp { background-color: #000000; color: #FF8C00; }
    section[data-testid="stSidebar"] { display: none; }
    header[data-testid="stHeader"] { background-color: #000000; }
    div.block-container { padding-top: 1.1rem; max-width: 1500px; }

    h1, h2, h3, h4, h5, h6 { color: #FF8C00 !important; letter-spacing: 0.5px; }
    p, span, label, .stMarkdown, .stCaption { color: #FFB84D !important; }

    /* Masthead */
    .term-title {
        color: #FF8C00 !important;
        font-weight: 700;
        font-size: 1.55rem;
        letter-spacing: 3px;
        margin-top: 0.3em;
    }
    .term-sub {
        color: #7A5A2E !important;
        font-size: 0.68rem;
        letter-spacing: 1.4px;
        margin-top: -2px;
        margin-bottom: 12px;
    }

    /* Command bar */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border: 1px solid #FF8C00 !important;
        border-radius: 0px !important;
        background-color: #050505 !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] > div { border-radius: 0px !important; }

    .term-label {
        color: #FF8C00 !important;
        font-size: 0.65rem;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        margin-bottom: 3px;
    }

    .stTextInput input {
        background-color: #000000 !important;
        color: #FF8C00 !important;
        border: 1px solid #FF8C00 !important;
        border-radius: 0px !important;
        font-family: 'IBM Plex Mono', monospace !important;
        font-weight: 600;
        letter-spacing: 1px;
        caret-color: #FF8C00;
    }
    .stTextInput input:focus {
        box-shadow: 0 0 0 1px #FF8C00 !important;
        border: 1px solid #FFB84D !important;
    }

    .stButton button {
        background-color: #000000;
        color: #FF8C00;
        border: 1px solid #FF8C00;
        border-radius: 0px;
        font-family: 'IBM Plex Mono', monospace;
        font-weight: 700;
        letter-spacing: 1px;
        width: 100%;
        transition: none;
    }
    .stButton button:hover {
        background-color: #FF8C00;
        color: #000000;
        border: 1px solid #FF8C00;
    }

    /* Screen headings */
    .screen-title {
        color: #FF8C00 !important;
        font-size: 1.25rem;
        font-weight: 700;
        letter-spacing: 1px;
        margin-top: 6px;
    }
    .screen-sub {
        color: #7A5A2E !important;
        font-size: 0.7rem;
        letter-spacing: 1.2px;
        text-transform: uppercase;
        margin-bottom: 14px;
    }
    .block-label {
        color: #7A5A2E !important;
        font-size: 0.62rem;
        letter-spacing: 1.6px;
        text-transform: uppercase;
        margin: 16px 0 6px 0;
    }

    /* Stat strip */
    .stat-row {
        display: flex; gap: 44px; flex-wrap: wrap;
        margin: 4px 0 14px 0; padding-bottom: 14px;
        border-bottom: 1px solid #2a2a2a;
    }
    .stat-block { display: flex; flex-direction: column; }
    .stat-label {
        color: #7A5A2E !important; font-size: 0.6rem;
        letter-spacing: 1.5px; text-transform: uppercase; margin-bottom: 3px;
    }
    .stat-value {
        color: #FFFFFF !important; font-size: 1.15rem; font-weight: 700;
        font-family: 'IBM Plex Mono', monospace;
    }
    .stat-value.accent { color: #FF8C00 !important; }
    .stat-value.up { color: #4CAF50 !important; }
    .stat-value.down { color: #E74C3C !important; }

    .profile-text {
        color: #FFB84D !important; font-size: 0.82rem;
        line-height: 1.6; max-width: 1100px;
    }

    .help-body { color: #FFB84D !important; font-size: 0.85rem; line-height: 1.7; }
    .help-table { border-collapse: collapse; margin: 4px 0 10px 0; }
    .help-table td { padding: 4px 26px 4px 0; color: #FFB84D !important; font-size: 0.82rem; }
    .help-body code {
        background-color: #141414; color: #FF8C00;
        padding: 2px 7px; font-family: 'IBM Plex Mono', monospace;
    }

    div[data-testid="stDataFrame"] { border: 1px solid #331d00; }
    div[data-testid="stAlert"] {
        background-color: #050505; color: #FF8C00;
        border: 1px solid #FF8C00; border-radius: 0px;
    }
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------------------------------
# Access control
# --------------------------------------------------------------------------
DEFAULT_ALLOWED_USERS = {("augustine", "villalobos"), ("david", "villalobos")}


def get_allowed_users() -> set:
    try:
        configured = st.secrets.get("allowed_users", None)
    except Exception:
        configured = None
    if not configured:
        return DEFAULT_ALLOWED_USERS
    return {
        (e["first_name"].strip().lower(), e["last_name"].strip().lower())
        for e in configured
    }


if "authenticated" not in st.session_state:
    st.session_state.authenticated = False


def masthead():
    st.markdown('<div class="term-title">TERMINAL</div>', unsafe_allow_html=True)
    st.markdown('<div class="term-sub">AUGUSTINE VILLALOBOS</div>', unsafe_allow_html=True)


if not st.session_state.authenticated:
    masthead()
    st.markdown("<br>", unsafe_allow_html=True)
    _, mid, _ = st.columns([1, 1.1, 1])
    with mid:
        with st.container(border=True):
            st.markdown("### RESTRICTED ACCESS")
            st.caption("ENTER YOUR FIRST AND LAST NAME TO CONTINUE")
            with st.form("login"):
                first = st.text_input("First name", placeholder="FIRST NAME")
                last = st.text_input("Last name", placeholder="LAST NAME")
                ok = st.form_submit_button("ACCESS TERMINAL", use_container_width=True)
            if ok:
                key = (first.strip().lower(), last.strip().lower())
                if first.strip() and last.strip() and key in get_allowed_users():
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("ACCESS DENIED — NAME NOT RECOGNIZED.")
    st.stop()

# --------------------------------------------------------------------------
# Session state
# --------------------------------------------------------------------------
if "active_command" not in st.session_state:
    st.session_state.active_command = "MENU"
if "active_ticker" not in st.session_state:
    st.session_state.active_ticker = None
if "last_ticker" not in st.session_state:
    st.session_state.last_ticker = None
if "bar_error" not in st.session_state:
    st.session_state.bar_error = None


def run_command(raw: str):
    """Parse input and update what the terminal is showing."""
    result = router.parse(raw, last_ticker=st.session_state.last_ticker)

    if result.error:
        st.session_state.bar_error = result.error
        return

    st.session_state.bar_error = None
    st.session_state.active_command = result.command
    st.session_state.active_ticker = result.ticker
    if result.ticker:
        st.session_state.last_ticker = result.ticker


# --------------------------------------------------------------------------
# Shell
# --------------------------------------------------------------------------
masthead()

with st.container(border=True):
    c1, c2, c3 = st.columns([5, 1, 1])
    with c1:
        st.markdown('<div class="term-label">Command</div>', unsafe_allow_html=True)
        typed = st.text_input(
            "Command", key="command_input", placeholder="E.G.  AAPL SNAP",
            label_visibility="collapsed",
        )
    with c2:
        st.markdown('<div class="term-label">&nbsp;</div>', unsafe_allow_html=True)
        go = st.button("GO", type="primary", use_container_width=True)
    with c3:
        st.markdown('<div class="term-label">&nbsp;</div>', unsafe_allow_html=True)
        menu_clicked = st.button("MENU", use_container_width=True)

    active = registry.get(st.session_state.active_command)
    crumb = f"{st.session_state.active_ticker}  \u203a  " if st.session_state.active_ticker else ""
    st.caption(f"{crumb}{active.code} \u2014 {active.title.upper()}   |   TYPE MENU FOR ALL COMMANDS, HELP FOR SYNTAX")

if menu_clicked:
    run_command("MENU")
elif go or typed:
    run_command(typed)

if st.session_state.bar_error:
    st.warning(st.session_state.bar_error)

st.write("")

cmd = registry.get(st.session_state.active_command)
if cmd is None or not cmd.implemented:
    st.info(
        f"{st.session_state.active_command} IS IN THE VOCABULARY BUT NOT BUILT YET. "
        "TYPE MENU TO SEE WHAT IS LIVE."
    )
else:
    cmd.handler(st.session_state.active_ticker)
