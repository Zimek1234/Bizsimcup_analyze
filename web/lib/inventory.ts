import Decimal from 'decimal.js';
import type {DashboardData,Row} from './types';
import {materialCode,text} from './products';

export type MaterialType='finished'|'raw'|'packaging'|'unclassified';
export const materialTypes:Record<MaterialType,string>={finished:'Hotové výrobky',raw:'Suroviny',packaging:'Obaly',unclassified:'Nezařazené'};
export type InventoryLocation={location:string;stock:string|null;restricted:string|null;conflict:boolean;observations:{stock:string|null;restricted:string|null}[]};
export type InventoryItem={id:string;material:string;code:string;name:string;company:string;unit:string;type:MaterialType;stock:string|null;locations:InventoryLocation[];duplicateRows:number;classificationNote:string;rate:number|null;days:number|null;wip:number|null;estimateNote:string};
const numeric=(v:unknown)=>{if(v===null||v===undefined||v==='')return null;try{const n=new Decimal(String(v));return n.isFinite()?n:null;}catch{return null;}};
const total=(values:(Decimal|null)[])=>values.length&&values.every(v=>v!==null)?values.reduce<Decimal>((a,v)=>a.plus(v!),new Decimal(0)):null;
// Values verified in the supplied rules and InventoryExport, not code prefixes.
const categories:Record<string,MaterialType>={'Finished products':'finished','Finished Goods':'finished',Packing:'packaging',Packaging:'packaging',Perishable:'raw','Raw Materials':'raw'};
function classify(data:DashboardData,origin:string,company:string,material:string){
 const rules=data.heads.find(h=>h.origin===origin&&h.dataset==='Current_Game_Rules')?.snapshots.rows??[];
 const exported=data.heads.find(h=>h.origin===origin&&h.dataset==='InventoryExport')?.snapshots.rows??[];
 const values=[...exported.filter(r=>text(r.Material)===material).map(r=>text(r.Category)).filter(Boolean),...rules.filter(r=>r.CATEGORY==='Product'&&text(r.ELEMENT)===material&&text(r.COMPANY_CODE)===company).map(r=>text(r.VALUE))];
 const types=[...new Set(values.map(v=>categories[v]??'unclassified'))];
 const type:MaterialType=types.length===1?types[0]:'unclassified';
 return {type,note:type==='unclassified'?(values.length?'Typ není jednoznačně doložen: '+[...new Set(values)].join(', '):'Typ ve zdroji ani pravidlech není uveden.'):'Typ podle zdrojových údajů / Current_Game_Rules: '+[...new Set(values)].join(', ')};
}
function finishedEstimates(data:DashboardData,origin:string,item:InventoryItem){
 if(!item.unit||!item.company||!item.material)return {rate:null,days:null,wip:null,estimateNote:'Nedostupné: chybí ověřený materiál, společnost nebo jednotka.'};
 const salesHead=['Sales','SalesExport','SummarySalesExport'].map(dataset=>data.heads.find(h=>h.origin===origin&&h.dataset===dataset)).find(Boolean);
 const sales=(salesHead?.snapshots.views??[]).filter(r=>text(r.organization)===item.company&&text(r.unit)===item.unit);
 const steps=sales.map(r=>numeric(r.elapsed_steps)?.toNumber()).filter((v):v is number=>v!==undefined);
 const end=steps.length?Math.max(...steps):null,start=steps.length?Math.min(...steps):null;
 const span=end!==null&&start!==null?Math.min(5,end-start+1):null;
 const delivered=sales.filter(r=>materialCode(text(r.product))===item.code&&end!==null&&numeric(r.elapsed_steps)!==null&&Number(r.elapsed_steps)>end-5);
 const quantity=total(delivered.map(r=>numeric(r.delivered)));
 const rate=quantity&&span&&span>0?quantity.div(span).toNumber():null;
 const stock=numeric(item.stock);const days=stock&&rate!==null&&rate>0?stock.div(rate).toNumber():null;
 const orders=data.heads.find(h=>h.origin===origin&&h.dataset==='Production_Orders');
 const productOrders=(orders?.snapshots.views??[]).filter(r=>text(r.organization)===item.company&&materialCode(text(r.product))===item.code);
 const quantities=productOrders.map(r=>{const target=numeric(r.target),confirmed=numeric(r.confirmed);return text(r.unit)===item.unit&&target&&confirmed?Decimal.max(0,target.minus(confirmed)):null;});
 const wip=orders?(productOrders.length?total(quantities)?.toNumber()??null:0):null;
 return {rate,days,wip,estimateNote:rate===null?'Nedostupné: chybí dodávky ve skutečných herních krocích a stejné jednotce.':rate===0?'Nedostupné: v pozorovaném okně je nulové tempo dodávek.':item.stock===null?'Nedostupné: zásoba není jednoznačně dostupná.':'Dodávky / nejvýše 5 pozorovaných herních kroků; nejde o předpověď poptávky.'};
}
export function inventoryItems(data:DashboardData,origin:string,company:string):InventoryItem[]{
 // Only the complete current snapshot, not Inventory history, KPI or another import.
 const head=data.heads.find(h=>h.origin===origin&&h.dataset==='Current_Inventory');if(!head)return [];
 const buckets=new Map<string,Row[]>();
 for(const [index,r] of head.snapshots.rows.entries()){
  const plant=text(r.PLANT);if(company&&plant!==company)continue;
  const material=text(r.MATERIAL_NUMBER),unit=text(r.UNIT);
  const key=JSON.stringify([plant,material,unit,...(!material||!plant||!unit?[index]:[])]);
  buckets.set(key,[...(buckets.get(key)??[]),r]);
 }
 return [...buckets].map(([id,rows])=>{
  const first=rows[0],material=text(first.MATERIAL_NUMBER),plant=text(first.PLANT),unit=text(first.UNIT);
  const grouped=new Map<string,Row[]>();for(const [index,r] of rows.entries()){
   const location=text(r.STORAGE_LOCATION);const key=location||`missing:${index}`;grouped.set(key,[...(grouped.get(key)??[]),r]);
  }
  let duplicateRows=0;
  const locations=[...grouped.values()].map(facts=>{
   const distinct=[...new Map(facts.map(r=>{const stock=numeric(r.STOCK)?.toString()??null,restricted=numeric(r.RESTRICTED)?.toString()??null;return [JSON.stringify([stock,restricted]),{stock,restricted}];})).values()];
   duplicateRows+=facts.length-distinct.length;
   const conflict=distinct.length>1;
   return {location:text(facts[0].STORAGE_LOCATION),stock:conflict?null:distinct[0].stock,restricted:conflict?null:distinct[0].restricted,conflict,observations:distinct};
  }).sort((a,b)=>a.location.localeCompare(b.location,'cs',{numeric:true}));
  // Missing locations on multiple observations cannot be proven disjoint.
  const ambiguousLocations=rows.length>1&&locations.some(l=>!l.location);
  const stock=ambiguousLocations?null:total(locations.map(l=>numeric(l.stock)))?.toString()??null;
  const classification=classify(data,origin,plant,material);
  const item:InventoryItem={id,material,code:materialCode(material),name:[...new Set(rows.map(r=>text(r.MATERIAL_DESCRIPTION)).filter(Boolean))].join(' / '),company:plant,unit,type:classification.type,stock,locations,duplicateRows,classificationNote:classification.note,rate:null,days:null,wip:null,estimateNote:'Nedostupné: chybí ověřená spotřeba nebo úplná receptura s výrobním plánem.'};
  return item.type==='finished'?{...item,...finishedEstimates(data,origin,item)}:item;
 }).sort((a,b)=>['finished','raw','packaging','unclassified'].indexOf(a.type)-['finished','raw','packaging','unclassified'].indexOf(b.type)||a.code.localeCompare(b.code,'cs',{numeric:true})||a.unit.localeCompare(b.unit,'cs'));
}
export function filterInventory(items:InventoryItem[],type:MaterialType|'all',location=''){
 return items.filter(i=>(type==='all'||i.type===type)&&(!location||i.locations.some(l=>l.location===location)));
}
