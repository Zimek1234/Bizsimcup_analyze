// Local authenticated fixture only; no production writes or mobile checks.
import {chromium} from '@playwright/test';
import {readFileSync,existsSync} from 'node:fs';
import assert from 'node:assert/strict';
const root=new URL('../../',import.meta.url),c=JSON.parse(readFileSync(new URL('.local/demo.json',root),'utf8'));
const browser=await chromium.launch({executablePath:existsSync('/usr/bin/chromium')?'/usr/bin/chromium':undefined,args:['--no-sandbox']});
const page=await browser.newPage({viewport:{width:2240,height:1400},locale:'cs-CZ'}),errors=[];page.on('pageerror',e=>errors.push(e.message));
try{
 await page.goto('http://127.0.0.1:3000');await page.getByLabel('E-mail').fill(c.email);await page.getByLabel('Heslo',{exact:true}).fill(c.password);await page.getByRole('button',{name:'Přihlásit se',exact:true}).click();await page.getByRole('heading',{name:'Přehled hry',exact:true}).waitFor();
 await page.getByRole('button',{name:'Grafy a analýza',exact:true}).click();const view=page.getByTestId('analysis-view');await view.waitFor();
 const actual=await (await page.request.get('http://127.0.0.1:3000/api/dashboard')).json();const expected=new Set(actual.heads.find(h=>h.dataset==='Sales').snapshots.views.filter(r=>r.organization==='AA'&&r.currency==='EUR'&&r.unit==='ST').map(r=>r.product)).size;assert.equal(await view.getByRole('table',{name:'Porovnání výrobků',exact:true}).locator('tbody tr').count(),expected);
 await page.getByLabel('Výrobek',{exact:true}).selectOption('F01');await page.getByRole('heading',{name:'Vývoj vybraného výrobku ve vlastní firmě'}).waitFor();assert.equal(await view.getByRole('table',{name:'Porovnání výrobků',exact:true}).locator('tbody tr').count(),1);
 
 assert((await view.getByLabel('Tržní období',{exact:true}).locator('option').count())>1);
 await page.getByLabel('Výrobek',{exact:true}).selectOption('');
 const verify=view.getByRole('table',{name:'Ověření nastavení Extended',exact:true});assert.match(await verify.innerText(),/Introduction/);assert.match(await verify.innerText(),/Ve zdroji neuvedeno/);assert.equal(await verify.getByText('Shoda',{exact:true}).count(),0);
 await page.getByText('Porovnání investic',{exact:true}).click();const capacity=page.getByLabel('Současná kapacita (kusů / den)',{exact:false}),days=page.getByLabel('Zbývající herní dny',{exact:false});assert.equal(await capacity.inputValue(),'24000','Never initialize Extended from Introduction 16000');
 assert.equal(await page.getByRole('button',{name:/Převzít současnou kapacitu/}).count(),0);
 await days.fill('10');await capacity.fill('25000');await page.getByLabel('Cílová kapacita (kusů / den)',{exact:false}).fill('26000');await page.getByLabel('Využitý a prodaný podíl (0–1)',{exact:false}).fill('0.5');await page.getByLabel('Očekávaný příspěvek / prodaný kus (EUR)',{exact:false}).fill('2');
 assert.match(await capacity.locator('..').innerText(),/Ruční zadání/);
 await page.getByRole('button',{name:'Použít manuálové ceny do ručního scénáře'}).click();assert.equal(await page.getByLabel('Investice do kapacity (EUR)',{exact:false}).inputValue(),'1000000');
 for(const [width,height] of [[2240,1400],[1493,800]]){await page.setViewportSize({width,height});await page.evaluate(()=>scrollTo(0,0));assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);const boxes=await view.locator(':scope > .grid > section, :scope > .grid > div').evaluateAll(els=>els.slice(0,2).map(el=>({x:el.getBoundingClientRect().x,y:el.getBoundingClientRect().y})));assert.equal(boxes.length,2);assert(Math.abs(boxes[0].y-boxes[1].y)<2&&boxes[1].x>boxes[0].x);await page.mouse.move(1,1);await page.screenshot({path:new URL(`web/docs/analysis-${width}.png`,root).pathname,fullPage:true});}
 await page.getByLabel('Výrobek',{exact:true}).selectOption('F01');await page.mouse.move(1,1);await page.screenshot({path:new URL('web/docs/analysis-product-1493.png',root).pathname,fullPage:true});await page.getByLabel('Výrobek',{exact:true}).selectOption('');
 // Read-only synthetic HTTP response verifies future Extended comparison and explicit adoption.
 const data=await (await page.request.get('http://127.0.0.1:3000/api/dashboard')).json();
 const mock={...data,heads:data.heads.map(h=>h.dataset==='Current_Game_Rules'?{...h,snapshots:{...h.snapshots,rows:h.snapshots.rows.map(r=>({...r,SCENARIO:'Manufacturing Extended',...(r.DETAIL==='Daily Production Capacity'?{VALUE:'30000'}:{})}))}}:h)};
 await page.route('**/api/dashboard*',route=>route.fulfill({json:mock}));await page.waitForResponse(r=>r.url().includes('/api/dashboard'),{timeout:20000});
 assert.equal(await capacity.inputValue(),'25000','New rules must never overwrite manual parameter');await page.getByRole('button',{name:/Převzít současnou kapacitu/}).click();assert.equal(await capacity.inputValue(),'30000');assert.match(await capacity.locator('..').innerText(),/Aktuální hra Extended/);
 await page.getByRole('button',{name:'Během kola',exact:true}).click();assert.equal(await page.getByTestId('inventory-card').locator('tbody tr').count(),22);await page.getByRole('button',{name:'Trh / Price market',exact:true}).click();await page.getByRole('table',{name:'Trh / Price market'}).waitFor();
 assert.deepEqual(errors,[]);console.log('PASS: authenticated Introduction analysis, weighted product table, market independent of product filter, 2240/1493 CSS layouts/screenshots, manual Extended provenance/defaults, no automatic overwrite on future rules, explicit game adoption, preserved stock/market. Mock Extended response only in browser test, no production writes.');
}finally{await browser.close();}
