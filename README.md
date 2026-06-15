# FitFindr

I built FitFindr — a thrift-shopping agent that searches secondhand listings, suggests outfits from your wardrobe, and writes a shareable fit card.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Add to `.env`: `GROQ_API_KEY=your_key_here`

```bash
python agent.py    # CLI test
python app.py      # Gradio UI
pytest tests/ -v   # tool tests
```

---

## Tool inventory

### `search_listings(description: str, size: str | None = None, max_price: float | None = None) -> list[dict]`

**Purpose:** Search mock listings by keywords, optional size, and optional price ceiling.

**Inputs:**
- `description` (str) — keywords to match
- `size` (str | None) — substring match on listing size; `None` skips filter
- `max_price` (float | None) — max price inclusive; `None` skips filter

**Output:** `list[dict]` of full listing objects sorted by relevance score. Each dict has `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, `platform`. Returns `[]` if nothing matches.

### `suggest_outfit(new_item: dict, wardrobe: dict) -> str`

**Purpose:** Suggest 1–2 outfits pairing a thrift find with the user's wardrobe via Groq (`llama-3.3-70b-versatile`).

**Inputs:**
- `new_item` (dict) — a listing dict from `search_listings`
- `wardrobe` (dict) — `{"items": [...]}` where each item has `id`, `name`, `category`, `colors`, `style_tags`, optional `notes`

**Output:** `str` — non-empty styling advice. General advice if wardrobe is empty; names specific pieces otherwise.

### `create_fit_card(outfit: str, new_item: dict) -> str`

**Purpose:** Generate a casual 2–4 sentence social caption for the find + outfit.

**Inputs:**
- `outfit` (str) — output from `suggest_outfit`
- `new_item` (dict) — the listing dict

**Output:** `str` — caption, or `"Can't create a fit card without an outfit suggestion."` if `outfit` is empty/whitespace.

---

## Planning loop

`run_agent(query: str, wardrobe: dict) -> dict` runs a fixed sequence with conditional early exits:

1. Create session via `_new_session()`.
2. Parse query with regex → `session["parsed"]` (`description`, `size`, `max_price`).
3. Call `search_listings(...)`.
   - **If `search_results` is empty** → set `session["error"]`, return immediately. `suggest_outfit` and `create_fit_card` are **not** called.
   - **Else** → `session["selected_item"] = search_results[0]`.
4. Call `suggest_outfit(selected_item, wardrobe)`.
   - **On LLM exception** → set `session["error"]`, return.
5. Call `create_fit_card(outfit_suggestion, selected_item)`.
   - **If result starts with `"Can't create"`** → set `session["error"]`, return.
   - **On LLM exception** → set `session["error"]`, return.
6. Set `session["fit_card"]`, return with `error = None`.

The loop does not re-plan mid-run. The only branch that changes behavior is whether search returns results.

---

## State management

Everything lives in one `session` dict:

| Key | When set | Passed to |
|-----|----------|-----------|
| `query` | init | error messages |
| `parsed` | after regex parse | `search_listings` |
| `search_results` | after search | empty-check, `selected_item` |
| `selected_item` | `search_results[0]` | `suggest_outfit`, `create_fit_card` |
| `wardrobe` | init (from caller) | `suggest_outfit` |
| `outfit_suggestion` | after suggest | `create_fit_card` |
| `fit_card` | after fit card | UI output |
| `error` | on early exit | caller checks first |

Flow: `parsed` → `search_results` → `selected_item` → `outfit_suggestion` → `fit_card`

---

## Error handling

| Tool | Failure | What happens |
|------|---------|--------------|
| `search_listings` | No matches | Returns `[]`. Agent sets error, returns early. |
| `suggest_outfit` | Empty wardrobe | Not an error — returns general advice. |
| `suggest_outfit` | LLM failure | Agent sets error, returns early. |
| `create_fit_card` | Empty outfit | Returns error string. Agent sets `session["error"]`. |
| `create_fit_card` | LLM failure | Agent sets error, returns early. |

**Examples from my testing:**

- `test_search_empty_results`: `search_listings("designer ballgown", size="XXS", max_price=5)` → `[]`, no exception.
- `python agent.py` no-results path: `"designer ballgown size XXS under $5"` → `session["error"]` set, `session["fit_card"]` is `None`, no `[suggest_outfit]` logs in terminal.
- `test_fit_card_empty_outfit`: `create_fit_card("", item)` → `"Can't create a fit card without an outfit suggestion."`, no LLM call.

---

## Spec reflection

**How the spec helped:** Writing the planning loop branches in `planning.md` before coding stopped me from calling all three tools unconditionally. I knew exactly where to early-return.

**Where I diverged:** My walkthrough expected `lst_033` (Vintage Band Tee) as the top graphic tee result, but keyword scoring ranked Y2K Baby Tee first. I kept simple word-count scoring instead of weighting `style_tags` higher — good enough for the assignment, not perfect relevance.

---

## AI usage

I used Cursor (Claude) at key points and always gave it a specific `planning.md` section, not a vague prompt.

### 1. `search_listings` in `tools.py`

**What I gave it:** Tool 1 spec (inputs, return shape, scoring, failure mode) + `load_listings()` docstring.

**What it produced:** Filter + keyword-score implementation sorted by relevance.

**What I changed:** Added `[search_listings]` print logs, split `_score_listing` helper, and wrote `tests/conftest.py` after pytest couldn't import `tools`.

### 2. `run_agent` in `agent.py`

**What I gave it:** Planning Loop, State Management, Error Handling sections, Architecture ASCII diagram, and the `agent.py` stub.

**What it produced:** Session-based loop with early return on empty search.

**What I changed:** Rejected LLM query parsing for regex `_parse_query` with filler-word stripping. Verified with `python agent.py` that the no-results path never calls downstream tools.

---

## Project structure

```
agent.py       planning loop + session state
tools.py       search_listings, suggest_outfit, create_fit_card
app.py         Gradio interface
planning.md    my spec
tests/         pytest for each tool
data/          mock listings + wardrobe schema
```
