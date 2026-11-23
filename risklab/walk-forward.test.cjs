'use strict';
const {test}=require('node:test'),assert=require('node:assert/strict');
const {walkForward}=require('./walk-forward.cjs');
function bars(n=1400){return Array.from({length:n},(_,i)=>{const c=3000+Math.sin(i/9)*8+i*.02;return {time:new Date(Date.UTC(2025,0,1,0,i)).toISOString(),open:c-.1,high:c+1,low:c-1,close:c}})}
test('chronological walk-forward separates train, embargo and test windows',()=>{const r=walkForward(bars(),{trainBars:400,testBars:200,embargoBars:30,folds:3});assert.equal(r.totalFolds,3);for(const f of r.folds){assert.ok(Date.parse(f.trainRange[1])<Date.parse(f.testRange[0]));assert.ok(Number.isFinite(f.testNetPnl));}});
test('fixed data and parameters produce identical fold reports',()=>{const b=bars();assert.deepEqual(walkForward(b),walkForward(b))});
test('rejects insufficient data',()=>assert.throws(()=>walkForward(bars(100)),/Insufficient/));
test('rejects zero embargo',()=>assert.throws(()=>walkForward(bars(),{embargoBars:0}),/Invalid/));
