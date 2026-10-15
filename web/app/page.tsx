import {redirect} from 'next/navigation';
import {loadDashboard} from '@/lib/data';
import {configError} from '@/lib/supabase';
import {Dashboard} from '@/components/dashboard';
import {Card} from '@/components/ui/card';
import {logout} from './login/actions';
export const dynamic='force-dynamic';
export default async function Page(){
 if(configError())redirect('/login');
 let data;
 try{data=await loadDashboard();}catch(e){if(e instanceof Error&&e.message==='AUTH')redirect('/login');return <main className="mx-auto max-w-xl p-10"><Card><h1 className="text-xl font-bold">Data nejsou dostupná</h1><p className="mt-3">Ověřte dostupnost Supabase a provedení databázových migrací. Přihlášení zůstává chráněné.</p><a href="/" className="mt-5 inline-block underline">Zkusit znovu</a></Card></main>;}
 return <><form action={logout} className="absolute right-5 top-5"><button className="text-sm text-slate-500">Odhlásit se</button></form><Dashboard initial={data}/></>;
}
