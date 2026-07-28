# Terminal

A command-driven financial terminal. Type a ticker, a command, or both.

```
AAPL              snapshot for a ticker
AAPL BOOKS        ticker plus command
BOOKS AAPL        same thing, order does not matter
BOOKS             reuses your last ticker
MENU              index of every command
```

## Architecture

Four modules, deliberately separated:

| File | Responsibility |
|---|---|
| `registry.py` | The command vocabulary — the single source of truth |
| `router.py` | Parsing a typed string into (command, ticker). Pure functions, no Streamlit |
| `screens.py` | One function per screen, uniform signature |
| `app.py` | Shell: theme, login, command bar, dispatch |

### Adding a screen

1. Write `def screen_thing(ticker):` in `screens.py`
2. Add `registry.bind("THING", screen_thing)` at the bottom of that file
3. If the command is new, declare it with `register(...)` in `registry.py`

That's it — the router and MENU pick it up automatically. `app.py` never
needs to change.

Commands declared without a handler render in MENU as PLANNED, so the
menu doubles as a live roadmap.

## Running locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

---

Created by Augustine Villalobos
