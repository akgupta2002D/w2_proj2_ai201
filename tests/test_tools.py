import os

import pytest

from tools import create_fit_card, search_listings, suggest_outfit
from utils.data_loader import get_empty_wardrobe, get_example_wardrobe, load_listings

SAMPLE_ITEM = next(
    item for item in load_listings() if item["id"] == "lst_033"
)


# ── search_listings ───────────────────────────────────────────────────────────

def test_search_returns_results():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert isinstance(results, list)
    assert len(results) > 0


def test_search_empty_results():
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    assert results == []


def test_search_price_filter():
    results = search_listings("jacket", size=None, max_price=10)
    assert all(item["price"] <= 10 for item in results)


def test_search_size_filter():
    results = search_listings("flannel", size="XL")
    assert len(results) > 0
    assert all("XL".lower() in item["size"].lower() for item in results)


# ── suggest_outfit ────────────────────────────────────────────────────────────

@pytest.mark.skipif(
    not os.getenv("GROQ_API_KEY"),
    reason="needs GROQ_API_KEY for LLM integration test",
)
def test_suggest_outfit_empty_wardrobe():
    result = suggest_outfit(SAMPLE_ITEM, get_empty_wardrobe())
    assert isinstance(result, str)
    assert result.strip() != ""


@pytest.mark.skipif(
    not os.getenv("GROQ_API_KEY"),
    reason="needs GROQ_API_KEY for LLM integration test",
)
def test_suggest_outfit_with_wardrobe():
    result = suggest_outfit(SAMPLE_ITEM, get_example_wardrobe())
    assert isinstance(result, str)
    assert result.strip() != ""


# ── create_fit_card ───────────────────────────────────────────────────────────

def test_fit_card_empty_outfit():
    result = create_fit_card("", SAMPLE_ITEM)
    assert result == "Can't create a fit card without an outfit suggestion."


def test_fit_card_whitespace_outfit():
    result = create_fit_card("   ", SAMPLE_ITEM)
    assert result == "Can't create a fit card without an outfit suggestion."


@pytest.mark.skipif(
    not os.getenv("GROQ_API_KEY"),
    reason="needs GROQ_API_KEY for LLM integration test",
)
def test_fit_card_returns_caption():
    outfit = (
        "Pair the faded grey band tee with baggy straight-leg jeans "
        "and chunky white sneakers."
    )
    result = create_fit_card(outfit, SAMPLE_ITEM)
    assert isinstance(result, str)
    assert result.strip() != ""
    assert result != "Can't create a fit card without an outfit suggestion."
