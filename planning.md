# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## Tools

List every tool your agent will use. For each tool, fill in all four fields.
You must have at least 3 tools. The three required tools are listed — add any additional tools below them.

### Tool 1: search_listings

**What it does:**
Filters mock listings by optional size and max price, then scores remaining items by keyword overlap with `description` across `title`, `description`, `style_tags`, and `category`. Returns matches sorted by score (best first).

**Input parameters:**
- `description` (str): Keywords to search for (case-insensitive).
- `size` (str | None): If set, listing `size` must contain this string (e.g. `"M"` matches `"S/M"`). If `None`, skip.
- `max_price` (float | None): If set, exclude listings above this price. If `None`, skip.

**What it returns:**
`list[dict]` of full listing objects from `listings.json` (`id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, `platform`), sorted by relevance. Returns `[]` if nothing matches — never raises.

**What happens if it fails or returns nothing:**
Agent sets `session["error"]` with a message suggesting broader filters, leaves downstream fields `None`, and returns early. Does not call `suggest_outfit` or `create_fit_card`.

---

### Tool 2: suggest_outfit

**What it does:**
Suggests 1–2 outfits pairing a thrift find with the user's wardrobe via Groq. Names specific wardrobe pieces by `name` when available; gives general styling advice if wardrobe is empty.

**Input parameters:**
- `new_item` (dict): A listing dict from `search_listings`.
- `wardrobe` (dict): `{"items": [...]}` — each item has `id`, `name`, `category`, `colors`, `style_tags`, optional `notes`.

**What it returns:**
Non-empty `str` with styling advice (2–5 sentences). Never raises or returns `""`.

**What happens if it fails or returns nothing:**
Empty wardrobe is not a failure — tool still returns general advice. On LLM failure, agent sets `session["error"]` and returns without calling `create_fit_card`.

---

### Tool 3: create_fit_card

**What it does:**
Generates a casual 2–4 sentence social caption for the find + outfit via Groq (higher temperature for variety). Mentions title, price, and platform naturally.

**Input parameters:**
- `outfit` (str): Output from `suggest_outfit`.
- `new_item` (dict): The listing dict.

**What it returns:**
Caption `str`, or `"Can't create a fit card without an outfit suggestion."` if `outfit` is empty. Never raises.

**What happens if it fails or returns nothing:**
If outfit is missing, tool returns the error string above. Agent sets `session["error"]` and returns. On LLM failure, agent sets `session["error"]` and returns.

---

### Additional Tools (if any)

None.

---

## Planning Loop

**How does your agent decide which tool to call next?**

Fixed sequence: search → suggest → fit card. Early return only on errors.

1. `_new_session(query, wardrobe)` — create session.
2. **Parse query** with regex: extract `max_price` (e.g. `under $30`), `size` (e.g. `size M`), and remaining text as `description`. Store in `session["parsed"]`.
3. **`search_listings(parsed...)`** → `session["search_results"]`.
   - If empty → set `session["error"]`, return.
   - Else → `session["selected_item"] = search_results[0]`.
4. **`suggest_outfit(selected_item, wardrobe)`** → `session["outfit_suggestion"]`. On LLM error → set `session["error"]`, return.
5. **`create_fit_card(outfit_suggestion, selected_item)`** → `session["fit_card"]`. If result starts with `"Can't create"` or LLM fails → set `session["error"]`, return.
6. Return session with `error = None`.

Throughout the loop, print a **descriptive terminal log** at each step — parsed params, tool calls (name + inputs), result summaries (match count, selected item title, outfit/fit card previews), and any early-exit errors. This makes the agent's decision path visible when running `python agent.py` or the Streamlit app.

---

## State Management

**How does information from one tool get passed to the next?**

Everything lives in one `session` dict from `_new_session()`:

`parsed` → `search_results` → `selected_item` → `outfit_suggestion` → `fit_card`

`wardrobe` is passed in at init and used by `suggest_outfit`. `error` is set on any early exit; caller checks it first.

**Terminal logging:** `agent.py` and `tools.py` will use `print()` statements to log each step to the terminal — what was parsed, which tool ran, what it returned, and why the loop stopped (success or error). Logs should be detailed enough to trace a full run without reading the session dict.

---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results | Set error: *"No listings matched. Try raising your budget, dropping size, or fewer keywords."* Return early — no downstream calls. |
| suggest_outfit | Empty wardrobe | Not an error. Tool gives general advice; agent continues. |
| suggest_outfit | LLM failure | Set error: *"Couldn't generate an outfit suggestion. Please try again."* Return early. |
| create_fit_card | Missing outfit | Tool returns error string. Agent sets `session["error"]`, returns. |
| create_fit_card | LLM failure | Set error: *"Couldn't generate a fit card. Please try again."* Return. |

---

## Architecture

```
User query + wardrobe
        │
        ▼
Planning Loop (run_agent)
        │
        ├─► Parse query (regex) ──► Session: parsed
        │
        ├─► search_listings(description, size, max_price)
        │       ├── results = [] ──► [ERROR] ──► return session
        │       └── results = [item, …] ──► selected_item = results[0]
        │
        ├─► suggest_outfit(selected_item, wardrobe) ──► outfit_suggestion
        │
        └─► create_fit_card(outfit_suggestion, selected_item)
                ├── outfit missing ──► [ERROR] ──► return session
                └── fit_card set ──► return session (error = None)
```

---

## AI Tool Plan

**Milestone 3 — Individual tool implementations:**

- **`search_listings`:** Give Claude the Tool 1 spec + `load_listings()`. Verify it filters all three params, scores by keywords, returns `[]` on no match. Test: graphic tee under $30 (hits), ballgown under $5 (empty), flannel size XL.
- **`suggest_outfit`:** Give Claude Tool 2 spec + wardrobe schema + `_get_groq_client()`. Verify empty vs populated wardrobe paths. Test with `get_example_wardrobe()` and `get_empty_wardrobe()`.
- **`create_fit_card`:** Give Claude Tool 3 spec + docstring guidelines. Verify empty-outfit guard and caption mentions title/price/platform. Test with sample outfit + `lst_033`.

**Milestone 4 — Planning loop and state management:**

Give Claude the Planning Loop, State Management, Error Handling, and Architecture sections + `agent.py` stubs. Verify empty search returns early, happy path fills all session keys, and terminal prints show each step clearly. Run `python agent.py` for both paths.

---

## A Complete Interaction (Step by Step)

Write out what a full user interaction looks like from start to finish — tool call by tool call. Use a specific example query.

**What FitFindr does:** FitFindr finds thrift listings, styles the top match with the user's wardrobe, and writes a shareable fit card. `search_listings` runs first on the user's query; if it finds matches, `suggest_outfit` and `create_fit_card` follow. If search returns nothing, the agent explains what to try and stops.

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1:** Parse → `description="vintage graphic tee"`, `max_price=30.0`. Call `search_listings("vintage graphic tee", max_price=30.0)`. Top result: `lst_033` — Vintage Band Tee, $19, depop. Set `selected_item = results[0]`.

**Step 2:** Call `suggest_outfit(lst_033, get_example_wardrobe())`. Returns advice pairing the tee with baggy jeans (`w_001`) and chunky sneakers (`w_007`).

**Step 3:** Call `create_fit_card(outfit, lst_033)`. Returns a casual caption mentioning the tee, $19, and depop.

**Final output to user:** The found item (title, price, platform, condition), outfit advice, and fit card caption.

**Error path:** Query *"vintage graphic tee size XXS under $5"* → `search_listings` returns `[]` → agent sets error and returns. `suggest_outfit` and `create_fit_card` are never called.
