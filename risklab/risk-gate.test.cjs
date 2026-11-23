// Run: node --test risklab/risk-gate.test.cjs
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

const html = fs.readFileSync(path.join(__dirname, 'index.html'), 'utf8');
const script = html.match(/<script>([\s\S]*?)<\/script>/)?.[1];
assert.ok(script, 'risk gate script must exist');

function evaluate(overrides = {}, verified = true) {
  const defaults = { equity: 10000, entry: 100, stop: 99, contract: 1,
    minlot: 1, step: 1, margin: 100, spread: 0.1, slippage: 0.2,
    commission: 0, risk: 0.25 };
  const inputs = { ...defaults, ...overrides };
  const ids = ['status', 'reasons', 'allowance', 'loss', 'minmargin', 'maxlot',
    'evaluate', 'verified', 'export'];
  const nodes = Object.fromEntries(ids.map(id => [id, {
    value: inputs[id], checked: id === 'verified' ? verified : false,
    textContent: '', className: '', children: [],
    replaceChildren() { this.children = []; },
    appendChild(child) { this.children.push(child); },
    addEventListener() {}
  }]));
  for (const [id, value] of Object.entries(inputs)) {
    nodes[id] = { value: String(value) };
  }
  const context = { document: {
    getElementById: id => nodes[id],
    createElement: () => ({ textContent: '' })
  }, Number, Object, Math };
  vm.runInNewContext(script, context, { timeout: 1000 });
  return { status: nodes.status.textContent,
    reasons: nodes.reasons.children.map(x => x.textContent),
    loss: nodes.loss.textContent };
}
test('nonzero adverse slippage with verified inputs permits arithmetic-only PASS', () => {
  assert.match(evaluate().status, /^PASS/);
});
test('zero adverse slippage blocks a PASS', () => {
  const result = evaluate({ slippage: 0 });
  assert.equal(result.status, 'NO TRADE');
  assert.ok(result.reasons.some(x => /slippage/.test(x)));
});
test('unverified contract blocks a PASS', () => {
  assert.equal(evaluate({}, false).status, 'NO TRADE');
});
test('oversized minimum-lot loss blocks a PASS', () => {
  assert.equal(evaluate({ stop: 1 }).status, 'NO TRADE');
});
test('invalid negative slippage is rejected', () => {
  assert.equal(evaluate({ slippage: -1 }).status, 'INVALID INPUT');
});
