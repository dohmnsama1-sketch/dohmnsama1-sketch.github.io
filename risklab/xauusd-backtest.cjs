/* XAUUSD research backtester — no broker connectivity or orders.
   Input: array of {time,open,high,low,close} sorted ascending, consistent quote currency.
   Educational simulation, not investment advice. */
'use strict';
function backtest(bars, opts={}) {
 const o={initialEquity:500,riskFraction:0.005,fast:10,slow:30,atrPeriod:14,stopATR:2,rewardRisk:1.5,spread:0.30,slippage:0.15,commissionPerUnit:0,maxDrawdown:0.15,maxDailyLoss:0.02,contractUnits:100,minLot:0.01,lotStep:0.01,...opts};
 const fail=msg=>{throw Error(msg)};
 if(!Array.isArray(bars)||bars.length<Math.max(o.slow,o.atrPeriod)+5)fail('Insufficient OHLC bars');
 for(let i=0;i<bars.length;i++){const b=bars[i];if(!b||!Number.isFinite(b.open)||!Number.isFinite(b.high)||!Number.isFinite(b.low)||!Number.isFinite(b.close)||b.low<=0||b.low>Math.min(b.open,b.close)||b.high<Math.max(b.open,b.close)||!Number.isFinite(Date.parse(b.time))||(i&&Date.parse(b.time)<=Date.parse(bars[i-1].time)))fail('Invalid or unordered OHLC data')}
 for(const k of ['initialEquity','riskFraction','fast','slow','atrPeriod','stopATR','rewardRisk','spread','slippage','commissionPerUnit','maxDrawdown','maxDailyLoss','contractUnits','minLot','lotStep'])if(!Number.isFinite(o[k]))fail('Invalid '+k);
 if(o.initialEquity<=0||o.riskFraction<=0||o.riskFraction>0.02||o.fast<2||o.slow<=o.fast||o.atrPeriod<2||o.stopATR<=0||o.rewardRisk<=0||o.spread<0||o.slippage<0||o.commissionPerUnit<0||o.maxDrawdown<=0||o.maxDrawdown>0.5||o.maxDailyLoss<=0||o.maxDailyLoss>0.1||o.contractUnits<=0||o.minLot<=0||o.lotStep<=0)fail('Unsafe parameters');
 const sma=(end,n)=>bars.slice(end-n+1,end+1).reduce((a,b)=>a+b.close,0)/n;
 const atr=end=>{let sum=0;for(let j=end-o.atrPeriod+1;j<=end;j++){const b=bars[j],p=bars[j-1].close;sum+=Math.max(b.high-b.low,Math.abs(b.high-p),Math.abs(b.low-p))}return sum/o.atrPeriod};
 let equity=o.initialEquity,peak=equity,position=null,day='',dayStart=equity,halted=false,maxDD=0;const trades=[];
 const close=(i,raw,reason)=>{const p=position,exit=raw-(p.side*(o.spread/2+o.slippage)),pnl=(exit-p.entry)*p.side*p.units-o.commissionPerUnit*p.units;equity+=pnl;peak=Math.max(peak,equity);maxDD=Math.max(maxDD,(peak-equity)/peak);trades.push({entryTime:p.time,exitTime:bars[i].time,side:p.side,lots:p.lots,entry:p.entry,exit,pnl,equity,reason});position=null;if((peak-equity)/peak>=o.maxDrawdown)halted=true;};
 for(let i=Math.max(o.slow,o.atrPeriod)+1;i<bars.length;i++){
  const b=bars[i],date=b.time.slice(0,10);if(date!==day){day=date;dayStart=equity}
  if(position){const p=position;const stopHit=p.side===1?b.low<=p.stop:b.high>=p.stop;const targetHit=p.side===1?b.high>=p.target:b.low<=p.target;
   if(stopHit||targetHit){let raw=stopHit?p.stop:p.target;if((p.side===1&&b.open<p.stop)||(p.side===-1&&b.open>p.stop))raw=b.open;close(i,raw,stopHit?'stop_or_gap':'target');}}
  if(halted||equity<=0||equity<=dayStart*(1-o.maxDailyLoss)||position||i>=bars.length-1)continue;
  const f0=sma(i-1,o.fast),s0=sma(i-1,o.slow),f1=sma(i,o.fast),s1=sma(i,o.slow);
  const side=f0<=s0&&f1>s1?1:f0>=s0&&f1<s1?-1:0;if(!side)continue;
  const distance=atr(i)*o.stopATR,unitRisk=distance+o.spread+2*o.slippage+o.commissionPerUnit;
  const rawLots=(equity*o.riskFraction)/(unitRisk*o.contractUnits);
  const lots=rawLots>=o.minLot?o.minLot+Math.floor((rawLots-o.minLot)/o.lotStep+1e-9)*o.lotStep:0;
  if(lots<o.minLot)continue;
  const units=lots*o.contractUnits,entry=bars[i+1].open+side*(o.spread/2+o.slippage);
  position={side,lots,units,entry,stop:entry-side*distance,target:entry+side*distance*o.rewardRisk,time:bars[i+1].time};
 }
 if(position)close(bars.length-1,bars[bars.length-1].close,'end_of_data');
 return {initialEquity:o.initialEquity,finalEquity:equity,netPnl:equity-o.initialEquity,returnPct:(equity/o.initialEquity-1)*100,maxDrawdownPct:maxDD*100,tradeCount:trades.length,wins:trades.filter(t=>t.pnl>0).length,halted,trades,assumptions:'Synthetic OHLC simulation; not tick-exact; gaps and spreads modeled approximately; no margin, swap, liquidity, latency, broker execution or walk-forward validation. Never use for live trading.'};
}
module.exports={backtest};
