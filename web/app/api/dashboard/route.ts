import {NextRequest,NextResponse} from 'next/server';
import {loadDashboard} from '@/lib/data';
import {supabase} from '@/lib/supabase';
export const dynamic='force-dynamic';
export async function GET(request:NextRequest){
 try{const asof=request.nextUrl.searchParams.get('asof')??undefined;if(asof&&!Number.isFinite(Date.parse(asof)))return NextResponse.json({error:'Neplatný čas historie.'},{status:400});return NextResponse.json(await loadDashboard(request.nextUrl.searchParams.get('game')??undefined,asof),{headers:{'Cache-Control':'private, no-store'}});}
 catch(e){return NextResponse.json({error:e instanceof Error&&e.message==='AUTH'?'Přihlášení vypršelo. Přihlaste se znovu.':'Data se nepodařilo načíst. Poslední přehled zůstává zobrazen; ověřte službu a migrace.'},{status:e instanceof Error&&e.message==='AUTH'?401:503});}
}
export async function POST(request:NextRequest){
 if(process.env.VERCEL_ENV==='preview')return NextResponse.json({error:'Náhled je pouze pro čtení.'},{status:403});
 let origin:URL;try{origin=new URL(request.headers.get('origin')??'');}catch{return NextResponse.json({error:'Neplatný původ požadavku.'},{status:403});}
 if(origin.host!==request.headers.get('host')||!['http:','https:'].includes(origin.protocol)||(process.env.VERCEL_ENV&&origin.protocol!=='https:'))return NextResponse.json({error:'Neplatný původ požadavku.'},{status:403});
 try{
 const db=await supabase();const {data:{user}}=await db.auth.getUser();if(!user)return NextResponse.json({error:'Přihlaste se znovu.'},{status:401});
 const body=await request.json();if(!/^[0-9a-f-]{36}$/i.test(body.game??''))throw new Error('invalid');
 const s=body.settings;const within=(v:unknown,min:number,max:number)=>typeof v==='number'&&Number.isFinite(v)&&v>=min&&v<=max;
 if(!s||!Number.isInteger(s.interval_seconds)||!within(s.interval_seconds,10,3600)||!Number.isInteger(s.stale_seconds)||!within(s.stale_seconds,30,86400)||!within(s.stock_days,0,1000)||!within(s.margin_percent,-1000,100)||!(s.marketing_limit===null||within(s.marketing_limit,0,1e12)))throw new Error('invalid');
 const {data,error}=await db.from('game_settings').update({interval_seconds:s.interval_seconds,stale_seconds:s.stale_seconds,stock_days:s.stock_days,margin_percent:s.margin_percent,marketing_limit:s.marketing_limit,currency:typeof s.currency==='string'?s.currency.slice(0,30):null,unit:typeof s.unit==='string'?s.unit.slice(0,30):null,updated_at:new Date().toISOString()}).eq('game_id',body.game).select('game_id');
 if(error||!data?.length)return NextResponse.json({error:'Nastavení nebylo uloženo. Potřebujete oprávnění editor nebo admin.'},{status:403});
 return NextResponse.json({ok:true});
 }catch{return NextResponse.json({error:'Nastavení není platné nebo služba není dostupná.'},{status:400});}
}
