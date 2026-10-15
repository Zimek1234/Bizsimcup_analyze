import 'server-only';
import {createServerClient} from '@supabase/ssr';
import {cookies} from 'next/headers';
export function configError():string|null{
 if(!process.env.NEXT_PUBLIC_SUPABASE_URL||!process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY)return 'Supabase zatím není propojena. Nastavte veřejnou URL a veřejný klíč podle návodu.';
 if(process.env.VERCEL_ENV==='preview'&&process.env.SUPABASE_DATA_ENV!=='staging')return 'Náhled je zablokován: potřebuje samostatný staging projekt Supabase.';
 if(process.env.VERCEL_ENV&&!process.env.NEXT_PUBLIC_SUPABASE_URL.startsWith('https://'))return 'Cloudové připojení vyžaduje HTTPS.';
 return null;
}
export async function supabase(){
 if(configError())throw new Error('CONFIGURATION_UNAVAILABLE');
 const jar=await cookies();
 return createServerClient(process.env.NEXT_PUBLIC_SUPABASE_URL!,process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,{cookieOptions:{httpOnly:true,sameSite:'lax',secure:!!process.env.VERCEL_ENV,path:'/'},cookies:{getAll:()=>jar.getAll(),setAll:items=>{try{items.forEach(({name,value,options})=>jar.set(name,value,options));}catch{/* Server component cannot write; API/action refreshes. */}}}});
}
