# FitFindr

I built FitFindr — a thrift-shopping agent that searches secondhand listings, suggests outfits from your wardrobe, and writes a shareable fit card.

## What I did

I started with `planning.md` before writing any code. I mapped out three tools, the planning loop, and error paths so I wasn't guessing as I built.

Then I implemented each tool in `tools.py` on its own and tested with pytest before touching `agent.py`. That saved me — when the full loop broke, I knew the tools themselves were fine.

Finally I wired everything in `agent.py` and connected the Gradio UI in `app.py`.

## Trial and error

- I tried using an LLM to parse queries but switched to regex — simpler, faster, and I could actually predict what `search_listings` would receive.
- My keyword scorer sometimes ranked the wrong tee first (e.g. Y2K Baby Tee over the band tee). I learned scoring is good enough for a mock dataset but not perfect.
- pytest hides `print()` output by default. I used `pytest tests/ -v -s` when I wanted to see tool logs.
- I hit the macOS `externally-managed-environment` error and fixed it with a local `.venv`.
- The biggest loop bug I almost made: calling all three tools every time. The fix was returning early when `search_listings` returns `[]`.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Add to `.env`:
```
GROQ_API_KEY=your_key_here
```

## Run

```bash
python agent.py    # CLI — happy path + no-results test
python app.py      # Gradio UI
pytest tests/ -v   # tool tests
```

## Project structure

```
agent.py       planning loop + session state
tools.py       search_listings, suggest_outfit, create_fit_card
app.py         Gradio interface
planning.md    my spec
tests/         pytest for each tool
data/          mock listings + wardrobe schema
```

## AI usage

I used Cursor (Claude) at a few key points. I always gave it a specific slice of `planning.md` — not a vague "help me build this" — and reviewed the output before keeping anything.

### 1. `search_listings` in `tools.py`

**What I gave it:** The Tool 1 block from `planning.md` (inputs, return shape, scoring logic, empty-list failure mode) plus the `load_listings()` docstring from `utils/data_loader.py`.

**What it produced:** A `search_listings` function that filters by price and size, scores listings by keyword overlap across `title`, `description`, `style_tags`, and `category`, and returns results sorted by score.

**What I changed:** I added the `[search_listings]` print logs myself because my spec called for terminal tracing. I also split scoring into a `_score_listing` helper to keep the main function readable. I ran pytest on three queries (graphic tee, ballgown under $5, flannel size XL) before moving on — one test failed at first because imports needed `tests/conftest.py`, which I added manually.

### 2. `run_agent` in `agent.py`

**What I gave it:** The Planning Loop, State Management, and Error Handling sections from `planning.md`, the Architecture ASCII diagram, and the `run_agent()` TODO stub already in `agent.py`.

**What it produced:** A session-based planning loop: parse query → `search_listings` → early return if empty → `suggest_outfit` → `create_fit_card`, with `[run_agent]` logs at each step.

**What I changed:** The first draft considered LLM-based query parsing. I overrode that and wrote `_parse_query` with regex instead — I wanted deterministic parsing I could predict and test. I also added filler-word stripping (`"looking for"`, `"how would I style it"`) so those phrases don't end up in the search description. I verified the no-results path with `python agent.py` and confirmed `suggest_outfit` never runs when search returns `[]`.

