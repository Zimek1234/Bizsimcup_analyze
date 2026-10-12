// Disposable localhost demo only. Synthetic cases change browser responses,
// never Supabase rows or uploaded data.
import {chromium} from '@playwright/test';
import {readFileSync,mkdirSync,existsSync} from 'node:fs';
import assert from 'node:assert/strict';
const root=new URL('../../',import.meta.url);
const c=JSON.parse(readFileSync(new URL('.local/demo.json',root),'utf8'));
const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH??(existsSync('/usr/bin/chromium')?'/usr/bin/chromium':undefined),args:['--no-sandbox']});
const page=await browser.newPage({viewport:{width:1440,height:1100},locale:'cs-CZ',timezoneId:'Europe/Prague'}),errors=[];page.on('pageerror',e=>errors.push(e.message));
try{
 await page.goto('http://127.0.0.1:3000/');await page.getByLabel('E-mail').fill(c.email);await page.getByLabel('Heslo',{exact:true}).fill(c.password);await page.getByRole('button',{name:'Přihlásit se',exact:true}).click();await page.getByRole('heading',{name:'Přehled hry',exact:true}).waitFor();
 const card=page.getByTestId('inventory-card');await card.getByRole('table').waitFor();
 assert.equal(await card.locator('tbody tr').count(),22);assert.match(await card.innerText(),/AA-R01/);assert.match(await card.innerText(),/KG/);assert.match(await card.innerText(),/AA-P01/);
 const rows=card.locator('tbody tr');assert.equal(await rows.filter({hasText:'F01'}).locator('td').nth(3).innerText(),'0');
 mkdirSync(new URL('web/docs/',root),{recursive:true});await card.screenshot({path:new URL('web/docs/inventory-introduction.png',root).pathname});
 await card.getByRole('button',{name:'Suroviny',exact:true}).click();assert.equal(await rows.count(),6);assert((await rows.allTextContents()).every(t=>t.includes('KG')&&t.includes('ověřená spotřeba')));
 await card.getByRole('button',{name:'Obaly',exact:true}).click();assert.equal(await rows.count(),4);assert((await rows.allTextContents()).every(t=>t.includes('ST')));
 await card.getByRole('button',{name:'Hotové výrobky',exact:true}).click();assert.equal(await rows.count(),12);
 await card.getByRole('button',{name:'Vše',exact:true}).click();await page.getByLabel('Skladová lokace').selectOption('88');assert.equal(await rows.count(),10);
 await rows.filter({hasText:'AA-P01'}).locator('summary').click();assert.match(await rows.filter({hasText:'AA-P01'}).innerText(),/STOCK: 32\s000 ST/);assert.match(await rows.filter({hasText:'AA-P01'}).locator('td').nth(3).innerText(),/^32\s000$/);
 await page.getByRole('button',{name:'Podrobnosti',exact:true}).click();await page.getByLabel('Jednotka',{exact:true}).selectOption('KG');await page.getByRole('button',{name:'Přehled',exact:true}).click();assert.equal(await rows.count(),22);assert.match(await card.innerText(),/AA-P01/); // Sales unit KG must not remove ST packaging/finished items.
 await page.getByLabel('Skladová lokace').selectOption('');await page.setViewportSize({width:390,height:844});assert(await card.getByRole('region').evaluate(e=>e.scrollWidth>e.clientWidth));
 await page.setViewportSize({width:1440,height:1100});
 const response=await page.request.get('http://127.0.0.1:3000/api/dashboard'),fixture=await response.json();fixture.heads=fixture.heads.filter(h=>!['Sales','SalesExport','SummarySalesExport','Production_Orders'].includes(h.dataset));
 const current=fixture.heads.find(h=>h.dataset==='Current_Inventory');
 current.snapshots.rows=current.snapshots.rows.map(r=>['AA-R01','AA-P01'].includes(r.MATERIAL_NUMBER)?{...r,STOCK:'0',RESTRICTED:'0'}:r);
 current.snapshots.rows.push({PLANT:'AA',MATERIAL_NUMBER:'AA-X99',MATERIAL_DESCRIPTION:'Test nezařazené položky',STORAGE_LOCATION:'88',STOCK:'0',RESTRICTED:'0',UNIT:'L'});
 await page.route('**/api/dashboard*',route=>route.fulfill({json:fixture}));
 await page.getByRole('button',{name:'Nastavení a zdroje',exact:true}).click();await page.getByLabel('Historie: stav uložený do reálného času').fill('2000-01-01T12:00');await page.getByText('Historický stav dostupný při stažení do',{exact:false}).waitFor();await page.getByRole('button',{name:'Přehled',exact:true}).click();
 assert.equal(await rows.count(),23);assert.equal(await rows.filter({hasText:'AA-R01'}).locator('td').nth(3).innerText(),'0');assert.equal(await rows.filter({hasText:'AA-P01'}).locator('td').nth(3).innerText(),'0');
 await card.getByRole('button',{name:'Nezařazené',exact:true}).click();assert.equal(await rows.count(),1);assert.match(await rows.first().innerText(),/AA-X99/);assert.equal(await rows.first().locator('td').nth(4).innerText(),'L');
 assert.deepEqual(errors,[]);console.log('PASS: real Introduction 22 items, KG/ST, 8 zero finished stocks, type/location filters, restricted stock not added, location detail/mobile scroll; browser-only zero raw/packaging and unclassified L material without sales/orders. Screenshot uses unmodified fixture.');
}finally{await browser.close();}
