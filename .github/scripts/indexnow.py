#!/usr/bin/env python3
"""Submit every URL in sitemap.xml to IndexNow. Free, no secrets (key is already public)."""
import json, sys, urllib.request, xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # repo root
SITEMAP = ROOT / "sitemap.xml"
# key file is the published {key}.txt at the site root
keys = list(ROOT.glob("[0-9a-f]*.txt"))
if not keys:
    sys.exit("No IndexNow key file (32-hex .txt) at repo root")
key = keys[0].stem
HOST = "dohmnsama1-sketch.github.io"
KEY_LOC = f"https://{HOST}/{key}.txt"

ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
tree = ET.parse(SITEMAP)
urls = [el.text.strip() for el in tree.findall("sm:url/sm:loc", ns) if el.text]
if not urls:
    # try without namespace (some writers omit it on children)
    urls = [el.text.strip() for el in tree.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}loc") if el.text]
if not urls:
    sys.exit("No URLs in sitemap")

payload = {
    "host": HOST,
    "key": key,
    "keyLocation": KEY_LOC,
    "urlList": urls,
}
body = json.dumps(payload).encode()
req = urllib.request.Request(
    "https://api.indexnow.org/indexnow",
    data=body,
    headers={"Content-Type": "application/json; charset=utf-8", "User-Agent": "dohmnsama1-indexnow/1.0"},
    method="POST",
)
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        print(f"IndexNow {r.status} — {len(urls)} URLs")
        print(r.read()[:300].decode("utf-8", "replace"))
except urllib.error.HTTPError as e:
    print(f"IndexNow HTTP {e.code}: {e.read()[:400].decode('utf-8','replace')}", file=sys.stderr)
    sys.exit(1)
