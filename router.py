"""
Command parsing and routing.

Pure functions — no Streamlit imports — so the parsing rules can be tested
directly. The app layer handles rendering and session state.
"""

from dataclasses import dataclass
from typing import Optional

import registry

DEFAULT_COMMAND = "SNAP"

CRYPTO_ALIASES = {
    "BTC": "BTC-USD", "ETH": "ETH-USD", "SOL": "SOL-USD",
    "DOGE": "DOGE-USD", "ADA": "ADA-USD", "XRP": "XRP-USD",
    "LTC": "LTC-USD", "AVAX": "AVAX-USD",
}


@dataclass
class ParseResult:
    command: Optional[str] = None      # resolved command code, e.g. "SNAP"
    ticker: Optional[str] = None       # resolved symbol, e.g. "AAPL"
    error: Optional[str] = None        # human-readable problem, if any


def normalize_ticker(raw: str) -> str:
    t = raw.strip().upper()
    return CRYPTO_ALIASES.get(t, t)


def parse(raw_input: str, last_ticker: Optional[str] = None) -> ParseResult:
    """Turn a typed command string into a (command, ticker) pair.

    Order-independent: 'AAPL BOOKS' and 'BOOKS AAPL' are equivalent.
    A bare ticker defaults to the snapshot screen. A bare command reuses
    the last ticker you looked at, when it needs one.
    """
    if raw_input is None:
        return ParseResult(error="Type a command. Try MENU to see everything.")

    tokens = [t for t in raw_input.strip().upper().split() if t]
    if not tokens:
        return ParseResult(error="Type a command. Try MENU to see everything.")

    if len(tokens) > 2:
        return ParseResult(
            error=f"Too many terms ({len(tokens)}). Use one ticker and one command, e.g. AAPL BOOKS."
        )

    known = registry.all_codes()
    commands = [t for t in tokens if t in known]
    others = [t for t in tokens if t not in known]

    if len(commands) > 1:
        return ParseResult(error=f"Two commands given ({', '.join(commands)}). Pick one.")

    command = commands[0] if commands else None
    ticker = normalize_ticker(others[0]) if others else None

    # A lone unrecognized token: assume it's a ticker and show the snapshot.
    if command is None:
        if ticker is None:
            return ParseResult(error="Nothing recognized. Try MENU.")
        command = DEFAULT_COMMAND

    cmd = registry.get(command)

    # Command needs a symbol but none was given — fall back to the last one.
    if cmd.needs_ticker and ticker is None:
        if last_ticker:
            ticker = last_ticker
        else:
            return ParseResult(
                command=command,
                error=f"{command} needs a ticker. Try: AAPL {command}",
            )

    # Command takes no symbol but one was supplied — ignore it rather than fail.
    if not cmd.needs_ticker:
        ticker = None

    return ParseResult(command=command, ticker=ticker)


def suggest(unknown: str, limit: int = 3) -> list:
    """Closest command codes to a typo, for 'did you mean' hints."""
    import difflib
    return difflib.get_close_matches(unknown.upper(), sorted(registry.all_codes()), n=limit, cutoff=0.5)
