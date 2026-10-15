import Decimal from 'decimal.js';
import {dec,salesRows,snapshot,type Filters} from './analytics';
import type {DashboardData,Row} from './types';
import {marketProductKey,type MarketRow} from './market';
// Incomplete groups stay incomplete; never silently drop missing values.
export function completeSum(rows:Row[],key:string):number|null {
 if(!rows.length)return null;const values=rows.map(r=>dec(r[key]));
 return values.some(v=>v===null)?null:values.reduce<Decimal>((a,b)=>a.plus(b!),new Decimal(0)).toNumber();
}
export function salesAnalysis(data:DashboardData,f:Filters,dimension:'product'|'channel'|'time'='product'){
 const buckets=new Map<string,Row[]>();
 for(const r of salesRows(data,f)){const key=JSON.stringify([dimension==='time'?[r.round,r.step,r.elapsed_steps]:r[dimension],r.currency,r.unit,r.organization]);buckets.set(key,[...(buckets.get(key)??[]),r]);}
 return [...buckets.values()].map(rows=>{const r=rows[0],revenue=completeSum(rows,'revenue'),cost=completeSum(rows,'cost'),quantity=completeSum(rows,'ordered'),delivered=completeSum(rows,'delivered');
 const contribution=revenue===null||cost===null?null:new Decimal(revenue).minus(cost).toNumber();
 // Sales NET_VALUE and COST refer to the order line, so use QUANTITY for BOTH.
 const per=(value:number|null)=>quantity!==null&&quantity>0&&value!==null?new Decimal(value).div(quantity).toNumber():null;
 return {label:dimension==='time'?`${r.round} · ${r.step}`:String(r[dimension]??'—'),name:String(r.description??'—'),currency:String(r.currency??'—'),unit:String(r.unit??'—'),elapsed:dec(r.elapsed_steps)?.toNumber()??null,revenue,cost,contribution,quantity,delivered,price:per(revenue),unitCost:per(cost),unitContribution:per(contribution),margin:revenue!==null&&revenue!==0&&contribution!==null?new Decimal(contribution).div(revenue).mul(100).toNumber():null};
 }).sort((a,b)=>dimension==='time'?(a.elapsed??Infinity)-(b.elapsed??Infinity):a.label.localeCompare(b.label,'cs',{numeric:true}));
}
// Only explicit package weights in source descriptions, never material-code guesses.
export function packageWeight(name:string):number|null {const match=name.match(/^\s*(\d+(?:[.,]\d+)?)\s*(kg|g)\b/i);if(!match)return null;return Number(match[1].replace(',','.'))/(match[2].toLowerCase()==='g'?1000:1);}
export function marketShares(rows:MarketRow[],measure:'quantity'|'value'){
 const buckets=new Map<string,MarketRow[]>();for(const r of rows){const key=JSON.stringify([r.periodKey,r.currency,r.unit]);buckets.set(key,[...(buckets.get(key)??[]),r]);}
 return [...buckets.values()].flatMap(part=>{
  const total=completeSum(part.map(r=>({amount:r[measure]})),'amount');
  const products=new Map<string,MarketRow[]>();for(const r of part){const key=marketProductKey(r);products.set(key,[...(products.get(key)??[]),r]);}
  return [...products.values()].sort((a,b)=>(a[0].code||a[0].name).localeCompare(b[0].code||b[0].name,'cs',{numeric:true})).map(p=>{const value=completeSum(p.map(r=>({amount:r[measure]})),'amount');return {label:p[0].code||'Chybí kód',fullLabel:`${p[0].code||'Chybí kód'} · ${p[0].name}`,period:p[0].periodLabel,periodKey:p[0].periodKey,currency:p[0].currency,unit:p[0].unit,value,share:total!==null&&total>0&&value!==null?new Decimal(value).div(total).mul(100).toNumber():null};});
 });
}
export type Investment={days:number;capacity:number;targetCapacity:number;currentHours:number;targetHours:number;changes:number;capacityCost:number;setupCost:number;contribution:number;utilization:number;extraCashCosts:number;depreciation:number|null;interest:number|null};
export function cumulativeSetup(hours:number,model={floor:2,numerator:1500000,offset:250000}){
 if(![hours,model.floor,model.numerator,model.offset].every(Number.isFinite)||model.numerator<=0||model.offset<0||hours<=model.floor)return null;
 const value=model.numerator/(hours-model.floor)-model.offset;return value>=0?value:null;
}
export function investment(i:Investment){
 const inputs=[i.days,i.capacity,i.targetCapacity,i.currentHours,i.targetHours,i.changes,i.capacityCost,i.setupCost,i.contribution,i.utilization,i.extraCashCosts];
 if(inputs.some(n=>!Number.isFinite(n))||i.days<=0||i.capacity<0||i.targetCapacity<i.capacity||i.currentHours<0||i.targetHours<0||i.targetHours>i.currentHours||i.changes<0||i.capacityCost<0||i.setupCost<0||i.extraCashCosts<0||(i.depreciation!==null&&(!Number.isFinite(i.depreciation)||i.depreciation<0))||(i.interest!==null&&(!Number.isFinite(i.interest)||i.interest<0))||i.utilization<0||i.utilization>1)return null;
 const base=i.capacity*Math.max(0,i.days-i.changes*i.currentHours/24),target=i.targetCapacity*Math.max(0,i.days-i.changes*i.targetHours/24);
 const additional=Math.max(0,target-base)*i.utilization,benefit=additional*i.contribution,netCash=benefit-i.extraCashCosts-(i.interest??0),outlay=i.capacityCost+i.setupCost;
 return {additional,benefit,netCash,outlay,cashAfterInvestment:netCash-outlay,payback:netCash>0?outlay/(netCash/i.days):null,accounting:i.depreciation!==null&&i.interest!==null&&i.setupCost===0?benefit-i.extraCashCosts-i.depreciation-i.interest:null};
}

export function extendedRules(data:DashboardData,f:Filters){
 const rows=(snapshot(data,f.origin,'Current_Game_Rules')?.rows??[]).filter(r=>r.COMPANY_CODE===f.company);
 const scenarios=[...new Set(rows.map(r=>String(r.SCENARIO??'').trim()).filter(Boolean))];
 const extended=scenarios.length===1&&/extended/i.test(scenarios[0]);
 const rule=(detail:string)=>{const values=[...new Set(rows.filter(r=>r.ELEMENT==='Production'&&r.DETAIL===detail).map(r=>r.VALUE))];return extended&&values.length===1?dec(values[0])?.toNumber()??null:null;};
 return {scenarios,extended,capacity:rule('Daily Production Capacity'),hours:rule('Setup Time')};
}
export function verifyExtended(data:DashboardData,f:Filters){
 const s=snapshot(data,f.origin,'Current_Game_Rules');
 const rows=(s?.rows??[]).filter(r=>r.COMPANY_CODE===f.company);
 const {scenarios,extended}=extendedRules(data,f);
 const value=(detail:string)=>{const values=[...new Set(rows.filter(r=>r.ELEMENT==='Production'&&r.DETAIL===detail).map(r=>String(r.VALUE??'')))].filter(Boolean);return values.length===1?values[0]:null;};
 const channels=[...new Set(rows.filter(r=>r.ELEMENT==='Distribution_Channel').map(r=>String(r.DETAIL??'').trim()).filter(Boolean))].sort();
 const status=(present:boolean,equal:boolean)=>!present?'Ve zdroji neuvedeno':extended&&equal?'Shoda':'Rozdíl';
 return {at:s?.created_at??null,rows:[
 {parameter:'Scénář',manual:'Manufacturing Extended',actual:scenarios.join(', ')||null,status:status(scenarios.length>0,extended)},
 {parameter:'Denní kapacita (kusů/den)',manual:'24 000',actual:value('Daily Production Capacity'),status:status(value('Daily Production Capacity')!==null,dec(value('Daily Production Capacity'))?.eq(24000)??false)},
 {parameter:'Přestavba (h; základní stav)',manual:'8',actual:value('Setup Time'),status:status(value('Setup Time')!==null,dec(value('Setup Time'))?.eq(8)??false)},
 // The inspected source has no verified min/max lot-size fields. Order targets
 // are NOT rule limits. Do not invent Current_Game_Rules DETAIL identifiers.
 {parameter:'Minimální / maximální výrobní dávka (kusů)',manual:'16 000 / 48 000',actual:null,status:'Ve zdroji neuvedeno'},
 {parameter:'Distribuční kanály (kódy)',manual:'10, 12, 14',actual:channels.length?channels.join(', '):null,status:status(channels.length>0,JSON.stringify(channels)===JSON.stringify(['10','12','14']))}
 ]};
}
