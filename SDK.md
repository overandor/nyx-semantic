# NyxSemantic SDK

The importable surface for selector-free semantic element location. Part of the
[syndication standard](https://github.com/overandor/jorki/blob/main/syndication/STANDARD.md).

## Install

```bash
pip install nyx-semantic
```

## Minimal example

```python
from nyx import DOMElement, SemanticLocator

elements = [DOMElement(index=0, tag="input", text="",
                       attrs={"type": "email", "placeholder": "Enter email"},
                       depth=4, sibling_index=0, child_count=0,
                       x=200, y=300, width=200, height=30)]

locator = SemanticLocator()
locator.build_index(elements)
matches = locator.find("find the email input field", top_k=5)
for m in matches:
    print(m.rank, m.confidence, m.element.tag, m.matched_terms)
```

## Public API

| Symbol | Purpose |
|---|---|
| `DOMElement(...)` | A DOM element record (tag, text, attrs, geometry, structure) |
| `DOMElement.from_dict(d)` | Build a `DOMElement` from an extracted JSON dict |
| `SemanticLocator()` | The locator engine |
| `SemanticLocator.build_index(elements)` | Build the TF-IDF vocabulary + embeddings |
| `SemanticLocator.find(intent, top_k=5)` | Rank elements by cosine similarity to an intent; returns matches (`rank`, `confidence`, `element`, `matched_terms`) |
| `extract_dom_js()` | Returns the JS snippet to dump a page's DOM (run via Playwright/Selenium `evaluate`) |

## Stability

- **Stable:** `DOMElement`, `SemanticLocator.build_index`, `.find`,
  `extract_dom_js` — exercised by `nyx test` and the CLI.
- **Deterministic:** no network, no LLM; same DOM + intent → same ranking.
