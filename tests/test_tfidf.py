"""Tests for TF-IDF engine."""

import math
from nyx.tfidf import TFIDFEngine


def test_tokenize_basic():
    tokens = TFIDFEngine.tokenize("Find the Email Input Field")
    assert "email" in tokens
    assert "input" in tokens
    assert "field" in tokens
    assert "find" in tokens
    assert "the" not in tokens  # stop word


def test_tokenize_empty():
    assert TFIDFEngine.tokenize("") == []


def test_tokenize_punctuation():
    tokens = TFIDFEngine.tokenize("hello, world! foo-bar")
    assert "hello" in tokens
    assert "world" in tokens
    assert "foo" in tokens
    assert "bar" in tokens


def test_vocabulary_building():
    engine = TFIDFEngine()
    docs = [
        "email password login",
        "email username",
        "password confirm",
        "login submit button",
    ]
    engine.build_vocabulary(docs)
    assert engine.vocab_size > 0
    assert engine.total_documents == 4


def test_tfidf_vector_dim():
    engine = TFIDFEngine()
    engine.build_vocabulary([
        "email password login",
        "email username",
        "password confirm",
        "login submit button",
    ])
    vec = engine.tfidf_vector("email password")
    assert len(vec) == engine.vocab_size


def test_tfidf_vector_empty_doc():
    engine = TFIDFEngine()
    engine.build_vocabulary(["hello world", "hello foo", "world bar"])
    vec = engine.tfidf_vector("")
    assert all(v == 0.0 for v in vec)


def test_tfidf_similarity():
    """Similar documents should have positive cosine similarity."""
    from nyx.similarity import cosine_similarity
    engine = TFIDFEngine()
    engine.build_vocabulary([
        "email password login",
        "email username",
        "password confirm",
        "login submit button",
    ])
    vec1 = engine.tfidf_vector("email password")
    vec2 = engine.tfidf_vector("email login")
    sim = cosine_similarity(vec1, vec2)
    assert sim > 0


def test_rare_term_filtered():
    """Terms appearing in only 1 doc should be filtered when corpus is large enough."""
    engine = TFIDFEngine()
    # 60 docs so min_df = max(1, 60//50) = max(1, 1) = 1
    # Actually with 60 docs, min_df=1, so we need > 50 docs for min_df=2
    # Use 100 docs: min_df = max(1, 100//50) = 2
    docs = ["unique_term email"] + ["email password"] * 50 + ["password login"] * 49
    engine.build_vocabulary(docs)
    # "unique_term" appears in only 1 of 100 docs, min_df = 2
    assert "unique_term" not in engine.term_indices
