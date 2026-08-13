"""Semantic embedder — multi-signal element embeddings + intent vectors.

The core novelty: each DOM element is embedded into a shared vector space
that combines:
  1. TF-IDF of text content (weighted by tag importance)
  2. TF-IDF of attribute text (aria-label, placeholder, name, id, href)
  3. TF-IDF of ancestor text (contextual signal from parent chain)
  4. Structural features (tag weight, depth, position, size, visibility,
     child count)

User intent is embedded into the same space via:
  - TF-IDF of the query (with synonym expansion)
  - Structural hints inferred from query keywords

Matching is done via cosine similarity — no selectors, no XPath, no LLM.
"""

from __future__ import annotations

from typing import Dict, List

from .dom import DOMElement
from .tfidf import TFIDFEngine


class SemanticEmbedder:
    """Builds multi-signal embeddings for DOM elements and user intent.

    The embedding vector has ``tfidf.vocab_size + 8`` dimensions:
      [0 .. vocab_size-1]: Combined TF-IDF (text + attr + context)
      [vocab_size + 0]:    Tag weight
      [vocab_size + 1]:    Depth (normalized, inverted — shallower = higher)
      [vocab_size + 2]:    X position (normalized)
      [vocab_size + 3]:    Y position (normalized)
      [vocab_size + 4]:    Width (normalized)
      [vocab_size + 5]:    Height (normalized)
      [vocab_size + 6]:    Visibility
      [vocab_size + 7]:    Child count (normalized, inverted — fewer = higher)
    """

    # Feature weights — tuned empirically from Swift implementation.
    W_TEXT_TFIDF: float = 3.0  # text content is primary signal
    W_ATTR_TFIDF: float = 2.0  # attribute text (aria-label, placeholder)
    W_CONTEXT_TFIDF: float = 1.0  # ancestor text provides context
    W_TAG_MATCH: float = 1.5  # tag name matching
    W_DEPTH: float = 0.3  # depth as positional signal
    W_POSITION: float = 0.2  # x, y position
    W_SIZE: float = 0.1  # width, height
    W_VISIBILITY: float = 0.5  # visible elements preferred
    W_CHILD_COUNT: float = 0.1  # container vs leaf

    # Tag importance weights — some tags carry more semantic weight.
    TAG_WEIGHTS: Dict[str, float] = {
        "input": 2.0,
        "button": 2.0,
        "a": 1.8,
        "textarea": 2.0,
        "select": 2.0,
        "form": 1.5,
        "label": 1.5,
        "h1": 1.3,
        "h2": 1.2,
        "h3": 1.1,
        "img": 1.2,
        "title": 1.5,
        "span": 0.8,
        "div": 0.5,
        "p": 1.0,
        "li": 0.9,
    }

    # Semantic synonym groups for query expansion.
    SYNONYMS: Dict[str, List[str]] = {
        "email": ["email", "e-mail", "mail", "contact", "address"],
        "password": ["password", "passwd", "pwd", "passcode", "secret"],
        "name": ["name", "username", "user", "login", "fullname", "first", "last"],
        "phone": ["phone", "telephone", "mobile", "cell", "contact", "number", "tel"],
        "search": ["search", "find", "query", "filter", "lookup"],
        "submit": ["submit", "send", "continue", "next", "go", "login", "sign", "register"],
        "button": ["button", "btn", "submit", "click", "action", "continue"],
        "input": ["input", "field", "textbox", "text", "enter", "type", "form"],
        "address": ["address", "location", "street", "city", "zip", "postal", "region"],
        "price": ["price", "cost", "amount", "total", "fee", "payment", "dollar", "rate"],
        "date": ["date", "time", "day", "month", "year", "calendar", "schedule"],
        "image": ["image", "img", "photo", "picture", "avatar", "thumbnail"],
        "link": ["link", "href", "url", "navigation", "anchor", "redirect"],
        "description": ["description", "detail", "info", "about", "summary", "bio"],
        "review": ["review", "rating", "feedback", "comment", "testimonial", "opinion"],
        "profile": ["profile", "account", "user", "member", "settings"],
        "login": ["login", "signin", "sign in", "authenticate", "log in", "account"],
        "register": ["register", "signup", "sign up", "create", "join", "enroll"],
        "message": ["message", "text", "chat", "comment", "reply", "send"],
        "location": ["location", "city", "state", "country", "area", "region", "address"],
    }

    def __init__(self) -> None:
        self.tfidf = TFIDFEngine()
        self.element_count: int = 0

    def build_corpus(self, elements: List[DOMElement]) -> None:
        """Build TF-IDF vocabulary from all elements.

        Each element's "document" is the concatenation of its text,
        attribute values, and ancestor text.
        """
        documents: List[str] = []
        for el in elements:
            attr_text = " ".join(el.attrs.values())
            doc = f"{el.text} {attr_text} {el.ancestor_text}"
            documents.append(doc)
        self.tfidf.build_vocabulary(documents)
        self.element_count = len(elements)

    def embed(self, element: DOMElement) -> List[float]:
        """Compute the full embedding vector for a DOM element.

        Combines TF-IDF (text + attrs + context) with structural features
        into a single vector of length ``tfidf.vocab_size + 8``.
        """
        text_vec = self.tfidf.tfidf_vector(element.text)
        attr_doc = " ".join(element.attrs.values())
        attr_vec = self.tfidf.tfidf_vector(attr_doc)
        context_vec = self.tfidf.tfidf_vector(element.ancestor_text)

        vec_len = self.tfidf.vocab_size + 8
        vector = [0.0] * vec_len

        # Combine TF-IDF vectors with weights.
        for i in range(self.tfidf.vocab_size):
            vector[i] = (
                self.W_TEXT_TFIDF * text_vec[i]
                + self.W_ATTR_TFIDF * attr_vec[i]
                + self.W_CONTEXT_TFIDF * context_vec[i]
            )

        # Structural features (appended after TF-IDF dimensions).
        offset = self.tfidf.vocab_size
        tag_weight = self.TAG_WEIGHTS.get(element.tag, 1.0)

        vector[offset] = self.W_TAG_MATCH * tag_weight

        norm_depth = min(element.depth / 20.0, 1.0)
        vector[offset + 1] = self.W_DEPTH * (1.0 - norm_depth)

        vector[offset + 2] = self.W_POSITION * (element.x / 1920.0)
        vector[offset + 3] = self.W_POSITION * (element.y / 1080.0)

        vector[offset + 4] = self.W_SIZE * min(element.width / 500.0, 1.0)
        vector[offset + 5] = self.W_SIZE * min(element.height / 200.0, 1.0)

        vector[offset + 6] = self.W_VISIBILITY if element.is_visible else 0.0

        child_norm = min(element.child_count / 20.0, 1.0)
        vector[offset + 7] = self.W_CHILD_COUNT * (1.0 - child_norm)

        return vector

    def embed_intent(self, query: str) -> List[float]:
        """Compute the intent vector from a natural language query.

        The query is expanded with synonyms and embedded into the same
        TF-IDF + structural space as DOM elements.
        """
        expanded = self._expand_query(query)
        query_doc = " ".join(expanded)

        tfidf_vec = self.tfidf.tfidf_vector(query_doc)
        vec_len = self.tfidf.vocab_size + 8
        vector = [0.0] * vec_len

        for i in range(self.tfidf.vocab_size):
            vector[i] = self.W_TEXT_TFIDF * tfidf_vec[i]

        # Intent structural hints.
        offset = self.tfidf.vocab_size
        lower_query = query.lower()

        if any(w in lower_query for w in ("input", "field", "text box", "textbox")):
            vector[offset] = self.W_TAG_MATCH * 2.0  # input
        elif any(w in lower_query for w in ("button", "submit", "click")):
            vector[offset] = self.W_TAG_MATCH * 2.0  # button
        elif any(w in lower_query for w in ("link", "navigation", "anchor")):
            vector[offset] = self.W_TAG_MATCH * 1.8  # a
        elif any(w in lower_query for w in ("image", "photo", "picture")):
            vector[offset] = self.W_TAG_MATCH * 1.2  # img
        elif any(w in lower_query for w in ("heading", "title")):
            vector[offset] = self.W_TAG_MATCH * 1.3  # h1
        else:
            vector[offset] = self.W_TAG_MATCH * 1.0  # neutral

        vector[offset + 1] = self.W_DEPTH * 0.5  # prefer specific elements
        vector[offset + 2] = 0.0
        vector[offset + 3] = 0.0
        vector[offset + 4] = 0.0
        vector[offset + 5] = 0.0
        vector[offset + 6] = self.W_VISIBILITY  # prefer visible
        vector[offset + 7] = self.W_CHILD_COUNT * 0.7  # prefer leaf-ish

        return vector

    def _expand_query(self, query: str) -> List[str]:
        """Expand query with semantic synonyms.

        For each token in the query, add all synonyms from matching groups.
        Also checks partial string containment for broader matching.
        """
        tokens = self.tfidf.tokenize(query)
        expanded: List[str] = []
        seen: set[str] = set()

        for token in tokens:
            if token not in seen:
                expanded.append(token)
                seen.add(token)

            # Direct synonym lookup.
            if token in self.SYNONYMS:
                for syn in self.SYNONYMS[token]:
                    if syn not in seen:
                        expanded.append(syn)
                        seen.add(syn)

            # Partial containment check.
            for key, syns in self.SYNONYMS.items():
                if key in token or token in key:
                    for syn in syns:
                        if syn not in seen:
                            expanded.append(syn)
                            seen.add(syn)

        return expanded if expanded else tokens
