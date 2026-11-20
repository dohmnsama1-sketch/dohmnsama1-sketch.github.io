#!/usr/bin/env python3
"""Zero-cost, read-only discovery scout for x402 paid API competitors.

Uses public Autonomo directory; no wallet, keys, paid requests, or outreach.
Produces an evidence snapshot, not a claim of sales or marketplace eligibility.
"""
import argparse
import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone

BASE = "https://autonomo.fun/api/v1/projects"
TERMS = ("email verification", "domain enrichment", "openapi", "schema", "receipt", "agent safety", "data quality")

def fetch(term, limit=20):
    params = urllib.parse.urlencode({"q": term, "sort": "usage", "limit": limit})
    req = urllib.request.Request(BASE + "?" + params, headers={"User-Agent": "DohmnRevenueScout/1.0"})
    with urllib.request.urlopen(req, timeout=12) as response:
        if response.status != 200:
            raise RuntimeError(f"Directory HTTP {response.status}")
        payload = json.load(response)
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise ValueError("Unexpected directory response")
    return payload["data"]

def scout(terms=TERMS):
    results = []
    for term in terms:
        try:
            entries = fetch(term)
            for item in entries:
                if not isinstance(item, dict):
                    continue
                results.append({
                    "query": term,
                    "name": item.get("name"),
                    "website": item.get("website"),
                    "category": item.get("category"),
                    "calls30d": item.get("calls30d"),
                    "minPriceUsd": item.get("minPriceUsd"),
                    "networks": item.get("networks"),
                    "source": BASE,
                    "status": "research_only_not_qualified"
                })
        except Exception as exc:
            results.append({"query": term, "error": str(exc), "status": "fetch_failed"})
    return {"checked_at_utc": datetime.now(timezone.utc).isoformat(), "sources": [BASE],
            "disclaimer": "Usage figures are third-party directory claims, not verified sales, profit, eligibility or demand for our APIs.",
            "candidates": results}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", default="-", help="JSON path or - for stdout")
    args = p.parse_args()
    data = json.dumps(scout(), ensure_ascii=False, indent=2)
    if args.output == "-":
        print(data)
    else:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(data + "\n")

if __name__ == "__main__":
    main()
