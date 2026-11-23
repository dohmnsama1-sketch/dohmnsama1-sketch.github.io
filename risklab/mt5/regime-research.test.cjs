'use strict';
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const baseline=fs.readFileSync(path.join(__dirname,'ZALAH_Demo_Guard.mq5'),'utf8');
const candidate=fs.readFileSync(path.join(__dirname,'ZALAH_Regime_Research_v103.mq5'),'utf8');
test('research version is separate; baseline v1.02 remains intact',()=>{
 assert.match(baseline,/#property version "1.02"/);
 assert.match(candidate,/#property version "1.03"/);
});
test('candidate is strictly demo-only and order sending remains opt-in',()=>{
 assert.match(candidate,/ACCOUNT_TRADE_MODE\)!=ACCOUNT_TRADE_MODE_DEMO/);
 assert.match(candidate,/input bool InpAllowDemoOrders=false/);
 assert.match(candidate,/locked\|\|!InpAllowDemoOrders/);
});
test('all added multi-timeframe signals use closed bars, not currently forming bar',()=>{
 assert.match(candidate,/CopyBuffer\(trendHandle,0,1,1,higherEMA\)/);
 assert.match(candidate,/iClose\(InpSymbol,InpTrendTimeframe,1\)/);
 for(const i of [0,1,2])assert.ok(candidate.includes('CopyBuffer(adxHandle,'+i+',1,1,'));
 assert.match(candidate,/CopyBuffer\(fastHandle,0,1,2,f\)/);
 assert.match(candidate,/CopyBuffer\(slowHandle,0,1,2,s\)/);
});
test('candidate filters trend, sideways regime and expensive spreads relative to ATR',()=>{
 assert.match(candidate,/InpUseHTFTrendFilter=true/);
 assert.match(candidate,/InpUseADXFilter=true/);
 assert.match(candidate,/InpUseCostToATRFilter=true/);
 assert.match(candidate,/\(tick.ask-tick.bid\)\/a\[0\]>InpMaxSpreadToATR/);
});
test('candidate preserves broker-side stops and capital risk gate',()=>{
 assert.match(candidate,/OrderCalcProfit/);
 assert.match(candidate,/lots<minVol/);
 assert.match(candidate,/trade\.Buy\(lots,InpSymbol,0,stop,target/);
 assert.match(candidate,/trade\.Sell\(lots,InpSymbol,0,stop,target/);
});
test('candidate emits numeric rejection counters for A/B diagnosis',()=>{
 for(const s of ['regime_filtered','adx_filtered','cost_filtered','regime_no_data','risk_lot_rejections','order_attempts'])assert.ok(candidate.includes(s));
});
