"""
NyxSemantic — Semantic Element Location Without Selectors

Novel algorithm: No CSS selectors. No XPath. No LLM calls. Pure math.

1. Extract every DOM element with text, tag, attributes, position, depth
2. Build TF-IDF vocabulary across all elements
3. Compute embedding vector per element:
   - TF-IDF of text content (weighted by tag importance)
   - TF-IDF of attribute text (aria-label, placeholder, name, id, href)
   - TF-IDF of ancestor text (contextual signal)
   - Structural features (depth, sibling index, child count, tag type)
   - Positional encoding (normalized x, y, width, height)
   - Visibility weighting
4. Convert user intent to query vector in same TF-IDF space
   + semantic expansion (synonyms, related terms)
5. Cosine similarity ranking with intent-aware bonuses
6. Self-healing: works after redesigns because it matches meaning, not structure

This is what no browser tool does. Selenium/Playwright/Puppeteer
all break when a designer changes a class name. This doesn't.
"""

from .dom import DOMElement, extract_dom_js
from .tfidf import TFIDFEngine
from .embedder import SemanticEmbedder
from .similarity import cosine_similarity
from .locator import SemanticLocator, SemanticMatch

__version__ = "1.0.0"
__all__ = [
    "DOMElement",
    "extract_dom_js",
    "TFIDFEngine",
    "SemanticEmbedder",
    "cosine_similarity",
    "SemanticLocator",
    "SemanticMatch",
]
