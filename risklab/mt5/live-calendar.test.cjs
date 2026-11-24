'use strict';
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path');
const base=path.join(__dirname,'ZALAH_NewsShock_SafeResearch_v105.mq5');
const full=path.join(__dirname,'ZALAH_LiveCalendar_SafeResearch_v106.mq5');
const v105=fs.readFileSync(base,'utf8');
const v106=fs.readFileSync(full,'utf8');
test('v1.06 is independent, DEMO only, default manual entries still disabled',()=>{
 assert.match(v105,/#property version "1.05"/);
 assert.match(v106,/#property version "1.06"/);
 assert.match(v106,/ACCOUNT_TRADE_MODE\)!=ACCOUNT_TRADE_MODE_DEMO/);
 assert.match(v106,/InpAllowDemoOrders=false/);
});
test('live USD economic calendar uses official native MT5 APIs',()=>{
 assert.match(v106,/InpUseLiveUsdEconomicCalendar=true/);
 assert.match(v106,/CalendarValueHistory\(values,/);
 assert.match(v106,/now\+InpCalendarLookaheadHours\*3600,"","USD"/);
 assert.match(v106,/CalendarEventById\(values\[i\]\.event_id,event\)/);
 assert.match(v106,/event\.importance<CALENDAR_IMPORTANCE_HIGH/);
 assert.match(v106,/event\.time_mode!=CALENDAR_TIMEMODE_DATETIME/);
});
test('unavailable, unreliable and tester calendar fail CLOSED',()=>{
 assert.match(v106,/if\(MQLInfoInteger\(MQL_TESTER\)\)/);
 assert.match(v106,/diagCalendarFailed\+\+/);
 assert.match(v106,/if\(found<0\)/);
 assert.match(v106,/calendarFeedOK=false;/);
 assert.match(v106,/if\(!calendarFeedOK\|\|now>=calendarExpiry\) return true;/);
 assert.match(v106,/NewsWindowActive\(now\)\|\|LiveUsdCalendarWindow\(now\)/);
});
test('news windows and refreshes use server timestamps and are not signals',()=>{
 assert.match(v106,/datetime calendarCheckedAt=0/);
 assert.match(v106,/calendarExpiry=now\+InpCalendarRefreshMinutes\*60;/);
 assert.match(v106,/now>=t-InpNewsBeforeMinutes\*60&&now<=t\+InpNewsAfterMinutes\*60/);
 assert.match(v106,/InpCalendarRefreshMinutes<5/);
 assert.match(v106,/InpCalendarLookaheadHours<1/);
});
test('unexpected volatility circuit-breaker is retained',()=>{
 assert.match(v106,/ArmShockHalt\(now,"spread exceeds allowed price band"\)/);
 assert.match(v106,/GlobalVariableSet\(guardPrefix\+"SHOCK"/);
 assert.match(v106,/InpDiscontinuityMinutes\*60/);
 assert.match(v106,/CopyBuffer\(atrHandle,0,2,1,historicalATR\)/);
});
test('real-money gate and capital-risk rejection remain',()=>{
 assert.match(v106,/InpRiskPct>1/);
 assert.match(v106,/OrderCalcProfit/);
 assert.match(v106,/OrderCalcMargin/);
 assert.match(v106,/lots<minVol/);
 assert.match(v106,/trade\.PositionClose\(ticket\)/);
});
