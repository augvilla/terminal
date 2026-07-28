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

    Order is fixed: TICKER first, COMMAND second — 'AAPL BOOKS'.

    Fixed order matters because plenty of commands are also real tickers
    (SNAP is Snapchat; DIV, EARN, PORT and HOLD are all listed symbols).
    Position, not the word itself, decides which is which — so 'SNAP SNAP'
    unambiguously means the snapshot screen for Snapchat.

    A lone token is read as a command if it is one, otherwise as a ticker.
    """
    if raw_input is None:
        return ParseResult(error="Type a command. Try MENU to see everything.")

    tokens = [t for t in raw_input.strip().upper().split() if t]
    if not tokens:
        return ParseResult(error="Type a command. Try MENU to see everything.")

    if len(tokens) > 2:
        return ParseResult(error="Too many terms. Use TICKER then COMMAND, e.g. AAPL BOOKS.")

    known = registry.all_codes()

    if len(tokens) == 2:
        ticker_tok, command_tok = tokens
        if command_tok not in known:
            return ParseResult(
                error=f"Invalid command '{command_tok}'. Order is TICKER then COMMAND. Type MENU to see them."
            )
        command = command_tok
        ticker = normalize_ticker(ticker_tok)
    else:
        lone = tokens[0]
        if lone in known:
            command = lone
            ticker = None
        else:
            command = DEFAULT_COMMAND
            ticker = normalize_ticker(lone)

    cmd = registry.get(command)

    # Command needs a symbol but none was given — fall back to the last one.
    if cmd.needs_ticker and ticker is None:
        if last_ticker:
            ticker = last_ticker
        else:
            return ParseResult(error=f"{command} needs a ticker. Try: AAPL {command}")

    # Command takes no symbol but one was supplied — ignore it rather than fail.
    if not cmd.needs_ticker:
        ticker = None

    return ParseResult(command=command, ticker=ticker)
