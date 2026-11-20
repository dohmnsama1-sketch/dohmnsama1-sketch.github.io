#!/usr/bin/env python3
"""Read-only x402 receipt revenue audit. No wallet keys, transfers, or RPC calls."""
import argparse
import csv
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path

CONFIRMED = {"confirmed", "settled", "completed", "success"}
NON_CUSTOMER = {"provider_verification_canary", "self_payment", "test", "refund", "reversed"}

def audit(receipts, classifications):
    by_key = {}
    for row in classifications:
        key = str(row.get("receipt_key") or "")
        if key:
            by_key[key] = str(row.get("classification") or "unknown").strip().lower()
    seen = set()
    out = {"rows": 0, "duplicates": 0, "confirmed_gross_usd": "0", "confirmed_non_customer_usd": "0",
           "confirmed_unattributed_usd": "0", "confirmed_customer_candidate_usd": "0",
           "missing_transaction": 0, "invalid_amount": 0, "not_confirmed": 0,
           "warning": "Candidate is NOT verified buyer revenue, withdrawable cash or profit."}
    totals = {k: Decimal("0") for k in ("confirmed_gross_usd", "confirmed_non_customer_usd",
             "confirmed_unattributed_usd", "confirmed_customer_candidate_usd")}
    for row in receipts:
        out["rows"] += 1
        key = str(row.get("receipt_key") or "").strip()
        tx = str(row.get("settlement_tx") or "").strip().lower()
        network = str(row.get("network") or "").strip()
        unique = (network, tx) if tx else (network, key)
        if not key or not unique[1] or unique in seen:
            out["duplicates"] += 1
            continue
        seen.add(unique)
        if str(row.get("settlement_status") or "").lower().strip() not in CONFIRMED:
            out["not_confirmed"] += 1
            continue
        if not tx:
            out["missing_transaction"] += 1
            continue
        try:
            amount = Decimal(str(row.get("amount_usd") or ""))
            if not amount.is_finite() or amount <= 0:
                raise InvalidOperation
        except (InvalidOperation, ValueError):
            out["invalid_amount"] += 1
            continue
        totals["confirmed_gross_usd"] += amount
        cls = by_key.get(key, "unknown")
        if cls in NON_CUSTOMER:
            totals["confirmed_non_customer_usd"] += amount
        elif cls in ("external_customer_verified", "buyer_verified"):
            totals["confirmed_customer_candidate_usd"] += amount
        else:
            totals["confirmed_unattributed_usd"] += amount
    out.update({k: format(v, "f") for k, v in totals.items()})
    return out

def load(path):
    p = Path(path)
    if p.suffix.lower() == ".json":
        obj = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(obj, list):
            raise ValueError("JSON input must be an array of objects")
        return obj
    with p.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipts", help="CSV/JSON export of public.machine_x402_receipts")
    parser.add_argument("--classifications", help="CSV/JSON export of portfolio_ops.machine_receipt_classifications")
    args = parser.parse_args()
    print(json.dumps(audit(load(args.receipts), load(args.classifications) if args.classifications else []), indent=2))
if __name__ == "__main__":
    main()
