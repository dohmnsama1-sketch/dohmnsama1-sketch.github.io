# Source Watch Lite — free, auditable public-source drift check

**A small, original Node.js 22+ command-line tool that checks one allowlisted public HTTPS page and records a SHA-256 byte hash.** Its goal is to give a developer or AI workflow a clear, inspectable `unchanged` / `changed` / `baseline-created` result. It does not claim to validate content accuracy, predict the future or find disinformation.

## Quick start

```bash
# From this folder; no npm install needed
node --test test.mjs
node watch.mjs https://docs.github.com/en
# Subsequent run compares against local .source-watch-lite-state.json
```

To monitor an approved different host, **explicitly** select it:

```bash
WATCH_ALLOWED_HOSTS=huggingface.co node watch.mjs https://huggingface.co/docs/hub/spaces-overview
```

For CI, you can set `WATCH_FAIL_ON_CHANGE=1` so a detected change exits with status 2. The tool exits 1 for invalid input or a failed HTTP probe; it never silently treats an HTTP error as unchanged. It prints one JSON record to stdout on successful probes. Delete the generated state file to start a new baseline. Do not commit user-specific state files.

## Why it's designed this way

- Single explicit allowlisted HTTPS host; refuses userinfo, query tokens, non-443 ports, IP addresses and common local hostnames.
- Rejects redirects, unrecognized MIME types, non-200 responses, and responses larger than 256 KiB by default.
- Bounded timeout and stream-size guard; SHA-256 is computed over raw response bytes, not extracted text.
- State file written through a temporary file and atomic rename.
- Output states are **not** security certification or semantic diffs. Even a benign tracking snippet can change bytes; changing JavaScript-rendered content is not captured unless present in the HTTP response.

**Important:** Host allowlisting is a conservative input filter, not a comprehensive SSRF firewall. DNS-rebinding and custom resolvers are not protected by this starter. Do not run against attacker-supplied URLs or in a privileged corporate network. Respect target-site terms and fetch limits. Never put a credential in a target URL. Public HTTPS only.

## Paid option (different, larger scope)

For multiple sources, cache-aware checks, validators (ETag/Last-Modified), JSONL proof and stronger private-network filtering, see the separate **[AI Agent Web Change & Source Health Kit — $79](https://dohmnsama.gumroad.com/l/ommpg?utm_source=github-pages&utm_medium=free-starter&utm_campaign=source-watch-lite)**. The paid kit's published description is the authoritative list of capabilities and limits. **Buying it does not guarantee security, commercial success, uptime or factual truth.** This free sample is not the premium source package.

## Licenses and attribution

Free starter `core.mjs`, `watch.mjs`, `test.mjs`, and this README: MIT License (see `LICENSE`). This is an original free sampler and is not associated with GitHub, Hugging Face, or a monitoring vendor.