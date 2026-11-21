/** Source Watch Lite: one public HTTPS document, byte-level SHA-256 drift only.
 * Free starter. No credentials, AI interpretation, semantic differencing or hosting.
 */
import { createHash } from 'node:crypto';
import { isIP } from 'node:net';

export const DEFAULT_MAX_BYTES = 256 * 1024;
export const DEFAULT_TIMEOUT_MS = 10_000;

export function validateTarget(raw, allowHosts) {
  if (!Array.isArray(allowHosts) || !allowHosts.length) throw new Error('An explicit host allowlist is required');
  if (typeof raw !== 'string' || raw.length > 2048) throw new Error('URL must be a string of at most 2048 characters');
  let u;
  try { u = new URL(raw); } catch { throw new Error('Invalid URL'); }
  if (u.protocol !== 'https:' || (u.port && u.port !== '443')) throw new Error('Only HTTPS on port 443 is permitted');
  if (u.username || u.password || u.search || u.hash) throw new Error('Credentials, query parameters and fragments are not supported');
  const host = u.hostname.toLowerCase().replace(/\.$/, '');
  if (isIP(host) || host === 'localhost' || /\.(localhost|local|internal|test|invalid)$/.test(host)) {
    throw new Error('IP addresses and local/reserved names are forbidden');
  }
  const allowed = allowHosts.map(x => String(x).toLowerCase().replace(/\.$/, ''));
  if (!allowed.every(x => x && !isIP(x) && /^(?:[a-z0-9-]+\.)+[a-z0-9-]+$/.test(x))) {
    throw new Error('Allowlist entries must be exact DNS hostnames');
  }
  if (!allowed.includes(host)) throw new Error('Hostname is not on the explicit allowlist');
  if (u.hostname !== host) throw new Error('Non-canonical hostname');
  return u.toString();
}

export async function probe(raw, { allowHosts, fetchImpl = fetch, timeoutMs = DEFAULT_TIMEOUT_MS, maxBytes = DEFAULT_MAX_BYTES } = {}) {
  const url = validateTarget(raw, allowHosts);
  if (!Number.isSafeInteger(timeoutMs) || timeoutMs < 1 || timeoutMs > 60000) throw new Error('timeoutMs outside 1–60000');
  if (!Number.isSafeInteger(maxBytes) || maxBytes < 1 || maxBytes > 1048576) throw new Error('maxBytes outside 1–1048576');
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(new Error('Timed out')), timeoutMs);
  let response;
  try {
    response = await fetchImpl(url, {
      method: 'GET',
      redirect: 'manual',
      signal: controller.signal,
      headers: { 'Accept': 'text/html, text/plain, application/json, application/xml, text/xml;q=0.8', 'User-Agent': 'SourceWatchLite/1.0 (controlled public content)' }
    });
    if (response.status >= 300 && response.status < 400) throw new Error('Redirect refused; explicitly allow and review any new target');
    if (response.status !== 200) throw new Error(`HTTP ${response.status}; probe not accepted`);
    const contentType = (response.headers?.get?.('content-type') || '').split(';')[0].trim().toLowerCase();
    if (!['text/plain', 'text/html', 'application/json', 'application/xml', 'text/xml'].includes(contentType)) {
      throw new Error(`Content type not supported: ${contentType || 'unknown'}`);
    }
    const headerLength = response.headers?.get?.('content-length');
    if (headerLength !== null && headerLength !== undefined && Number(headerLength) > maxBytes) {
      throw new Error('Content-Length above maximum');
    }
    if (!response.body || typeof response.body.getReader !== 'function') throw new Error('Response body is not a readable stream');
    const reader = response.body.getReader();
    const hash = createHash('sha256');
    let bytes = 0;
    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = value instanceof Uint8Array ? value : new Uint8Array(value);
        bytes += chunk.byteLength;
        if (bytes > maxBytes) throw new Error('Stream exceeds maximum response size');
        hash.update(chunk);
      }
    } finally { try { await reader.cancel(); } catch {} }
    return { url, bytes, sha256: hash.digest('hex'), contentType, capturedAt: new Date().toISOString(), status: 200 };
  } finally {
    clearTimeout(timer);
    if (response?.body && !response.body.locked) try { await response.body.cancel(); } catch {}
  }
}

export function compare(current, previous) {
  if (!current || !/^[0-9a-f]{64}$/.test(current.sha256)) throw new Error('Current SHA-256 required');
  if (previous == null) return 'baseline-created';
  if (previous.url !== current.url || !/^[0-9a-f]{64}$/.test(previous.sha256 ?? '')) throw new Error('Invalid baseline or different target URL');
  return previous.sha256 === current.sha256 ? 'unchanged' : 'changed';
}