'use client';
import {useId,useMemo,useState} from 'react';
import {Card} from './ui/card';
import {inventoryItems,filterInventory,materialTypes,type MaterialType} from '@/lib/inventory';
import type {DashboardData} from '@/lib/types';

const fmt=(v:string|number|null)=>v===null?'Nedostupné':new Intl.NumberFormat('cs-CZ',{maximumFractionDigits:3}).format(Number(v));
export function InventoryTable({data,origin,company}:{data:DashboardData;origin:string;company:string}){
 const items=useMemo(()=>inventoryItems(data,origin,company),[data,origin,company]);
 const [type,setType]=useState<MaterialType|'all'>('all'),[location,setLocation]=useState('');const id=useId();
 const visible=filterInventory(items,type,location),locations=[...new Set(items.flatMap(i=>i.locations.map(l=>l.location)).filter(Boolean))].sort();
 const head=data.heads.find(h=>h.origin===origin&&h.dataset==='Current_Inventory');
 return <Card className="mt-5 min-w-0" data-testid="inventory-card"><h2 className="font-semibold">Výrobky a zásoba</h2>
 <p className="mt-2 text-sm text-slate-600">Kompletní aktuální zásoby · společnost {company||'všechny dostupné'} · {origin==='odata'?'Živé OData':`Import · ${origin.slice(5)}`}</p>
 <p className="mt-1 text-xs leading-5 text-slate-500">Všechny skladové položky a jejich skutečné jednotky, nezávisle na prodejních filtrech. Jednotky se nesčítají. Zásoba = STOCK; RESTRICTED se nepřičítá. {head?`Snímek načten ${new Date(head.last_success).toLocaleString('cs-CZ')}.`:'Current_Inventory není dostupný.'}</p>
 <div role="group" aria-label="Typ skladových položek" className="mt-4 flex flex-wrap gap-2">{([['all','Vše'],['finished','Hotové výrobky'],['raw','Suroviny'],['packaging','Obaly'],['unclassified','Nezařazené']] as const).map(([value,label])=><button key={value} aria-pressed={type===value} onClick={()=>setType(value)} className={`rounded-lg border px-3 py-2 text-sm ${type===value?'border-teal-700 bg-teal-50 font-semibold text-teal-800':'border-slate-200 bg-white text-slate-600'}`}>{label}</button>)}</div>
 <div className="my-3 flex flex-wrap items-end justify-between gap-3"><span className="text-xs text-slate-500">{visible.length} položek · nuly zůstávají zobrazené</span><div><label htmlFor={id} className="mb-1 block">Skladová lokace</label><select id={id} value={location} onChange={e=>setLocation(e.target.value)}><option value="">Všechny lokace</option>{locations.map(l=><option key={l} value={l}>{l}</option>)}</select></div></div>
 {location&&<p className="mb-3 text-xs text-slate-500">Filtr vybírá položky přítomné v lokaci {location}. Zásoba v hlavním řádku zůstává celková za společnost; množství jednotlivých lokací je v detailu.</p>}
 <div className="overflow-x-auto" tabIndex={0} role="region" aria-label="Kompletní zásoby, vodorovně posuvné"><table className="w-full min-w-[1100px]" aria-label="Kompletní zásoby"><thead><tr>{['Kód','Název','Typ','Aktuální zásoba','Jednotka','Dodávky / herní den','Odhad dnů zásoby','Rozpracováno','Lokace'].map(h=><th key={h} scope="col">{h}</th>)}</tr></thead><tbody>{visible.map(i=><tr key={i.id}>
 <td className="font-semibold" title={`Zdrojový materiál: ${i.material}`}>{i.code||'—'}</td><td>{i.name||'Název neuveden'}</td><td title={i.classificationNote}>{materialTypes[i.type]}</td><td className="text-right tabular-nums">{fmt(i.stock)}{i.locations.some(l=>l.conflict)&&<span className="block text-xs text-amber-700">Rozpor v lokaci</span>}</td><td>{i.unit||'Neuvedeno'}</td>
 <td className="text-right tabular-nums">{fmt(i.rate)}{i.rate!==null&&` ${i.unit}`}</td><td className="max-w-[200px] text-right tabular-nums">{fmt(i.days)}{i.days===null&&<span className="mt-1 block text-left text-xs text-slate-500">{i.estimateNote.replace(/^Nedostupné: /,'')}</span>}</td><td className="text-right tabular-nums">{fmt(i.wip)}{i.wip!==null&&` ${i.unit}`}</td>
 <td><details><summary className="whitespace-nowrap text-sm text-teal-700">{i.locations.map(l=>l.location||'Neuvedeno').join(', ')}</summary><div className="mt-2 min-w-[230px] space-y-2 text-xs">{i.locations.map((l,n)=><div key={n}><strong>Lokace {l.location||'neuvedena'}</strong>{l.observations.map((o,k)=><p key={k}>STOCK: {fmt(o.stock)} {i.unit} · RESTRICTED: {fmt(o.restricted)} {i.unit}</p>)}{l.conflict&&<p className="text-amber-700">Konfliktní záznamy se nesčítají; celková zásoba je nedostupná.</p>}</div>)}{i.duplicateRows>0&&<p>{i.duplicateRows} shodných opakovaných řádků započteno pouze jednou.</p>}</div></details></td>
 </tr>)}</tbody></table></div>
 {!visible.length&&<p className="py-8 text-sm text-slate-500">{head?'Pro vybraný typ a lokaci nejsou položky.':'Chybí kompletní snímek Current_Inventory; historické stavy jej nenahrazují.'}</p>}
 </Card>;
}
