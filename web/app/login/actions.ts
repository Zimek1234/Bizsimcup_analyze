'use server';
import {redirect} from 'next/navigation';
import {supabase,configError} from '@/lib/supabase';
export async function login(form:FormData){
 if(configError())redirect('/login?error=config');
 const db=await supabase();const email=String(form.get('email')??'').trim();const password=String(form.get('password')??'');
 if(!email||!password||email.length>320||password.length>1024)redirect('/login?error=auth');
 const {error}=await db.auth.signInWithPassword({email,password});if(error)redirect('/login?error=auth');redirect('/');
}
export async function logout(){const db=await supabase();await db.auth.signOut();redirect('/login');}
