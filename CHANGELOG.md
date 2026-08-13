# Changelog

All notable changes to **nyx-semantic** are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] — 2026-08-13

### Changed
- Bumped from 0.1.0 → 1.0.0 (first stable release).
- Classifier changed from "4 - Beta" → "5 - Production/Stable".

### Added
- GitHub Actions CI: test matrix (Python 3.9–3.13), ruff lint + format, mypy type check, build.
- Release workflow: publish to PyPI on `v*` tags (trusted publishing).
- CHANGELOG.md.

### Fixed
- Removed 4 unused imports flagged by ruff.
- Applied ruff formatting across all source and test files.

## [0.1.0] — 2026-07-23

### Added
- `DOMElement` dataclass + `extract_dom_js()` JS snippet for Playwright/Selenium.
- `TFIDFEngine` — vocabulary building + TF-IDF vector computation.
- `SemanticEmbedder` — multi-signal embeddings (text + attrs + ancestors + structural + positional).
- `SemanticLocator` — cosine similarity ranking with intent-aware bonuses.
- `cosine_similarity` + `euclidean_distance` vector math.
- CLI (`nyx` command) for standalone use.
- Swift package (`Sources/NyxSemantic/main.swift`).
- 42 tests covering DOM, TF-IDF, embedder, similarity, and locator.
