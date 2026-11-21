#!/usr/bin/env node
import { probe, compare } from './core.mjs';
import { readFile, writeFile, rename, unlink } from 'node:fs/promises';
import { basename, dirname, join } from 'node:path';
import { randomUUID } from 'node:crypto';

async function main() {
  const url = process.argv[2];
  if (!url || process.argv.length > 3) throw new Error('Usage: node watch.mjs <single-public-https-url>');
  const allowHosts = (process.env.WATCH_ALLOWED_HOSTS || 'docs.github.com').split(',').map(x => x.trim()).filter(Boolean);
  const path = process.env.WATCH_STATE_FILE || '.source-watch-lite-state.json';
  if (!path.endsWith('.json') || path.length > 300 || basename(path).startsWith('..')) throw new Error('State file must be a controlled .json path');
  let previous = null;
  try { previous = JSON.parse(await readFile(path, 'utf8')); } catch (e) { if (e.code !== 'ENOENT') throw new Error('State JSON is unreadable or invalid'); }
  const current = await probe(url, { allowHosts });
  const outcome = compare(current, previous);
  const record = { tool: 'source-watch-lite', outcome, current, priorSha256: previous?.sha256 ?? null, note: 'Byte-level change only, not a semantic judgement; no claims about factual reliability.' };
  const temp = join(dirname(path), `.source-watch-${randomUUID()}.tmp`);
  try { await writeFile(temp, JSON.stringify(current, null, 2) + '\n', { encoding: 'utf8', mode: 0o600, flag: 'wx' }); await rename(temp, path); }
  catch(e) { await unlink(temp).catch(()=>{}); throw e; }
  process.stdout.write(JSON.stringify(record) + '\n');
  if (outcome === 'changed' && process.env.WATCH_FAIL_ON_CHANGE === '1') process.exitCode = 2;
}
main().catch(e => { process.stderr.write(JSON.stringify({tool:'source-watch-lite',error:String(e.message||e)}) + '\n'); process.exitCode = 1; });