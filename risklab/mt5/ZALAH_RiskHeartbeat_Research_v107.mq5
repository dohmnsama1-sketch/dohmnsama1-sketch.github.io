//+------------------------------------------------------------------+
//| ZALAH Risk Heartbeat & News Shock Research EA - MT5 / MQL5                             |
//| Demo-only research EA. No profit or execution guarantee.          |
//+------------------------------------------------------------------+
#property strict
#property version "1.07"
#include <Trade/Trade.mqh>
CTrade trade;
input string InpSymbol="XAUUSDm"; // Must match chart/tester symbol
input ENUM_TIMEFRAMES InpTimeframe=PERIOD_M5;
input double InpRiskPct=0.5;
input double InpDailyLossPct=2.0;
input double InpMaxDrawdownPct=15.0;
input int InpFastMA=10;
input int InpSlowMA=30;
input int InpATRPeriod=14;
input double InpStopATR=2.0;
input double InpRewardRisk=1.5;
input double InpMaxSpreadPrice=0.50; // Ask-Bid maximum in USD/oz (price units), NOT points
// Research-only candidate: hypotheses, NOT empirically validated alpha.
input bool InpUseHTFTrendFilter=true;
input ENUM_TIMEFRAMES InpTrendTimeframe=PERIOD_H1;
input int InpTrendEMAPeriod=100;
input bool InpUseADXFilter=true;
input int InpADXPeriod=14;
input double InpMinADX=20.0;
input bool InpUseCostToATRFilter=true;
input double InpMaxSpreadToATR=0.20;
input int InpMaxDeviationPoints=30;
input ulong InpMagic=20261123;
input bool InpAllowDemoOrders=false; // Opt-in only; still DEMO ONLY
input bool InpCloseOwnPositionsOnLock=true; // Demo only; best effort, broker can reject
input int InpMaxTickAgeSeconds=10; // Applied in connected DEMO; tester exempts historical time
// Volatility/geopolitical *reaction* guards, not prediction of an unknown event.
input bool InpUseShockCircuitBreaker=true;
input double InpShockBarRangeATR=3.0; // prior closed M5 range / ATR before that bar
input int InpShockCooldownMinutes=60;
input int InpDiscontinuityMinutes=30;
// Scheduled known events must come from an independently verified point-in-time source.
// Event timestamps and expiry are in BROKER SERVER TIME (not Riyadh/UTC by default).
// Optional: when enabled, absent/malformed/stale schedules fail CLOSED (no new orders).
input bool InpUseManualNewsBlackout=false;
input string InpHighImpactServerTimes=""; // e.g. "2026.11.25 16:30;2026.12.02 16:30"
input datetime InpNewsScheduleExpiresServer=0;
input int InpNewsBeforeMinutes=45;
input int InpNewsAfterMinutes=45;
// Online USD macro calendar is NOT available inside MT5 Strategy Tester.
// Default enabled for supervised DEMO; Tester must set false + use archived
// point-in-time manual news schedule if news-aware backtesting is required.
input bool InpUseLiveUsdEconomicCalendar=true;
input int InpCalendarRefreshMinutes=15;
input int InpCalendarLookaheadHours=48;
// USD-denominated DEMO only: research loss allowances, NOT brokerage fee claims.
input double InpAdverseStopSlippagePrice=0.50;
input double InpAssumedCommissionUSDPerLotRoundTurn=7.0;
input int InpSafetyTimerSeconds=5;
input int InpOpenPositionMaxQuoteAgeSeconds=45;

int fastHandle=INVALID_HANDLE,slowHandle=INVALID_HANDLE,atrHandle=INVALID_HANDLE;
int trendHandle=INVALID_HANDLE,adxHandle=INVALID_HANDLE;
datetime lastBar=0;
double dayStartEquity=0,peakEquity=0;
int dayKey=-1;
bool locked=false;
long diagTicks=0,diagSpreadBlocked=0,diagBarChecks=0,diagSignals=0,diagRiskBlocked=0,diagMarginBlocked=0,diagOrderAttempts=0;
long diagRegimeBlocked=0,diagADXBlocked=0,diagCostBlocked=0,diagRegimeNoData=0;
string guardPrefix="";
bool persistState=false;
long diagKillCloseAttempts=0,diagStaleTicks=0;
datetime shockHaltUntil=0;
datetime newsEvents[];
long diagShockDetected=0,diagShockBlocked=0,diagNewsBlocked=0,diagMissingSchedule=0;
long diagCalendarRefreshes=0,diagCalendarFailed=0;
long diagTimerChecks=0,diagTimerQuoteAlerts=0;
datetime calendarCheckedAt=0;
datetime calendarExpiry=0;
datetime calendarHighImpact[];
bool calendarFeedOK=false;

bool LiveUsdCalendarWindow(datetime now)
{
 if(!InpUseLiveUsdEconomicCalendar) return false;
 // MT5 calendar APIs cannot be validated by Strategy Tester.
 // Do not bypass this gate or silently label tester P/L "news aware".
 if(MQLInfoInteger(MQL_TESTER))
 {
  diagCalendarFailed++;
  return true;
 }
 if(!calendarFeedOK||now>=calendarExpiry||calendarCheckedAt==0)
 {
  diagCalendarRefreshes++;
  MqlCalendarValue values[];
  int found=CalendarValueHistory(values,
        now-InpNewsBeforeMinutes*60,
        now+InpCalendarLookaheadHours*3600,"","USD");
  if(found<0)
  {
   calendarFeedOK=false;
   diagCalendarFailed++;
   PrintFormat("ZALAH_CALENDAR unavailable err=%d: block all entries",GetLastError());
   return true;
  }
  if(ArrayResize(calendarHighImpact,0)!=0)
  {
   calendarFeedOK=false;
   diagCalendarFailed++;
   return true;
  }
  for(int i=0;i<found;i++)
  {
   MqlCalendarEvent event;
   if(!CalendarEventById(values[i].event_id,event))
   {
    calendarFeedOK=false;
    diagCalendarFailed++;
    Print("ZALAH_CALENDAR event metadata unavailable: block all entries");
    return true;
   }
   if(event.importance<CALENDAR_IMPORTANCE_HIGH) continue;
   if(values[i].time<=0||event.time_mode!=CALENDAR_TIMEMODE_DATETIME)
   {
    // Important event with uncertain timing: do NOT assume it is safe.
    calendarFeedOK=false;
    diagCalendarFailed++;
    Print("ZALAH_CALENDAR high-impact event with uncertain release time: block entries");
    return true;
   }
   int n=ArraySize(calendarHighImpact);
   if(ArrayResize(calendarHighImpact,n+1)!=n+1)
   {
    calendarFeedOK=false;
    diagCalendarFailed++;
    return true;
   }
   calendarHighImpact[n]=values[i].time;
  }
  calendarCheckedAt=now;
  calendarExpiry=now+InpCalendarRefreshMinutes*60;
  calendarFeedOK=true;
  PrintFormat("ZALAH_CALENDAR refreshed USD HIGH events=%d until=%s",
    ArraySize(calendarHighImpact),TimeToString(calendarExpiry,TIME_DATE|TIME_SECONDS));
 }
 if(!calendarFeedOK||now>=calendarExpiry) return true;
 for(int i=0;i<ArraySize(calendarHighImpact);i++)
 {
  datetime t=calendarHighImpact[i];
  if(now>=t-InpNewsBeforeMinutes*60&&now<=t+InpNewsAfterMinutes*60)
   return true;
 }
 return false;
}

bool LoadNewsSchedule()
{
 if(!InpUseManualNewsBlackout) return true;
 if(InpNewsScheduleExpiresServer<=TimeTradeServer()) return false;
 string tokens[];
 int n=StringSplit(InpHighImpactServerTimes,';',tokens);
 if(n<1||n>40) return false;
 if(ArrayResize(newsEvents,n)!=n) return false;
 for(int i=0;i<n;i++)
 {
  string token=tokens[i];
  StringTrimLeft(token);
  StringTrimRight(token);
  if(StringLen(token)!=16||StringSubstr(token,4,1)!="."||
     StringSubstr(token,7,1)!="."||StringSubstr(token,10,1)!=" "||
     StringSubstr(token,13,1)!=":") return false;
  datetime stamp=StringToTime(token);
  if(stamp<=0||stamp>InpNewsScheduleExpiresServer) return false;
  newsEvents[i]=stamp;
 }
 return true;
}
bool NewsWindowActive(datetime now)
{
 if(!InpUseManualNewsBlackout) return false;
 // Expired calendar means no reliable future event coverage, so no entries.
 if(now>InpNewsScheduleExpiresServer) return true;
 for(int i=0;i<ArraySize(newsEvents);i++)
 {
  datetime t=newsEvents[i];
  if(now>=t-InpNewsBeforeMinutes*60&&now<=t+InpNewsAfterMinutes*60)
   return true;
 }
 return false;
}
void ArmShockHalt(datetime now,const string reason)
{
 if(!InpUseShockCircuitBreaker) return;
 datetime until=now+InpShockCooldownMinutes*60;
 if(until<=shockHaltUntil) return;
 shockHaltUntil=until;
 diagShockDetected++;
 PrintFormat("ZALAH_SHOCK %s; pause until %s",reason,TimeToString(shockHaltUntil,TIME_DATE|TIME_SECONDS));
 if(persistState)
 {
  if(GlobalVariableSet(guardPrefix+"SHOCK",(double)shockHaltUntil)==0)
   LatchGuard("cannot persist volatility shock cooldown");
  else GlobalVariablesFlush();
 }
}


int DayCode()
{
 MqlDateTime dt;
 TimeToStruct(TimeTradeServer(),dt);
 return dt.year*10000+dt.mon*100+dt.day;
}
bool WriteGuardState(const bool flushNow=false)
{
 if(!persistState) return true; // Tester state is always isolated.
 bool ok=true;
 if(GlobalVariableSet(guardPrefix+"DAY",(double)dayKey)==0) ok=false;
 if(GlobalVariableSet(guardPrefix+"START",dayStartEquity)==0) ok=false;
 if(GlobalVariableSet(guardPrefix+"PEAK",peakEquity)==0) ok=false;
 if(GlobalVariableSet(guardPrefix+"LOCK",locked?1.0:0.0)==0) ok=false;
 if(flushNow) GlobalVariablesFlush();
 if(!ok) Print("SAFETY LOCK: persistent guard state write failed");
 return ok;
}
bool LoadGuardState()
{
 dayKey=DayCode();
 double eq=AccountInfoDouble(ACCOUNT_EQUITY);
 dayStartEquity=eq; peakEquity=eq;
 persistState=(!MQLInfoInteger(MQL_TESTER));
 if(!persistState) return true;
 guardPrefix=StringFormat("Z104_%I64d_%s_%I64u_",AccountInfoInteger(ACCOUNT_LOGIN),InpSymbol,InpMagic);
 // Existing locks cannot be cleared by restarting, reattaching or changing parameters.
 if(GlobalVariableCheck(guardPrefix+"LOCK") && GlobalVariableGet(guardPrefix+"LOCK")>=1.0)
  locked=true;
 if(GlobalVariableCheck(guardPrefix+"SHOCK"))
 {
  shockHaltUntil=(datetime)(long)GlobalVariableGet(guardPrefix+"SHOCK");
 }
 if(GlobalVariableCheck(guardPrefix+"PEAK"))
  peakEquity=MathMax(eq,GlobalVariableGet(guardPrefix+"PEAK"));
 if(GlobalVariableCheck(guardPrefix+"DAY") && GlobalVariableCheck(guardPrefix+"START") &&
    (int)GlobalVariableGet(guardPrefix+"DAY")==dayKey)
  dayStartEquity=GlobalVariableGet(guardPrefix+"START");
 if(dayStartEquity<=0 || peakEquity<=0) return false;
 return WriteGuardState(true);
}
void LatchGuard(const string reason)
{
 if(locked) return;
 locked=true;
 Print("SAFETY LOCK: ",reason);
 if(!WriteGuardState(true)) Print("SAFETY ALERT: guard persistence unavailable");
}
void CloseOwnDemoPositions()
{
 if(!InpAllowDemoOrders||!InpCloseOwnPositionsOnLock) return;
 if(!TerminalInfoInteger(TERMINAL_CONNECTED)||!TerminalInfoInteger(TERMINAL_TRADE_ALLOWED)||
    !MQLInfoInteger(MQL_TRADE_ALLOWED)) return;
 for(int i=PositionsTotal()-1;i>=0;i--)
 {
  ulong ticket=PositionGetTicket(i);
  if(ticket==0||!PositionSelectByTicket(ticket)) continue;
  if(PositionGetString(POSITION_SYMBOL)!=InpSymbol||
     (ulong)PositionGetInteger(POSITION_MAGIC)!=InpMagic) continue;
  diagKillCloseAttempts++;
  bool submitted=trade.PositionClose(ticket);
  PrintFormat("SAFETY_CLOSE ticket=%I64u request=%d retcode=%u %s",
    ticket,(int)submitted,trade.ResultRetcode(),trade.ResultRetcodeDescription());
 }
}


bool MonitorEquitySafety()
{
 if(AccountInfoInteger(ACCOUNT_TRADE_MODE)!=ACCOUNT_TRADE_MODE_DEMO)
  return false;
 int key=DayCode();
 double eq=AccountInfoDouble(ACCOUNT_EQUITY);
 if(eq<=0)
 {
  LatchGuard("invalid or depleted account equity");
 }
 if(dayKey!=key)
 {
  dayKey=key;
  dayStartEquity=eq;
  if(!WriteGuardState(true)) LatchGuard("failed to persist daily baseline");
 }
 if(eq>peakEquity)
 {
  peakEquity=eq;
  if(persistState && GlobalVariableSet(guardPrefix+"PEAK",peakEquity)==0)
   LatchGuard("failed to persist peak equity");
 }
 if(eq<=dayStartEquity*(1-InpDailyLossPct/100.0)||
    eq<=peakEquity*(1-InpMaxDrawdownPct/100.0))
  LatchGuard("daily loss or max equity drawdown");
 if(locked)
 {
  CloseOwnDemoPositions(); // Best effort; slippage/gaps can exceed budget.
  return false;
 }
 return true;
}
// Independent of market ticks: works on a connected running DEMO terminal.
void OnTimer()
{
 diagTimerChecks++;
 if(AccountInfoInteger(ACCOUNT_TRADE_MODE)!=ACCOUNT_TRADE_MODE_DEMO) return;
 if(!MonitorEquitySafety()) return;
 if(!InpAllowDemoOrders||!HasOwnPosition()) return;
 MqlTick lastTick;
 if(!SymbolInfoTick(InpSymbol,lastTick)||lastTick.time<=0||
    TimeTradeServer()-(datetime)lastTick.time>InpOpenPositionMaxQuoteAgeSeconds)
 {
  diagTimerQuoteAlerts++;
  LatchGuard("open DEMO position with stale or unavailable quote");
  CloseOwnDemoPositions(); // May fail when connection or market is unavailable.
 }
}

int OnInit()
{
 if(AccountInfoInteger(ACCOUNT_TRADE_MODE)!=ACCOUNT_TRADE_MODE_DEMO)
 { Print("SAFETY LOCK: EA requires DEMO account."); return INIT_FAILED; }
 if(InpRiskPct<=0||InpRiskPct>1||InpDailyLossPct<=0||InpDailyLossPct>5||
    InpMaxDrawdownPct<=0||InpMaxDrawdownPct>25||InpFastMA<2||
    InpSlowMA<=InpFastMA||InpATRPeriod<2||InpStopATR<=0||
    InpRewardRisk<=0||InpMaxSpreadPrice<=0||InpMaxSpreadPrice>2.0||InpMaxDeviationPoints<=0||
    InpTrendEMAPeriod<10||InpADXPeriod<2||InpMinADX<0||InpMinADX>80||
    InpMaxSpreadToATR<=0||InpMaxSpreadToATR>1.0||InpMaxTickAgeSeconds<1||InpMaxTickAgeSeconds>120||
    InpShockBarRangeATR<1.0||InpShockBarRangeATR>15.0||
    InpShockCooldownMinutes<5||InpShockCooldownMinutes>1440||
    InpDiscontinuityMinutes<5||InpDiscontinuityMinutes>1440||
    InpNewsBeforeMinutes<0||InpNewsBeforeMinutes>1440||
    InpNewsAfterMinutes<0||InpNewsAfterMinutes>1440||
    InpCalendarRefreshMinutes<5||InpCalendarRefreshMinutes>120||
    InpCalendarLookaheadHours<1||InpCalendarLookaheadHours>168||
    InpAdverseStopSlippagePrice<0||InpAdverseStopSlippagePrice>20.0||
    InpAssumedCommissionUSDPerLotRoundTurn<0||InpAssumedCommissionUSDPerLotRoundTurn>1000.0||
    InpSafetyTimerSeconds<1||InpSafetyTimerSeconds>60||
    InpOpenPositionMaxQuoteAgeSeconds<10||InpOpenPositionMaxQuoteAgeSeconds>3600)
 return INIT_PARAMETERS_INCORRECT;
 if(AccountInfoString(ACCOUNT_CURRENCY)!="USD")
 {
  Print("SAFETY LOCK: USD account required for explicit USD fee reserve.");
  return INIT_PARAMETERS_INCORRECT;
 }
 // Tester cannot access current native calendar: refuse a deceptive zero-trade run.
 // For an offline test, explicitly opt out and document news-filter limitation.
 if(MQLInfoInteger(MQL_TESTER)&&InpUseLiveUsdEconomicCalendar)
 {
  Print("SAFETY LOCK: disable live calendar explicitly in Strategy Tester; tester has no native news feed.");
  return INIT_PARAMETERS_INCORRECT;
 }
 if(StringFind(InpSymbol,"XAUUSD")!=0||InpSymbol!=_Symbol||
    InpTimeframe!=_Period)
 {
  PrintFormat("SAFETY LOCK: attach to matching gold chart. InpSymbol=%s chart=%s inputTF=%d chartTF=%d",
    InpSymbol,_Symbol,(int)InpTimeframe,(int)_Period);
  return INIT_FAILED;
 }
 if(!SymbolSelect(InpSymbol,true)) return INIT_FAILED;
 fastHandle=iMA(InpSymbol,InpTimeframe,InpFastMA,0,MODE_SMA,PRICE_CLOSE);
 slowHandle=iMA(InpSymbol,InpTimeframe,InpSlowMA,0,MODE_SMA,PRICE_CLOSE);
 atrHandle=iATR(InpSymbol,InpTimeframe,InpATRPeriod);
 if(fastHandle==INVALID_HANDLE||slowHandle==INVALID_HANDLE||atrHandle==INVALID_HANDLE)
 return INIT_FAILED;
 if(InpUseHTFTrendFilter)
 {
  if(PeriodSeconds(InpTrendTimeframe)<=PeriodSeconds(InpTimeframe))
   return INIT_PARAMETERS_INCORRECT;
  trendHandle=iMA(InpSymbol,InpTrendTimeframe,InpTrendEMAPeriod,0,MODE_EMA,PRICE_CLOSE);
  if(trendHandle==INVALID_HANDLE) return INIT_FAILED;
 }
 if(InpUseADXFilter)
 {
  adxHandle=iADX(InpSymbol,InpTimeframe,InpADXPeriod);
  if(adxHandle==INVALID_HANDLE) return INIT_FAILED;
 }
 if(!LoadGuardState())
 {
  Print("SAFETY LOCK: cannot recover persistent guard state.");
  return INIT_FAILED;
 }
 if(!LoadNewsSchedule())
 {
  Print("SAFETY LOCK: manual high-impact news schedule missing, invalid, or expired.");
  return INIT_PARAMETERS_INCORRECT;
 }
 if(!MQLInfoInteger(MQL_TESTER) && !EventSetTimer(InpSafetyTimerSeconds))
 {
  PrintFormat("SAFETY LOCK: cannot activate periodic risk heartbeat, error=%d",GetLastError());
  return INIT_FAILED;
 }
 trade.SetExpertMagicNumber(InpMagic);
 trade.SetDeviationInPoints(InpMaxDeviationPoints);
 trade.SetTypeFillingBySymbol(InpSymbol);
 Print("ZALAH EA initialized: DEMO ONLY; order opt-in=",InpAllowDemoOrders);
 PrintFormat("ZALAH_DIAG research v1.07 symbol=%s point=%.6f max_spread_price=%.6f min_lot=%.4f",InpSymbol,SymbolInfoDouble(InpSymbol,SYMBOL_POINT),InpMaxSpreadPrice,SymbolInfoDouble(InpSymbol,SYMBOL_VOLUME_MIN));
 return INIT_SUCCEEDED;
}
void OnDeinit(const int reason)
{
 EventKillTimer();
 PrintFormat("ZALAH_DIAG research_v1.07 ticks=%I64d spread_blocked_ticks=%I64d eligible_bars=%I64d crossover_signals=%I64d regime_filtered=%I64d adx_filtered=%I64d cost_filtered=%I64d regime_no_data=%I64d risk_lot_rejections=%I64d margin_rejections=%I64d order_attempts=%I64d stale_ticks=%I64d safety_close_attempts=%I64d latched=%d shock_detected=%I64d shock_blocked=%I64d news_blocked=%I64d live_calendar_refreshes=%I64d live_calendar_failures=%I64d timer_checks=%I64d stale_quote_alerts=%I64d",
 diagTicks,diagSpreadBlocked,diagBarChecks,diagSignals,diagRegimeBlocked,diagADXBlocked,diagCostBlocked,diagRegimeNoData,diagRiskBlocked,diagMarginBlocked,diagOrderAttempts,diagStaleTicks,diagKillCloseAttempts,(int)locked,diagShockDetected,diagShockBlocked,diagNewsBlocked,diagCalendarRefreshes,diagCalendarFailed,diagTimerChecks,diagTimerQuoteAlerts);
 if(fastHandle!=INVALID_HANDLE) IndicatorRelease(fastHandle);
 if(slowHandle!=INVALID_HANDLE) IndicatorRelease(slowHandle);
 if(atrHandle!=INVALID_HANDLE) IndicatorRelease(atrHandle);
 if(trendHandle!=INVALID_HANDLE) IndicatorRelease(trendHandle);
 if(adxHandle!=INVALID_HANDLE) IndicatorRelease(adxHandle);
}
bool HasOwnPosition()
{
 for(int i=PositionsTotal()-1;i>=0;i--)
 {
  ulong ticket=PositionGetTicket(i);
  if(ticket>0&&PositionSelectByTicket(ticket)&&
     PositionGetString(POSITION_SYMBOL)==InpSymbol&&
     (ulong)PositionGetInteger(POSITION_MAGIC)==InpMagic)
   return true;
 }
 return false;
}
bool HasPosition()
{
 for(int i=PositionsTotal()-1;i>=0;i--)
 {
  ulong ticket=PositionGetTicket(i);
  if(ticket>0&&PositionSelectByTicket(ticket)&&
     PositionGetString(POSITION_SYMBOL)==InpSymbol) return true;
 }
 return false;
}
void OnTick()
{
 diagTicks++;
 if(!MonitorEquitySafety()) return;
 double eq=AccountInfoDouble(ACCOUNT_EQUITY);
 if(!InpAllowDemoOrders||HasPosition()) return;
 if(!TerminalInfoInteger(TERMINAL_CONNECTED)||
    !TerminalInfoInteger(TERMINAL_TRADE_ALLOWED)||
    !MQLInfoInteger(MQL_TRADE_ALLOWED)) return;
 MqlTick tick;
 if(!SymbolInfoTick(InpSymbol,tick)||tick.bid<=0||tick.ask<=tick.bid) return;
 if(!MQLInfoInteger(MQL_TESTER) &&
    (TimeTradeServer()-(datetime)tick.time)>InpMaxTickAgeSeconds)
 { diagStaleTicks++; return; }
 double point=SymbolInfoDouble(InpSymbol,SYMBOL_POINT);
 if(point<=0) return;
 datetime now=TimeTradeServer();
 if((tick.ask-tick.bid)>InpMaxSpreadPrice)
 {
  diagSpreadBlocked++;
  ArmShockHalt(now,"spread exceeds allowed price band");
  return;
 }
 datetime bar=iTime(InpSymbol,InpTimeframe,0);
 if(bar<=0||bar==lastBar) return;
 if(InpUseShockCircuitBreaker&&lastBar>0&&
    bar-lastBar>InpDiscontinuityMinutes*60)
  ArmShockHalt(now,"M5 market data discontinuity");
 lastBar=bar;
 diagBarChecks++;
 if(InpUseShockCircuitBreaker)
 {
  double historicalATR[1];
  if(CopyBuffer(atrHandle,0,2,1,historicalATR)!=1||historicalATR[0]<=0)
  { diagRegimeNoData++; return; }
  double closedHigh=iHigh(InpSymbol,InpTimeframe,1);
  double closedLow=iLow(InpSymbol,InpTimeframe,1);
  if(closedHigh<=0||closedLow<=0||closedHigh<closedLow)
  { diagRegimeNoData++; return; }
  if((closedHigh-closedLow)>InpShockBarRangeATR*historicalATR[0])
   ArmShockHalt(now,"closed bar extreme range versus prior ATR");
  if(now<shockHaltUntil)
  { diagShockBlocked++; return; }
 }
 if(NewsWindowActive(now)||LiveUsdCalendarWindow(now))
 { diagNewsBlocked++; return; }
 double f[2],s[2],a[1];
 // CopyBuffer static arrays: index 0 oldest, so use 0=older, 1=last closed.
 if(CopyBuffer(fastHandle,0,1,2,f)!=2||
    CopyBuffer(slowHandle,0,1,2,s)!=2||
    CopyBuffer(atrHandle,0,1,1,a)!=1) return;
 int side=0;
 if(f[0]<=s[0]&&f[1]>s[1]) side=1;
 if(f[0]>=s[0]&&f[1]<s[1]) side=-1;
 if(side==0||a[0]<=0) return;
 diagSignals++;
 // Fail closed when independent closed-bar indicators are unavailable.
 if(InpUseHTFTrendFilter)
 {
  double higherEMA[1];
  if(CopyBuffer(trendHandle,0,1,1,higherEMA)!=1)
  { diagRegimeNoData++; return; }
  double higherClose=iClose(InpSymbol,InpTrendTimeframe,1);
  if(higherClose<=0||higherEMA[0]<=0)
  { diagRegimeNoData++; return; }
  if((side==1&&higherClose<=higherEMA[0])||
     (side==-1&&higherClose>=higherEMA[0]))
  { diagRegimeBlocked++; return; }
 }
 if(InpUseADXFilter)
 {
  double adxMain[1],diPlus[1],diMinus[1];
  if(CopyBuffer(adxHandle,0,1,1,adxMain)!=1||
     CopyBuffer(adxHandle,1,1,1,diPlus)!=1||
     CopyBuffer(adxHandle,2,1,1,diMinus)!=1)
  { diagRegimeNoData++; return; }
  if(adxMain[0]<InpMinADX||
     (side==1&&diPlus[0]<=diMinus[0])||
     (side==-1&&diMinus[0]<=diPlus[0]))
  { diagADXBlocked++; return; }
 }
 if(InpUseCostToATRFilter&&
    (tick.ask-tick.bid)/a[0]>InpMaxSpreadToATR)
 { diagCostBlocked++; return; }
 double distance=a[0]*InpStopATR;
 double entry=side==1?tick.ask:tick.bid;
 double priceStep=SymbolInfoDouble(InpSymbol,SYMBOL_TRADE_TICK_SIZE);
 int digits=(int)SymbolInfoInteger(InpSymbol,SYMBOL_DIGITS);
 if(priceStep<=0) return;
 double stop=0,target=0;
 if(side==1)
 {
  stop=NormalizeDouble(MathFloor((entry-distance)/priceStep)*priceStep,digits);
  target=NormalizeDouble(MathCeil((entry+distance*InpRewardRisk)/priceStep)*priceStep,digits);
 }
 else
 {
  stop=NormalizeDouble(MathCeil((entry+distance)/priceStep)*priceStep,digits);
  target=NormalizeDouble(MathFloor((entry-distance*InpRewardRisk)/priceStep)*priceStep,digits);
 }
 double minStop=(double)SymbolInfoInteger(InpSymbol,SYMBOL_TRADE_STOPS_LEVEL)*point;
 if(MathAbs(entry-stop)<=minStop+(tick.ask-tick.bid)) return;
 double minVol=SymbolInfoDouble(InpSymbol,SYMBOL_VOLUME_MIN);
 double step=SymbolInfoDouble(InpSymbol,SYMBOL_VOLUME_STEP);
 double maxVol=SymbolInfoDouble(InpSymbol,SYMBOL_VOLUME_MAX);
 if(minVol<=0||step<=0||maxVol<minVol) return;
 double lossPerLot=0;
 ENUM_ORDER_TYPE kind=side==1?ORDER_TYPE_BUY:ORDER_TYPE_SELL;
 // Stress the exit fill beyond the specified SL for realistic adverse gaps.
 double stressedExit=side==1?stop-InpAdverseStopSlippagePrice:
                             stop+InpAdverseStopSlippagePrice;
 if(!OrderCalcProfit(kind,InpSymbol,1.0,entry,stressedExit,lossPerLot)||
    lossPerLot>=0) return;
 double budget=eq*InpRiskPct/100.0;
 // Reserve an extra spread-sized loss allowance, to reject marginal lots.
 double spreadCost=MathAbs(tick.ask-tick.bid)*SymbolInfoDouble(InpSymbol,SYMBOL_TRADE_CONTRACT_SIZE);
 double lossBudgetPerLot=-lossPerLot+spreadCost+
                         InpAssumedCommissionUSDPerLotRoundTurn;
 if(lossBudgetPerLot<=0) return;
 double raw=budget/lossBudgetPerLot;
 double lots=MathFloor((raw+1e-10)/step)*step;
 lots=NormalizeDouble(lots,8);
 if(lots<minVol||lots>maxVol) { diagRiskBlocked++; if(diagRiskBlocked<=3) PrintFormat("ZALAH_DIAG risk reject: budget=%.4f USD, estimated minimum-lot loss=%.4f USD, minVol=%.4f, ATR=%.4f, spread_price=%.4f",budget,lossBudgetPerLot*minVol,minVol,a[0],tick.ask-tick.bid); return; }
 double margin=0;
 if(!OrderCalcMargin(kind,InpSymbol,lots,entry,margin)||
    margin>AccountInfoDouble(ACCOUNT_MARGIN_FREE)*0.5) { diagMarginBlocked++; return; }
 // Demo orders are opt-in, and every order includes a broker-side SL and TP.
 diagOrderAttempts++;
 bool sent=side==1?trade.Buy(lots,InpSymbol,0,stop,target,"ZALAH safe research"):
                   trade.Sell(lots,InpSymbol,0,stop,target,"ZALAH safe research");
 Print("DEMO order attempt=",sent," retcode=",trade.ResultRetcode(),
       " ",trade.ResultRetcodeDescription());
}
