import Decimal from 'decimal.js';
import type {DashboardData,Row} from './types';
import {productCatalogue,resolveProduct,text,type Product} from './products';

export type MarketRow=Product&{id:string;periodKey:string;periodLabel:string;round:string;period:string;date:string;periodKind:'period'|'date';area:string;channel:string;currency:string;unit:string;quantity:string|null;value:string|null;price:string|null;priceBasis:'weighted'|'source'|'missing'};
export type MarketFilters={period:string;product:string;area:string;channel:string};
const number=(v:unknown)=>{if(v===null||v===undefined||v==='')return null;try{const n=new Decimal(String(v));return n.isFinite()?n:null;}catch{return null;}};
const total=(rows:Row[],key:string)=>{const values=rows.map(r=>number(r[key]));return values.some(v=>v===null)?null:values.reduce<Decimal>((a,b)=>a.plus(b!),new Decimal(0));};
const compare=(a:string,b:string)=>a.localeCompare(b,'cs',{numeric:true});
export function marketRows(data:DashboardData,origin:string,company:string):MarketRow[]{
 // One authoritative complete source. Never add an Excel export to OData.
 const head=data.heads.find(h=>h.origin===origin&&h.dataset==='Market')??data.heads.find(h=>h.origin===origin&&h.dataset==='MarketExport');
 if(!head)return [];
 const catalogue=productCatalogue(data,origin,company),buckets=new Map<string,{row:MarketRow;raw:Row[]}>();
 for(const [index,r] of head.snapshots.rows.entries()){
  const org=text(r.COMPANY_CODE);if(company&&org&&org!==company)continue;
  const exported=head.dataset==='MarketExport';
  const round=exported?'':text(r.SIM_ROUND),period=exported?'':text(r.SIM_PERIOD),date=exported?text(r['Simulation Date']):'';
  const p=resolveProduct(catalogue,text(r.MATERIAL_DESCRIPTION??r.Description),exported?text(r.Material):text(r.MATERIAL_NUMBER));
  const periodKey=JSON.stringify([exported?'date':'period',round,period,date]);
  const row:MarketRow={...p,id:'',round,period,date,periodKind:exported?'date':'period',periodKey,periodLabel:exported?(date||'—'):`${round||'—'} / ${period||'—'}`,area:text(r.AREA??r.Area),channel:text(r.DISTRIBUTION_CHANNEL??r['D. Channel']),currency:text(r.CURRENCY),unit:text(r.UNIT??r.Unit),quantity:null,value:null,price:null,priceBasis:'missing'};
  // Include description even when a source code exists: conflicts must stay visible.
  const complete=!!(row.code&&row.name&&row.area&&row.channel&&row.currency&&row.unit&&(exported?date:round&&period))&&row.status!=='ambiguous';
  const key=JSON.stringify([org,periodKey,row.code,row.name,row.status,row.area,row.channel,row.currency,row.unit,...(complete?[]:[index])]);row.id=key;
  const normalized={quantity:r.QUANTITY??r.Quantity??null,value:r.NET_VALUE??r.Value??null,price:r.AVERAGE_PRICE??r.Price??null};
  const bucket=buckets.get(key)??{row,raw:[]};bucket.raw.push(normalized);buckets.set(key,bucket);
 }
 return [...buckets.values()].map(({row,raw})=>{
  const q=total(raw,'quantity'),v=total(raw,'value');
  // Do not divide by zero or average supplied prices. A single unaggregated
  // source price remains useful when quantity/value is missing or q=0.
  const weighted=!!(q&&!q.isZero()&&v);
  const price=weighted?v!.div(q!):raw.length===1?number(raw[0].price):null;
  return {...row,quantity:q?.toString()??null,value:v?.toString()??null,price:price?.toString()??null,priceBasis:weighted?'weighted' as const:price?'source' as const:'missing' as const};
 });
}
export function periods(rows:MarketRow[]){return [...new Map(rows.map(r=>[r.periodKey,r])).values()].sort((a,b)=>{
 if(a.periodKind!==b.periodKind)return compare(a.periodKind,b.periodKind);
 if(a.periodKind==='date'){const aa=a.date.split('/'),bb=b.date.split('/');return compare(bb[0]??'',aa[0]??'')||compare(bb[1]??'',aa[1]??'');}
 return compare(b.round,a.round)||compare(b.period,a.period);
 });}
export const marketProductKey=(r:MarketRow)=>JSON.stringify([r.code,r.name,r.status]);
export function filterMarket(rows:MarketRow[],f:MarketFilters){return rows.filter(r=>(!f.period||r.periodKey===f.period)&&(!f.product||marketProductKey(r)===f.product)&&(!f.area||r.area===f.area)&&(!f.channel||r.channel===f.channel));}
export function groupedMarket(rows:MarketRow[],descending=false){
 const ordered=[...rows].sort((a,b)=>compare(b.round,a.round)||compare(b.period,a.period)||compare(b.date,a.date)||((descending?-1:1)*(compare(a.code,b.code)||compare(a.name,b.name)))||compare(a.status,b.status)||compare(a.area,b.area)||compare(a.channel,b.channel)||compare(a.currency,b.currency)||compare(a.unit,b.unit));
 return ordered.map((r,i)=>{
  const previous=ordered[i-1];const showPeriod=!previous||previous.periodKey!==r.periodKey;
  const showProduct=showPeriod||marketProductKey(previous)!==marketProductKey(r);
  const showArea=showProduct||previous.area!==r.area;
  return {...r,showPeriod,showProduct,showArea};
 });
}
const csvCell=(v:string)=>`"${v.replaceAll('"','""')}"`;
export function marketCSV(rows:MarketRow[]){
 const headers=['Kolo / období','Druh období','Kód','Výrobek','Propojení kódu','Oblast','Typ obchodu (kód)','Měna','Jednotka','Tržní cena','Množství','Hodnota prodejů','Původ ceny'];
 return '\uFEFF'+[headers,...rows.map(r=>[r.periodLabel,r.periodKind==='period'?'SIM_ROUND / SIM_PERIOD':'Simulation Date',r.code,r.name,r.status,r.area,r.channel,r.currency,r.unit,r.price??'',r.quantity??'',r.value??'',r.priceBasis])].map(row=>row.map(csvCell).join(';')).join('\r\n');
}
