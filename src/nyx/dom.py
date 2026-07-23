"""DOM element dataclass and JavaScript extraction string."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class DOMElement:
    """A single DOM element extracted from a page.

    Attributes:
        index: Position in extraction order.
        tag: Lowercase tag name (e.g. "input", "button", "a").
        text: Trimmed inner text, max 200 chars.
        depth: Nesting depth from root.
        sibling_index: Position among siblings.
        child_count: Number of element children.
        x: Viewport-relative left coordinate.
        y: Viewport-relative top coordinate.
        width: Bounding rect width.
        height: Bounding rect height.
        attrs: Selected attributes (type, role, aria-label, placeholder,
               name, id, href, class, value, title, alt, for, action,
               data-testid).
        parent_tags: Chain of ancestor tag names from parent to root.
        ancestor_text: Concatenated text of ancestors (max 500 chars).
        is_visible: Whether the element is rendered and visible.
        xpath: Debugging-only XPath — never used for matching.
    """

    index: int
    tag: str
    text: str
    depth: int
    sibling_index: int
    child_count: int
    x: float
    y: float
    width: float
    height: float
    attrs: Dict[str, str] = field(default_factory=dict)
    parent_tags: List[str] = field(default_factory=list)
    ancestor_text: str = ""
    is_visible: bool = True
    xpath: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> DOMElement:
        """Build a DOMElement from a JSON-decoded dict."""
        return cls(
            index=d.get("index", 0),
            tag=d.get("tag", ""),
            text=d.get("text", ""),
            depth=d.get("depth", 0),
            sibling_index=d.get("siblingIndex", 0),
            child_count=d.get("childCount", 0),
            x=d.get("x", 0.0),
            y=d.get("y", 0.0),
            width=d.get("width", 0.0),
            height=d.get("height", 0.0),
            attrs=d.get("attrs", {}),
            parent_tags=d.get("parentTags", []),
            ancestor_text=d.get("ancestorText", ""),
            is_visible=d.get("isVisible", True),
            xpath=d.get("xpath", ""),
        )


# JavaScript that extracts all visible DOM elements as JSON.
# Run this in any browser context (Playwright, Selenium, WKWebView, etc.)
# and parse the returned JSON string into List[DOMElement].
EXTRACT_DOM_JS = """
(function() {
    var elements = [];
    var all = document.querySelectorAll('*');
    for (var i = 0; i < all.length && i < 2000; i++) {
        var el = all[i];
        var rect = el.getBoundingClientRect();
        if (rect.width === 0 && rect.height === 0) continue;

        var tag = el.tagName.toLowerCase();
        var text = (el.innerText || el.textContent || '').trim().substring(0, 500);
        if (text.length > 200) text = text.substring(0, 200);

        var depth = 0;
        var parent = el.parentElement;
        var parentTags = [];
        var ancestorText = '';
        while (parent && depth < 15) {
            parentTags.push(parent.tagName.toLowerCase());
            var pText = (parent.innerText || '').trim();
            if (pText.length > 0 && ancestorText.length < 300) {
                ancestorText += ' ' + pText.substring(0, 100);
            }
            parent = parent.parentElement;
            depth++;
        }

        var siblingIndex = 0;
        var sib = el.previousElementSibling;
        while (sib) { siblingIndex++; sib = sib.previousElementSibling; }

        var attrs = {};
        var attrNames = ['type', 'role', 'aria-label', 'placeholder', 'name', 'id',
                         'href', 'class', 'value', 'title', 'alt', 'for', 'action',
                         'data-testid'];
        for (var j = 0; j < attrNames.length; j++) {
            var val = el.getAttribute(attrNames[j]);
            if (val) attrs[attrNames[j]] = val.substring(0, 200);
        }

        var style = window.getComputedStyle(el);
        var visible = style.display !== 'none' && style.visibility !== 'hidden'
                      && parseFloat(style.opacity) > 0;

        var xpath = '';
        var node = el;
        while (node && node.nodeType === 1) {
            var idx = 1;
            var s = node.previousElementSibling;
            while (s) { if (s.tagName === node.tagName) idx++; s = s.previousElementSibling; }
            xpath = '/' + node.tagName.toLowerCase() + '[' + idx + ']' + xpath;
            node = node.parentElement;
        }

        elements.push({
            index: elements.length,
            tag: tag,
            text: text,
            depth: depth,
            siblingIndex: siblingIndex,
            childCount: el.children.length,
            x: rect.left, y: rect.top,
            width: rect.width, height: rect.height,
            attrs: attrs,
            parentTags: parentTags,
            ancestorText: ancestorText.substring(0, 500),
            isVisible: visible,
            xpath: xpath
        });
    }
    return JSON.stringify(elements);
})();
"""


def extract_dom_js() -> str:
    """Return the JavaScript snippet for DOM extraction.

    Evaluate this in a browser context and parse the result as JSON
    into a list of dicts, then use ``DOMElement.from_dict`` for each.
    """
    return EXTRACT_DOM_JS
