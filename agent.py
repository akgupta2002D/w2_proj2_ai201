"""
agent.py

The FitFindr planning loop. Orchestrates the three tools in response to a
natural language user query, passing state between them via a session dict.

Complete tools.py and test each tool in isolation before implementing this file.

Usage (once implemented):
    from agent import run_agent
    from utils.data_loader import get_example_wardrobe

    result = run_agent(
        query="vintage graphic tee under $30, size M",
        wardrobe=get_example_wardrobe(),
    )
    print(result["fit_card"])
    print(result["error"])   # None on success
"""

import re

from tools import create_fit_card, search_listings, suggest_outfit


# ── session state ─────────────────────────────────────────────────────────────

def _new_session(query: str, wardrobe: dict) -> dict:
    """
    Initialize and return a fresh session dict for one user interaction.

    The session dict is the single source of truth for everything that happens
    during a run — it stores the original query, parsed parameters, tool results,
    and any error that caused early termination.

    You may add fields to this dict as needed for your implementation.
    """
    return {
        "query": query,              # original user query
        "parsed": {},                # extracted description / size / max_price
        "search_results": [],        # list of matching listing dicts
        "selected_item": None,       # top result, passed into suggest_outfit
        "wardrobe": wardrobe,        # user's wardrobe dict
        "outfit_suggestion": None,   # string returned by suggest_outfit
        "fit_card": None,            # string returned by create_fit_card
        "error": None,               # set if the interaction ended early
    }


# ── query parsing ─────────────────────────────────────────────────────────────

_PRICE_PATTERN = re.compile(
    r"(?:under|below|max|less than)\s*\$?(\d+(?:\.\d+)?)",
    re.IGNORECASE,
)
_SIZE_PATTERN = re.compile(r"\bsize\s+(\S+)", re.IGNORECASE)
_FILLER_PATTERN = re.compile(
    r"\b(looking for|i'm looking for|i am looking for|i want|"
    r"what's out there|how would i style it|show me)\b",
    re.IGNORECASE,
)


def _parse_query(query: str) -> dict:
    """Extract description, size, and max_price from a natural-language query."""
    text = query.strip()
    max_price = None
    size = None

    price_match = _PRICE_PATTERN.search(text)
    if price_match:
        max_price = float(price_match.group(1))
        text = text[: price_match.start()] + text[price_match.end() :]

    size_match = _SIZE_PATTERN.search(text)
    if size_match:
        size = size_match.group(1).rstrip(".,;")
        text = text[: size_match.start()] + text[size_match.end() :]

    description = _FILLER_PATTERN.sub("", text)
    description = re.sub(r"\s+", " ", description).strip(" ,.-")
    if not description:
        description = query.strip()

    return {"description": description, "size": size, "max_price": max_price}


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Main agent entry point. Runs the FitFindr planning loop for a single
    user interaction and returns the completed session dict.

    Args:
        query:    Natural language user request
                  (e.g., "vintage graphic tee under $30, size M")
        wardrobe: User's wardrobe dict — use get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py

    Returns:
        The session dict after the interaction completes. Check session["error"]
        first — if it is not None, the interaction ended early and the other
        output fields (outfit_suggestion, fit_card) will be None.

    TODO — implement this function using the planning loop you designed in planning.md:

        Step 1: Initialize the session with _new_session().

        Step 2: Parse the user's query to extract a description, size, and
                max_price. You can use regex, string splitting, or ask the LLM
                to parse it — document your choice in planning.md.
                Store the result in session["parsed"].

        Step 3: Call search_listings() with the parsed parameters.
                Store results in session["search_results"].
                If no results: set session["error"] to a helpful message and
                return the session early. Do NOT proceed to suggest_outfit
                with empty input.

        Step 4: Select the item to use (e.g., the top result).
                Store it in session["selected_item"].

        Step 5: Call suggest_outfit() with the selected item and wardrobe.
                Store the result in session["outfit_suggestion"].

        Step 6: Call create_fit_card() with the outfit suggestion and selected item.
                Store the result in session["fit_card"].

        Step 7: Return the session.

    Before writing code, complete the Planning Loop and State Management sections
    of planning.md — your implementation should match what you described there.
    """
    session = _new_session(query, wardrobe)
    print(f"[run_agent] query={query!r}")

    session["parsed"] = _parse_query(query)
    parsed = session["parsed"]
    print(
        f"[run_agent] parsed description={parsed['description']!r}, "
        f"size={parsed['size']!r}, max_price={parsed['max_price']}"
    )

    session["search_results"] = search_listings(
        parsed["description"],
        size=parsed["size"],
        max_price=parsed["max_price"],
    )
    print(f"[run_agent] search returned {len(session['search_results'])} result(s)")

    if not session["search_results"]:
        price_clause = f" under ${parsed['max_price']:.0f}" if parsed["max_price"] else ""
        size_clause = f", size {parsed['size']}" if parsed["size"] else ""
        session["error"] = (
            f"No listings matched '{parsed['description']}'{price_clause}{size_clause}. "
            "Try raising your budget, dropping the size filter, or using fewer keywords."
        )
        print(f"[run_agent] early exit — {session['error']}")
        return session

    session["selected_item"] = session["search_results"][0]
    print(f"[run_agent] selected_item={session['selected_item']['title']!r}")

    try:
        session["outfit_suggestion"] = suggest_outfit(
            session["selected_item"], session["wardrobe"]
        )
    except Exception as exc:
        session["error"] = "Couldn't generate an outfit suggestion. Please try again."
        print(f"[run_agent] early exit — {session['error']} ({exc})")
        return session

    print(
        f"[run_agent] outfit_suggestion preview: "
        f"{session['outfit_suggestion'][:100]!r}..."
    )

    try:
        fit_card = create_fit_card(
            session["outfit_suggestion"], session["selected_item"]
        )
    except Exception as exc:
        session["error"] = "Couldn't generate a fit card. Please try again."
        print(f"[run_agent] early exit — {session['error']} ({exc})")
        return session

    if fit_card.startswith("Can't create"):
        session["error"] = fit_card
        print(f"[run_agent] early exit — {session['error']}")
        return session

    session["fit_card"] = fit_card
    print(f"[run_agent] fit_card preview: {session['fit_card'][:100]!r}...")
    print("[run_agent] done — error=None")
    return session


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

    print("=== Happy path: graphic tee ===\n")
    session = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )
    if session["error"]:
        print(f"Error: {session['error']}")
    else:
        print(f"Found: {session['selected_item']['title']}")
        print(f"\nOutfit: {session['outfit_suggestion']}")
        print(f"\nFit card: {session['fit_card']}")

    print("\n\n=== No-results path ===\n")
    session2 = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    print(f"Error message: {session2['error']}")
    print(f"fit_card is None: {session2['fit_card'] is None}")
