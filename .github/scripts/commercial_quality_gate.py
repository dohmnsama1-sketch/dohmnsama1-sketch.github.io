#!/usr/bin/env python3
"""Commercial page preflight: deterministic local checks, no network/secrets/deps.

A passing result is not a guarantee of checkout functionality, accessibility,
customer acceptance, security certification or business performance.
Keep those checks separate and explicitly evidenced.
"""
from __future__ import annotations

import html
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[2]
PAGES = [Path("index.html"), Path("gradercheck/index.html")]
BASE_HOST = "dohmnsama1-sketch.github.io"


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.refs: list[tuple[str, str, dict[str, str]]] = []
        self.ids: set[str] = set()
        self.title_text = ""
        self.in_title = False
        self.lang = ""
        self.h1_count = 0
        self.meta: dict[str, str] = {}
        self.images_missing_alt = 0

    def handle_starttag(self, tag, raw_attrs):
        attrs = dict(raw_attrs)
        if tag == "html":
            self.lang = attrs.get("lang", "")
        if tag == "title":
            self.in_title = True
        if tag == "h1":
            self.h1_count += 1
        if attrs.get("id"):
            self.ids.add(attrs["id"])
        if tag == "meta" and attrs.get("name"):
            self.meta[attrs["name"].lower()] = attrs.get("content", "")
        if tag == "img" and "alt" not in attrs:
            self.images_missing_alt += 1
        for key in ("href", "src"):
            if key in attrs:
                self.refs.append((tag, attrs[key], attrs))

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False

    def handle_data(self, data):
        if self.in_title:
            self.title_text += data


def resolve_local(source: Path, raw: str) -> tuple[Path | None, str]:
    raw = html.unescape(raw.strip())
    if not raw or raw.startswith(("#",)):
        parsed = urlparse(raw)
        return source, parsed.fragment
    parsed = urlparse(raw)
    if parsed.scheme in {"mailto", "tel", "sms", "data"}:
        return None, ""
    if parsed.scheme and parsed.scheme != "https":
        raise ValueError("insecure or unsupported URL scheme")
    if parsed.netloc and parsed.netloc != BASE_HOST:
        return None, ""
    if not parsed.path and parsed.fragment:
        return source, parsed.fragment
    relative = Path(unquote(parsed.path).lstrip("/"))
    if parsed.path.startswith("/"):
        target = ROOT / relative
    else:
        target = ROOT / source.parent / relative
    if parsed.path.endswith("/") or target.is_dir():
        target = target / "index.html"
    if target.resolve() != ROOT.resolve() and ROOT.resolve() not in target.resolve().parents:
        raise ValueError("local link escapes website root")
    return target.relative_to(ROOT), parsed.fragment


def main() -> int:
    errors: list[str] = []
    checked = 0
    for relative in PAGES:
        path = ROOT / relative
        if not path.is_file():
            errors.append(f"{relative}: page missing")
            continue
        source = path.read_text(encoding="utf-8")
        p = Page()
        try:
            p.feed(source)
            p.close()
        except Exception as exc:
            errors.append(f"{relative}: HTML parse failed: {exc}")
            continue
        for label, condition in [
            ("missing HTML lang", bool(p.lang)),
            ("missing descriptive title", len(p.title_text.strip()) >= 20),
            ("missing viewport", bool(p.meta.get("viewport"))),
            ("missing meta description", len(p.meta.get("description", "")) >= 35),
            ("expected exactly one H1", p.h1_count == 1),
            ("image without alt", p.images_missing_alt == 0),
        ]:
            if not condition:
                errors.append(f"{relative}: {label}")
        for tag, raw, attrs in p.refs:
            checked += 1
            link = html.unescape(raw.strip())
            if link.lower().startswith("javascript:"):
                errors.append(f"{relative}: prohibited javascript URL")
                continue
            if tag == "a" and attrs.get("target") == "_blank" and "noopener" not in attrs.get("rel", ""):
                errors.append(f"{relative}: external new-tab link without noopener")
            try:
                target, fragment = resolve_local(relative, link)
            except ValueError as exc:
                errors.append(f"{relative}: {link[:80]}: {exc}")
                continue
            if target is None:
                continue
            candidate = ROOT / target
            if not candidate.is_file():
                errors.append(f"{relative}: broken local ref {link}")
                continue
            if fragment:
                if target == relative:
                    other = p
                elif target.suffix.lower() in {".html", ".htm"}:
                    other = Page()
                    other.feed(candidate.read_text(encoding="utf-8"))
                else:
                    other = None
                if other is not None and unquote(fragment) not in other.ids:
                    errors.append(f"{relative}: nonexistent fragment {link}")
        if relative.as_posix() == "gradercheck/index.html":
            for expected in (
                "synthetic", "No payment is collected",
                "not a customer result", "WebCrypto",
                "contact", "USD 500",
            ):
                if expected.lower() not in source.lower():
                    errors.append(f"{relative}: missing required commercial disclosure {expected!r}")
            if "mailto:" not in source:
                errors.append(f"{relative}: no functioning contact path")
        if relative.as_posix() == "index.html":
            if "gumroad.com/l/meezan-pro" not in source:
                errors.append(f"{relative}: existing paid product route unexpectedly absent")
    print(f"Commercial preflight: {len(PAGES)} pages; {checked} references")
    if errors:
        for error in errors:
            print("FAIL:", error)
        print(f"FAIL: {len(errors)} issue(s). No release approval claimed.")
        return 1
    print("PASS: deterministic page structure, local-link and disclosure preflight")
    print("NOT VERIFIED HERE: external checkout, real mobile UX, security, or customer acceptance")
    return 0


if __name__ == "__main__":
    sys.exit(main())
