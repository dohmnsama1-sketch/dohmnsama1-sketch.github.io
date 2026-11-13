#!/usr/bin/env python3
"""Weekly buyer-journey link check.

Finds every shop link (Gumroad, Payhip, Amazon) and every same-site link in the
published HTML pages and Pinterest RSS feeds, then requests each one.
- Gumroad / Payhip / own-site links that are not HTTP 200 FAIL the job, so GitHub
  emails the repo owner that a buy link is broken.
- Amazon often blocks datacenter IPs (503/403), so Amazon problems are warnings only.
Standard library only; no secrets.
"""
import html, os, re, sys, time, urllib.error, urllib.request
from urllib.parse import urljoin, urlparse

SITE = "https://dohmnsama1-sketch.github.io/"
SHOP = re.compile(r"(gumroad\.com|payhip\.com|amazon\.|amzn\.)", re.I)
UA = "Mozilla/5.0 (link-check; +https://dohmnsama1-sketch.github.io/)"

def collect():
    urls = {}
    for dp, dn, fn in os.walk("."):
        dn[:] = [d for d in dn if not d.startswith(".")]
        for f in fn:
            if not f.endswith((".html", ".xml")):
                continue
            path = os.path.join(dp, f)
            rel = os.path.relpath(path, ".").replace(os.sep, "/")
            if f.endswith(".xml") and not rel.startswith("feeds/"):
                continue
            page = SITE + (rel[:-10] if rel.endswith("index.html") else rel)
            text = open(path, encoding="utf-8", errors="ignore").read()
            found = re.findall(r'(?:href|src)="([^"]+)"', text)
            found += re.findall(r"<link>([^<]+)</link>", text)
            for raw in found:
                h = html.unescape(raw).strip()
                if not h or h.startswith(("#", "mailto:", "tel:", "javascript:", "data:")):
                    continue
                u = urljoin(page, h).split("#")[0]
                host = urlparse(u).netloc
                if host == urlparse(SITE).netloc or SHOP.search(host):
                    urls.setdefault(u, rel)
    return urls

def status(u):
    for attempt in range(3):
        try:
            req = urllib.request.Request(u, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=25) as r:
                return r.status
        except urllib.error.HTTPError as e:
            code = e.code
        except Exception as e:  # network hiccup
            code = f"ERR {type(e).__name__}"
        if code in (429, 500, 502, 503, 504) or str(code).startswith("ERR"):
            time.sleep(5 * (attempt + 1))
            continue
        return code
    return code

def main():
    urls = collect()
    print(f"Checking {len(urls)} links")
    fails, warns = [], []
    for u, src in sorted(urls.items()):
        c = status(u)
        time.sleep(0.3)
        if c == 200:
            continue
        line = f"{c}  {u}  (first seen in {src})"
        (warns if re.search(r"amazon\.|amzn\.", u) else fails).append(line)
    for w in warns:
        print("WARN", w)
    for f in fails:
        print("FAIL", f)
    print(f"Done: {len(urls)} checked, {len(fails)} broken, {len(warns)} Amazon warnings")
    sys.exit(1 if fails else 0)

if __name__ == "__main__":
    main()
