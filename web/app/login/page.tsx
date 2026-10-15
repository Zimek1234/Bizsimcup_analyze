import {configError} from '@/lib/supabase';
import {login} from './actions';
import {Button} from '@/components/ui/button';
import {Card} from '@/components/ui/card';
export const dynamic='force-dynamic';
export default async function Login({searchParams}:{searchParams:Promise<{error?:string}>}){
 const error=configError();const params=await searchParams;
 return <main className="mx-auto flex min-h-screen max-w-md items-center px-5"><Card className="w-full p-8"><p className="text-sm font-semibold text-teal-700">ERPsim / Manufacturing</p><h1 className="mt-3 text-2xl font-bold">Přihlášení týmu</h1><p className="mt-2 text-sm text-slate-500">Přístup mají pouze přidaní členové týmu.</p>{error?<p role="alert" className="mt-6 rounded-lg bg-amber-50 p-4 text-sm">{error}</p>:<form action={login} className="mt-6 flex flex-col gap-4"><label>E-mail<input className="mt-1 w-full" type="email" name="email" autoComplete="username" required/></label><label>Heslo<input className="mt-1 w-full" type="password" name="password" autoComplete="current-password" required/></label>{params.error&&<p role="alert" className="text-sm text-red-700">Přihlášení se nezdařilo. Ověřte údaje a dostupnost služby; zkuste to znovu.</p>}<Button type="submit">Přihlásit se</Button></form>}<p className="mt-6 text-xs text-slate-500">Přihlašovací údaje ERPsim se používají pouze v samostatném synchronizátoru.</p></Card></main>;
}
