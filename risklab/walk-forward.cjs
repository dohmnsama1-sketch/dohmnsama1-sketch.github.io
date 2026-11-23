/* Walk-forward evaluation for XAUUSD research. Never tune on held-out results.
   Requires chronological OHLC bars; no broker connection. */
'use strict';
const {backtest}=require('./xauusd-backtest.cjs');
function walkForward(bars,opts={}) {
 const {trainBars=500,testBars=200,embargoBars=30,folds=4,strategies=[
 {fast:8,slow:24},{fast:10,slow:30},{fast:15,slow:45}
 ],...base}=opts;
 if(!Array.isArray(bars)||!Number.isInteger(trainBars)||!Number.isInteger(testBars)||!Number.isInteger(embargoBars)||!Number.isInteger(folds)||trainBars<100||testBars<100||embargoBars<1||folds<1||!Array.isArray(strategies)||!strategies.length)throw Error('Invalid walk-forward configuration');
 const out=[];
 for(let k=0;k<folds;k++){
  const start=k*testBars,trainEnd=start+trainBars,testStart=trainEnd+embargoBars,testEnd=testStart+testBars;
  if(testEnd>bars.length)break;
  const train=bars.slice(start,trainEnd),test=bars.slice(testStart,testEnd);
  const candidates=strategies.map(params=>({params,metrics:backtest(train,{...base,...params})}));
  // Rank ONLY training results. No use of test outcomes for selection.
  candidates.sort((a,b)=>b.metrics.netPnl-a.metrics.netPnl);
  const selected=candidates[0].params;
  const metrics=backtest(test,{...base,...selected});
  out.push({fold:k+1,trainRange:[train[0].time,train.at(-1).time],testRange:[test[0].time,test.at(-1).time],selected,trainNetPnl:candidates[0].metrics.netPnl,testNetPnl:metrics.netPnl,testReturnPct:metrics.returnPct,testMaxDrawdownPct:metrics.maxDrawdownPct,testTrades:metrics.tradeCount});
 }
 if(!out.length)throw Error('Insufficient chronological bars for a full out-of-sample fold');
 return {folds:out,positiveFolds:out.filter(f=>f.testNetPnl>0).length,totalFolds:out.length,warning:'Out-of-sample research only; no guarantee of live performance, independent validation, or trade execution'};
}
module.exports={walkForward};
