'use client';
import {ResponsiveContainer,LineChart,Line,XAxis,YAxis,Tooltip,CartesianGrid,BarChart,Bar,Legend} from 'recharts';
const fmt=(n:number)=>new Intl.NumberFormat('cs-CZ',{notation:'compact',maximumFractionDigits:1}).format(n);
export function Trend({data,currency}:{data:{label:string;value:number|null}[];currency:string}){
 if(!data.length)return <p className="py-12 text-center text-sm text-slate-500">Pro toto období nejsou dostupné srovnatelné údaje.</p>;
 return <div className="h-64 min-w-0" role="img" aria-label="Vývoj tržeb podle kola a herního dne"><ResponsiveContainer width="100%" height="100%"><LineChart data={data} margin={{top:15,right:15,left:0,bottom:5}}><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0"/><XAxis dataKey="label" tick={{fontSize:11}} minTickGap={24}/><YAxis tickFormatter={fmt} width={65} tick={{fontSize:11}}/><Tooltip formatter={(value)=>[`${fmt(Number(value))} ${currency}`,'Tržby']} labelFormatter={label=>`Kolo · den: ${label}`}/><Line type="monotone" dataKey="value" stroke="#0f766e" strokeWidth={2.5} isAnimationActive={false} dot={false} connectNulls={false}/></LineChart></ResponsiveContainer></div>;
}
export function Bars({data,unit}:{data:{label:string;value:number|null}[];unit:string}){
 if(!data.length)return <p className="py-8 text-sm text-slate-500">Data nejsou dostupná.</p>;
 return <div className="h-56 min-w-0"><ResponsiveContainer width="100%" height="100%"><BarChart data={data} margin={{left:0,right:10,top:10,bottom:10}}><CartesianGrid strokeDasharray="3 3" vertical={false}/><XAxis dataKey="label" tick={{fontSize:11}}/><YAxis tickFormatter={fmt} width={65} tick={{fontSize:11}}/><Tooltip formatter={value=>[`${fmt(Number(value))} ${unit}`,'Hodnota']}/><Bar dataKey="value" fill="#0f766e" isAnimationActive={false} radius={[4,4,0,0]}/></BarChart></ResponsiveContainer></div>;
}
export function FinanceChart({data,currency}:{data:{label:string;profit:number|null;cash:number|null}[];currency:string}){
 if(!data.length)return <p className="text-sm text-slate-500">Vývoj financí není dostupný.</p>;
 return <div className="h-64 min-w-0"><ResponsiveContainer width="100%" height="100%"><LineChart data={data}><CartesianGrid strokeDasharray="3 3" vertical={false}/><XAxis dataKey="label" tick={{fontSize:11}}/><YAxis tickFormatter={fmt} width={65}/><Tooltip formatter={(v)=>`${fmt(Number(v))} ${currency}`}/><Legend/><Line dataKey="profit" name="Vykázaný zisk" stroke="#0f766e" dot={false}/><Line dataKey="cash" name="Hotovost" stroke="#6366f1" dot={false}/></LineChart></ResponsiveContainer></div>;
}
