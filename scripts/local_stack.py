"""Local integration environment, NOT cloud provisioning. Secrets generated in ignored .local/."""
from pathlib import Path
import base64
import hashlib
import hmac
import json
import secrets
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / '.local'
ENV = STATE / 'stack.env'

def compose(*args, **kwargs):
    return subprocess.run(['docker','compose','--env-file',str(ENV),'-f',str(ROOT/'deployment/local/compose.yml'),*args],check=True,**kwargs)

def token(secret, role):
    def enc(x):
        return base64.urlsafe_b64encode(json.dumps(x,separators=(',',':')).encode()).rstrip(b'=')
    msg = enc({'alg':'HS256','typ':'JWT'})+b'.'+enc({'role':role,'iss':'local-test','exp':int(time.time())+86400*365})
    return (msg+b'.'+base64.urlsafe_b64encode(hmac.new(secret.encode(),msg,hashlib.sha256).digest()).rstrip(b'=')).decode()

def setup():
    STATE.mkdir(exist_ok=True,mode=0o700)
    if not ENV.exists() and (ROOT/'web/.env.local').exists():
        raise RuntimeError('Existující web/.env.local se nepřepisuje. Použijte čistý checkout pro lokální integrační prostředí.')
    if not ENV.exists():
        db = secrets.token_hex(24)
        jwt = secrets.token_hex(32)
        ENV.write_text(f'LOCAL_DB_PASSWORD={db}\nLOCAL_JWT_SECRET={jwt}\n')
        ENV.chmod(0o600)
        (STATE/'worker.env').write_text('SUPABASE_URL=http://127.0.0.1:54321\nSUPABASE_SERVICE_ROLE_KEY='+token(jwt,'service_role')+'\n')
        (STATE/'worker.env').chmod(0o600)
        web_env = ROOT/'web/.env.local'
        if web_env.exists():
            raise RuntimeError('web/.env.local již existuje; ponechte ji zachovanou a použijte oddělený checkout pro lokální testy.')
        web_env.write_text('NEXT_PUBLIC_SUPABASE_URL=http://127.0.0.1:54321\nNEXT_PUBLIC_SUPABASE_ANON_KEY='+token(jwt,'anon')+'\nSUPABASE_DATA_ENV=local\n')
    values = dict(line.split('=',1) for line in ENV.read_text().splitlines())
    compose('up','-d','--wait','db')
    # Docker volumes may not survive a new cloud task; on-disk markers alone are insufficient.
    role = compose('exec','-T','db','psql','-U','postgres','-tAc',
        "select count(*) from pg_roles where rolname='supabase_auth_admin'",capture_output=True,text=True).stdout.strip()
    if role == '0':
        for marker in ['bootstrapped','initialized','demo.json',*[p.stem for p in (ROOT/'supabase/migrations').glob('*.sql')]]:
            (STATE/marker).unlink(missing_ok=True)
    initialized = STATE/'initialized'
    if not (STATE/'bootstrapped').exists():
        # No secret printed. stdin psql variable is used only by ephemeral test bootstrap.
        sql = "\\set db_password '"+values['LOCAL_DB_PASSWORD']+"'\n"+(ROOT/'deployment/local/bootstrap.sql').read_text()
        compose('exec','-T','db','psql','-U','postgres','-v','ON_ERROR_STOP=1',input=sql,text=True,stdout=subprocess.DEVNULL)
        (STATE/'bootstrapped').touch()
    compose('up','-d','auth')
    for _ in range(60):
        try:
            # gateway not up yet; health from container, no credentials.
            result=compose('exec','-T','auth','wget','-Y','off','-qO-','http://127.0.0.1:9999/health',capture_output=True)
            if result.returncode==0: break
        except subprocess.CalledProcessError:
            pass
        time.sleep(1)
    else: raise RuntimeError('Local Auth failed readiness check')
    if not initialized.exists():
        uid_sql = "create or replace function auth.uid() returns uuid language sql stable as $$ select (nullif(current_setting('request.jwt.claims',true),'')::jsonb ->> 'sub')::uuid; $$;"
        compose('exec','-T','db','psql','-U','postgres','-v','ON_ERROR_STOP=1',input=uid_sql,text=True,stdout=subprocess.DEVNULL)
        compose('exec','-T','db','psql','-U','postgres','-v','ON_ERROR_STOP=1',
            input=(ROOT/'supabase/migrations/202610100001_analytics.sql').read_text(),text=True,stdout=subprocess.DEVNULL)
        initialized.touch()
    for migration in sorted((ROOT/'supabase/migrations').glob('*.sql')):
        marker = STATE/migration.stem
        if migration.name.startswith('202610100001'):
            marker.touch()  # Already applied above during initial boot.
        elif not marker.exists():
            compose('exec','-T','db','psql','-U','postgres','-v','ON_ERROR_STOP=1',input=migration.read_text(),text=True,stdout=subprocess.DEVNULL)
            marker.touch()
    compose('up','-d','rest','gateway')
    compose('kill','-s','SIGUSR1','rest')
    print('Lokální PostgreSQL, Supabase Auth a PostgREST spuštěny. Cloud není nakonfigurován.')

if __name__=='__main__': setup()
