import {describe,it,expect} from 'vitest';
import {readFileSync} from 'node:fs';
import {filterMarket,groupedMarket,marketCSV,marketProductKey,marketRows,periods} from './market';
import {channelLabels,productCatalogue,resolveProduct,productLabel} from './products';
import {defaultSettings,type DashboardData,type Row,type Head} from './types';

const origin='file:zkouska';
const fixture=JSON.parse(readFileSync(new URL('../../.local/parity.json',import.meta.url),'utf8'));
const base:DashboardData={...fixture,games:[],game:null,runs:[],settings:defaultSettings,editable:false,preview:false};
const head=(dataset:string,rows:Row[]):Head=>({dataset,origin,last_success:'2026-10-10T12:00:00Z',snapshots:{id:dataset,dataset,origin,created_at:'2026-10-10T12:00:00Z',rows,views:[]}});
const market=(extra:Row={}):Row=>({COMPANY_CODE:'AA',SIM_ROUND:'03',SIM_PERIOD:20,MATERIAL_DESCRIPTION:'Výrobek A',AREA:'North',DISTRIBUTION_CHANNEL:'12',CURRENCY:'EUR',UNIT:'ST',QUANTITY:'1',NET_VALUE:'10',AVERAGE_PRICE:'10',...extra});
const data=(rows:Row[],extra:Head[]=[])=>({...base,heads:[head('Market',rows),head('Current_Game_Rules',[
 {COMPANY_CODE:'AA',CATEGORY:'Product',ELEMENT:'AA-F01',DETAIL:'Výrobek A',VALUE:'Finished products'},
 {COMPANY_CODE:'AA',ELEMENT:'Distribution_Channel',DETAIL:'12',VALUE:'Grocery chains'},
 {COMPANY_CODE:'AA',ELEMENT:'Distribution_Channel',DETAIL:'14',VALUE:'Hypermarkets'},
 ]),...extra]});
describe('Tržní data nezávislá na vlastních prodejích',()=>{
 it('ověří skutečný Introduction sešit, zdrojové kódy a nejnovější SIM_PERIOD',()=>{
  const rows=marketRows(base,origin,'AA');expect(rows.length).toBeGreaterThan(0);
  expect(rows.every(r=>r.status==='matched'&&/^F\d{2}$/.test(r.code))).toBe(true);
  const latest=periods(rows)[0];
  const raw=base.heads.find(h=>h.dataset==='Market')!.snapshots.rows;
  expect(Number(latest.round)).toBe(Math.max(...raw.map(r=>Number(r.SIM_ROUND))));
  expect(Number(latest.period)).toBe(Math.max(...raw.filter(r=>r.SIM_ROUND===latest.round).map(r=>Number(r.SIM_PERIOD))));
  expect(rows.every(r=>r.periodKind==='period'&&!r.date)).toBe(true);
 });
 it('ukáže více kanálů a trh bez jakéhokoli vlastního prodeje',()=>{
  const d=data([market(),market({DISTRIBUTION_CHANNEL:'14'}),market({DISTRIBUTION_CHANNEL:'99'})]);
  const rows=marketRows(d,origin,'AA');expect(rows.map(r=>r.channel).sort()).toEqual(['12','14','99']);
  expect(rows.every(r=>r.code==='F01')).toBe(true);
  const names=channelLabels(d,origin,'AA');expect(names.get('14')).toBe('Hypermarkets');expect(names.get('99')??'99').toBe('99');
 });
 it('počítá váženou cenu z přesných součtů, nikoli průměrem cen',()=>{
  const [r]=marketRows(data([market(),market({QUANTITY:'3',NET_VALUE:'60',AVERAGE_PRICE:'20'})]),origin,'AA');
  expect(r.quantity).toBe('4');expect(r.value).toBe('70');expect(r.price).toBe('17.5');
  const [precise]=marketRows(data([market({NET_VALUE:'0.1'}),market({QUANTITY:'2',NET_VALUE:'0.2'})]),origin,'AA');expect(precise.price).toBe('0.1');
 });
 it('nikdy nesloučí různé dimenze ani neznámý produkt podle pořadí',()=>{
  for(const field of ['MATERIAL_DESCRIPTION','AREA','DISTRIBUTION_CHANNEL','SIM_PERIOD','SIM_ROUND','CURRENCY','UNIT']){
   expect(marketRows(data([market(),market({[field]:'OTHER'})]),origin,'AA')).toHaveLength(2);
  }
  const [r]=marketRows(data([market({MATERIAL_DESCRIPTION:'Nenalezený výrobek'})]),origin,'AA');expect(r.code).toBe('');expect(r.status).toBe('missing');
  expect(marketRows(data([market({UNIT:null}),market({UNIT:null})]),origin,'AA')).toHaveLength(2);
 });
 it('odmítne nejednoznačné propojení a cizí společnost či původ',()=>{
  const d=data([market()],[head('Sales',[{MATERIAL_NUMBER:'AA-F02',MATERIAL_DESCRIPTION:'Výrobek A',SALES_ORGANIZATION:'AA'}])]);
  expect(marketRows(d,origin,'AA')[0].status).toBe('ambiguous');expect(marketRows(d,origin,'AA')[0].code).toBe('');
  const foreign=head('Sales',[{MATERIAL_NUMBER:'BB-F02',MATERIAL_DESCRIPTION:'Výrobek A',SALES_ORGANIZATION:'BB'}]);
  expect(marketRows(data([market()],[foreign]),origin,'AA')[0].code).toBe('F01');
  const otherOrigin={...head('Sales',[{MATERIAL_NUMBER:'AA-F03',MATERIAL_DESCRIPTION:'Výrobek A',SALES_ORGANIZATION:'AA'}]),origin:'odata'};
  expect(marketRows(data([market()],[otherOrigin]),origin,'AA')[0].code).toBe('F01');
  expect(productLabel(resolveProduct(productCatalogue(d,origin,'AA'),'Výrobek A'))).toContain('nejednoznačné');
 });
 it('rozlišuje chybějící hodnotu a nulu a nikdy nedělí nulovým množstvím',()=>{
  const [zero]=marketRows(data([market({QUANTITY:'0',NET_VALUE:'0',AVERAGE_PRICE:null})]),origin,'AA');expect(zero.price).toBeNull();expect(zero.quantity).toBe('0');expect(zero.value).toBe('0');
  const [sourceZero]=marketRows(data([market({QUANTITY:'0',NET_VALUE:'0',AVERAGE_PRICE:'0'})]),origin,'AA');expect(sourceZero.price).toBe('0');expect(sourceZero.priceBasis).toBe('source');
  expect(marketRows(data([market({QUANTITY:'0',NET_VALUE:'0'}),market({QUANTITY:'0',NET_VALUE:'0'})]),origin,'AA')[0].price).toBeNull();
  const [free]=marketRows(data([market({QUANTITY:'5',NET_VALUE:'0'})]),origin,'AA');expect(free.price).toBe('0');
  const [missing]=marketRows(data([market({QUANTITY:null,NET_VALUE:null,AVERAGE_PRICE:null})]),origin,'AA');expect(missing.quantity).toBeNull();expect(missing.price).toBeNull();expect(missing.value).toBeNull();
  const [partial]=marketRows(data([market(),market({NET_VALUE:null})]),origin,'AA');expect(partial.value).toBeNull();expect(partial.price).toBeNull();
 });
 it('po filtrování i změně řazení obnoví první viditelné buňky skupiny',()=>{
  const d=data([market(),market({DISTRIBUTION_CHANNEL:'14'}),market({AREA:'South'}),market({SIM_PERIOD:19})]);
  const rows=marketRows(d,origin,'AA');const f={period:periods(rows)[0].periodKey,product:marketProductKey(rows[0]),area:'',channel:''};
  const grouped=groupedMarket(filterMarket(rows,f));expect(grouped[0].showPeriod&&grouped[0].showProduct&&grouped[0].showArea).toBe(true);
  expect(grouped[1].showProduct||grouped[1].showArea).toBe(false);expect(grouped[2].showArea).toBe(true);
  for(const descending of [false,true]){const filtered=groupedMarket(filterMarket(rows,{...f,area:'South'}),descending);expect(filtered[0].showPeriod&&filtered[0].showProduct&&filtered[0].showArea).toBe(true);}
  const csv=marketCSV(grouped);expect(csv.split('\r\n').slice(1).every(line=>line.includes('"03 / 20";"SIM_ROUND / SIM_PERIOD";"F01";"Výrobek A"'))).toBe(true);
  const two=marketRows(data([market(),market({MATERIAL_DESCRIPTION:'Výrobek B'})],[head('Current_Inventory',[{MATERIAL_NUMBER:'AA-F02',MATERIAL_DESCRIPTION:'Výrobek B',PLANT:'AA'}])]),origin,'AA');
  const reverse=groupedMarket(two,true);expect(reverse[0].code).toBe('F02');expect(reverse[1].code).toBe('F01');expect(reverse.every(r=>r.showProduct&&r.showArea)).toBe(true);expect(reverse[1].showPeriod).toBe(false);
 });
 it('zachová exportované skutečné kódy a datum bez vymyšleného období, měny nebo kanálu',()=>{
  const d={...base,heads:[head('MarketExport',[{'Simulation Date':'03/20',Material:'X900',Description:'Výrobek X',Area:'West',Price:'2.5',Quantity:'4',Value:'10'}])]};
  const [r]=marketRows(d,origin,'AA');expect(r.code).toBe('X900');expect(r.status).toBe('source');expect(r.periodKind).toBe('date');expect(r.period).toBe('');expect(r.currency).toBe('');expect(r.channel).toBe('');
 });
 it('nepřičte alternativní souborový export k úplnému OData snímku',()=>{
  const d=data([market()],[head('MarketExport',[{Material:'F01',Description:'Výrobek A',Quantity:'999',Value:'999'}])]);expect(marketRows(d,origin,'AA')).toHaveLength(1);expect(marketRows(d,origin,'AA')[0].quantity).toBe('1');
 });
});
