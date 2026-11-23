'use strict';
const {test}=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path');
const v103=fs.readFileSync(path.join(__dirname,'ZALAH_Regime_Research_v103.mq5'),'utf8');
const v104=fs.readFileSync(path.join(__dirname,'ZALAH_SafeResearch_v104.mq5'),'utf8');
test('v1.03 control is preserved for unbiased comparison',()=>{
 assert.match(v103,/#property version "1.03"/);
 assert.match(v104,/#property version "1.04"/);
});
test('real accounts remain prohibited and orders opt-in only',()=>{
 assert.match(v104,/ACCOUNT_TRADE_MODE\)!=ACCOUNT_TRADE_MODE_DEMO/);
 assert.match(v104,/return INIT_FAILED/);
 assert.match(v104,/InpAllowDemoOrders=false/);
 assert.match(v104,/!InpAllowDemoOrders\|\|HasPosition\(\)/);
});
test('chart symbol must equal configured symbol and be gold',()=>{
 assert.match(v104,/StringFind\(InpSymbol,"XAUUSD"\)!=0/);
 assert.match(v104,/InpSymbol!=_Symbol/);
 assert.match(v104,/InpTimeframe!=_Period/);
});
test('demo online kill lock persists and is not reset after restart',()=>{
 for(const snippet of ['GlobalVariableCheck(guardPrefix+"LOCK")','GlobalVariableGet(guardPrefix+"LOCK")>=1.0','GlobalVariableSet(guardPrefix+"LOCK",locked?1.0:0.0)','GlobalVariablesFlush()','persistState=(!MQLInfoInteger(MQL_TESTER))'])assert.ok(v104.includes(snippet),snippet);
 assert.match(v104,/bool locked=false;/);
});
test('only own magic-tagged positions can be closed by drawdown response',()=>{
 assert.match(v104,/PositionGetString\(POSITION_SYMBOL\)!=InpSymbol/);
 assert.match(v104,/PositionGetInteger\(POSITION_MAGIC\)!=InpMagic/);
 assert.match(v104,/trade\.PositionClose\(ticket\)/);
 assert.match(v104,/ResultRetcode\(\)/);
});
test('stop/take-profit prices respect symbol tick size and risk budget',()=>{
 assert.match(v104,/SYMBOL_TRADE_TICK_SIZE/);
 assert.match(v104,/MathFloor\(\(entry-distance\)\/priceStep\)/);
 assert.match(v104,/MathCeil\(\(entry\+distance\)\/priceStep\)/);
 assert.match(v104,/OrderCalcProfit/);
 assert.match(v104,/lots<minVol/);
});
test('stale ticks fail closed outside Strategy Tester',()=>{
 assert.match(v104,/TimeTradeServer\(\)-\(datetime\)tick\.time/);
 assert.match(v104,/diagStaleTicks\+\+/);
});
test('no requirement for real-account key or secret is present',()=>{
 assert.doesNotMatch(v104,/input\s+string\s+(Password|ApiKey|Secret|Token)/i);
});
