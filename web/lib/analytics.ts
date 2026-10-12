import Decimal from 'decimal.js';
import {productCatalogue,resolveProduct,productLabel} from './products';
import type {DashboardData,Row,Settings} from './types';
export type Filters={origin:string;company:string;currency:string;unit:string;product:string;area:string;channel:string;round:string};
export const unknown='Neuvedeno';
export const str=(r:Row,k:string)=>String(r[k]??unknown);
export function dec(v:unknown):Decimal|null{if(v===null||v===undefined||v==='')return null;try{const value=new Decimal(String(v));return value.isFinite()?value:null;}catch{return null;}}
export const num=(v:unknown)=>dec(v)?.toNumber()??null;
export function sum(rows:Row[],key:string):number|null{const values=rows.map(r=>dec(r[key])).filter((v):v is Decimal=>v!==null);return values.length?values.reduce((a,b)=>a.plus(b),new Decimal(0)).toNumber():null;}
export function unique(rows:Row[],key:string){return [...new Set(rows.map(r=>str(r,key)))].sort();}
export function snapshot(data:DashboardData,origin:string,dataset:string){return data.heads.find(h=>h.origin===origin&&h.dataset===dataset)?.snapshots;}
const scope=(rows:Row[],f:Filters)=>rows.filter(r=>(!f.company||str(r,'organization')===f.company)&&(!f.currency||str(r,'currency')===f.currency));
export function salesSource(data:DashboardData,origin:string){for(const dataset of ['Sales','SalesExport','SummarySalesExport']){const s=snapshot(data,origin,dataset);if(s)return s;}return null;}
export function salesRows(data:DashboardData,f:Filters){return scope(salesSource(data,f.origin)?.views??[],f).filter(r=>(!f.unit||str(r,'unit')===f.unit)&&(!f.product||str(r,'product')===f.product)&&(!f.area||str(r,'area')===f.area)&&(!f.channel||str(r,'channel')===f.channel)&&(!f.round||str(r,'round')===f.round));}
export function group(rows:Row[],keys:string[],measure:string){const buckets=new Map<string,{label:string;rows:Row[]}>();for(const r of rows){const label=keys.map(k=>str(r,k)).join(' · ');const b=buckets.get(label)??{label,rows:[]};b.rows.push(r);buckets.set(label,b);}return [...buckets.values()].map(b=>({label:b.label,value:sum(b.rows,measure)}));}
export function compute(data:DashboardData,f:Filters){
 const sales=salesRows(data,f);const moneySafe=unique(sales,'currency').length<=1;const quantitySafe=unique(sales,'unit').length<=1;
 const revenue=moneySafe?sum(sales,'revenue'):null;const cost=moneySafe?sum(sales,'cost'):null;const contribution=moneySafe?sum(sales,'contribution'):null;
 const valuation=(snapshot(data,f.origin,'Company_Valuation')?.rows??[]).filter(r=>(!f.company||str(r,'COMPANY_CODE')===f.company)&&(!f.currency||str(r,'CURRENCY')===f.currency));
 const valuationKeys=unique(valuation,'COMPANY_CODE');const valuationCurrencies=unique(valuation,'CURRENCY');
 const latest=valuationKeys.length===1&&valuationCurrencies.length===1?[...valuation].sort((a,b)=>(num(b.SIM_ELAPSED_STEPS)??-1)-(num(a.SIM_ELAPSED_STEPS)??-1))[0]:undefined;
 const finance={profit:num(latest?.PROFIT),cash:num(latest?.BANK_CASH_ACCOUNT),valuation:num(latest?.COMPANY_VALUATION),currency:latest?str(latest,'CURRENCY'):f.currency,at:latest?`Kolo ${str(latest,'SIM_ROUND')}, den ${str(latest,'SIM_STEP')}`:'Nedostupné'};
 const inventory=(snapshot(data,f.origin,'Current_Inventory')??snapshot(data,f.origin,'InventoryExport'))?.views;
 // Current stock is for company/product/unit, never guessed regional inventory.
 const stocks=(inventory??[]).filter(r=>(!f.company||str(r,'organization')===f.company)&&(!f.unit||str(r,'unit')===f.unit));
 const orders=(snapshot(data,f.origin,'Production_Orders')?.views??[]).filter(r=>(!f.company||str(r,'organization')===f.company)&&(!f.unit||str(r,'unit')===f.unit)&&(!f.product||str(r,'product')===f.product));
 const masterSales=scope(salesSource(data,f.origin)?.views??[],f).filter(r=>!f.unit||str(r,'unit')===f.unit);
 const steps=masterSales.map(r=>num(r.elapsed_steps)).filter((n):n is number=>n!==null);const end=steps.length?Math.max(...steps):null;
 const recent=masterSales.filter(r=>end!==null&&num(r.elapsed_steps)!==null&&Number(r.elapsed_steps)>end-5);
 const availableStart=steps.length?Math.min(...steps):null;
 // Fixed rolling five observed game steps; does not assume round length or turn wall time.
 const span=end!==null&&availableStart!==null?Math.min(5,end-availableStart+1):null;
 const pending=(r:Row)=>{const a=dec(r.target),b=dec(r.confirmed);return a&&b?Decimal.max(0,a.minus(b)).toNumber():null;};
 const catalogue=new Map<string,string>();for(const r of [...stocks,...masterSales,...orders])if(str(r,'product')!==unknown)catalogue.set(str(r,'product'),str(r,'description'));
 const rules=snapshot(data,f.origin,'Current_Game_Rules')?.rows??[];
 const finished=new Set(rules.filter(r=>r.CATEGORY==='Product'&&r.VALUE==='Finished products').map(r=>String(r.ELEMENT).replace(/^[A-Z0-9]{2}-(?=F\d+$)/,'')));
 const products=[...catalogue].filter(([code])=>(!f.product||code===f.product)&&(masterSales.some(r=>str(r,'product')===code)||finished.has(code)||orders.some(r=>str(r,'product')===code))).map(([code,name])=>{
  const stockRows=stocks.filter(r=>str(r,'product')===code);const s=unique(stockRows,'unit').length<=1?sum(stockRows,'stock'):null;
  const delivered=recent.filter(r=>str(r,'product')===code);const q=unique(delivered,'unit').length<=1?sum(delivered,'delivered'):null;
  const rate=q!==null&&span?new Decimal(q).div(span).toNumber():null;
  const productOrders=orders.filter(r=>str(r,'product')===code);const amounts=productOrders.map(pending);const wip=productOrders.length&&amounts.every(x=>x!==null)?amounts.reduce<number>((a,b)=>a+(b??0),0):productOrders.length?null:(snapshot(data,f.origin,'Production_Orders')?0:null);
  return {code,name,stock:s,unit:stockRows[0]?str(stockRows[0],'unit'):f.unit,rate,days:s!==null&&rate!==null&&rate>0?s/rate:null,wip};
 }).sort((a,b)=>(a.days??Infinity)-(b.days??Infinity));
 const timeline=moneySafe?group(sales,['round','step'],'revenue').sort((a,b)=>{const ar=a.label.split(' · ').map(Number),br=b.label.split(' · ').map(Number);return ar[0]-br[0]||ar[1]-br[1];}):[];
 const areas=moneySafe?group(sales,['area'],'revenue'):[];
 const marketing=scope(snapshot(data,f.origin,'Marketing_Expenses')?.views??[],f).filter(r=>(!f.product||str(r,'product')===f.product)&&(!f.area||str(r,'area')===f.area)&&(!f.round||str(r,'round')===f.round));
 const market=snapshot(data,f.origin,'Market')?.views??[];
 const materialCatalogue=productCatalogue(data,f.origin,f.company);
 // ERPsim Market has no material number. Exact description plus EVERY comparison dimension is mandatory.
 const priceGroups=new Map<string,Row[]>();for(const r of sales){const key=['product','description','area','channel','currency','unit','round','period'].map(k=>str(r,k)).join('\u0000');priceGroups.set(key,[...(priceGroups.get(key)??[]),r]);}
 const comparisons=[...priceGroups.values()].map(rows=>{
  const r=rows[0];const dims=['description','area','channel','currency','unit','round','period'];
  const unambiguous=new Set(masterSales.filter(s=>str(s,'description')===str(r,'description')).map(s=>str(s,'product'))).size===1;
  const comparable=unambiguous&&resolveProduct(materialCatalogue,str(r,'description')).code===str(r,'product')&&dims.every(k=>![unknown,'Měna neuvedena','Jednotka neuvedena'].includes(str(r,k)));
  const matches=comparable?market.filter(m=>dims.every(k=>str(m,k)===str(r,k))):[];
  const mq=sum(matches,'quantity'),mv=sum(matches,'revenue'),sq=sum(rows,'ordered'),sv=sum(rows,'revenue');
  const own=sq&&sv!==null?new Decimal(sv).div(sq).toNumber():null;
  const price=mq&&mv!==null?new Decimal(mv).div(mq).toNumber():null;
  return {code:str(r,'product'),name:productLabel(resolveProduct(materialCatalogue,str(r,'description'),str(r,'product'))),area:str(r,'area'),channel:str(r,'channel'),round:str(r,'round'),period:str(r,'period'),currency:str(r,'currency'),unit:str(r,'unit'),own,market:price,margin:sv&&sum(rows,'contribution')!==null?100*sum(rows,'contribution')!/sv:null};
 });
 return {sales,revenue,cost,contribution,quantity:quantitySafe?sum(sales,'ordered'):null,finance,products,timeline,areas,marketing,orders,comparisons,rules,settings:data.settings};
}
export type Alert={title:string;detail:string;severity:number};
export function alerts(data:DashboardData,f:Filters,model:ReturnType<typeof compute>,now=Date.now()):Alert[]{
 const result:Alert[]=[];const settings:Settings=data.settings;
 if(f.origin==='odata'){
  const heads=data.heads.filter(h=>h.origin===f.origin);
  for(const h of heads)if(now-Date.parse(h.last_success)>settings.stale_seconds*1000)result.push({title:`Živý zdroj ${h.dataset} se neobnovuje`,detail:'Zobrazen je poslední úspěšný snímek. Ověřte síť a běh samostatného synchronizátoru.',severity:3});
  const latest=new Map<string,DashboardData['runs'][number]>();for(const r of data.runs.filter(r=>r.origin===f.origin))if(!latest.has(r.dataset))latest.set(r.dataset,r);
  for(const r of latest.values())if(r.status==='failed')result.push({title:`Načtení ${r.dataset} selhalo`,detail:r.error??'Ověřte připojení v diagnostice.',severity:4});
 }
 for(const p of model.products)if(p.days!==null&&p.days<settings.stock_days){result.push({title:`${p.code} · ${p.name}: odhad zásoby ${p.days.toFixed(1)} herního dne`,detail:`Odhad podle dodávek za nejvýše posledních 5 herních kroků. Rozpracováno: ${p.wip===null?'nedostupné':p.wip+' '+p.unit}. Prověřte poptávku, termíny příkazů a recepturu před změnou výroby.`,severity:p.stock===0?3:2});}
 if(model.revenue&&model.contribution!==null&&100*model.contribution/model.revenue<settings.margin_percent)result.push({title:'Nízký příspěvek před režijními náklady',detail:`Podíl příspěvku je ${(100*model.contribution/model.revenue).toFixed(1)} %. Ověřte ceny a náklady v kanálech. Nejde o účetní čistý zisk.`,severity:2});
 const mkCurrencies=unique(model.marketing,'currency');const mk=sum(model.marketing,'marketing');
 if(settings.marketing_limit!==null&&mk!==null&&mkCurrencies.length===1&&mkCurrencies[0]===settings.currency&&mk>settings.marketing_limit)result.push({title:'Marketing překročil nastavený limit',detail:`Výdaj ${mk} ${mkCurrencies[0]} ve zvoleném období. Prověřte rozdělení podle oblastí; souběh s prodejem neprokazuje návratnost.`,severity:1});
 return result.sort((a,b)=>b.severity-a.severity);
}
