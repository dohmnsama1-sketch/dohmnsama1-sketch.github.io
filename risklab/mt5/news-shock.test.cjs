'use strict';
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path');
const old=fs.readFileSync(path.join(__dirname,'ZALAH_SafeResearch_v104.mq5'),'utf8');
const newer=fs.readFileSync(path.join(__dirname,'ZALAH_NewsShock_SafeResearch_v105.mq5'),'utf8');
test('v1.05 is a separate unvalidated demo-only EA',()=>{
 assert.match(old,/#property version "1.04"/);
 assert.match(newer,/#property version "1.05"/);
 assert.match(newer,/ACCOUNT_TRADE_MODE\)!=ACCOUNT_TRADE_MODE_DEMO/);
 assert.match(newer,/InpAllowDemoOrders=false/);
 assert.match(newer,/!InpAllowDemoOrders\|\|HasPosition\(\)/);
});
test('no claimed automatic news intelligence; manual data required and fails closed',()=>{
 assert.match(newer,/InpUseManualNewsBlackout=false/);
 assert.match(newer,/StringSplit\(InpHighImpactServerTimes,';',tokens\)/);
 assert.match(newer,/InpNewsScheduleExpiresServer<=TimeTradeServer\(\)/);
 assert.match(newer,/return INIT_PARAMETERS_INCORRECT;/);
 assert.match(newer,/NewsWindowActive\(now\)/);
 assert.match(newer,/diagNewsBlocked\+\+/);
});
test('future market-news windows are clocked in explicit BROKER SERVER TIME',()=>{
 assert.match(newer,/BROKER SERVER TIME/);
 assert.match(newer,/InpNewsBeforeMinutes\*60/);
 assert.match(newer,/InpNewsAfterMinutes\*60/);
 assert.match(newer,/now>InpNewsScheduleExpiresServer/);
});
test('unforeseen price dislocation trips persistent fail-closed market circuit breaker',()=>{
 assert.match(newer,/InpUseShockCircuitBreaker=true/);
 assert.match(newer,/closedHigh-closedLow/);
 assert.match(newer,/InpShockBarRangeATR\*historicalATR\[0\]/);
 assert.match(newer,/CopyBuffer\(atrHandle,0,2,1,historicalATR\)/);
 assert.match(newer,/InpDiscontinuityMinutes\*60/);
 assert.match(newer,/GlobalVariableSet\(guardPrefix\+"SHOCK"/);
 assert.match(newer,/GlobalVariableGet\(guardPrefix\+"SHOCK"/);
 assert.match(newer,/diagShockBlocked\+\+/);
});
test('news and shocks are entry blockers, not countertrend alpha claims',()=>{
 assert.match(newer,/if\(NewsWindowActive\(now\)\)/);
 assert.match(newer,/ArmShockHalt\(now,"spread exceeds allowed price band"\)/);
 assert.match(newer,/if\(now<shockHaltUntil\)/);
 assert.match(newer,/CopyBuffer\(fastHandle,0,1,2,f\)/);
 assert.match(newer,/CopyBuffer\(slowHandle,0,1,2,s\)/);
});
test('broker-side stops, lot floor and margin remain protected',()=>{
 for(const s of ['OrderCalcProfit','OrderCalcMargin','lots<minVol','trade.Buy(lots,InpSymbol,0,stop,target','trade.Sell(lots,InpSymbol,0,stop,target'])assert.ok(newer.includes(s),s);
 assert.match(newer,/InpRiskPct>1/);
 assert.match(newer,/InpSymbol!=_Symbol/);
 assert.match(newer,/InpTimeframe!=_Period/);
});
