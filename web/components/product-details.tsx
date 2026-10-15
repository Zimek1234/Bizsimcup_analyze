'use client';
import {useEffect,useId,useRef} from 'react';
import type {compute} from '@/lib/analytics';
import {InfoHint} from './ui/info-hint';
const fmt=(n:number|null)=>n===null?'—':new Intl.NumberFormat('cs-CZ',{maximumFractionDigits:2}).format(n);
type Comparison=ReturnType<typeof compute>['comparisons'][number];
export function ProductPrices({rows,channelNames}:{rows:Comparison[];channelNames:Map<string,string>}){
 return <div className="overflow-x-auto"><table className="w-full min-w-[700px]"><thead><tr>{['Oblast','Kanál','Kolo / období','Měna / jednotka','Vlastní cena','Tržní cena','Příspěvek %'].map(h=><th key={h}>{h}</th>)}</tr></thead><tbody>{rows.map((r,i)=><tr key={i}><td>{r.area}</td><td>{channelNames.get(r.channel)??r.channel}</td><td>{r.round} / {r.period}</td><td>{r.currency} / {r.unit}</td><td className="text-right">{fmt(r.own)}</td><td className="text-right">{fmt(r.market)}</td><td className="text-right">{fmt(r.margin)}</td></tr>)}</tbody></table>{!rows.length&&<p className="py-4 text-sm text-slate-500">V tomto rozsahu analýzy nejsou pro výrobek dostupné vlastní prodeje.</p>}</div>;
}
export function ProductDetailDialog({code,rows,channelNames,onClose}:{code:string|null;rows:Comparison[];channelNames:Map<string,string>;onClose:()=>void}){
 const dialog=useRef<HTMLDialogElement>(null);
 const titleId=useId();
 useEffect(()=>{if(code&&!dialog.current?.open)dialog.current?.showModal();if(!code&&dialog.current?.open)dialog.current.close();},[code]);
 const scoped=rows.filter(r=>r.code===code);
 return <dialog ref={dialog} aria-labelledby={titleId} onCancel={onClose} onClose={onClose} className="w-[min(1000px,95vw)] max-h-[85vh] overflow-auto rounded-2xl border border-slate-200 p-5 shadow-xl backdrop:bg-slate-900/40"><div className="flex items-center justify-between"><h2 id={titleId} className="text-lg font-semibold">Detail výrobku · {scoped[0]?.name??code}</h2><button className="rounded-lg border px-3 py-1" onClick={onClose}>Zavřít detail</button></div><p className="my-3 text-sm text-slate-500">Vlastní realizované ceny a příspěvek pro vybraný výrobek. Oblast, kanál, kolo a měna odpovídají filtrům analýzy; jednotka vychází z vybrané skladové položky. Úplné dimenze jsou uvedené v každém řádku.</p><ProductPrices rows={scoped} channelNames={channelNames}/></dialog>;
}
export function ProductDetails({rows,channelNames}:{rows:Comparison[];channelNames:Map<string,string>}){
 const products=[...new Map(rows.map(r=>[r.code,r.name]))];
 return <section><h2 className="flex items-center gap-1 font-semibold">Detail výrobku: realizované ceny a příspěvek<InfoHint label="Význam realizované ceny a příspěvku">Vlastní cena = NET_VALUE / objednané množství. Příspěvek je (NET_VALUE − COST) / NET_VALUE před režijními náklady. Tržní cena vyžaduje shodu všech srovnávacích dimenzí. Nejde o účetní čistý zisk.</InfoHint></h2><p className="mt-2 text-xs text-slate-500">Rozbalte výrobek pro ceny podle oblasti, kanálu a období v jejich skutečné měně a jednotce.</p><div className="mt-3 divide-y divide-slate-200">{products.map(([code,name])=><details key={code} className="py-2"><summary className="text-sm font-medium text-teal-700">{name}</summary><ProductPrices rows={rows.filter(r=>r.code===code)} channelNames={channelNames}/></details>)}</div>{!products.length&&<p className="py-4 text-sm text-slate-500">V tomto rozsahu nejsou prodejní údaje dostupné.</p>}</section>;
}
