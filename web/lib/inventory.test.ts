import {describe,it,expect} from 'vitest';
import {readFileSync} from 'node:fs';
import {inventoryItems,filterInventory} from './inventory';
import {compute,alerts,type Filters} from './analytics';
import {defaultSettings,type DashboardData,type Head,type Row} from './types';
const origin='file:zkouska';
const fixture=JSON.parse(readFileSync(new URL('../../.local/parity.json',import.meta.url),'utf8'));
const data:DashboardData={...fixture,games:[],game:null,runs:[],settings:defaultSettings,editable:false,preview:false};
const f:Filters={origin,company:'AA',currency:'EUR',unit:'ST',product:'',area:'',channel:'',round:''};
const stock=(extra:Row={}):Row=>({PLANT:'AA',MATERIAL_NUMBER:'AA-R01',MATERIAL_DESCRIPTION:'Nuts',STORAGE_LOCATION:'88',STOCK:'0',RESTRICTED:'0',UNIT:'KG',...extra});
const replace=(rows:Row[])=>({...data,heads:data.heads.map(h=>h.dataset==='Current_Inventory'?{...h,snapshots:{...h.snapshots,rows}}:h)});
describe('Kompletní aktuální zásoby',()=>{
 it('ze skutečného Introduction zobrazí 22 položek, suroviny KG, obaly ST i nuly',()=>{
  const items=inventoryItems(data,origin,'AA');expect(items).toHaveLength(22);
  expect(filterInventory(items,'finished')).toHaveLength(12);expect(filterInventory(items,'raw')).toHaveLength(6);expect(filterInventory(items,'packaging')).toHaveLength(4);
  expect(filterInventory(items,'raw').every(i=>i.unit==='KG')).toBe(true);expect(filterInventory(items,'packaging').every(i=>i.unit==='ST')).toBe(true);
  expect(items.filter(i=>i.stock==='0').length).toBe(8);expect(items.find(i=>i.material==='AA-R04')?.stock).toBe('7201.2');
  expect(items.find(i=>i.material==='AA-P01')?.stock).toBe('32000'); // RESTRICTED is not added again.
 });
 it('nevyžaduje prodej, výrobní příkaz ani prodejní jednotku',()=>{
  const missing={...data,heads:data.heads.filter(h=>!['Sales','Production_Orders'].includes(h.dataset))};
  expect(inventoryItems(missing,origin,'AA')).toHaveLength(22);
  expect(inventoryItems(missing,origin,'AA').filter(i=>i.type==='finished').every(i=>i.rate===null&&i.wip===null)).toBe(true);
  expect(inventoryItems(data,origin,'AA').some(i=>i.unit==='KG')).toBe(true);
  const zeros=inventoryItems(replace([stock(),stock({MATERIAL_NUMBER:'AA-P01',MATERIAL_DESCRIPTION:'Large Box (1kg)',UNIT:'ST'})]),origin,'AA');
  expect(zeros.map(i=>[i.type,i.stock]).sort()).toEqual([['packaging','0'],['raw','0']]);
 });
 it('udržuje filtr typu i lokace a nesčítá odlišné jednotky',()=>{
  const items=inventoryItems(replace([stock({STOCK:'2'}),stock({UNIT:'ST',STOCK:'3'})]),origin,'AA');
  expect(items).toHaveLength(2);expect(items.map(i=>[i.unit,i.stock])).toEqual([['KG','2'],['ST','3']]);
  expect(filterInventory(items,'raw','88')).toHaveLength(2);expect(filterInventory(items,'packaging')).toHaveLength(0);expect(filterInventory(items,'all','02')).toHaveLength(0);
 });
 it('neodvozuje typ z prefixu a neznámé či konfliktní typy neskrývá',()=>{
  const d=replace([stock({MATERIAL_NUMBER:'AA-R99'}),stock({MATERIAL_NUMBER:'AA-F99',UNIT:'ST'})]);
  const items=inventoryItems(d,origin,'AA');expect(items.every(i=>i.type==='unclassified')).toBe(true);expect(filterInventory(items,'all')).toHaveLength(2);
  const rules=data.heads.find(h=>h.dataset==='Current_Game_Rules')!;
  const conflict={...data,heads:data.heads.map(h=>h===rules?{...h,snapshots:{...h.snapshots,rows:[...h.snapshots.rows,{CATEGORY:'Product',COMPANY_CODE:'AA',ELEMENT:'AA-R01',VALUE:'Packing'}]}}:h)};
  expect(inventoryItems(conflict,origin,'AA').find(i=>i.material==='AA-R01')?.type).toBe('unclassified');
  const noRules={...replace([stock()]),heads:replace([stock()]).heads.filter(h=>h.dataset!=='Current_Game_Rules')};
  const native=noRules.heads.find(h=>h.dataset==='Current_Inventory')!;
  const exported:Head={...native,dataset:'InventoryExport',snapshots:{...native.snapshots,rows:[{Material:'AA-R01',Category:'Raw Materials',Stock:'999'}]}};
  const both=inventoryItems({...noRules,heads:[...noRules.heads,exported]},origin,'AA');expect(both[0].type).toBe('raw');expect(both[0].stock).toBe('0');
 });
 it('odděluje společnost, původ a kompletní snímek od historie a alternativních zdrojů',()=>{
  const items=inventoryItems(replace([stock(),stock({PLANT:'BB',STOCK:'999'})]),origin,'AA');expect(items).toHaveLength(1);expect(items[0].stock).toBe('0');
  expect(inventoryItems(data,'odata','AA')).toHaveLength(0);
  const historical={...data,heads:data.heads.map(h=>h.dataset==='Current_Inventory'?{...h,dataset:'Inventory'}:h)};expect(inventoryItems(historical,origin,'AA')).toHaveLength(0);
  const other:Head={...data.heads.find(h=>h.dataset==='Current_Inventory')!,origin:'odata'};
  expect(inventoryItems({...data,heads:[...data.heads,other]},origin,'AA')).toHaveLength(22);
 });
 it('sčítá různé lokace, přesné duplicity pouze jednou a konflikty označí',()=>{
  const items=inventoryItems(replace([stock({STOCK:'2',RESTRICTED:'2'}),stock({STOCK:'2.0',RESTRICTED:'2.0'}),stock({STORAGE_LOCATION:'01',STOCK:'3'})]),origin,'AA');
  expect(items[0].stock).toBe('5');expect(items[0].duplicateRows).toBe(1);expect(items[0].locations).toHaveLength(2);
  expect(filterInventory(items,'all','88')[0].stock).toBe('5'); // Item total, location detail remains separate.
  const conflict=inventoryItems(replace([stock({STOCK:'2'}),stock({STOCK:'3'})]),origin,'AA')[0];expect(conflict.stock).toBeNull();expect(conflict.locations[0].conflict).toBe(true);
  const unknownLocations=inventoryItems(replace([stock({STORAGE_LOCATION:null}),stock({STORAGE_LOCATION:null})]),origin,'AA')[0];expect(unknownLocations.stock).toBeNull();
 });
 it('u surovin a obalů nepočítá prodejní tempo, výdrž ani výrobní rozpracovanost',()=>{
  const items=inventoryItems(data,origin,'AA').filter(i=>i.type==='raw'||i.type==='packaging');expect(items.every(i=>i.rate===null&&i.days===null&&i.wip===null)).toBe(true);expect(items.every(i=>i.estimateNote.includes('ověřená spotřeba'))).toBe(true);
 });
 it('zachová hotovým výrobkům tempo, odhad zásoby a WIP ve stejné jednotce',()=>{
  const model=compute(data,f),items=inventoryItems(data,origin,'AA');
  for(const p of model.products){const i=items.find(i=>i.code===p.code&&i.unit===p.unit)!;expect(i.rate).toBe(p.rate);if(p.days===null)expect(i.days).toBeNull();else expect(i.days).toBeCloseTo(p.days,12);expect(i.wip).toBe(p.wip);}
  const conflicting=structuredClone(data);const orders=conflicting.heads.find(h=>h.dataset==='Production_Orders')!;
  orders.snapshots.views=[{organization:'AA',product:'F01',unit:'KG',target:'100',confirmed:'0'}];expect(inventoryItems(conflicting,origin,'AA').find(i=>i.code==='F01')?.wip).toBeNull();
 });
 it('upozornění na výdrž nesmí používat prodejní tempo surovin',()=>{
  const d=structuredClone(data);const sales=d.heads.find(h=>h.dataset==='Sales')!;
  sales.snapshots.views=[{...sales.snapshots.views[0],product:'AA-R01',description:'Nuts',unit:'KG',delivered:'100',elapsed_steps:'1'}];
  const kg={...f,unit:'KG'};expect(alerts(d,kg,compute(d,kg)).some(a=>a.title.includes('Nuts: odhad'))).toBe(false);
 });
});
