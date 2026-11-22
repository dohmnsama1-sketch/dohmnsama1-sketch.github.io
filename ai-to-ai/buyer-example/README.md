# DOHMAN Agent Tools — x402 buyer quickstart

**For developers building AI agents that need paid, scoped data evidence.** Use an existing, live x402 endpoint with no seller API key or subscription. A wallet-compatible x402 client must approve and pay the exact quote for real execution.

## Four real services

| Alias | Task | Price | Example request |
| --- | --- | ---: | --- |
| `email` | Email address format and public DNS/domain evidence (NOT mailbox verification) | 0.001 USDC | `{"email":"support@example.com"}` |
| `domain` | Public DNS/company website context (NOT legal KYB) | 0.003 USDC | `{"domain":"example.com"}` |
| `batch` | Domain evidence for 1–10 emails | 0.005 USDC | `{"emails":["support@example.com"]}` |
| `web` | Bounded public-web source evidence for RAG | 0.002 USDC | `{"urls":["https://example.com/"],"respect_robots":true}` |

All prices are **per call** and subject to the live quote. No promise of response accuracy, inbox deliverability, trading signal, or business results. Base mainnet (chain 8453) USDC is the payment asset. Your code/agent must handle service errors and rate limits; no hosted dashboard subscription.

## Free integration: validate the live payment quote

Requirements: Node.js 22+. Run from this directory:

```bash
node buyer.mjs --quote email
node buyer.mjs --quote domain
node --test test.mjs
```

The quote step sends an **unsigned GET** and expects HTTP **402**, checks the Base USDC token address, recipient wallet, payment type, and capped amount, then prints a quote. **It cannot debit a wallet** and requires no secret or API key.

## Optional *real* payment, initiated by the buyer only

The following is **not** a simulation: it can send real USDC from the buyer's wallet on Base. Do not run it unless you own the wallet, understand and approve the amount, and want to purchase the actual service. **DO NOT put a private key in GitHub, a webpage, a chat, or a public build log.** Use a dedicated low-balance buyer wallet and secret manager. No seller secrets are required.

```bash
npm install @x402/fetch @x402/evm viem
# Configure EVM_PRIVATE_KEY privately in your local environment or secret manager.
node buyer.mjs --pay email
```

The example validates both the initial 402 and the subsequent 402 before signing. It rejects unknown seller URLs, wrong recipient, wrong settlement rail, multiple payment choices, and quotes exceeding the service-specific maximum or $0.005. A `--pay` call requires an explicit command; the script never charges on startup, unattended quote, or test. A successful paid response is accepted only when the server also supplies a bounded `payment-response` receipt header; otherwise the client fails closed and instructs the buyer to reconcile the wallet before any retry. Network errors after settlement may require reconciliation, so **do not blindly retry** a failed paid call.

For production, integrate a transaction ledger, wallet-based per-agent spending policies, replay protection, idempotency support and a human approval workflow for spending. This is a reference buyer client, **not a claim of external paid-call production test**. The 18 automated tests use synthetic payment quotes only.

## Agent/MCP and machine discovery

- [Price and limitations](https://dohmnsama1-sketch.github.io/ai-to-ai/services.json)
- [Buyer landing](https://dohmnsama1-sketch.github.io/ai-to-ai/)
- [Live x402 service discovery](https://tutevpsjeewjulryvvdo.supabase.co/functions/v1/x402-market-gateway/.well-known/x402)
- [MCP gateway (tool discovery / payment handoff)](https://tutevpsjeewjulryvvdo.supabase.co/functions/v1/mcp-gateway)
- [OpenAPI](https://tutevpsjeewjulryvvdo.supabase.co/functions/v1/x402-market-gateway/openapi.json)

This seller also appears in the [Agent402 marketplace](https://agent402.tools/marketplace), but listing is not evidence of customer-funded purchase or guaranteed dispatch.

## Security and commercial terms

The example reads only published HTTP 402 quotes. Vendor data is not guaranteed to be accurate, fresh or complete. The API payment is executed directly between the buyer and deployed seller resource using the facilitator specified in its quote. We are not affiliated with Coinbase, Circle, PayAI, Agent402 or Supabase. Do not use these tools for indiscriminate email harvesting, spam, unlawful targeting or confidential data.