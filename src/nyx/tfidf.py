"""TF-IDF engine — vocabulary building and vector computation."""

from __future__ import annotations

import math
import re
from typing import Dict, List, Set

# Stop words filtered from tokenization.
_STOP_WORDS: frozenset[str] = frozenset(
    {
        "the",
        "a",
        "an",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "must",
        "can",
        "this",
        "that",
        "these",
        "those",
        "i",
        "you",
        "he",
        "she",
        "it",
        "we",
        "they",
        "and",
        "or",
        "but",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "with",
        "by",
        "from",
        "as",
        "into",
        "about",
        "than",
        "then",
        "so",
        "if",
        "not",
        "no",
    }
)

# Precompiled tokenizer pattern: split on non-alphanumeric.
_TOKEN_RE = re.compile(r"[^a-z0-9]+")


class TFIDFEngine:
    """TF-IDF vocabulary builder and vector computer.

    Builds a vocabulary from a corpus of documents (one per DOM element),
    filtering rare terms (appear in < min_df documents) and overly common
    terms (appear in > max_df documents). Computes TF-IDF vectors for
    individual documents in the same vocabulary space.
    """

    def __init__(self) -> None:
        self.vocabulary: Dict[str, int] = {}  # term → document frequency
        self.total_documents: int = 0
        self.term_indices: Dict[str, int] = {}  # term → vector index
        self.vocab_size: int = 0

    def build_vocabulary(self, documents: List[str]) -> None:
        """Build vocabulary from a corpus of documents.

        Args:
            documents: List of text strings, one per DOM element.
        """
        self.vocabulary = {}
        self.term_indices = {}
        self.vocab_size = 0
        self.total_documents = len(documents)

        for doc in documents:
            terms: Set[str] = set(self.tokenize(doc))
            for term in terms:
                self.vocabulary[term] = self.vocabulary.get(term, 0) + 1

        # Filter: min_df = max(1, total/50), max_df = total * 4/5
        # For small corpora (< 50 docs), min_df=1 so we don't filter everything.
        min_df = max(1, self.total_documents // 50)
        max_df = self.total_documents * 4 // 5

        for term, df in self.vocabulary.items():
            if min_df <= df <= max_df:
                self.term_indices[term] = self.vocab_size
                self.vocab_size += 1

    def tfidf_vector(self, document: str) -> List[float]:
        """Compute the TF-IDF vector for a single document.

        Args:
            document: Text to vectorize.

        Returns:
            Float vector of length ``self.vocab_size``.
        """
        if self.vocab_size == 0:
            return []

        vector = [0.0] * self.vocab_size
        tokens = self.tokenize(document)
        if not tokens:
            return vector

        # Term frequency.
        tf: Dict[str, int] = {}
        for token in tokens:
            tf[token] = tf.get(token, 0) + 1

        doc_len = float(len(tokens))
        for term, count in tf.items():
            idx = self.term_indices.get(term)
            if idx is None:
                continue
            df = self.vocabulary.get(term, 0)
            tf_val = count / doc_len
            idf_val = math.log(self.total_documents / (df + 1))
            vector[idx] = tf_val * idf_val

        return vector

    @staticmethod
    def tokenize(text: str) -> List[str]:
        """Tokenize text: lowercase, split on non-alphanumeric, remove stop words.

        Args:
            text: Input string.

        Returns:
            List of tokens with length > 1 that are not stop words.
        """
        lowered = text.lower()
        parts = _TOKEN_RE.split(lowered)
        return [p for p in parts if len(p) > 1 and p not in _STOP_WORDS]
