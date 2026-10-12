'use client';
import type {DashboardData} from '@/lib/types';
import {group,type compute,type Filters} from '@/lib/analytics';
import {Card} from './ui/card';
import {InfoHint} from './ui/info-hint';
import {MarketTable} from './market-table';
import {InventoryTable} from './inventory-table';
import {Bars,Trend,FinanceChart} from './charts';

type Point={label:string;value:number|null;fullLabel?:string};
type FinancePoint={label:string;profit:number|null;cash:number|null};
function Metric({label,value,currency,note}:{label:string;value:number|null;currency:string;note:string}){
 return <Card className="p-3" data-testid={`round-kpi-${label}`} data-value={value===null?'missing':String(value)}><div className="flex items-center justify-between text-xs text-slate-500">{label}<InfoHint label={`Význam ukazatele ${label}`}>{note}</InfoHint></div><p className="text-xl font-semibold tabular-nums">{value===null?'—':new Intl.NumberFormat('cs-CZ',{maximumFractionDigits:0}).format(value)} <span className="text-xs font-normal text-slate-500">{value===null?'':currency}</span></p></Card>;
}
export function DuringRound({data,filters,model,financeData,products,marketPeriod,onMarketPeriod,onInventoryExpand,onMarketExpand,onProductOpen}:{data:DashboardData;filters:Filters;model:ReturnType<typeof compute>;financeData:FinancePoint[];products:Point[];marketPeriod:string;onMarketPeriod:(v:string)=>void;onInventoryExpand:()=>void;onMarketExpand:()=>void;onProductOpen:(code:string,unit?:string)=>void}){
 return <div data-testid="during-round" className="mt-3 space-y-3">
 <div className="grid grid-cols-4 gap-3"><Metric label="Tržby" value={model.revenue} currency={filters.currency} note="Čistá hodnota objednaných prodejů podle zvolených prodejních filtrů a kola; nejde o výsledek celého trhu."/><Metric label="Vykázaný zisk" value={model.finance.profit} currency={model.finance.currency} note={`Celá společnost ${filters.company}; poslední finanční výkaz, ${model.finance.at}. Oblast ani kanál jej neomezují.`}/><Metric label="Hotovost" value={model.finance.cash} currency={model.finance.currency} note={`Bankovní účet celé společnosti ${filters.company}; ${model.finance.at}.`}/><Metric label="Hodnota firmy" value={model.finance.valuation} currency={model.finance.currency} note={`Celá společnost ${filters.company}; ${model.finance.at}.`}/></div>
 <p className="flex flex-wrap items-center gap-1 text-xs text-slate-600">Prodejní analýza: <strong>{filters.round?`kolo ${filters.round}`:'všechna dostupná kola'}</strong> · {filters.company} · {filters.currency} · {filters.unit}{filters.area&&` · oblast ${filters.area}`}{filters.channel&&` · kanál ${filters.channel}`}{filters.product&&` · výrobek ${filters.product}`}<InfoHint label="Rozsah jednotlivých údajů">Sklad je aktuální stav celé společnosti ve všech jednotkách. Trh má vlastní zvolené období. Finanční ukazatele a finanční graf jsou za celou společnost, bez regionálních a produktových filtrů.</InfoHint></p>
 <div className="round-tables grid items-start gap-3 min-[1440px]:grid-cols-2">
 <InventoryTable compact data={data} origin={filters.origin} company={filters.company} onExpand={onInventoryExpand} onProductOpen={onProductOpen}/>
 <MarketTable compact data={data} origin={filters.origin} company={filters.company} periodSelection={marketPeriod} onPeriodSelection={onMarketPeriod} onExpand={onMarketExpand}/>
 </div>
 <div className="round-charts grid grid-cols-2 gap-3"><Card className="min-w-0 p-3"><h2 className="mb-2 text-sm font-semibold">Tržby v herním čase</h2><Trend data={model.timeline} currency={filters.currency}/></Card><Card className="min-w-0 p-3"><h2 className="mb-2 text-sm font-semibold">Prodeje podle oblastí · {filters.currency}</h2><Bars data={model.areas} unit={filters.currency}/></Card><Card className="min-w-0 p-3"><h2 className="mb-2 text-sm font-semibold">Tržby podle výrobků · {filters.currency}</h2><Bars productAxis data={products} unit={filters.currency}/></Card><Card className="min-w-0 p-3"><h2 className="mb-2 text-sm font-semibold">Marketing podle oblastí · {filters.currency}</h2><Bars data={group(model.marketing,['area'],'marketing')} unit={filters.currency}/></Card></div>
 <Card className="min-w-0 p-3" data-testid="round-finance"><h2 className="mb-2 text-sm font-semibold">Hotovost a vykázaný zisk · celá společnost {filters.company}</h2><FinanceChart data={financeData} currency={filters.currency}/></Card>
 </div>;
}
