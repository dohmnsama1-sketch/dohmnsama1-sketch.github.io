'use strict';
const {test}=require('node:test'),assert=require('node:assert/strict');
const {backtest}=require('./xauusd-backtest.cjs');
function bars(n=120){return Array.from({length:n},(_,i)=>{const c=3000+i*.1+Math.sin(i/4)*5;return {time:new Date(Date.UTC(2026,0,1,0,i)).toISOString(),open:c-.2,high:c+1,low:c-1,close:c}})}
test('deterministic backtest with finite metrics and valid trade records',()=>{const a=backtest(bars()),b=backtest(bars());assert.deepEqual(a,b);assert.ok(Number.isFinite(a.finalEquity));assert.equal(a.initialEquity,500);assert.equal(a.tradeCount,a.trades.length);});
test('does not mutate input bars',()=>{const b=bars(),before=JSON.stringify(b);backtest(b);assert.equal(JSON.stringify(b),before)});
test('rejects unordered timestamps',()=>{const b=bars();b[3].time=b[2].time;assert.throws(()=>backtest(b),/unordered/)});
test('rejects OHLC corruption',()=>{const b=bars();b[4].low=b[4].high+1;assert.throws(()=>backtest(b),/OHLC/)});
test('rejects aggressive risk settings',()=>assert.throws(()=>backtest(bars(),{riskFraction:.5}),/Unsafe/));
test('rejects negative execution costs',()=>assert.throws(()=>backtest(bars(),{slippage:-1}),/Unsafe/));
test('insufficient data fails closed',()=>assert.throws(()=>backtest(bars(12)),/Insufficient/));
test('minimum lot constraint can prevent entries',()=>{const r=backtest(bars(),{minLot:1000});assert.equal(r.tradeCount,0)});
