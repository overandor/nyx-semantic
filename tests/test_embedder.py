"""Tests for semantic embedder — query expansion and embedding."""

from nyx.dom import DOMElement
from nyx.embedder import SemanticEmbedder


def _make_elements():
    return [
        DOMElement(index=0, tag="h1", text="Welcome to Example",
                   depth=2, sibling_index=0, child_count=0,
                   x=100, y=100, width=400, height=40),
        DOMElement(index=1, tag="a", text="Learn more",
                   depth=3, sibling_index=0, child_count=0,
                   x=100, y=200, width=120, height=20,
                   attrs={"href": "https://example.com/more"}),
        DOMElement(index=2, tag="input", text="",
                   depth=4, sibling_index=0, child_count=0,
                   x=200, y=300, width=200, height=30,
                   attrs={"type": "email", "placeholder": "Enter email",
                          "name": "email", "aria-label": "Email address"}),
        DOMElement(index=3, tag="button", text="Submit",
                   depth=4, sibling_index=1, child_count=0,
                   x=200, y=340, width=100, height=30,
                   attrs={"type": "submit"}),
    ]


def test_build_corpus():
    emb = SemanticEmbedder()
    elements = _make_elements()
    emb.build_corpus(elements)
    assert emb.element_count == 4
    assert emb.tfidf.vocab_size > 0


def test_embed_dimensions():
    emb = SemanticEmbedder()
    elements = _make_elements()
    emb.build_corpus(elements)
    vec = emb.embed(elements[0])
    assert len(vec) == emb.tfidf.vocab_size + 8


def test_embed_intent_dimensions():
    emb = SemanticEmbedder()
    elements = _make_elements()
    emb.build_corpus(elements)
    vec = emb.embed_intent("find the email input field")
    assert len(vec) == emb.tfidf.vocab_size + 8


def test_query_expansion_email():
    emb = SemanticEmbedder()
    expanded = emb._expand_query("find the email input")
    assert "email" in expanded
    assert "mail" in expanded or "contact" in expanded  # synonym


def test_query_expansion_password():
    emb = SemanticEmbedder()
    expanded = emb._expand_query("find the password field")
    assert "password" in expanded
    assert "pwd" in expanded or "passwd" in expanded  # synonym


def test_query_expansion_empty():
    emb = SemanticEmbedder()
    expanded = emb._expand_query("")
    assert expanded == []


def test_tag_weights():
    assert SemanticEmbedder.TAG_WEIGHTS["input"] == 2.0
    assert SemanticEmbedder.TAG_WEIGHTS["button"] == 2.0
    assert SemanticEmbedder.TAG_WEIGHTS["div"] == 0.5


def test_synonym_groups():
    assert "email" in SemanticEmbedder.SYNONYMS
    assert "password" in SemanticEmbedder.SYNONYMS
    assert "search" in SemanticEmbedder.SYNONYMS
    assert len(SemanticEmbedder.SYNONYMS) >= 20
