# První spuštění: Supabase → Vercel → notebook

Tento postup je pro větev `feat/web-supabase`. Projekt zatím nemá připojené vaše cloudové účty. Root Directory Vercelu je **`web`**, nikoli kořen repozitáře. Notebook bude první hostitel synchronizátoru; původní OData klient je zachovaný.

## A. Založte Supabase

Na https://supabase.com/dashboard založte organizaci a projekt **erpsim-production**, vyberte evropský region a vygenerujte silné Database password. Heslo uschovejte ve správci hesel. Počkejte na vytvoření databáze. Stejně vytvořte **erpsim-staging** pro náhledy; soutěžní projekt se nesmí používat pro preview.

V Connect nebo Settings → API / API Keys najdete Project URL a klíče. Názvy položek se mohou mezi verzemi portálu lišit.

| Hodnota | Citlivost | Použití |
| --- | --- | --- |
| Project URL `https://…supabase.co` | Veřejná | `NEXT_PUBLIC_SUPABASE_URL` ve Vercelu, `SUPABASE_URL` v notebookovém `service/.env` |
| Publishable key / legacy anon | Veřejná | `NEXT_PUBLIC_SUPABASE_ANON_KEY` ve Vercelu; název proměnné zůstává stejný pro obě varianty |
| Legacy service_role **JWT** key | Tajná, obchází RLS | Pouze `SUPABASE_SERVICE_ROLE_KEY` v notebookovém `service/.env` |
| Database password | Tajná | Správce hesel; SQL Editor ji nevyžaduje v konfiguraci aplikace |
| Heslo Auth uživatele | Tajná | Vytvoření účtu v Supabase Auth; přihlašovací formulář webu |
| ERPsim login / heslo | Přihlašovací údaje | Jen `ERPSIM_ODATA_USER` / `ERPSIM_ODATA_PASSWORD` v notebookovém `service/.env` |
| Team UUID / Game UUID | Identifikátory, nikoli hesla | Místní poznámka, `ERPSIM_GAME_ID`; znalost UUID sama neuděluje přístup |
| `SUPABASE_DATA_ENV` | Veřejné označení konfigurace | `production` pro produkci, `staging` pro náhled |

Pro současný Python adaptér vyberte legacy **service_role JWT** v sekci legacy klíčů; nový `sb_secret_…` není tímto návodem ověřen. Service-role klíč ani ERPsim heslo nevkládejte do Vercelu/GitHubu/chatu. Veřejný klíč přístup nechrání sám; skutečná ochrana je Auth a RLS.

## B. Migrace a první člen týmu

V **erpsim-production → SQL Editor → New query** spusťte celý obsah postupně:

1. `supabase/migrations/202610100001_analytics.sql`
2. `supabase/migrations/202610100002_history.sql`

Každou migraci jen jednou. Po každém Run ověřte úspěch. Neignorujte hlášení o existujících tabulkách či chybě; zjistěte, zda už migrace proběhla, místo slepého opakování. V novém samostatném staging projektu proveďte totéž.

V **Authentication → nastavení registrací** vypněte veřejné přihlašování nových uživatelů (Allow new users to sign up). Ponechte povolený poskytovatel Email. V **Authentication → Users → Add user → Create new user** vytvořte vlastní účet aplikace, zadejte e-mail a silné heslo a účet potvrďte (Auto Confirm User / potvrzený e-mail). Tento účet je odlišný od přihlášení do portálu Supabase. Heslo zadáváte výhradně do portálu a přihlašovacího formuláře aplikace.

Otevřete `supabase/setup_first_team.sql`, nahraďte **jediný** text `DOPLNTE_EMAIL_UZIVATELE` e-mailem tohoto Auth uživatele a spusťte soubor v SQL Editoru. Heslo se do SQL nepíše. Skript vytvoří první tým, vaše členství `admin` a dvě prázdné hry. Uložte si výstup:

- `team_id` – tým;
- `game_id` s `purpose=trial` – zkušební Introduction export;
- `game_id` s `purpose=competition` – skutečná soutěž Manufacturing Extended.

Opakování tohoto setup skriptu nevytvoří další kopie ani neresetuje existující hry. Pro každý další herní běh/reset vytvořte **nové** UUID pomocí `create-game`; nevracejte nový běh do původní soutěžní hry. Samotný setup žádná zkušební data do soutěže neimportuje.

Spusťte `supabase/check_setup.sql`: všech osm tabulek musí mít `rls_enabled=true`, členství musí mít `admin` a musí existovat dvě oddělené hry. Před prvním importem je chybějící `last_success` očekávaný stav.

Další členy vytvořte v Auth stejným způsobem. Jejich UUID přidejte v SQL Editoru:

```sql
insert into public.team_members(team_id,user_id,role)
values ('SKUTECNE_TEAM_UUID','SKUTECNE_AUTH_USER_UUID','viewer')
on conflict(team_id,user_id) do update set role=excluded.role;
```

`viewer` čte, `editor` může měnit analytické nastavení. Admin je potřeba jen pro důvěryhodného správce. Registrace či existence Auth účtu sama členství nepřidá.

## C. Nasazení do Vercelu

Na https://vercel.com/signup založte/připojte svůj účet přes GitHub. Zvolte Add New → Project → Import Git Repository → `Zimek1234/Bizsimcup_analyze`. GitHub oprávnění Vercelu omezte na potřebný soukromý repozitář.

Ověřte toto nastavení:

| Položka | Hodnota |
| --- | --- |
| Framework | Next.js |
| Root Directory | **web** |
| Node.js | **24.x** |
| Install Command | `npm ci` |
| Build Command | `npm run build` |
| Production Branch | **feat/web-supabase** |

Při importu vyberte migrační větev, pokud dialog nabízí volbu větve. Pokud ji nenabízí, po vytvoření projektu nastavte větev v Settings → Git / Environments → Production → Branch Tracking (název sekce se může lišit), Root Directory v Build and Deployment a vytvořte deployment z reference **feat/web-supabase**. Případný první neúspěšný build z `main` není webová verze; neopravujte ho přepisováním `main`. V detailu výsledného deploymentu ověřte skutečnou Git větev a commit, nikoli jen projektový název.

Do Environment Variables pro **Production** vložte:

```dotenv
NEXT_PUBLIC_SUPABASE_URL=https://SKUTECNY_PRODUCTION_PROJEKT.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=VEREJNY_KLIC_Z_PRODUCTION
SUPABASE_DATA_ENV=production
```

Žádný service-role klíč, ERPsim účet ani heslo do Vercelu. Deploy musí skončit **Ready**. Zkopírujte stabilní doménu projektu z Domains (ne jednorázovou adresu konkrétního buildu). V Supabase production → Authentication → URL Configuration nastavte Site URL na tuto HTTPS adresu. Používáte-li pozvánky či obnovu hesla, nastavte jen konkrétní povolené návratové adresy. Základní ruční přihlášení používá heslo a není závislé na OAuth callbacku.

Pro **Preview** nastavte stejné proměnné, ale URL a veřejný klíč z **erpsim-staging**, `SUPABASE_DATA_ENV=staging`. Staging má vlastní migrace a vlastní Auth účty/členství. Pokud staging ještě nemáte, preview nepropojujte se soutěžní databází; bez staging konfigurace je náhled zablokován. Po změně proměnných proveďte nový deployment; nastavení nezmění už hotový build zpětně.

Ověřte v anonymním okně, že web nabízí pouze přihlášení. Přihlaste se Auth účtem z kroku B. Dvě hry se mohou zatím zobrazit bez dat – to není chyba. Nečlen týmu nesmí vidět hry ani data.

## D. Notebook Windows: první funkční Python synchronizátor

Použijte notebook s fungujícím ERPsim přístupem. Nainstalujte Git a Python 3.12. V příkazovém řádku **cmd**:

```bat
git clone https://github.com/Zimek1234/Bizsimcup_analyze.git
cd Bizsimcup_analyze
git switch feat/web-supabase
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-service.txt
copy service\.env.example service\.env
notepad service\.env
```

Pokud už pracovní kopii máte, neklonujte ji znovu a nezahazujte vlastní změny. Přepněte existující čistou kopii na migrační větev a aktualizujte ji `git pull --ff-only`. Pokud `service/.env` existuje, nepřepisujte ho kopírováním vzoru.

Do místního `service/.env` vyplňte skutečné hodnoty podle tabulky z A:

```dotenv
SUPABASE_URL=https://SKUTECNY_PRODUCTION_PROJEKT.supabase.co
SUPABASE_SERVICE_ROLE_KEY=TAJNY_LEGACY_SERVICE_ROLE_JWT
ERPSIM_GAME_ID=SKUTECNE_COMPETITION_GAME_UUID
ERPSIM_ODATA_URL=https://r75p.ucc.cloud/odata/792
ERPSIM_ODATA_USER=VAS_ERPSIM_UZIVATEL
ERPSIM_ODATA_PASSWORD="VAS_ERPSIM_HESLO"
```

Jde o vzor, nikoli funkční přístupové údaje. Heslo s mezerami/# dejte do uvozovek podle formátu `.env`; do uvozovek patří pouze samotná hodnota. Soubor je ignorovaný Gitem. Udržujte ho v nesdílené složce s přístupem pouze pro vás a správce. Vlastní nastavené proměnné procesu mají přednost před `.env`: používejte nové okno terminálu, pokud jste dříve exportovali jiné hodnoty. Tajné hodnoty nevypisujte pomocí `set` ani do chatu.

Nejprve ověřte cloudové ukládání bez OData pomocí zkušebního exportu:

```bat
import-data.bat --game SKUTECNE_TRIAL_GAME_UUID --file "samples\BIZ SIM data ze zkušebky.xlsx" --origin zkouska --dataset Workbook
```

Použijte **trial UUID** z B, nikoli competition. Výpis má ukázat úspěšné uložení podporovaných listů, včetně `Sales: 186` řádků. Na webu vyberte zkušební hru a `Import · zkouska`, společnost AA, EUR, ST a všechna kola. Kontrolní hodnoty:

| Ukazatel | Hodnota před zaokrouhlením |
| --- | ---: |
| Tržby | 3 973 037,20 EUR |
| Objednané množství | 626 554 ST |
| Vykázaný zisk | 2 148 215,54 EUR |
| Hotovost | 3 718 307,00 EUR |
| Hodnota firmy | 85 928 621,60 EUR |

Tím ověříte **notebookový import → váš Supabase → váš nasazený dashboard**, nikoli ještě živé OData.

Potom v témže terminálu:

```bat
test-odata.bat
start-sync.bat --once
```

První příkaz musí potvrdit připojení a schéma. Druhý musí skončit úspěšným počtem zdrojů, ideálně `N/N`; N závisí na dostupných podporovaných entitách, není napevno předepsaných 18. V případě chyby celé neúplné snímky nejsou publikovány a poslední úspěšná data zůstávají.

Pokud aktuální OData stále vrací Introduction, soutěžní hra aktualizaci odmítne. Použijte pro tento test **trial UUID**, případně vytvořte novou označenou zkušební hru; soutěžní UUID použijte až pro skutečné Extended. Pravidla načítá služba, nepřepisujte je ručně ani nepřejmenovávejte scénář v Excelu.

Po úspěšném `--once`:

1. V SQL Editoru znovu spusťte `supabase/check_setup.sql`. Správná hra musí mít `origin=odata`, `status=success`, počty řádků a aktuální `last_success`. Zkontrolujte také nejnovější chyby, samotný poslední úspěch neprokazuje úspěch posledního pokusu.
2. Ve webu vyberte tuto hru a **Živé OData**. Nastavení a zdroje musí odpovídat SQL výstupu. Zkontrolujte skutečný scénář z `Current_Game_Rules`, herní čas prodejů/financí a oddělení od reálného času stažení.
3. Teprve potom spusťte pravidelný běh:

```bat
start-sync.bat
```

Terminál nechte běžet. Přibližně po dalším cyklu se musí posunout poslední úspěch; prohlížeč čte uložená data každých 15 s. Pokud jsou aktuální metadata jen Intro, tím jste ověřili živý tok pro Intro, nikoli Extended. Výchozích 30 s je interval kandidát; pokud jeden cyklus trvá déle nebo server vrací omezení, zvyšte interval v nastavení hry. Počítač musí být zapnutý, připojený k síti a nesmí usnout. Pro ruční ukončení stiskněte Ctrl+C.

## E. Automatický běh notebooku a budoucí hosting

Po prvním úspěšném ručním běhu vytvořte úlohu v Plánovači úloh Windows:

- Program: skutečná úplná cesta k `.venv\Scripts\python.exe`.
- Argumenty: `scripts\worker_launcher.py sync`.
- Spustit v: skutečná kořenová složka `Bizsimcup_analyze`.
- Spouštět při přihlášení vašeho uživatele, při chybě restartovat, **nespouštět novou instanci**, když už jedna běží.

Nepoužívejte BAT instalující balíčky jako pravidelnou plánovanou úlohu. Balíčky jsou nainstalované z D. Kontrolujte stav zdrojů ve webu; stav Running úlohy není důkazem úspěšného načítání. Pro ruční test nebo import úlohu nejprve zastavte – zámek hry odmítá souběh. Web sám synchronizátor nespouští.

Přesun na trvalý Linux hosting s Dockerem je připraven v `deployment/compose.sync.yml`. Na **cílovém** hostingu je nejprve nutné ověřit `probe`, poté `sync --once`, potom pravidelný běh a čas posledního úspěchu ve webu. Bez tohoto testu není cloudové načítání ověřené. Notebookový synchronizátor neposuzujte jako spuštěný jen proto, že BAT existuje; jeho první skutečné spuštění a výsledky musí být ověřeny na notebooku.

## F. Další změny bez ZIPů

Po propojení Vercelu s GitHubem:

1. Zadáte změnu do Codexu nad tímto repozitářem; změna vznikne v nové větvi a projde testy.
2. Push nové větve / PR vytvoří Vercel preview se **staging** daty.
3. Po kontrole sloučíte změnu do **feat/web-supabase**, dokud je tato větev Production Branch.
4. Vercel z GitHubu nasadí novou verzi na stejnou stabilní projektovou adresu.

SQL migrace se aplikují zvlášť nejprve na staging, potom na produkci. Změna Python synchronizátoru vyžaduje `git pull --ff-only`, případnou instalaci změněných balíčků a restart notebookové úlohy/služby. Samotné nasazení webu Python proces neaktualizuje. `main` a `backup/streamlit-local` zůstávají zálohou původní aplikace.

## Stav před propojením účtů

Připraveno a lokálně ověřeno: web, obě migrace, původní importy a klient, Auth/RLS, idempotence, oddělení her, lease, scénářová pojistka, Docker a prohlížeč. Nový počáteční týmový SQL skript byl ověřen na lokálním Auth/PostgreSQL včetně opakování bez duplicit.

Dosud **neprovedeno ve vašich účtech**: založení Supabase/Vercel, aplikace migrací do vašich projektů, reálná týmová členství, Vercel deployment, první Windows import/sync a autentizované soutěžní Extended OData. Funkční stabilní adresa vznikne až po skutečném deploymentu Ready; vzorovou adresu nevydáváme za nasazený web.
