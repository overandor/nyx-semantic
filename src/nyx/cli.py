"""CLI for NyxSemantic — semantic element location without selectors."""

from __future__ import annotations

import argparse
import json
import sys
from typing import List

from .dom import DOMElement
from .locator import SemanticLocator
from .similarity import cosine_similarity
from .tfidf import TFIDFEngine


def _parse_elements_from_file(path: str) -> List[DOMElement]:
    """Load DOM elements from a JSON file (list of dicts)."""
    with open(path) as f:
        data = json.load(f)
    return [DOMElement.from_dict(d) for d in data]


def cmd_find(args: argparse.Namespace) -> int:
    """Find elements by natural language intent."""
    elements = _parse_elements_from_file(args.dom)
    locator = SemanticLocator()
    locator.build_index(elements)
    stats = locator.stats()

    print(f"Elements: {stats['elements']}")
    print(f"Vocabulary: {stats['vocabulary_size']}")
    print(f"Embedding dim: {stats['embedding_dim']}")
    print(f'\nSemantic search: "{args.intent}"')
    print(f"Top {args.top} matches:\n")

    matches = locator.find(args.intent, top_k=args.top)
    if not matches:
        print("  No matches found")
        return 1

    for m in matches:
        el = m.element
        print(f"  ┌─ Rank #{m.rank} — {m.confidence}% match")
        print(f"  │ Tag: <{el.tag}>  Depth: {el.depth}  Children: {el.child_count}")
        if el.text:
            print(f'  │ Text: "{el.text[:100]}"')
        if el.attrs:
            attr_str = ", ".join(f'{k}="{v[:40]}"' for k, v in el.attrs.items())
            print(f"  │ Attrs: {attr_str}")
        if m.matched_terms:
            print(f"  │ Matched: {', '.join(m.matched_terms)}")
        print(f"  │ XPath: {el.xpath[:80]}")
        print(f"  └─ Position: ({int(el.x)}, {int(el.y)}) Size: {int(el.width)}x{int(el.height)}")
        print()

    return 0


def cmd_analyze(args: argparse.Namespace) -> int:
    """Analyze page element stats."""
    elements = _parse_elements_from_file(args.dom)
    locator = SemanticLocator()
    locator.build_index(elements)
    stats = locator.stats()

    print("\nPage Analysis")
    print("=" * 50)
    print(f"  Elements: {stats['elements']}")
    print(f"  Visible: {stats['visible_elements']}")
    print(f"  Vocabulary: {stats['vocabulary_size']}")
    print(f"  Embedding dim: {stats['embedding_dim']}")
    print(f"  Tags: {', '.join(stats['tags'])}")
    return 0


def cmd_test(args: argparse.Namespace) -> int:
    """Run self-tests."""
    print("NyxSemantic — Self-Tests")
    print("=" * 50)
    passed = 0
    failed = 0

    def check(name: str, cond: bool) -> None:
        nonlocal passed, failed
        if cond:
            print(f"  PASS  {name}")
            passed += 1
        else:
            print(f"  FAIL  {name}")
            failed += 1

    # 1. Cosine similarity properties.
    print("\n  Test 1: Cosine Similarity")
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    v3 = [0.0, 1.0, 0.0]
    check("Identical vectors → 1.0", abs(cosine_similarity(v1, v2) - 1.0) < 0.001)
    check("Orthogonal vectors → 0.0", abs(cosine_similarity(v1, v3)) < 0.001)

    # 2. TF-IDF properties.
    print("\n  Test 2: TF-IDF")
    engine = TFIDFEngine()
    engine.build_vocabulary(
        [
            "email password login",
            "email username",
            "password confirm",
            "login submit button",
        ]
    )
    check("Vocabulary filters rare terms", engine.vocab_size > 0)
    vec1 = engine.tfidf_vector("email password")
    vec2 = engine.tfidf_vector("email login")
    sim = cosine_similarity(vec1, vec2)
    check("Similar docs have positive similarity", sim > 0)
    print(f"    → similarity(email+password, email+login) = {sim:.3f}")

    # 3. Semantic find with synthetic DOM.
    print("\n  Test 3: Semantic Find")
    elements = [
        DOMElement(
            index=0,
            tag="h1",
            text="Example Domain",
            depth=2,
            sibling_index=0,
            child_count=0,
            x=100,
            y=100,
            width=400,
            height=40,
        ),
        DOMElement(
            index=1,
            tag="p",
            text="This domain is for use in illustrative examples",
            depth=2,
            sibling_index=1,
            child_count=0,
            x=100,
            y=160,
            width=400,
            height=60,
        ),
        DOMElement(
            index=2,
            tag="a",
            text="More information...",
            depth=3,
            sibling_index=0,
            child_count=0,
            x=100,
            y=240,
            width=150,
            height=20,
            attrs={"href": "https://www.iana.org/domains/example"},
        ),
        DOMElement(
            index=3,
            tag="input",
            text="",
            depth=4,
            sibling_index=0,
            child_count=0,
            x=200,
            y=300,
            width=200,
            height=30,
            attrs={
                "type": "email",
                "placeholder": "Enter your email",
                "name": "email",
                "aria-label": "Email address",
            },
        ),
        DOMElement(
            index=4,
            tag="button",
            text="Submit",
            depth=4,
            sibling_index=1,
            child_count=0,
            x=200,
            y=340,
            width=100,
            height=30,
            attrs={"type": "submit"},
        ),
    ]

    locator = SemanticLocator()
    locator.build_index(elements)
    stats = locator.stats()
    check("Index built with 5 elements", stats["elements"] == 5)
    check("Vocabulary > 0", stats["vocabulary_size"] > 0)

    # Find heading.
    heading = locator.find_one("find the main heading title")
    check("Found heading", heading is not None)
    if heading:
        print(
            f'    → <{heading.element.tag}> "{heading.element.text[:60]}" ({heading.confidence}%)'
        )
        check("Top match is heading", heading.element.tag in ("h1", "h2", "h3", "div"))
        check("Heading contains 'Example'", "example" in heading.element.text.lower())

    # Find link.
    link = locator.find_one("find the more information link")
    check("Found link", link is not None)
    if link:
        print(f'    → <{link.element.tag}> "{link.element.text[:60]}" ({link.confidence}%)')
        check("Link tag is anchor", link.element.tag == "a")
        check("Link text contains 'More'", "more" in link.element.text.lower())

    # Find email input.
    email = locator.find_one("find the email input field")
    check("Found email input", email is not None)
    if email:
        print(f'    → <{email.element.tag}> "{email.element.text[:60]}" ({email.confidence}%)')
        check("Email match is input tag", email.element.tag == "input")

    # Find submit button.
    button = locator.find_one("find the submit button")
    check("Found submit button", button is not None)
    if button:
        print(f'    → <{button.element.tag}> "{button.element.text[:60]}" ({button.confidence}%)')
        check("Button match is button tag", button.element.tag == "button")

    # 4. Self-healing test.
    print("\n  Test 4: Self-Healing (page redesign)")
    # Simulate redesign: rename classes, remove IDs, restructure.
    redesigned = [
        DOMElement(
            index=0,
            tag="h1",
            text="Example Domain",
            depth=3,
            sibling_index=0,
            child_count=0,
            x=50,
            y=80,
            width=500,
            height=50,
        ),
        DOMElement(
            index=1,
            tag="p",
            text="This domain is for use in illustrative examples",
            depth=3,
            sibling_index=1,
            child_count=0,
            x=50,
            y=140,
            width=500,
            height=70,
        ),
        DOMElement(
            index=2,
            tag="a",
            text="More information...",
            depth=5,
            sibling_index=0,
            child_count=0,
            x=50,
            y=230,
            width=180,
            height=25,
            attrs={"href": "https://www.iana.org/domains/example"},
        ),
        DOMElement(
            index=3,
            tag="input",
            text="",
            depth=6,
            sibling_index=0,
            child_count=0,
            x=150,
            y=320,
            width=250,
            height=35,
            attrs={
                "type": "email",
                "placeholder": "Enter your email",
                "name": "email",
                "aria-label": "Email address",
            },
        ),
        DOMElement(
            index=4,
            tag="button",
            text="Submit",
            depth=6,
            sibling_index=1,
            child_count=0,
            x=150,
            y=365,
            width=120,
            height=35,
            attrs={"type": "submit"},
        ),
    ]

    before_score, after_score, same = locator.self_heal_test(
        "find the more information link", redesigned
    )
    check("Before redesign found element", before_score > 0)
    check("After redesign found element", after_score > 0)
    check("Same element found after redesign", same)
    print(
        f"    → Before: {int(before_score * 100)}%, After: {int(after_score * 100)}%, Same: {same}"
    )

    # 5. Query expansion.
    print("\n  Test 5: Query Expansion")
    from .embedder import SemanticEmbedder

    emb = SemanticEmbedder()
    expanded = emb._expand_query("find the email input")
    check("Query expanded with synonyms", "email" in expanded)
    check("Synonyms added", len(expanded) > 3)
    print(f"    → Expanded: {expanded[:10]}")

    print(f"\n{'=' * 50}")
    print(f"  Results: {passed} passed, {failed} failed")
    return 1 if failed > 0 else 0


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="nyx",
        description="NyxSemantic — Semantic element location without selectors",
    )
    sub = parser.add_subparsers(dest="command")

    p_find = sub.add_parser("find", help="Find elements by natural language intent")
    p_find.add_argument(
        "--dom", required=True, help="Path to JSON file with extracted DOM elements"
    )
    p_find.add_argument("--intent", required=True, help="Natural language search query")
    p_find.add_argument("--top", type=int, default=5, help="Top K results (default: 5)")

    p_analyze = sub.add_parser("analyze", help="Analyze page element stats")
    p_analyze.add_argument(
        "--dom", required=True, help="Path to JSON file with extracted DOM elements"
    )

    sub.add_parser("test", help="Run self-tests")

    sub.add_parser("js", help="Print the DOM extraction JavaScript snippet")

    args = parser.parse_args()

    if args.command == "find":
        return cmd_find(args)
    elif args.command == "analyze":
        return cmd_analyze(args)
    elif args.command == "test":
        return cmd_test(args)
    elif args.command == "js":
        from .dom import extract_dom_js

        print(extract_dom_js())
        return 0
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
