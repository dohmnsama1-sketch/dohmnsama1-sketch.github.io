# DOHM Agent Commerce Directory

**Purpose:** machine-readable discovery and a browser-based, deterministic product suitability search, directing qualified buyers to existing published seller checkouts.

- Read-only catalog (`catalog.json`) captured from 9 published product records via the seller's authenticated Gumroad connection on 21 November 2026.
- Customer input stays in browser. No LLM inference API, tracking cookies, customer account creation, payments, server-side data collection, or hidden popups.
- Direct verified Gumroad URLs only, link attribution includes basic `utm_*` campaign parameters.
- The term "agent" here means *agent-compatible data discovery*, not a running A2A agent, MCP server, authenticated agent, autonomous buyer, paid API, or guarantee of agent traffic.
- Prices and availability are a dated snapshot; the seller checkout is the authority.

## Host

Deploy this folder under any static host path, e.g. `/agent-commerce/` on GitHub Pages. All files use relative references. The `README.md` and `index.html` can be copied into a Hugging Face Static Space (use its `README.md` frontmatter with `sdk: static`) after user credentials and account write access are available. Static hosting alone cannot take payments on behalf of buyers.

## QA

```bash
node test.mjs
python -m http.server 8765
# visit http://localhost:8765/index.html
```

## Revenue attribution limitations

The directory only reports product destinations and tags outgoing links with UTM. Without actual Google Analytics / Gumroad referral and payment reporting, purchases cannot be attributed reliably. A conversion funnel is not validated just because a button is visible.

## Future paid expansion

Potential enterprise version: signed catalog, independent A2A-compatible service backed by a secured server, authorized merchant accounting, product license validation and x402 only after a real issuer wallet, customer demand and tested security model. Do not advertise these as available today.