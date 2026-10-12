import type {DashboardData,Row} from './types';

const missing=new Set(['','Neuvedeno','Měna neuvedena','Jednotka neuvedena']);
export const text=(value:unknown)=>value===null||value===undefined||missing.has(String(value))?'':String(value);
// Same documented display convention as Python product_code; no positional codes.
export const materialCode=(raw:string)=>raw.match(/^(?:[A-Z0-9]{2}-)?(F\d{2})$/)?.[1]??raw;
export type Product={code:string;name:string;status:'source'|'matched'|'missing'|'ambiguous'};
export function productLabel(p:Product){return `${p.code||'—'} · ${p.name||'Název neuveden'}${p.status==='missing'?' · kód nenalezen':p.status==='ambiguous'?' · nejednoznačné propojení':''}`;}
export function productCatalogue(data:DashboardData,origin:string,company:string){
 const byName=new Map<string,Set<string>>(),byCode=new Map<string,Set<string>>();
 for(const h of data.heads.filter(h=>h.origin===origin))for(const r of h.snapshots.rows){
  const organization=text(r.SALES_ORGANIZATION??r.COMPANY_CODE??r.PLANT);
  if(company&&organization&&organization!=='Market'&&organization!==company)continue;
  const rule=h.dataset==='Current_Game_Rules'&&r.CATEGORY==='Product';
  const raw=text(rule?r.ELEMENT:r.MATERIAL_NUMBER??r.Material),name=text(rule?r.DETAIL:r.MATERIAL_DESCRIPTION??r.Description);
  if(!raw||!name)continue;
  const code=materialCode(raw);
  byName.set(name,new Set([...(byName.get(name)??[]),code]));
  byCode.set(code,new Set([...(byCode.get(code)??[]),name]));
 }
 return {byName,byCode};
}
export function resolveProduct(catalogue:ReturnType<typeof productCatalogue>,name:string,sourceCode=''):Product{
 if(sourceCode)return {code:materialCode(sourceCode),name:name||[...(catalogue.byCode.get(materialCode(sourceCode))??[])].join(' / '),status:'source'};
 const codes=catalogue.byName.get(name);
 if(codes?.size===1)return {code:[...codes][0],name,status:'matched'};
 return {code:'',name,status:codes?.size?'ambiguous':'missing'};
}
export function rowProduct(catalogue:ReturnType<typeof productCatalogue>,row:Row){return resolveProduct(catalogue,text(row.description),text(row.product));}
export function channelLabels(data:DashboardData,origin:string,company:string){
 const names=new Map<string,Set<string>>();
 const add=(code:string,name:string)=>{if(code&&name)names.set(code,new Set([...(names.get(code)??[]),name]));};
 for(const h of data.heads.filter(h=>h.origin===origin))for(const r of h.snapshots.rows){
  const org=text(r.SALES_ORGANIZATION??r.COMPANY_CODE);
  if(company&&org&&org!=='Market'&&org!==company)continue;
  if(h.dataset==='Current_Game_Rules'&&r.ELEMENT==='Distribution_Channel')add(text(r.DETAIL),text(r.VALUE));
  if(h.dataset==='Current_Pricing_Conditions')add(text(r.DISTRIBUTION_CHANNEL),text(r.DC_NAME));
 }
 return new Map([...names].filter(([,v])=>v.size===1).map(([k,v])=>[k,[...v][0]]));
}
