# Web ERPsim: spuštění a nasazení

Nová aplikace je ve větvi `feat/web-supabase`. Původní Streamlit je beze změny na `main` a `backup/streamlit-local`; jeho `start.bat`, SQLite, čtečky, výpočty a původní testy zůstávají v projektu.

## Co je nyní hotové

Český Next.js přehled, přihlášení Supabase Auth, týmová RLS, uložené snímky a historie, nastavení upozornění, původní XLSX/CSV import a samostatný Python synchronizátor. Lokální ověření používá skutečný sešit **Introduction**. Nejsou založené vaše Supabase/Vercel projekty; veřejný web ani cloudový synchronizátor zatím nejsou nasazené. Testovací lokální účet není účet pro cloud.

## 1. Založení Supabase

1. Založte dva projekty Supabase: **production** pro soutěž a **staging** pro náhledy. Heslo databáze ani tajný klíč neposílejte do chatu.
2. V každém projektu spusťte v SQL Editoru soubory `supabase/migrations/202610100001_analytics.sql` a potom `202610100002_history.sql`, každý právě jednou. Případně použijte Supabase CLI a `supabase db push`; připojte se ke správnému projektu. Migrace tvoří tabulky a oprávnění, Auth schéma spravuje Supabase.
3. V Authentication vypněte veřejné registrace. Vytvořte účty členů týmu přes administrační rozhraní (nebo odešlete pozvánky). Nastavte Site URL podle finální adresy webu; při pozvánkách nastavte jen konkrétní povolené návratové adresy. První verze používá přihlášení e-mailem a heslem, bez veřejné registrace/reset formuláře; obnovu řeší správce Auth.
4. Zkopírujte UUID uživatelů z Auth a v SQL Editoru vytvořte tým a členství:

```sql
insert into public.teams(name) values ('Náš tým') returning id;
-- Nahraďte UUID skutečnými hodnotami, zbytek příkazu neměňte.
insert into public.team_members(team_id,user_id,role)
values ('TEAM_UUID','AUTH_USER_UUID','admin');
-- Další členové: viewer = čtení, editor/admin = změna analytického nastavení.
```

Samotné přihlášení neopravňuje číst týmová data. Přidávání uživatelů, týmů a her je pouze administrátorská operace. Service-role klíč obchází RLS: patří výhradně na důvěryhodný notebook/službu správce, nikdy do webu, Vercelu, GitHubu či sdíleného souboru.

## 2. Notebook Windows: Python služba a import

Nainstalujte Python 3.12 a Git. Naklonujte repozitář a přepněte větev:

```bat
git clone https://github.com/Zimek1234/Bizsimcup_analyze.git
cd Bizsimcup_analyze
git switch feat/web-supabase
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-service.txt
```

Zkopírujte `service/.env.example` do `service/.env`. Vyplňte na notebooku `SUPABASE_URL`, **service-role JWT key** (Supabase Settings → API → legacy service_role; adapter posílá tento klíč také jako Bearer), uživatele a heslo ERPsim. Soubor je ignorovaný Gitem. Chraňte ho přístupovými právy Windows; přístup k service-role opravňuje ke všem projektovým datům. Hodnoty z prostředí mají přednost před souborem. Hesla se při spuštění nevypisují. Nepoužívejte cloudový tajný klíč pro Vercel.

Vytvořte **dvě různé hry**; UUID týmu získáte v předchozím kroku:

```bat
.venv\Scripts\python.exe scripts\worker_launcher.py create-game --team TEAM_UUID --name "Zkouška Introduction" --purpose trial
.venv\Scripts\python.exe scripts\worker_launcher.py create-game --team TEAM_UUID --name "Soutěž Manufacturing Extended" --purpose competition
```

Do `ERPSIM_GAME_ID` nastavte UUID příslušné hry. Při každém novém herním běhu vytvořte novou hru a přepněte ID služby. Metadata `GAME`/`SCENARIO` nejsou jedinečným identifikátorem soutěžní relace: systém reset hry podle stejné URL nedokáže spolehlivě poznat. Nesmíte pokračovat ve starém ID při restartu soutěže.

Import zkoušky (musí cílit na UUID zkušební hry; pravidla Introduction jsou pro soutěžní UUID odmítnuta před importem sešitu):

```bat
import-data.bat --game TRIAL_GAME_UUID --file "samples\BIZ SIM data ze zkušebky.xlsx" --origin zkouska --dataset Workbook
```

Jednotlivé exporty mají přesné ověřené hlavičky. Pro ně zvolte `Auto`, případně konkrétní entitu:

```bat
import-data.bat --game TRIAL_GAME_UUID --file "samples\Sales report.xlsx" --origin salesexport --dataset Auto
import-data.bat --game TRIAL_GAME_UUID --file "prodeje.csv" --origin zaloha --dataset Sales --separator ";" --decimal "," --encoding utf-8-sig
```

`--origin` je stabilní označení úplného zdroje; při opakovaném importu stejného zdroje použijte stejné označení. Sešit validuje všechny podporované listy před prvním zápisem; každý list se následně publikuje atomicky. Při chybě ukládání mezi listy mohou být části sešitu z různých importů, proto přehled ukazuje čas každé entity. Import souborů za účelem přidávání dílčích transakcí není podporován: zdroje jsou **úplné snímky**, nový úspěšný snímek nahrazuje předchozí, i když má méně nebo žádné řádky.

Test a spuštění OData:

```bat
test-odata.bat
start-sync.bat --once
start-sync.bat
```

Test čte metadata a zkušební řádek, nic neukládá do ERPsim ani Supabase. OData URL je konfigurovatelná v `ERPSIM_ODATA_URL`; původní funkční OData klient se neměnil. Používá pouze GET, ověřuje TLS, bezpečně stránkuje, má timeouty a opakování. Služba nejprve načte skutečná `Current_Game_Rules`, potom všechny dostupné **podporované** entity z ověřených metadat. Nové neznámé entity/sloupce vyžadují nové mapování; nic se nevymýšlí. Volitelně omezte rozsah `--datasets Sales Current_Inventory ...` (pravidla jsou vždy zahrnuta).

Výchozí interval je 30 s a mění se v webovém nastavení hry. Po dokončení celého čtení začne další cyklus; cykly se nepřekrývají. Při výpadku se prodlevy prodlužují až na 5 minut. Po výpadku Supabase služba bezpečně skončí; Docker/Plánovač úloh ji může restartovat. Poslední úspěšná data zůstávají. Zámek se obnovuje každých 15 s, expiruje po 120 s a při každém publikování se kontroluje vlastník i generace. Import do téže hry vyžaduje nejprve zastavit službu; import se jinak odmítne. Pro různé hry mohou běžet různé služby.

**Vhodnost 30 s nebyla ověřena na Extended.** Na notebooku spusťte `--once`, zkontrolujte délku cyklu, počty řádků a chyby. Pokud cyklus trvá přes 30 s nebo služba omezuje přístup, zvyšte interval a omezte entity. Na novém hostingu zopakujte `probe` a `sync --once` s oprávněným přístupem; úspěch na notebooku neprokazuje přístup z datacentra.

Pro automatický Windows běh použijte Plánovač úloh: program `.venv\Scripts\python.exe`, argumenty `scripts\worker_launcher.py sync`, pracovní složka kořen projektu; vypněte souběžné instance, nastavte restart po chybě a použijte důvěryhodný účet, který smí číst `service/.env`. `start-sync.bat` je vhodný pro ruční spuštění; při automatickém běhu se balíčky instalují předem.

## 3. Vercel z GitHubu

1. Vytvořte Vercel projekt → Import Git Repository → tento repozitář. Framework **Next.js**, Root Directory **web**, Node.js **24.x**. Konfigurace sestavení je v `web/vercel.json` a závislosti v lockfilu.
2. Dokud probíhá migrace, nastavte Production Branch `feat/web-supabase`. `main` zůstává původní aplikací. Později po přijetí migrace můžete větev sloučit do `main` a změnit Production Branch na `main`.
3. Pro **Production** nastavte `NEXT_PUBLIC_SUPABASE_URL` a `NEXT_PUBLIC_SUPABASE_ANON_KEY` z produkčního Supabase, `SUPABASE_DATA_ENV=production`. Ve webu je jen veřejný anon/publishable klíč; uživatelský token a RLS rozhodují o přístupu.
4. Pro **Preview** nastavte tyto tři proměnné ze **samostatného staging projektu**, `SUPABASE_DATA_ENV=staging`. Nikdy nevkládejte produkční URL/klíč do Preview. Aplikace blokuje preview bez staging označení a zakazuje změny nastavení, ale nemůže sama zjistit, zda jste skutečně použili jiný projekt. Oddělení projektů musíte nastavit v účtu.
5. Vercel po úspěšném nasazení poskytne stabilní produkční adresu `...vercel.app` a preview adresy pro ostatní větve/PR. Adresu nelze určit před založením projektu. Ověřte přihlášení, členství týmu, outsider přístup, nastavení a dostupnost importovaných dat na skutečné produkční adrese. Doporučena je i ochrana preview na úrovni Vercelu.

Web neobsahuje synchronizační smyčku na serveru. Prohlížeč každých 15 s čte uložená data; počet návštěvníků neovlivňuje OData. Při výpadku čtení ponechá poslední přehled se srozumitelnou zprávou. Pro lokální web použijte Node.js 24 LTS, zkopírujte `web/.env.example` do `web/.env.local`, vyplňte veřejné hodnoty a spusťte `start-web.bat`. Nové BAT soubory nebyly spuštěny ve Windows v tomto Linux prostředí.

## 4. Trvale běžící Python služba

Na Linux VPS s Dockerem nebo hostingu podporujícím trvalé kontejnery použijte:

```sh
docker compose -f deployment/compose.sync.yml up -d --build
```

Soubor `service/.env` zůstává jen na hostingu. Container běží pod běžným uživatelem; tajné soubory se neposílají do Docker buildu. Je možné místo souboru injektovat stejné proměnné přes bezpečné prostředí hostingu. Spusťte nejprve jednorázový test:

```sh
docker compose -f deployment/compose.sync.yml run --rm sync python scripts/worker_launcher.py probe
docker compose -f deployment/compose.sync.yml run --rm sync python scripts/worker_launcher.py sync --once
```

Ověření z cílového hostingu je **neprovedené**: není založený hosting ani dostupný oprávněný ERPsim účet v tomto prostředí. Cloudový Docker obraz je připravený; notebook zůstává podporovanou variantou. Dbejte na síťové povolení `r75p.ucc.cloud` i URL Supabase a běh právě jedné služby pro každé UUID hry. Nevkládejte nekonečný proces do Vercel Function.

## 5. Co znamenají údaje

- Tržby = `NET_VALUE`, množství = objednané `QUANTITY`. Dodávky a tempo zásob používají `QUANTITY_DELIVERED`; soubor bez dodávek nemá odhad tempa.
- Skutečný vykázaný zisk = nejnovější `Company_Valuation.PROFIT`; hotovost a hodnota firmy jsou stavové údaje stejného finančního záznamu. Nejde o součet vykázaných zisků ani `NET_VALUE−COST`. Finanční stav se nemění filtrem výrobku/oblasti/kanálu/kola.
- Peníze, množství a společnost se vybírají odděleně. Export bez měny/jednotky nese označení „Měna/Jednotka neuvedena“; měna se nikdy nedoplňuje ze sousedního zdroje.
- Aktuální zásoba je za všechny sklady společnosti a není dostupná po prodejních geografických oblastech. Tempo a odhad jsou za celou společnost a výrobek, bez odhadu budoucí poptávky. Rozpracováno = kladný rozdíl cílového a potvrzeného množství; nedokazuje termín dokončení ani okamžité započtení do zásoby.
- Cenové srovnání používá přesnou shodu popisu, geografické oblasti, kanálu, měny, jednotky, kola a období. `Market` nemá číslo materiálu; `Current_Pricing_Conditions` nemá oblast. Odlišné názvy oblastí (např. NO versus North) se automaticky nepřekládají. Chybějící rozměr znemožní srovnání.
- Historické snímky jsou oddělené od aktuálních projekcí. Volba historie je podle reálného času publikování; herní čas zůstává v datech. Data různých původů se nikdy automaticky nesčítají.
- Pravidla, produkty, kanály, kapacita, přestavby a náklady pocházejí z konkrétní hry. Časové jednotky a využití kapacity se bez doložené časové základny nedopočítávají. Žádný údaj o délce Introduction hry se nepřenáší do Extended.
- Prázdný prodejní filtr bez řádků zobrazí nedostupné součty; chybějící finance nejsou nula. Prázdná dostupná entita změn receptur znamená žádné zaznamenané změny; chybějící entita znamená nedostupná data.

## 6. Ověření a aktualizace bez ZIPu

Podrobný stav testů je v `docs/web-verification.md`. Pro vývoj:

```sh
python -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt -r requirements-service.txt
.venv/bin/python -m pytest -q
PYTHONPATH=. .venv/bin/python scripts/export_parity.py
npm --prefix web ci
npm --prefix web test
npm --prefix web run typecheck
npm --prefix web run build
```

Lokální integrační prostředí pro vývojáře s Dockerem:

```sh
.venv/bin/python scripts/local_stack.py
.venv/bin/python scripts/test_integration.py
.venv/bin/python scripts/seed_local.py
npm --prefix web start
# V druhém terminálu: (cd web && node scripts/smoke.mjs)
```

Používá skutečný PostgreSQL, Supabase GoTrue Auth a PostgREST, nikoli hostovaný Supabase projekt nebo plnou samohostovanou platformu. Generuje pouze lokální testovací klíče do ignorované `.local/` a `web/.env.local`; při existující webové konfiguraci ji nesmí přepsat. Heslo testovacího účtu je pouze v lokálním `.local/demo.json`. `smoke.mjs` očekává dostupný Chromium (`CHROMIUM_PATH`, v cloud workspace `/usr/bin/chromium`). Bez Dockeru můžete vyvíjet proti samostatnému staging projektu; nikdy nepoužívejte soutěžní databázi pro testy. Lokální prostředí zastavíte `docker compose --env-file .local/stack.env -f deployment/local/compose.yml down`; `down -v` smaže jen tuto testovací databázi.

Po propojení Vercelu zadávejte změny do Codexu nad tímto repozitářem: „Vytvoř samostatnou větev, změň …, otestuj a pushni.“ Vercel připraví preview ze staging dat. Po kontrole sloučíte větev do Production Branch; GitHub integrace nasadí novou verzi na stejnou adresu. SQL migrace aplikujte zvlášť nejdřív na staging; Python službu aktualizujte pomocí `git pull` a restartu/rebuildu. Nasazení webu samo neprovádí migrace a neaktualizuje běžící Python synchronizátor. Záloha původní aplikace zůstává v `backup/streamlit-local`.
