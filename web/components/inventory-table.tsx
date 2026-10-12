'use client';
import {useId,useMemo,useState} from 'react';
import {Card} from './ui/card';
import {InfoHint} from './ui/info-hint';
import {inventoryItems,filterInventory,materialTypes,type MaterialType} from '@/lib/inventory';
import type {DashboardData} from '@/lib/types';
import {materialCode,text} from '@/lib/products';

const fmt=(v:string|number|null,digits=3)=>v===null?'—':new Intl.NumberFormat('cs-CZ',{maximumFractionDigits:digits}).format(Number(v));
function Missing({label,reason}:{label:string;reason:string}){return <span className="inline-flex items-center gap-1 whitespace-nowrap">—<InfoHint label={label}>{reason.replace(/^Nedostupné: /,'')}</InfoHint></span>;}
export function InventoryTable({data,origin,company}:{data:DashboardData;origin:string;company:string}){
 const items=useMemo(()=>inventoryItems(data,origin,company),[data,origin,company]);
 const [type,setType]=useState<MaterialType|'all'>('all'),[location,setLocation]=useState('');const id=useId();
 const visible=filterInventory(items,type,location),locations=[...new Set(items.flatMap(i=>i.locations.map(l=>l.location)).filter(Boolean))].sort();
 const head=data.heads.find(h=>h.origin===origin&&h.dataset==='Current_Inventory');
 const orders=data.heads.find(h=>h.origin===origin&&h.dataset==='Production_Orders');
 function wipReason(i:typeof items[number]){
  if(!orders)return 'Chybí snímek výrobních příkazů.';
  if(!i.unit||!i.company||!i.material)return 'Chybí ověřený materiál, společnost nebo jednotka.';
  const mismatch=orders.snapshots.views.find(r=>text(r.organization)===i.company&&materialCode(text(r.product))===i.code&&text(r.unit)!==i.unit);
  return mismatch?`Jednotka výrobního příkazu (${text(mismatch.unit)||'neuvedena'}) neodpovídá skladové jednotce ${i.unit}. Převod není doložen.`:'Ve výrobních příkazech chybí platné cílové nebo potvrzené množství.';
 }
 return <Card className="mt-5 min-w-0" data-testid="inventory-card"><h2 className="font-semibold">Výrobky a zásoba</h2>
 <p className="mt-2 text-sm text-slate-600">Kompletní aktuální zásoby · společnost {company||'všechny dostupné'} · {origin==='odata'?'Živé OData':`Import · ${origin.slice(5)}`}</p>
 <p className="mt-1 text-xs leading-5 text-slate-500">Všechny skladové položky a jejich skutečné jednotky, nezávisle na prodejních filtrech. Jednotky se nesčítají. Zásoba = STOCK; RESTRICTED se nepřičítá. {head?`Snímek načten ${new Date(head.last_success).toLocaleString('cs-CZ')}.`:'Current_Inventory není dostupný.'}</p>
 <div role="group" aria-label="Typ skladových položek" className="mt-4 flex flex-wrap gap-2">{([['all','Vše'],['finished','Hotové výrobky'],['raw','Suroviny'],['packaging','Obaly'],['unclassified','Nezařazené']] as const).map(([value,label])=><button key={value} aria-pressed={type===value} onClick={()=>setType(value)} className={`rounded-lg border px-3 py-2 text-sm ${type===value?'border-teal-700 bg-teal-50 font-semibold text-teal-800':'border-slate-200 bg-white text-slate-600'}`}>{label}</button>)}</div>
 <div className="my-3 flex flex-wrap items-end justify-between gap-3"><span className="text-xs text-slate-500">{visible.length} položek · nuly zůstávají zobrazené</span><div><label htmlFor={id} className="mb-1 block">Skladová lokace</label><select id={id} value={location} onChange={e=>setLocation(e.target.value)}><option value="">Všechny lokace</option>{locations.map(l=><option key={l} value={l}>{l}</option>)}</select></div></div>
 <p className="mb-2 text-xs text-slate-500">Dodávky za herní den a rozpracované množství platí pouze pro hotové výrobky. Důvod chybějící hodnoty otevřete informační ikonou.</p>
 {location&&<p className="mb-3 text-xs text-slate-500">Filtr vybírá položky přítomné v lokaci {location}. Zásoba v hlavním řádku zůstává celková za společnost; množství jednotlivých lokací je v detailu.</p>}
 <div className="overflow-x-auto" tabIndex={0} role="region" aria-label="Kompletní zásoby, vodorovně posuvné"><table className="w-full min-w-[1100px]" aria-label="Kompletní zásoby"><thead><tr>{['Kód','Název','Typ','Aktuální zásoba','Jednotka','Dodávky / herní den','Odhad dnů zásoby','Rozpracováno','Lokace'].map(h=><th key={h} scope="col">{h}</th>)}</tr></thead><tbody>{visible.map(i=><tr key={i.id}>
 <td className="font-semibold" title={`Zdrojový materiál: ${i.material}`}>{i.code||'—'}</td><td>{i.name||'Název neuveden'}</td><td title={i.classificationNote}>{materialTypes[i.type]}</td><td className="text-right tabular-nums">{i.stock===null?<Missing label={`Proč chybí zásoba: ${i.code}`} reason={i.locations.some(l=>l.conflict)?'Rozporné skladové údaje stejné lokace nelze sečíst. Jednotlivé hodnoty jsou v detailu lokací.':i.locations.length>1&&i.locations.some(l=>!l.location)?'Nelze jednoznačně sečíst skladové údaje s neznámou lokací.':'Ve snímku chybí platné množství zásoby.'}/>:fmt(i.stock)}{i.locations.some(l=>l.conflict)&&<span className="block text-xs text-amber-700">Rozpor v lokaci</span>}</td><td>{i.unit||'Neuvedeno'}</td>
 <td className="text-right tabular-nums">{i.type!=='finished'?'—':i.rate===null?<Missing label={`Proč chybí tempo dodávek: ${i.code}`} reason={i.estimateNote}/>:`${fmt(i.rate)} ${i.unit}`}</td><td className="text-right tabular-nums">{i.days===null?<Missing label={`Proč chybí odhad dnů zásoby: ${i.code}`} reason={i.estimateNote}/>:fmt(i.days,1)}</td><td className="text-right tabular-nums">{i.type!=='finished'?'—':i.wip===null?<Missing label={`Proč chybí rozpracované množství: ${i.code}`} reason={wipReason(i)}/>:`${fmt(i.wip)} ${i.unit}`}</td>
 <td><details><summary className="whitespace-nowrap text-sm text-teal-700">{i.locations.map(l=>l.location||'Neuvedeno').join(', ')}</summary><div className="mt-2 min-w-[230px] space-y-2 text-xs">{i.locations.map((l,n)=><div key={n}><strong>Lokace {l.location||'neuvedena'}</strong>{l.observations.map((o,k)=><p key={k}>STOCK: {fmt(o.stock)} {i.unit} · RESTRICTED: {fmt(o.restricted)} {i.unit}</p>)}{l.conflict&&<p className="text-amber-700">Konfliktní záznamy se nesčítají; celková zásoba je nedostupná.</p>}</div>)}{i.duplicateRows>0&&<p>{i.duplicateRows} shodných opakovaných řádků započteno pouze jednou.</p>}</div></details></td>
 </tr>)}</tbody></table></div>
 {!visible.length&&<p className="py-8 text-sm text-slate-500">{head?'Pro vybraný typ a lokaci nejsou položky.':'Chybí kompletní snímek Current_Inventory; historické stavy jej nenahrazují.'}</p>}
 </Card>;
}
