# NyxSemantic — operating modes

Semantic DOM element location with no CSS selectors, no XPath, no LLM calls —
pure TF-IDF math, so every mode runs offline. Part of the
[syndication standard](https://github.com/overandor/jorki/blob/main/syndication/STANDARD.md).

| Mode | Command | Requires | Status |
|---|---|---|---|
| `test` | `nyx test` | deps | ✅ self-tests |
| `library` | `import` and use `SemanticLocator` (see `SDK.md`) | deps | ✅ core path |
| `cli` | `nyx find --dom elements.json --intent "..." --top 5` | a DOM JSON dump | ✅ |
| `extract` | `nyx js` → run the printed JS in any browser to dump the DOM | a browser (Playwright/Selenium) | ✅ |
| `analyze` | `nyx analyze --dom elements.json` | a DOM JSON dump | ✅ |

## Typical pipeline

```
browser (Playwright/Selenium)
  → page.evaluate(extract_dom_js())      # dump every visible element
  → SemanticLocator().build_index(...)   # TF-IDF vocabulary + embeddings
  → locator.find("find the email input field", top_k=5)  # cosine ranking
```

## Honest note

No external services and no network calls — matching is deterministic math over
the extracted DOM. Accuracy depends on the quality of the extracted element
text/attributes; it ranks by semantic similarity and returns top-k candidates
with confidence, not a single guaranteed match.
