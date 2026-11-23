//+------------------------------------------------------------------+
//| ZALAH XAUUSD Demo Guard EA - MT5 / MQL5                           |
//| Demo-only research EA. No profit or execution guarantee.          |
//+------------------------------------------------------------------+
#property strict
#property version "1.01"
#include <Trade/Trade.mqh>
CTrade trade;
input string InpSymbol="XAUUSD";
input ENUM_TIMEFRAMES InpTimeframe=PERIOD_M5;
input double InpRiskPct=0.5;
input double InpDailyLossPct=2.0;
input double InpMaxDrawdownPct=15.0;
input int InpFastMA=10;
input int InpSlowMA=30;
input int InpATRPeriod=14;
input double InpStopATR=2.0;
input double InpRewardRisk=1.5;
input int InpMaxSpreadPoints=100;
input int InpMaxDeviationPoints=30;
input ulong InpMagic=20261123;
input bool InpAllowDemoOrders=false; // Opt-in only; still DEMO ONLY
int fastHandle=INVALID_HANDLE,slowHandle=INVALID_HANDLE,atrHandle=INVALID_HANDLE;
datetime lastBar=0;
double dayStartEquity=0,peakEquity=0;
int dayKey=-1;
bool locked=false;
long diagTicks=0,diagSpreadBlocked=0,diagBarChecks=0,diagSignals=0,diagRiskBlocked=0,diagMarginBlocked=0,diagOrderAttempts=0;

int OnInit()
{
 if(AccountInfoInteger(ACCOUNT_TRADE_MODE)!=ACCOUNT_TRADE_MODE_DEMO)
 { Print("SAFETY LOCK: EA requires DEMO account."); return INIT_FAILED; }
 if(InpRiskPct<=0||InpRiskPct>1||InpDailyLossPct<=0||InpDailyLossPct>5||
    InpMaxDrawdownPct<=0||InpMaxDrawdownPct>25||InpFastMA<2||
    InpSlowMA<=InpFastMA||InpATRPeriod<2||InpStopATR<=0||
    InpRewardRisk<=0||InpMaxSpreadPoints<=0||InpMaxDeviationPoints<=0)
 return INIT_PARAMETERS_INCORRECT;
 if(!SymbolSelect(InpSymbol,true)) return INIT_FAILED;
 fastHandle=iMA(InpSymbol,InpTimeframe,InpFastMA,0,MODE_SMA,PRICE_CLOSE);
 slowHandle=iMA(InpSymbol,InpTimeframe,InpSlowMA,0,MODE_SMA,PRICE_CLOSE);
 atrHandle=iATR(InpSymbol,InpTimeframe,InpATRPeriod);
 if(fastHandle==INVALID_HANDLE||slowHandle==INVALID_HANDLE||atrHandle==INVALID_HANDLE)
 return INIT_FAILED;
 dayStartEquity=AccountInfoDouble(ACCOUNT_EQUITY);
 peakEquity=dayStartEquity;
 trade.SetExpertMagicNumber(InpMagic);
 trade.SetDeviationInPoints(InpMaxDeviationPoints);
 trade.SetTypeFillingBySymbol(InpSymbol);
 Print("ZALAH EA initialized: DEMO ONLY; order opt-in=",InpAllowDemoOrders);
 return INIT_SUCCEEDED;
}
void OnDeinit(const int reason)
{
 PrintFormat("ZALAH_DIAG version=1.01 ticks=%I64d spread_blocked_ticks=%I64d eligible_bars=%I64d crossover_signals=%I64d risk_lot_rejections=%I64d margin_rejections=%I64d order_attempts=%I64d",diagTicks,diagSpreadBlocked,diagBarChecks,diagSignals,diagRiskBlocked,diagMarginBlocked,diagOrderAttempts);
 if(fastHandle!=INVALID_HANDLE) IndicatorRelease(fastHandle);
 if(slowHandle!=INVALID_HANDLE) IndicatorRelease(slowHandle);
 if(atrHandle!=INVALID_HANDLE) IndicatorRelease(atrHandle);
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
 if(AccountInfoInteger(ACCOUNT_TRADE_MODE)!=ACCOUNT_TRADE_MODE_DEMO) return;
 MqlDateTime dt; TimeToStruct(TimeTradeServer(),dt);
 int key=dt.year*10000+dt.mon*100+dt.day;
 double eq=AccountInfoDouble(ACCOUNT_EQUITY);
 if(dayKey!=key)
 {
  dayKey=key; dayStartEquity=eq;
  // A previous global drawdown lock persists until EA is manually reviewed.
 }
 peakEquity=MathMax(peakEquity,eq);
 if(eq<=dayStartEquity*(1-InpDailyLossPct/100.0)||
    eq<=peakEquity*(1-InpMaxDrawdownPct/100.0)) locked=true;
 if(locked||!InpAllowDemoOrders||HasPosition()) return;
 if(!TerminalInfoInteger(TERMINAL_CONNECTED)||
    !TerminalInfoInteger(TERMINAL_TRADE_ALLOWED)||
    !MQLInfoInteger(MQL_TRADE_ALLOWED)) return;
 MqlTick tick;
 if(!SymbolInfoTick(InpSymbol,tick)||tick.bid<=0||tick.ask<=tick.bid) return;
 double point=SymbolInfoDouble(InpSymbol,SYMBOL_POINT);
 if(point<=0||(tick.ask-tick.bid)/point>InpMaxSpreadPoints) { diagSpreadBlocked++; return; }
 datetime bar=iTime(InpSymbol,InpTimeframe,0);
 if(bar<=0||bar==lastBar) return;
 lastBar=bar;
 diagBarChecks++;
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
 double distance=a[0]*InpStopATR;
 double entry=side==1?tick.ask:tick.bid;
 double stop=entry-side*distance;
 double target=entry+side*distance*InpRewardRisk;
 double minStop=(double)SymbolInfoInteger(InpSymbol,SYMBOL_TRADE_STOPS_LEVEL)*point;
 if(distance<=minStop+(tick.ask-tick.bid)) return;
 double minVol=SymbolInfoDouble(InpSymbol,SYMBOL_VOLUME_MIN);
 double step=SymbolInfoDouble(InpSymbol,SYMBOL_VOLUME_STEP);
 double maxVol=SymbolInfoDouble(InpSymbol,SYMBOL_VOLUME_MAX);
 if(minVol<=0||step<=0||maxVol<minVol) return;
 double lossPerLot=0;
 ENUM_ORDER_TYPE kind=side==1?ORDER_TYPE_BUY:ORDER_TYPE_SELL;
 if(!OrderCalcProfit(kind,InpSymbol,1.0,entry,stop,lossPerLot)||lossPerLot>=0) return;
 double budget=eq*InpRiskPct/100.0;
 // Reserve an extra spread-sized loss allowance, to reject marginal lots.
 double spreadCost=MathAbs(tick.ask-tick.bid)*SymbolInfoDouble(InpSymbol,SYMBOL_TRADE_CONTRACT_SIZE);
 double lossBudgetPerLot=-lossPerLot+spreadCost;
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
 bool sent=side==1?trade.Buy(lots,InpSymbol,0,stop,target,"ZALAH demo guard"):
                   trade.Sell(lots,InpSymbol,0,stop,target,"ZALAH demo guard");
 Print("DEMO order attempt=",sent," retcode=",trade.ResultRetcode(),
       " ",trade.ResultRetcodeDescription());
}
