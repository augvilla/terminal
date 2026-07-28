"""
Command registry — the single source of truth for what commands exist.

Every screen is a plain function with the signature:

    def screen_<name>(ticker: str | None) -> None

...that renders itself into the current Streamlit container. Register it
below and the router and MENU pick it up automatically. Adding a screen
should never require touching the router.
"""

from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass
class Command:
    code: str                      # what the user types, e.g. "SNAP"
    title: str                     # human name, e.g. "Snapshot"
    description: str               # one line, shown in MENU
    category: str                  # grouping in MENU
    needs_ticker: bool = True      # does this screen require a symbol?
    handler: Optional[Callable] = field(default=None, repr=False)

    @property
    def implemented(self) -> bool:
        return self.handler is not None


# The full planned vocabulary. Commands without a handler show up in MENU
# as PLANNED — so the menu doubles as a live roadmap.
COMMANDS: dict[str, Command] = {}


def register(code, title, description, category, needs_ticker=True, handler=None):
    COMMANDS[code] = Command(code, title, description, category, needs_ticker, handler)


def bind(code: str, handler: Callable):
    """Attach a handler to an already-declared command."""
    if code in COMMANDS:
        COMMANDS[code].handler = handler


def get(code: str) -> Optional[Command]:
    return COMMANDS.get(code.upper())


def all_codes() -> set:
    return set(COMMANDS.keys())


# --------------------------------------------------------------------------
# Vocabulary
# --------------------------------------------------------------------------

# Company
register("SNAP",   "Snapshot",        "Price, key stats, sector, and company profile",       "Company")
register("CHART",  "Price Chart",     "Interactive price history over a custom range",       "Company")
register("BOOKS",  "Financials",      "Income statement, balance sheet, and cash flow",      "Company")
register("PEERS",  "Peer Comps",      "Comparable-company valuation table",                  "Company")
register("STREET", "Analyst View",    "Ratings, price targets, and consensus estimates",     "Company")
register("EARN",   "Earnings",        "Earnings history, upcoming dates, and surprises",     "Company")
register("DIV",    "Dividends",       "Dividend history, yield, and payout record",          "Company")
register("INSIDE", "Insider Activity","Insider buying and selling from Form 4 filings",      "Company")
register("OWNERS", "Institutions",    "Institutional holders from 13F filings",              "Company")
register("FILES",  "SEC Filings",     "Browse 10-K, 10-Q, 8-K and other filings",            "Company")
register("NEWS",   "Headlines",       "Recent news coverage for the company",                "Company")
register("CHAIN",  "Options Chain",   "Calls and puts by expiry and strike",                 "Company")
register("WEB",    "Relationship Map","Suppliers, customers, and competitors",               "Company")

# Markets & macro
register("PULSE",  "Market Pulse",    "Index levels, breadth, and notable movers",           "Markets", needs_ticker=False)
register("HEAT",   "Heatmap",         "Sector and market performance heatmap",               "Markets", needs_ticker=False)
register("MACRO",  "Economic Data",   "Key macroeconomic indicators and trends",             "Markets", needs_ticker=False)
register("CURVE",  "Yield Curve",     "Treasury yield curve and historical shape",           "Markets", needs_ticker=False)

# Tools
register("SCREEN", "Screener",        "Filter and rate securities on custom criteria",       "Tools",   needs_ticker=False)
register("PORT",   "Portfolio",       "Holdings allocation and exposure breakdown",          "Tools",   needs_ticker=False)
register("CORR",   "Co-Movement",     "Directional agreement between two securities",        "Tools",   needs_ticker=False)
register("HOLD",   "ETF Holdings",    "Underlying holdings and weights for a fund",          "Tools")
register("WATCH",  "Watchlist",       "Your tracked securities at a glance",                 "Tools",   needs_ticker=False)

# Meta
register("MENU",   "Command Index",   "Every available command, searchable",                 "System",  needs_ticker=False)
register("HELP",   "Help",            "How to use the command bar",                          "System",  needs_ticker=False)
