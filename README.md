# NyxSemantic

**Semantic element location without CSS selectors.**

No CSS selectors. No XPath. No LLM calls. Pure math.

NyxSemantic finds DOM elements by **semantic meaning** using TF-IDF embeddings, structural features, and cosine similarity. It survives page redesigns because it matches what an element *means*, not how it's *structured*.

## Why This Is Novel

Every browser automation tool — Selenium, Playwright, Puppeteer, Cypress — locates elements using CSS selectors or XPath. When a designer renames a class, removes an ID, or restructures the DOM, **every selector breaks**.

NyxSemantic doesn't use selectors. It builds a TF-IDF vocabulary across all DOM elements, computes multi-signal embeddings (text + attributes + ancestor context + structural features), and ranks elements by cosine similarity to a natural language intent vector. **Rename every class, remove half the IDs — it still finds the right element.**

## Install

```bash
pip install nyx-semantic
```

## Quick Start

```python
from nyx import DOMElement, SemanticLocator

# Extract DOM elements from any browser (Playwright, Selenium, etc.)
# Use nyx.extract_dom_js() to get the extraction JavaScript snippet.
elements = [
    DOMElement(index=0, tag="h1", text="Welcome",
               depth=2, sibling_index=0, child_count=0,
               x=100, y=100, width=400, height=40),
    DOMElement(index=1, tag="input", text="",
               depth=4, sibling_index=0, child_count=0,
               x=200, y=300, width=200, height=30,
               attrs={"type": "email", "placeholder": "Enter email",
                      "name": "email", "aria-label": "Email address"}),
    DOMElement(index=2, tag="button", text="Submit",
               depth=4, sibling_index=1, child_count=0,
               x=200, y=340, width=100, height=30,
               attrs={"type": "submit"}),
]

# Build semantic index
locator = SemanticLocator()
locator.build_index(elements)

# Find by natural language intent — no selectors!
matches = locator.find("find the email input field", top_k=5)
for m in matches:
    print(f"#{m.rank} {m.confidence}% <{m.element.tag}> {m.element.text[:60]}")
    print(f"  Matched: {m.matched_terms}")
```

## With Playwright

```python
from playwright.sync_api import sync_playwright
from nyx import DOMElement, SemanticLocator, extract_dom_js

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto("https://example.com")

    # Extract DOM elements using NyxSemantic's JS
    json_str = page.evaluate(extract_dom_js())
    elements = [DOMElement.from_dict(d) for d in json.loads(json_str)]

    # Build index and find
    locator = SemanticLocator()
    locator.build_index(elements)

    matches = locator.find("find the main heading", top_k=3)
    for m in matches:
        print(f"#{m.rank} {m.confidence}% <{m.element.tag}> \"{m.element.text[:80]}\"")

    browser.close()
```

## CLI

```bash
# Print the DOM extraction JavaScript
nyx js

# Find elements from extracted DOM JSON
nyx find --dom elements.json --intent "find the email input field" --top 5

# Analyze page stats
nyx analyze --dom elements.json

# Run self-tests
nyx test
```

## Algorithm

### 1. DOM Extraction
Extract every visible DOM element with: tag, text, attributes (type, role, aria-label, placeholder, name, id, href, class, value, title, alt, for, action, data-testid), depth, sibling index, child count, bounding rect position/size, parent tag chain, ancestor text, visibility, and XPath (for debugging only).

### 2. TF-IDF Vocabulary
Build a vocabulary across all elements (one document per element = text + attribute values + ancestor text). Filter rare terms (appear in < 2 documents) and overly common terms (> 80% of documents).

### 3. Multi-Signal Embedding
Each element is embedded into a vector of `vocab_size + 8` dimensions:

| Dimensions | Signal | Weight |
|---|---|---|
| 0 .. vocab_size-1 | TF-IDF of text content | 3.0 |
| 0 .. vocab_size-1 | TF-IDF of attribute text | 2.0 |
| 0 .. vocab_size-1 | TF-IDF of ancestor text | 1.0 |
| vocab_size + 0 | Tag weight (input=2.0, button=2.0, a=1.8, div=0.5, ...) | 1.5 |
| vocab_size + 1 | Depth (normalized, inverted) | 0.3 |
| vocab_size + 2 | X position (normalized) | 0.2 |
| vocab_size + 3 | Y position (normalized) | 0.2 |
| vocab_size + 4 | Width (normalized) | 0.1 |
| vocab_size + 5 | Height (normalized) | 0.1 |
| vocab_size + 6 | Visibility | 0.5 |
| vocab_size + 7 | Child count (normalized, inverted) | 0.1 |

### 4. Intent Vector
User query is expanded with 20 synonym groups (email, password, name, phone, search, submit, button, input, address, price, date, image, link, description, review, profile, login, register, message, location), then embedded into the same TF-IDF + structural space with intent-aware tag hints.

### 5. Cosine Similarity Ranking
Rank all elements by cosine similarity to the intent vector. Apply intent-aware bonuses:
- **Content intent** + element has text: +15%
- **Content intent** + empty container: -30%
- **Input intent** + input/textarea/select tag: +25%
- **Content intent** + leaf node with text: +5%

### 6. Self-Healing
Because matching is based on semantic meaning (TF-IDF of text/attrs/context + structural features), not selectors, the algorithm survives:
- Class name renames
- ID removal
- DOM restructuring (depth/position changes)
- Attribute reordering

## API Reference

### `DOMElement`
Dataclass for a single DOM element. Use `DOMElement.from_dict(d)` to build from JSON.

### `SemanticLocator`
- `build_index(elements: List[DOMElement])` — Build the semantic index.
- `find(intent: str, top_k: int = 5) -> List[SemanticMatch]` — Find elements by intent.
- `find_one(intent: str) -> Optional[SemanticMatch]` — Convenience: top match or None.
- `self_heal_test(intent: str, redesigned_elements: List[DOMElement]) -> Tuple[float, float, bool]` — Test self-healing.
- `stats() -> Dict[str, Any]` — Index statistics.

### `SemanticMatch`
- `element: DOMElement` — The matched element.
- `score: float` — Cosine similarity score.
- `rank: int` — 1-based rank.
- `matched_terms: List[str]` — Query tokens found in the element.
- `confidence: int` — Score as percentage (0-100).

### `extract_dom_js() -> str`
Returns JavaScript snippet for DOM extraction. Evaluate in any browser context.

## License

Apache-2.0
