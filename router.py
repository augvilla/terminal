"""
Command parsing and routing.

Pure functions — no Streamlit imports — so the parsing rules can be tested
directly. The app layer handles rendering and session state.
"""

import difflib
from dataclasses import dataclass
from typing import Optional

import registry

DEFAULT_COMMAND = "SNAP"

# A lone unknown token scoring at or above this against a command name is
# treated as a typo rather than a ticker. Measured separation is wide:
# real tickers score ~0.0, plausible typos score ~0.85+.
TYPO_CUTOFF = 0.75

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


def suggest(unknown: str, limit: int = 3, cutoff: float = 0.5) -> list:
    """Closest command codes to a typo, for 'did you mean' hints."""
    return difflib.get_close_matches(
        unknown.upper(), sorted(registry.all_codes()), n=limit, cutoff=cutoff
    )


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

    # Some tickers share a command name (SNAP is Snapchat, DIV and EARN are
    # real funds). Typing it twice — 'SNAP SNAP' — means command + ticker.
    if len(commands) == 2 and commands[0] == commands[1]:
        commands = [commands[0]]
        others = [commands[0]]
    elif len(commands) > 1:
        return ParseResult(error=f"Two commands given ({', '.join(commands)}). Pick one.")

    command = commands[0] if commands else None
    ticker = normalize_ticker(others[0]) if others else None

    if command is None:
        if ticker is None:
            return ParseResult(error="Nothing recognized. Try MENU.")
        # A lone unknown token is normally a ticker — but if it closely
        # resembles a command, it is almost certainly a typo. Say so rather
        # than sending a nonexistent symbol off to the data provider.
        hints = suggest(ticker, cutoff=TYPO_CUTOFF)
        if hints:
            return ParseResult(
                error=f"Unknown command '{ticker}'. Did you mean: {', '.join(hints)}?"
            )
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
