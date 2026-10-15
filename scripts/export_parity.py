"""Produce a disposable web fixture from the real workbook using unchanged Python code."""
from pathlib import Path
import json
from erpsim.loaders import read_workbook
from erpsim.analytics import views
from service.cloud import serial
ROOT=Path(__file__).resolve().parents[1]
data,_=read_workbook((ROOT/'samples/BIZ SIM data ze zkušebky.xlsx').read_bytes(),'Introduction.xlsx')
heads=[{'dataset':name,'origin':'file:zkouska','last_success':'2026-10-10T12:00:00Z',
    'snapshots':{'id':name,'dataset':name,'origin':'file:zkouska','created_at':'2026-10-10T12:00:00Z','rows':rows,'views':views(name,rows)}} for name,rows in data.items()]
state=ROOT/'.local';state.mkdir(exist_ok=True)
(state/'parity.json').write_text(json.dumps({'heads':heads},default=serial,ensure_ascii=False),encoding='utf-8')
print('Ověřovací fixture vytvořena z původní čtečky a skutečného sešitu Introduction.')
