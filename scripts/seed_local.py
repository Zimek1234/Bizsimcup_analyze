"""Create ephemeral LOCAL demo accounts and import actual workbook; never run against hosted projects."""
from pathlib import Path
import json
import os
import secrets
import sys
import time
import requests
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from service.cloud import CloudStore
from erpsim.loaders import read_workbook

def setup():
    env=dict(line.split('=',1) for line in (ROOT/'.local/worker.env').read_text().splitlines())
    assert env['SUPABASE_URL']=='http://127.0.0.1:54321'
    os.environ.update(env)
    store=CloudStore(allow_local=True)
    for _ in range(30):
        try:
            store.request('GET','teams?limit=1');break
        except Exception:time.sleep(1)
    credentials_path=ROOT/'.local/demo.json'
    if credentials_path.exists():
        return json.loads(credentials_path.read_text())
    password=secrets.token_urlsafe(24)
    email='local-'+secrets.token_hex(5)+'@example.test'
    response=requests.post(env['SUPABASE_URL']+'/auth/v1/admin/users',headers={'apikey':store.key,'Authorization':'Bearer '+store.key},json={'email':email,'password':password,'email_confirm':True},timeout=20)
    if not response.ok:raise RuntimeError('Local Auth user provisioning failed (body suppressed)')
    user=response.json()['id']
    team=store.request('POST','teams',{'name':'Lokální ověření Introduction'})[0]['id']
    store.request('POST','team_members',{'team_id':team,'user_id':user,'role':'admin'})
    game=store.request('POST','games',{'team_id':team,'name':'Zkouška Introduction · skutečný export','purpose':'trial'})[0]['id']
    store.request('POST','game_settings',{'game_id':game,'currency':'EUR','unit':'ST'})
    data,_=read_workbook((ROOT/'samples/BIZ SIM data ze zkušebky.xlsx').read_bytes(),'Introduction.xlsx')
    with store.lease(game):
        for dataset,rows in data.items():
            run=store.begin(game,dataset,'file:zkouska');store.finish(run,rows)
    credentials={'email':email,'password':password,'game':game,'team':team,'user':user}
    credentials_path.write_text(json.dumps(credentials));credentials_path.chmod(0o600)
    print('Skutečný sešit Introduction importován do lokálního PostgreSQL přes Supabase API; lokální přístup v ignorovaném .local/demo.json.')
    return credentials
if __name__=='__main__':setup()
