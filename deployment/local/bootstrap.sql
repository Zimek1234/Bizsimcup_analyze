create role anon nologin;
create role authenticated nologin;
create role service_role nologin bypassrls;
create role authenticator login password :'db_password' noinherit;
create role supabase_auth_admin login password :'db_password';
grant anon, authenticated, service_role to authenticator;
create schema auth authorization supabase_auth_admin;
grant usage on schema public,auth to anon,authenticated,service_role,supabase_auth_admin;
grant create on schema public to supabase_auth_admin;
create function auth.uid() returns uuid language sql stable as $$
 select coalesce(nullif(current_setting('request.jwt.claim.sub',true),''),
 (nullif(current_setting('request.jwt.claims',true),'')::jsonb ->> 'sub'))::uuid;
$$;

alter function auth.uid() owner to supabase_auth_admin;

alter role supabase_auth_admin set search_path to auth;
