'use strict';
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path');
const old=fs.readFileSync(path.join(__dirname,'ZALAH_LiveCalendar_SafeResearch_v106.mq5'),'utf8');
const latest=fs.readFileSync(path.join(__dirname,'ZALAH_RiskHeartbeat_Research_v107.mq5'),'utf8');
test('distinct v1.07 research EA preserves v1.06 and real account hard lock',()=>{
 assert.match(old,/#property version "1.06"/);
 assert.match(latest,/#property version "1.07"/);
 assert.match(latest,/ACCOUNT_TRADE_MODE\)!=ACCOUNT_TRADE_MODE_DEMO/);
 assert.match(latest,/InpAllowDemoOrders=false/);
});
test('timer heartbeat checks equity independently of market ticks',()=>{
 assert.match(latest,/void OnTimer\(\)/);
 assert.match(latest,/if\(!MonitorEquitySafety\(\)\) return;/);
 assert.match(latest,/EventSetTimer\(InpSafetyTimerSeconds\)/);
 assert.match(latest,/EventKillTimer\(\)/);
 assert.match(latest,/if\(!MonitorEquitySafety\(\)\) return;\n double eq/);
 assert.match(latest,/LatchGuard\("open DEMO position with stale or unavailable quote"\)/);
});
test('quote stale stop only applies to EA owned magic-tagged DEMO positions',()=>{
 assert.match(latest,/bool HasOwnPosition\(\)/);
 assert.match(latest,/PositionGetInteger\(POSITION_MAGIC\)==InpMagic/);
 assert.match(latest,/!InpAllowDemoOrders\|\|!HasOwnPosition\(\)/);
 assert.match(latest,/InpOpenPositionMaxQuoteAgeSeconds/);
});
test('conservative quote stress and estimated commission included before lot sizing',()=>{
 assert.match(latest,/InpAdverseStopSlippagePrice=0.50/);
 assert.match(latest,/InpAssumedCommissionUSDPerLotRoundTurn=7.0/);
 assert.match(latest,/stop-InpAdverseStopSlippagePrice/);
 assert.match(latest,/stop\+InpAdverseStopSlippagePrice/);
 assert.match(latest,/OrderCalcProfit\(kind,InpSymbol,1.0,entry,stressedExit,lossPerLot\)/);
 assert.match(latest,/InpAssumedCommissionUSDPerLotRoundTurn;/);
 assert.match(latest,/if\(lots<minVol\|\|lots>maxVol\)/);
 assert.match(latest,/AccountInfoString\(ACCOUNT_CURRENCY\)!="USD"/);
});
test('tester explicitly rejects native calendar instead of silently executing zero trades',()=>{
 assert.match(latest,/MQLInfoInteger\(MQL_TESTER\)&&InpUseLiveUsdEconomicCalendar/);
 assert.match(latest,/SAFETY LOCK: disable live calendar explicitly in Strategy Tester/);
 assert.match(latest,/return INIT_PARAMETERS_INCORRECT;/);
});
test('calendar failures, shock cooldown and order stop remain intact',()=>{
 assert.match(latest,/CalendarValueHistory/);
 assert.match(latest,/if\(!calendarFeedOK\|\|now>=calendarExpiry\) return true;/);
 assert.match(latest,/ArmShockHalt\(now,"spread exceeds allowed price band"\)/);
 assert.match(latest,/trade\.Buy\(lots,InpSymbol,0,stop,target/);
 assert.match(latest,/trade\.Sell\(lots,InpSymbol,0,stop,target/);
});
