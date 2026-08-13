"""Tests for semantic locator — find, self-healing, stats."""

from nyx.dom import DOMElement
from nyx.locator import SemanticLocator, SemanticMatch


def _make_elements():
    return [
        DOMElement(
            index=0,
            tag="h1",
            text="Example Domain",
            depth=2,
            sibling_index=0,
            child_count=0,
            x=100,
            y=100,
            width=400,
            height=40,
        ),
        DOMElement(
            index=1,
            tag="p",
            text="This domain is for use in illustrative examples",
            depth=2,
            sibling_index=1,
            child_count=0,
            x=100,
            y=160,
            width=400,
            height=60,
        ),
        DOMElement(
            index=2,
            tag="a",
            text="More information...",
            depth=3,
            sibling_index=0,
            child_count=0,
            x=100,
            y=240,
            width=150,
            height=20,
            attrs={"href": "https://www.iana.org/domains/example"},
        ),
        DOMElement(
            index=3,
            tag="input",
            text="",
            depth=4,
            sibling_index=0,
            child_count=0,
            x=200,
            y=300,
            width=200,
            height=30,
            attrs={
                "type": "email",
                "placeholder": "Enter your email",
                "name": "email",
                "aria-label": "Email address",
            },
        ),
        DOMElement(
            index=4,
            tag="button",
            text="Submit",
            depth=4,
            sibling_index=1,
            child_count=0,
            x=200,
            y=340,
            width=100,
            height=30,
            attrs={"type": "submit"},
        ),
    ]


def test_build_index():
    locator = SemanticLocator()
    elements = _make_elements()
    locator.build_index(elements)
    stats = locator.stats()
    assert stats["elements"] == 5
    assert stats["vocabulary_size"] > 0
    assert stats["embedding_dim"] > 0


def test_build_index_empty():
    locator = SemanticLocator()
    locator.build_index([])
    assert locator.stats()["elements"] == 0
    assert locator.find("anything") == []


def test_find_heading():
    locator = SemanticLocator()
    locator.build_index(_make_elements())
    matches = locator.find("find the main heading title", top_k=3)
    assert len(matches) > 0
    top = matches[0]
    assert top.rank == 1
    assert top.element.tag in ("h1", "h2", "h3", "div")
    assert "example" in top.element.text.lower()


def test_find_link():
    locator = SemanticLocator()
    locator.build_index(_make_elements())
    matches = locator.find("find the more information link", top_k=3)
    assert len(matches) > 0
    top = matches[0]
    assert top.element.tag == "a"
    assert "more" in top.element.text.lower()


def test_find_email_input():
    locator = SemanticLocator()
    locator.build_index(_make_elements())
    matches = locator.find("find the email input field", top_k=3)
    assert len(matches) > 0
    top = matches[0]
    assert top.element.tag == "input"


def test_find_submit_button():
    locator = SemanticLocator()
    locator.build_index(_make_elements())
    matches = locator.find("find the submit button", top_k=3)
    assert len(matches) > 0
    top = matches[0]
    assert top.element.tag == "button"


def test_find_one():
    locator = SemanticLocator()
    locator.build_index(_make_elements())
    match = locator.find_one("find the email input field")
    assert match is not None
    assert match.element.tag == "input"


def test_find_one_no_results():
    locator = SemanticLocator()
    locator.build_index(_make_elements())
    # Empty index after rebuild
    locator.build_index([])
    assert locator.find_one("anything") is None


def test_matched_terms():
    locator = SemanticLocator()
    locator.build_index(_make_elements())
    matches = locator.find("find the email input field", top_k=1)
    assert len(matches) > 0
    # Should have some matched terms
    assert isinstance(matches[0].matched_terms, list)


def test_confidence():
    match = SemanticMatch(
        element=_make_elements()[0],
        score=0.85,
        rank=1,
        matched_terms=["example"],
    )
    assert match.confidence == 85


def test_self_heal_same_element():
    """After redesign (class rename, ID removal, restructure),
    the same element should be found by semantic meaning."""
    locator = SemanticLocator()
    locator.build_index(_make_elements())

    # Redesigned: different depth, position, size, but same text/tag/attrs.
    redesigned = [
        DOMElement(
            index=0,
            tag="h1",
            text="Example Domain",
            depth=3,
            sibling_index=0,
            child_count=0,
            x=50,
            y=80,
            width=500,
            height=50,
        ),
        DOMElement(
            index=1,
            tag="p",
            text="This domain is for use in illustrative examples",
            depth=3,
            sibling_index=1,
            child_count=0,
            x=50,
            y=140,
            width=500,
            height=70,
        ),
        DOMElement(
            index=2,
            tag="a",
            text="More information...",
            depth=5,
            sibling_index=0,
            child_count=0,
            x=50,
            y=230,
            width=180,
            height=25,
            attrs={"href": "https://www.iana.org/domains/example"},
        ),
        DOMElement(
            index=3,
            tag="input",
            text="",
            depth=6,
            sibling_index=0,
            child_count=0,
            x=150,
            y=320,
            width=250,
            height=35,
            attrs={
                "type": "email",
                "placeholder": "Enter your email",
                "name": "email",
                "aria-label": "Email address",
            },
        ),
        DOMElement(
            index=4,
            tag="button",
            text="Submit",
            depth=6,
            sibling_index=1,
            child_count=0,
            x=150,
            y=365,
            width=120,
            height=35,
            attrs={"type": "submit"},
        ),
    ]

    before_score, after_score, same = locator.self_heal_test(
        "find the more information link", redesigned
    )
    assert before_score > 0
    assert after_score > 0
    assert same is True


def test_stats_tags():
    locator = SemanticLocator()
    locator.build_index(_make_elements())
    stats = locator.stats()
    assert "h1" in stats["tags"]
    assert "a" in stats["tags"]
    assert "input" in stats["tags"]
    assert "button" in stats["tags"]


def test_top_k_limit():
    locator = SemanticLocator()
    locator.build_index(_make_elements())
    matches = locator.find("find elements", top_k=2)
    assert len(matches) <= 2
