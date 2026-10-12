'use client';
import {useId,useMemo,useState} from 'react';
import {Card} from './ui/card';
import {Button} from './ui/button';
import {filterMarket,groupedMarket,marketCSV,marketProductKey,marketRows,periods} from '@/lib/market';
import {channelLabels,productLabel} from '@/lib/products';
import type {DashboardData} from '@/lib/types';

const fmt=(value:string|null,digits=2)=>value===null?'—':new Intl.NumberFormat('cs-CZ',{minimumFractionDigits:digits===2?2:0,maximumFractionDigits:digits}).format(Number(value));
function Filter({label,value,options,onChange}:{label:string;value:string;options:[string,string][];onChange:(v:string)=>void}){
 const id=useId();return <div><label htmlFor={id} className="mb-1 block">{label}</label><select className="w-full" id={id} value={value} onChange={e=>onChange(e.target.value)}>{options.map(([v,l])=><option key={v} value={v}>{l}</option>)}</select></div>;
}
export function MarketTable({data,origin,company}:{data:DashboardData;origin:string;company:string}){
 const rows=useMemo(()=>marketRows(data,origin,company),[data,origin,company]);
 const availablePeriods=periods(rows),channels=channelLabels(data,origin,company);
 const [selection,setSelection]=useState(''),[product,setProduct]=useState(''),[area,setArea]=useState(''),[channel,setChannel]=useState(''),[descending,setDescending]=useState(false);
 const period=selection==='all'?'':availablePeriods.some(r=>r.periodKey===selection)?selection:availablePeriods[0]?.periodKey??'';
 const periodRows=filterMarket(rows,{period,product:'',area:'',channel:''});
 const options=[...new Map(periodRows.map(r=>[marketProductKey(r),productLabel(r)])).entries()].sort((a,b)=>a[1].localeCompare(b[1],'cs',{numeric:true}));
 const areas=[...new Set(periodRows.map(r=>r.area))].sort(),channelCodes=[...new Set(periodRows.map(r=>r.channel))].sort();
 const visible=groupedMarket(filterMarket(rows,{period,product,area,channel}),descending);
 function download(){const url=URL.createObjectURL(new Blob([marketCSV(visible)],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download='price-market.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
 return <Card className="min-w-0" data-testid="market-card"><div className="flex flex-wrap items-start justify-between gap-3"><div><h2 className="font-semibold">Trh / Price market</h2><p className="mt-2 text-sm text-slate-600">Vybrané období: <strong>{selection==='all'?'Všechna dostupná období':availablePeriods.find(r=>r.periodKey===period)?.periodLabel??'—'}</strong>{selection===''&&rows.length?' · nejnovější dostupné':''}</p></div><Button onClick={download} disabled={!visible.length}>Export CSV</Button></div>
 <p className="mt-2 text-xs leading-5 text-slate-500">Trh je nezávislý na našich prodejích a na filtrech prodejní analýzy. OData období = SIM_ROUND / SIM_PERIOD, nikoli herní den ani čas stažení. Export s polem Simulation Date používá samostatně označené datum ze souboru. Cena = hodnota / množství před zaokrouhlením. Bez nenulového množství lze zobrazit jen cenu přímo ze zdroje; jinak —.</p>
 <div className="my-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4"><Filter label="Tržní období" value={selection==='all'?'all':period} options={[...availablePeriods.map(r=>[r.periodKey,`${r.periodLabel}${r.periodKind==='date'?' · Simulation Date':''}`] as [string,string]),['all','Všechna období']]} onChange={v=>{setSelection(v);setProduct('');setArea('');setChannel('');}}/><Filter label="Tržní výrobek" value={product} options={[["",'Všechny výrobky'],...options]} onChange={setProduct}/><Filter label="Tržní oblast" value={area} options={[["",'Všechny oblasti'],...areas.filter(Boolean).map(v=>[v,v] as [string,string])]} onChange={setArea}/><Filter label="Typ obchodu" value={channel} options={[["",'Všechny typy'],...channelCodes.filter(Boolean).map(v=>[v,channels.get(v)??v] as [string,string])]} onChange={setChannel}/></div>
 <div className="mb-2 flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500"><span>{visible.length} řádků · měna a jednotka jsou uvedené u každé hodnoty; chybějící údaj = —</span><button className="text-teal-700 underline" onClick={()=>setDescending(v=>!v)}>Výrobky: {descending?'sestupně':'vzestupně'} ↕</button></div>
 <div className="overflow-x-auto" tabIndex={0} role="region" aria-label="Tržní tabulka, vodorovně posuvná"><table className="w-full min-w-[1050px]" aria-label="Trh / Price market"><thead><tr>{['Kolo / období','Kód','Výrobek','Oblast','Typ obchodu','Tržní cena','Množství','Hodnota prodejů'].map((h,i)=><th key={h} scope="col" className={i>=5?'text-right':''}>{h}</th>)}</tr></thead><tbody>{visible.map(r=><tr key={r.id} className={r.showProduct?'market-product':r.showArea?'market-area':''}>
 <td>{r.showPeriod?<>{r.periodLabel}{r.periodKind==='date'&&<span className="block text-xs text-slate-500">Simulation Date</span>}</>:<span className="sr-only">{r.periodLabel}</span>}</td>
 <td className="font-semibold">{r.showProduct?(r.code||'—'):<span className="sr-only">{r.code||'—'}</span>}</td>
 <td className="max-w-[260px]">{r.showProduct?<>{r.name||'—'}{(r.status==='missing'||r.status==='ambiguous')&&<span className="mt-1 block text-xs text-amber-700">{r.status==='missing'?'Kód nenalezen v katalogu':'Nejednoznačné propojení kódu'}</span>}</>:<span className="sr-only">{r.name}</span>}</td>
 <td>{r.showArea?(r.area||'—'):<span className="sr-only">{r.area||'—'}</span>}</td><td>{channels.get(r.channel)??(r.channel||'—')}</td>
 <td title={r.priceBasis==='source'?'Cena přímo ze zdroje (AVERAGE_PRICE / Price); nelze ji vypočítat z dostupného množství a hodnoty.':r.priceBasis==='weighted'?'Součet hodnoty / součet množství, bez mezizaokrouhlení.':'Cena není dostupná.'} className="whitespace-nowrap text-right tabular-nums">{fmt(r.price)}{r.price!==null&&<span className="ml-1 text-xs text-slate-500">{r.currency||'—'}/{r.unit||'—'}</span>}</td>
 <td className="whitespace-nowrap text-right tabular-nums">{fmt(r.quantity,3)}{r.quantity!==null&&<span className="ml-1 text-xs text-slate-500">{r.unit||'—'}</span>}</td>
 <td className="whitespace-nowrap text-right tabular-nums">{fmt(r.value)}{r.value!==null&&<span className="ml-1 text-xs text-slate-500">{r.currency||'—'}</span>}</td></tr>)}</tbody></table></div>
 {!visible.length&&<p className="py-8 text-sm text-slate-500">Pro zvolený zdroj a tržní filtry nejsou dostupná data.</p>}
 </Card>;
}
