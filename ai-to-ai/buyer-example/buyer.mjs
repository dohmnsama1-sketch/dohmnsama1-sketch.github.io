/**
 * DOHMAN x402 buyer quickstart — explicit spend opt-in, known seller, fail closed.
 * \`node buyer.mjs --quote email\` makes no payment.
 * \`node buyer.mjs --pay email\` MAY TRANSFER REAL USDC after quote validation.
 */
const BASE = 'https://tutevpsjeewjulryvvdo.supabase.co/functions/v1/';
const RECIPIENT = '0xcfFC976906D38aA752937C9785Ed4f3FD046a946'.toLowerCase();
const USDC = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'.toLowerCase();
const CHAIN = 'eip155:8453';
const MAX_PRICE_MICRO_USDC = 5000n;
export const ROUTES = Object.freeze({
  email: Object.freeze({slug:'x402-email-verify-evidence',max:1000n,body:{email:'support@example.com'}}),
  domain: Object.freeze({slug:'x402-domain-company-enrich',max:3000n,body:{domain:'example.com'}}),
  batch: Object.freeze({slug:'x402-email-verify-batch',max:5000n,body:{emails:['support@example.com','sales@example.com']}}),
  web: Object.freeze({slug:'true402-web-read/invoke',max:2000n,body:{urls:['https://example.com/'],respect_robots:true}}),
});
export function quoteFromHeadersOrBody(headerValue, data) {
  let challenge = data;
  if (headerValue) {
    if(typeof headerValue!=='string'||headerValue.length>40000)throw Error('Payment header exceeds limits');
    try {challenge=JSON.parse(Buffer.from(headerValue.replaceAll('-','+').replaceAll('_','/'),'base64').toString('utf8'))}
    catch {throw Error('Malformed PAYMENT-REQUIRED header')}
  }
  if(!challenge||challenge.x402Version!==2||!Array.isArray(challenge.accepts)) throw Error('Expected x402 v2 Payment Required quote');
  return challenge;
}
export function validateQuote(quote, route, opts={}) {
  if (!route?.max || !quote || quote.x402Version!==2 || !Array.isArray(quote.accepts) || quote.accepts.length!==1) throw Error('Unexpected payment quote shape');
  const a=quote.accepts[0];
  if(a.scheme!=='exact'||a.network!==CHAIN||String(a.asset).toLowerCase()!==USDC||String(a.payTo).toLowerCase()!==RECIPIENT) throw Error('Payment recipient or settlement rail mismatch');
  if(!/^\d{1,9}$/.test(String(a.amount))) throw Error('Invalid atomic payment amount');
  const atomic=BigInt(a.amount),cap=opts.maxAtomic??MAX_PRICE_MICRO_USDC;
  if (atomic<=0n||atomic>cap||atomic>route.max) throw Error('Payment quote exceeds strict maximum');
  return {usd:Number(atomic)/1_000_000,atomic:String(atomic),network:CHAIN,payTo:RECIPIENT,service:route.slug};
}
export function permittedService(raw) {
  if(typeof raw!=='string'||!Object.prototype.hasOwnProperty.call(ROUTES,raw))throw Error('Unknown service; choose email, domain, batch or web');
  return ROUTES[raw];
}
export function requirePaymentReceipt(headerValue) {
  if(typeof headerValue!=='string'||headerValue.length===0)throw Error('Paid execution missing payment-response receipt; reconcile wallet before retrying');
  if(headerValue.length>40000)throw Error('Payment response receipt exceeds limits');
  return headerValue;
}
async function readQuote(url,route) {
  const ctrl=new AbortController();const t=setTimeout(()=>ctrl.abort(),9000);
  try {
    const res=await fetch(url,{method:'GET',redirect:'manual',signal:ctrl.signal,headers:{accept:'application/json'}});
    if(res.status!==402)throw Error('Expected unpaid HTTP 402, got '+res.status);
    const obj=await res.json().catch(()=>null);
    return validateQuote(quoteFromHeadersOrBody(res.headers.get('payment-required'),obj),route);
  } finally {clearTimeout(t)}
}
export async function main(argv=process.argv.slice(2)) {
  const pay=argv[0]==='--pay',quote=argv[0]==='--quote';
  if(!pay&&!quote)throw Error('Usage: node buyer.mjs --quote email | --pay email');
  const route=permittedService(argv[1]),url=BASE+route.slug;
  const terms=await readQuote(url,route);
  console.log(JSON.stringify({status:'quote_validated',service:route.slug,price_usdc:terms.usd,network:terms.network,recipient:terms.payTo,will_pay:pay},null,2));
  if(!pay){console.log('NO FUNDS SPENT. To pay, install @x402/fetch @x402/evm viem, set EVM_PRIVATE_KEY locally, and use --pay explicitly.');return 0;}
  const key=process.env.EVM_PRIVATE_KEY;
  if(typeof key!=='string'||!/^0x[0-9a-fA-F]{64}$/.test(key))throw Error('EVM_PRIVATE_KEY missing or malformed; do not paste it into a webpage');
  const [{x402Client,wrapFetchWithPayment},{registerExactEvmScheme},{privateKeyToAccount}]=await Promise.all([import('@x402/fetch'),import('@x402/evm/exact/client'),import('viem/accounts')]);
  const client=new x402Client();
  registerExactEvmScheme(client,{signer:privateKeyToAccount(key)});
  const guarded=async(urlOrRequest,init)=>{
    const actual=typeof urlOrRequest==='string'?urlOrRequest:urlOrRequest?.url;
    if(actual!==url)throw Error('Refusing request to unexpected endpoint');
    const result=await fetch(urlOrRequest,{...init,redirect:'manual'});
    if(result.status===402){
      const body=await result.clone().json().catch(()=>null);
      validateQuote(quoteFromHeadersOrBody(result.headers.get('payment-required'),body),route);
    } else if(result.status>=300&&result.status<400)throw Error('Refusing redirect');
    return result;
  };
  const paidFetch=wrapFetchWithPayment(guarded,client);
  const response=await paidFetch(url,{method:'POST',headers:{'content-type':'application/json','accept':'application/json'},body:JSON.stringify(route.body),redirect:'manual'});
  if(!response.ok)throw Error('Paid execution returned HTTP '+response.status+'; check wallet before retrying.');
  requirePaymentReceipt(response.headers.get('payment-response'));
  const data=await response.json();
  console.log(JSON.stringify({status:'executed',response:data,payment_receipt_present:true},null,2));
  return 0;
}
if(process.argv[1]&&import.meta.url===new URL('file://'+process.argv[1]).href){main().catch(err=>{console.error('ERROR:',err.message);process.exitCode=1;});}
