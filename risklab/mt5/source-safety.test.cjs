'use strict';
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'ZALAH_Demo_Guard.mq5'),'utf8');
// Source-level guardrails only. This does NOT compile MQL5 or validate live execution.
test('demo-only EA refuses initialization on a real trading account',()=>{
 assert.match(source,/AccountInfoInteger\(ACCOUNT_TRADE_MODE\)!=ACCOUNT_TRADE_MODE_DEMO/);
 assert.match(source,/return INIT_FAILED/);
});
test('broker order sending is opt-in and disabled by default',()=>{
 assert.match(source,/input bool InpAllowDemoOrders=false/);
 assert.match(source,/!InpAllowDemoOrders/);
});
test('spread threshold is in price units, not fragile broker points',()=>{
 assert.match(source,/InpMaxSpreadPrice=0\.50/);
 assert.match(source,/\(tick\.ask-tick\.bid\)>InpMaxSpreadPrice/);
 assert.doesNotMatch(source,/InpMaxSpreadPoints/);
});
test('risk-based position sizing and broker stop-loss are present',()=>{
 assert.match(source,/OrderCalcProfit/);
 assert.match(source,/lots<minVol/);
 assert.match(source,/trade\.Buy\(lots,InpSymbol,0,stop,target/);
 assert.match(source,/trade\.Sell\(lots,InpSymbol,0,stop,target/);
});
