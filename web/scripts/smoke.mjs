// Local integration smoke test. This file is never imported by the Next app.
import {chromium} from '@playwright/test';
import {readFileSync,existsSync} from 'node:fs';
import assert from 'node:assert/strict';
const credentials=JSON.parse(readFileSync(new URL('../../.local/demo.json',import.meta.url),'utf8'));
const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH??(existsSync('/usr/bin/chromium')?'/usr/bin/chromium':undefined),args:['--no-sandbox']});
const page=await browser.newPage({viewport:{width:1440,height:1050}});
const errors=[];page.on('pageerror',e=>errors.push(e.message));
try{
 const unauth=await page.request.get('http://127.0.0.1:3000/api/dashboard');assert.equal(unauth.status(),401);
 await page.goto('http://127.0.0.1:3000/');await page.getByRole('heading',{name:'Přihlášení týmu'}).waitFor();
 await page.getByLabel('E-mail').fill(credentials.email);await page.getByLabel('Heslo',{exact:true}).fill(credentials.password);
 await page.getByRole('button',{name:'Přihlásit se',exact:true}).click();await page.getByRole('heading',{name:'Přehled hry',exact:true}).waitFor();
 await page.getByText('3 973 037',{exact:false}).first().waitFor();
 const r=await page.request.get('http://127.0.0.1:3000/api/dashboard');assert.equal(r.status(),200);const data=await r.json();assert.equal(data.heads.find(h=>h.dataset==='Sales').snapshots.rows.length,186);
 await page.screenshot({path:new URL('../../.local/dashboard.png',import.meta.url).pathname,fullPage:true});
 await page.getByRole('button',{name:'Podrobnosti',exact:true}).click();await page.getByRole('heading',{name:'Ceny a příspěvek podle kanálu a oblasti'}).waitFor();
 await page.getByLabel('Kanál',{exact:true}).selectOption('12');await page.getByLabel('Výrobek',{exact:true}).selectOption('F01');
 await page.getByRole('button',{name:'Přehled',exact:true}).click();await page.getByRole('heading',{name:'Výrobky a zásoba'}).waitFor();
 await page.getByRole('button',{name:'Nastavení a zdroje',exact:true}).click();await page.getByRole('heading',{name:'Upozornění a interval služby'}).waitFor();
 const original=data.settings.stock_days;
 await page.getByText('Odhad zásoby pod (herní dny)',{exact:true}).locator('input').fill('4');await page.getByRole('button',{name:'Uložit nastavení'}).click();await page.getByRole('status').filter({hasText:'Nastavení uloženo'}).waitFor();
 await page.getByText('Odhad zásoby pod (herní dny)',{exact:true}).locator('input').fill(String(original));await page.getByRole('button',{name:'Uložit nastavení'}).click();
 await page.getByLabel('Historie: stav uložený do reálného času').fill('2000-01-01T12:00');await page.getByText('Historický stav dostupný při stažení do',{exact:false}).waitFor();
 await page.getByRole('button',{name:'Zpět na aktuální data'}).click();await page.getByText('Prodeje načteny',{exact:false}).waitFor();
 const csrf=await page.request.post('http://127.0.0.1:3000/api/dashboard',{data:{game:credentials.game,settings:data.settings},headers:{Origin:'https://external.invalid'}});assert.equal(csrf.status(),403);
 await page.getByRole('button',{name:'Odhlásit se',exact:true}).click();await page.getByRole('heading',{name:'Přihlášení týmu'}).waitFor();
 assert.deepEqual(errors,[]);
 console.log('PASS: real browser login, guarded API, actual imported dashboard, charts/rendering, product/channel filters, saved settings, history, CSRF rejection, logout; no browser exceptions.');
}finally{await browser.close();}
