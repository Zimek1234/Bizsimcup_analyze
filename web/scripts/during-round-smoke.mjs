// Local demo only. User explicitly excluded mobile testing for this task.
import {chromium} from '@playwright/test';
import {readFileSync,mkdirSync,existsSync} from 'node:fs';
import assert from 'node:assert/strict';
const root=new URL('../../',import.meta.url),c=JSON.parse(readFileSync(new URL('.local/demo.json',root),'utf8'));
const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH??(existsSync('/usr/bin/chromium')?'/usr/bin/chromium':undefined),args:['--no-sandbox']});
const page=await browser.newPage({viewport:{width:2240,height:1400},locale:'cs-CZ',timezoneId:'Europe/Prague'}),errors=[];page.on('pageerror',e=>errors.push(e.message));
try{
 await page.goto('http://127.0.0.1:3000/');await page.getByLabel('E-mail').fill(c.email);await page.getByLabel('Heslo',{exact:true}).fill(c.password);await page.getByRole('button',{name:'Přihlásit se',exact:true}).click();await page.getByRole('heading',{name:'Přehled hry',exact:true}).waitFor();
 const r=await page.request.get('http://127.0.0.1:3000/api/dashboard'),data=await r.json();assert.equal(r.status(),200);
 await page.getByRole('button',{name:'Během kola',exact:true}).click();const view=page.getByTestId('during-round'),stock=view.getByTestId('inventory-card'),market=view.getByTestId('market-card');
 for(const [label,value] of Object.entries({'Tržby':3973037.2,'Vykázaný zisk':2148215.54,'Hotovost':3718307,'Hodnota firmy':85928621.6}))assert.equal(await view.getByTestId('round-kpi-'+label).getAttribute('data-value'),String(value));
 assert.equal(await stock.locator('tbody tr').count(),22);assert.match(await stock.locator('tbody').innerText(),/KG/);
 const quantities=data.heads.find(h=>h.dataset==='Current_Inventory').snapshots.rows;
 for(const item of quantities){const row=stock.locator('tbody tr').filter({has:page.getByTitle('Zdrojový materiál: '+item.MATERIAL_NUMBER,{exact:true})});assert.equal(await row.count(),1);const quantity=(await row.locator('td').nth(3).innerText()).replaceAll('\u00a0',' ').replaceAll(' ','');assert(quantity.startsWith(new Intl.NumberFormat('cs-CZ',{maximumFractionDigits:3}).format(Number(item.STOCK)).replaceAll('\u00a0','').replaceAll(' ','')));assert(quantity.includes(item.UNIT));}
 mkdirSync(new URL('web/docs/',root),{recursive:true});
 for(const [width,height] of [[2240,1400],[1493,800]]){
  await page.setViewportSize({width,height});await view.locator('.recharts-surface').first().waitFor();
  const a=await stock.boundingBox(),b=await market.boundingBox();assert(Math.abs(a.y-b.y)<2&&a.x+a.width<b.x+2,'Tables must be side by side');
  assert(a.width>(width-80)/2-30,'Screen width must be used');
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,'No page-wide horizontal overflow');
  for(const card of [stock,market]){const region=card.getByRole('region');const dimensions=await region.evaluate(el=>({h:el.clientHeight,scroll:el.scrollHeight,w:el.clientWidth,sw:el.scrollWidth}));assert(dimensions.scroll>dimensions.h&&dimensions.h<=340);assert(dimensions.sw<=dimensions.w+2,'Fixture should fit without horizontal scrolling');const heading=region.locator('th:not(.hidden)').first();const before=await heading.boundingBox();await region.evaluate(el=>{el.scrollTop=160;});const after=await heading.boundingBox();assert(Math.abs(before.y-after.y)<2,'Sticky header must stay in place');await region.evaluate(el=>{el.scrollTop=0;});}
  const charts=await view.locator('.round-charts').boundingBox();assert(charts.y<height,'Charts must start in the initial notebook viewport');
  const finance=view.getByTestId('round-finance');assert((await finance.boundingBox()).width>width-80);assert.equal(await finance.locator('.recharts-line').count(),2);
  await page.screenshot({path:new URL(`web/docs/during-round-${width}.png`,root).pathname,fullPage:true});
 }
 await stock.getByRole('button',{name:'Detail výrobku F01',exact:true}).click();await page.getByRole('dialog').waitFor();assert.match(await page.getByRole('dialog').innerText(),/Příspěvek %/i);assert.match(await page.getByRole('dialog').innerText(),/EUR \/ ST/);assert.equal(await page.getByRole('dialog').locator('tbody tr').first().locator('td').nth(4).innerText(),'4');assert.equal(await page.getByRole('dialog').locator('tbody tr').first().locator('td').nth(6).innerText(),'77,5');await page.getByRole('button',{name:'Zavřít detail'}).click();
 const options=await page.getByLabel('Tržní období').locator('option').evaluateAll(xs=>xs.map(x=>x.value));const older=options.find(v=>v!=='all'&&v!==options[0]);assert(older);await page.getByLabel('Tržní období').selectOption(older);
 const refreshed=page.waitForResponse(resp=>resp.url().includes('/api/dashboard')&&resp.request().method()==='GET',{timeout:20000});await refreshed;assert.equal(await page.getByLabel('Tržní období').inputValue(),older,'Polling must retain selected market period');
 const marketCount=await market.locator('tbody tr').count();const saleFilters=page.locator('summary').filter({hasText:'Filtry prodejní analýzy'});await saleFilters.click();
 await page.getByLabel('Oblast',{exact:true}).selectOption('North');await page.getByLabel('Kolo',{exact:true}).selectOption('03');await page.getByLabel('Jednotka',{exact:true}).selectOption('KG');
 assert.equal(await stock.locator('tbody tr').count(),22);assert.equal(await market.locator('tbody tr').count(),marketCount);assert.equal(await page.getByLabel('Tržní období').inputValue(),older);assert.equal(await view.getByTestId('round-kpi-Tržby').getAttribute('data-value'),'missing');assert.equal(await view.getByTestId('round-kpi-Vykázaný zisk').getAttribute('data-value'),'2148215.54');await page.getByLabel('Výrobek',{exact:true}).selectOption('F02');await stock.getByRole('button',{name:'Detail výrobku F01',exact:true}).click();await page.getByRole('dialog').waitFor();assert((await page.getByRole('dialog').locator('tbody tr').count())>0,'Stock detail overrides unrelated sales product/unit filter');assert.match(await page.getByRole('dialog').innerText(),/EUR \/ ST/);await page.getByRole('button',{name:'Zavřít detail'}).click();await page.getByLabel('Výrobek',{exact:true}).selectOption('');
 await page.getByLabel('Jednotka',{exact:true}).selectOption('ST');await page.getByLabel('Oblast',{exact:true}).selectOption('');await page.getByLabel('Kolo',{exact:true}).selectOption('');await saleFilters.click();

 await market.getByRole('button',{name:'Úplný trh'}).click();assert.equal(await page.getByLabel('Tržní období').inputValue(),older,'Full market retains its own period');assert.equal(await page.getByRole('table',{name:'Trh / Price market'}).count(),1);
 await page.getByRole('button',{name:'Během kola',exact:true}).click();await stock.getByRole('button',{name:'Úplný sklad'}).click();await page.getByRole('heading',{name:'Výrobky a zásoba',exact:true}).waitFor();assert.equal(await page.getByTestId('inventory-card').locator('tbody tr').count(),22);
 await page.getByRole('button',{name:'Podrobnosti',exact:true}).click();assert.equal(await page.getByRole('heading',{name:'Ceny a příspěvek podle kanálu a oblasti',exact:true}).count(),0);await page.getByRole('heading',{name:'Detail výrobku: realizované ceny a příspěvek'}).waitFor();await page.getByRole('heading',{name:'Tržby podle výrobků',exact:true}).waitFor();
 await page.getByRole('button',{name:'Během kola',exact:true}).click();await page.setViewportSize({width:1280,height:800});const stackedA=await stock.boundingBox(),stackedB=await market.boundingBox();assert(stackedB.y>=stackedA.y+stackedA.height,'Narrow laptop stacks tables');
 assert.deepEqual(errors,[]);console.log('PASS: 2240x1400 and 1493x800 notebook layout, sticky bounded tables/no horizontal overflow, charts directly below, two-series full-width finance, native KPI/stock parity, product price details, independent market period through polling/full view, full stock, preserved Details charts and 1280px stacking. No mobile tests or production writes.');
}finally{await browser.close();}
