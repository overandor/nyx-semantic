"""Tests for DOM element dataclass."""

import json
from nyx.dom import DOMElement, extract_dom_js


def test_from_dict_basic():
    d = {
        "index": 0,
        "tag": "input",
        "text": "",
        "depth": 3,
        "siblingIndex": 1,
        "childCount": 0,
        "x": 100.0,
        "y": 200.0,
        "width": 300.0,
        "height": 30.0,
        "attrs": {"type": "email", "placeholder": "Enter email"},
        "parentTags": ["form", "div", "body"],
        "ancestorText": "Login form",
        "isVisible": True,
        "xpath": "/html/body/div/form/input[1]",
    }
    el = DOMElement.from_dict(d)
    assert el.tag == "input"
    assert el.depth == 3
    assert el.sibling_index == 1
    assert el.attrs["type"] == "email"
    assert el.parent_tags == ["form", "div", "body"]
    assert el.is_visible is True


def test_from_dict_defaults():
    el = DOMElement.from_dict({})
    assert el.tag == ""
    assert el.depth == 0
    assert el.attrs == {}
    assert el.is_visible is True


def test_extract_dom_js():
    js = extract_dom_js()
    assert isinstance(js, str)
    assert "querySelectorAll" in js
    assert "getBoundingClientRect" in js
    assert "JSON.stringify" in js


def test_dom_element_dataclass():
    el = DOMElement(
        index=0, tag="h1", text="Hello",
        depth=1, sibling_index=0, child_count=0,
        x=10, y=20, width=100, height=30,
    )
    assert el.tag == "h1"
    assert el.text == "Hello"
    assert el.attrs == {}
    assert el.parent_tags == []
