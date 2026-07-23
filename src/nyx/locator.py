"""Semantic locator — the core algorithm.

Builds an index of DOM element embeddings and finds elements by
natural language intent using cosine similarity with intent-aware
bonuses. Self-heals across page redesigns because it matches
semantic meaning, not CSS selectors or XPath.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .dom import DOMElement
from .embedder import SemanticEmbedder
from .similarity import cosine_similarity


@dataclass
class SemanticMatch:
    """A single search result.

    Attributes:
        element: The matched DOM element.
        score: Cosine similarity score (0-1, possibly > 1 with bonuses).
        rank: 1-based rank in the result list.
        matched_terms: Query tokens that appeared in the element's text/attrs.
    """

    element: DOMElement
    score: float
    rank: int
    matched_terms: List[str] = field(default_factory=list)

    @property
    def confidence(self) -> int:
        """Human-readable confidence percentage."""
        return min(100, int(self.score * 100))


class SemanticLocator:
    """Semantic element locator — browser-agnostic.

    Accepts DOM elements from any source (Playwright, Selenium, WKWebView,
    raw HTML parser) and builds a semantic index. Finds elements by
    natural language intent without CSS selectors or XPath.

    Usage:
        locator = SemanticLocator()
        locator.build_index(elements)
        matches = locator.find("find the email input field", top_k=5)
    """

    def __init__(self) -> None:
        self._embedder = SemanticEmbedder()
        self._elements: List[DOMElement] = []
        self._embeddings: List[List[float]] = []

    def build_index(self, elements: List[DOMElement]) -> None:
        """Build the semantic index from extracted DOM elements.

        Args:
            elements: List of DOMElement objects from any browser source.
        """
        self._elements = elements
        if not elements:
            self._embeddings = []
            return
        self._embedder.build_corpus(elements)
        self._embeddings = [self._embedder.embed(el) for el in elements]

    def find(self, intent: str, top_k: int = 5) -> List[SemanticMatch]:
        """Find DOM elements matching a natural language intent.

        Args:
            intent: Natural language query, e.g. "find the email input field".
            top_k: Maximum number of results to return.

        Returns:
            List of SemanticMatch sorted by score descending.
        """
        if not self._embeddings:
            return []

        query_vec = self._embedder.embed_intent(intent)
        lower_intent = intent.lower()

        # Determine intent type for bonus adjustments.
        wants_content = any(
            w in lower_intent
            for w in (
                "name", "text", "title", "heading", "review",
                "description", "profile", "therapist",
            )
        )
        wants_input = any(
            w in lower_intent
            for w in (
                "input", "field", "search", "form",
                "password", "email",
            )
        )
        wants_link = any(w in lower_intent for w in ("link", "navigation", "anchor"))
        wants_heading = any(w in lower_intent for w in ("heading", "title", "headline"))
        wants_image = any(w in lower_intent for w in ("image", "photo", "picture"))
        wants_button = any(w in lower_intent for w in ("button", "submit", "click"))

        scored: List[Tuple[int, float]] = []
        for i, emb in enumerate(self._embeddings):
            sim = cosine_similarity(query_vec, emb)
            el = self._elements[i]

            # Intent-aware bonuses.
            if wants_content and el.text:
                sim *= 1.15  # 15% boost for having text
            if wants_content and not el.text and el.child_count > 2:
                sim *= 0.7  # 30% penalty for empty containers
            if wants_input and el.tag in ("input", "textarea", "select"):
                sim *= 1.25  # 25% boost for input tags
            if wants_content and el.child_count == 0 and el.text:
                sim *= 1.05  # 5% boost for leaf nodes with text
            # Tag-specific bonuses for precise intent.
            if wants_heading and el.tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
                sim *= 1.50  # 50% boost for heading tags
            if wants_link and el.tag == "a":
                sim *= 1.50  # 50% boost for anchor tags
            if wants_image and el.tag == "img":
                sim *= 1.50  # 50% boost for image tags
            if wants_button and el.tag == "button":
                sim *= 1.50  # 50% boost for button tags
            # Tag-mismatch penalties: when intent is tag-specific, penalize
            # elements whose tag doesn't match the intent at all.
            if wants_heading and el.tag not in ("h1", "h2", "h3", "h4", "h5", "h6"):
                sim *= 0.60  # 40% penalty for non-heading tags
            if wants_link and el.tag != "a":
                sim *= 0.60  # 40% penalty for non-anchor tags
            if wants_image and el.tag != "img":
                sim *= 0.60  # 40% penalty for non-image tags
            if wants_button and el.tag != "button":
                sim *= 0.60  # 40% penalty for non-button tags

            scored.append((i, sim))

        scored.sort(key=lambda x: x[1], reverse=True)

        results: List[SemanticMatch] = []
        for rank, (idx, score) in enumerate(scored[:top_k], start=1):
            el = self._elements[idx]
            matched = self._find_matched_terms(intent, el)
            results.append(
                SemanticMatch(
                    element=el,
                    score=score,
                    rank=rank,
                    matched_terms=matched,
                )
            )

        return results

    def find_one(self, intent: str) -> Optional[SemanticMatch]:
        """Convenience: return the top match or None."""
        matches = self.find(intent, top_k=1)
        return matches[0] if matches else None

    def self_heal_test(
        self, original_intent: str, redesigned_elements: List[DOMElement]
    ) -> Tuple[float, float, bool]:
        """Test self-healing across a page redesign.

        Compares the top match before and after a redesign. The algorithm
        is self-healing because it matches semantic meaning (TF-IDF +
        structural features), not CSS selectors or element IDs.

        Args:
            original_intent: The natural language query to test.
            redesigned_elements: DOM elements extracted after the redesign
                (e.g. after renaming classes, removing IDs, restructuring).

        Returns:
            Tuple of (before_score, after_score, same_element_found).
        """
        before = self.find_one(original_intent)
        if before is None:
            return (0.0, 0.0, False)

        before_score = before.score
        before_text = before.element.text
        before_tag = before.element.tag

        # Rebuild index with redesigned elements.
        self.build_index(redesigned_elements)

        after = self.find_one(original_intent)
        if after is None:
            return (before_score, 0.0, False)

        after_score = after.score
        after_text = after.element.text
        after_tag = after.element.tag

        # Same element if text overlaps or tag matches.
        same = bool(
            before_text
            and (
                after_text in before_text
                or before_text in after_text
                or after_tag == before_tag
            )
        )

        return (before_score, after_score, same)

    def _find_matched_terms(self, query: str, element: DOMElement) -> List[str]:
        """Find which query tokens appear in the element's text/attrs."""
        query_tokens = set(self._embedder.tfidf.tokenize(query))
        element_text = " ".join(element.attrs.values())
        element_tokens = set(self._embedder.tfidf.tokenize(f"{element.text} {element_text}"))
        return list(query_tokens & element_tokens)

    def stats(self) -> Dict[str, Any]:
        """Return index statistics."""
        return {
            "elements": len(self._elements),
            "vocabulary_size": self._embedder.tfidf.vocab_size,
            "embedding_dim": len(self._embeddings[0]) if self._embeddings else 0,
            "visible_elements": sum(1 for e in self._elements if e.is_visible),
            "tags": sorted(set(e.tag for e in self._elements)),
        }
