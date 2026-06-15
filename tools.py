"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import os

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()


# ── Groq client ───────────────────────────────────────────────────────────────

GROQ_MODEL = "llama-3.3-70b-versatile"


def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def _score_listing(listing: dict, keywords: list[str]) -> int:
    """Count keyword matches across searchable listing fields."""
    searchable = " ".join(
        [
            listing.get("title", ""),
            listing.get("description", ""),
            listing.get("category", ""),
            " ".join(listing.get("style_tags", [])),
        ]
    ).lower()

    return sum(1 for kw in keywords if kw in searchable)


def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Args:
        description: Keywords describing what the user is looking for
                     (e.g., "vintage graphic tee").
        size:        Size string to filter by, or None to skip size filtering.
                     Matching is case-insensitive (e.g., "M" matches "S/M").
        max_price:   Maximum price (inclusive), or None to skip price filtering.

    Returns:
        A list of matching listing dicts, sorted by relevance (best match first).
        Returns an empty list if nothing matches — does NOT raise an exception.

    Each listing dict has the following fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand, platform
    """
    print(
        f"[search_listings] description={description!r}, "
        f"size={size!r}, max_price={max_price}"
    )

    keywords = [kw.lower() for kw in description.split() if kw.strip()]
    listings = load_listings()
    print(f"[search_listings] loaded {len(listings)} listings")

    filtered = []
    for listing in listings:
        if max_price is not None and listing["price"] > max_price:
            continue
        if size is not None and size.lower() not in listing["size"].lower():
            continue
        filtered.append(listing)

    print(f"[search_listings] {len(filtered)} listings after price/size filters")

    scored = []
    for listing in filtered:
        score = _score_listing(listing, keywords)
        if score > 0:
            scored.append((score, listing))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    results = [listing for _, listing in scored]

    if results:
        top = results[0]
        top_score = scored[0][0]
        print(
            f"[search_listings] {len(results)} match(es); "
            f"top result: {top['title']!r} (score={top_score})"
        )
    else:
        print("[search_listings] no matches found")

    return results


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def _format_wardrobe_items(wardrobe: dict) -> str:
    lines = []
    for item in wardrobe.get("items", []):
        tags = ", ".join(item.get("style_tags", []))
        notes = item.get("notes") or ""
        note_suffix = f" ({notes})" if notes else ""
        lines.append(
            f"- {item['name']} [{item['category']}] — colors: "
            f"{', '.join(item.get('colors', []))}; tags: {tags}{note_suffix}"
        )
    return "\n".join(lines)


def _call_groq(prompt: str, temperature: float = 0.7) -> str:
    client = _get_groq_client()
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
    )
    return response.choices[0].message.content.strip()


def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.

    Args:
        new_item: A listing dict (the item the user is considering buying).
        wardrobe: A wardrobe dict with an 'items' key containing a list of
                  wardrobe item dicts. May be empty — handle this gracefully.

    Returns:
        A non-empty string with outfit suggestions.
        If the wardrobe is empty, offer general styling advice for the item
        rather than raising an exception or returning an empty string.
    """
    items = wardrobe.get("items", [])
    print(
        f"[suggest_outfit] item={new_item.get('title')!r}, "
        f"wardrobe_items={len(items)}"
    )

    item_details = (
        f"Title: {new_item['title']}\n"
        f"Category: {new_item['category']}\n"
        f"Style tags: {', '.join(new_item.get('style_tags', []))}\n"
        f"Colors: {', '.join(new_item.get('colors', []))}\n"
        f"Description: {new_item['description']}"
    )

    if not items:
        print("[suggest_outfit] empty wardrobe — using general styling prompt")
        prompt = (
            "You are a thrift fashion stylist. The user has no wardrobe saved yet.\n\n"
            f"New thrift find:\n{item_details}\n\n"
            "Suggest 1–2 outfit ideas using general item types (not specific owned pieces). "
            "Describe the vibe and how to style it. Keep it to 2–5 sentences."
        )
    else:
        print("[suggest_outfit] populated wardrobe — using specific pieces prompt")
        wardrobe_text = _format_wardrobe_items(wardrobe)
        prompt = (
            "You are a thrift fashion stylist.\n\n"
            f"New thrift find:\n{item_details}\n\n"
            f"User's wardrobe:\n{wardrobe_text}\n\n"
            "Suggest 1–2 complete outfits pairing the new item with specific pieces "
            "from their wardrobe by name. Include one styling tip. Keep it to 2–5 sentences."
        )

    result = _call_groq(prompt, temperature=0.7)
    preview = result[:120] + ("..." if len(result) > 120 else "")
    print(f"[suggest_outfit] response preview: {preview!r}")
    return result


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

FIT_CARD_ERROR = "Can't create a fit card without an outfit suggestion."


def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.

    Args:
        outfit:   The outfit suggestion string from suggest_outfit().
        new_item: The listing dict for the thrifted item.

    Returns:
        A 2–4 sentence string usable as an Instagram/TikTok caption.
        If outfit is empty or missing, return a descriptive error message
        string — do NOT raise an exception.
    """
    print(
        f"[create_fit_card] item={new_item.get('title')!r}, "
        f"outfit_length={len(outfit.strip()) if outfit else 0}"
    )

    if not outfit or not outfit.strip():
        print(f"[create_fit_card] guard hit — returning error: {FIT_CARD_ERROR!r}")
        return FIT_CARD_ERROR

    prompt = (
        "Write a casual, authentic Instagram/TikTok outfit caption (2–4 sentences).\n\n"
        f"Thrift find: {new_item['title']}\n"
        f"Price: ${new_item['price']:.2f}\n"
        f"Platform: {new_item['platform']}\n"
        f"Outfit suggestion: {outfit}\n\n"
        "Mention the item name, price, and platform naturally once each. "
        "Sound like a real OOTD post, not a product listing. No hashtags."
    )

    result = _call_groq(prompt, temperature=0.9)
    preview = result[:120] + ("..." if len(result) > 120 else "")
    print(f"[create_fit_card] caption preview: {preview!r}")
    return result
