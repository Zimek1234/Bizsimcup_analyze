# Ověření webové migrace (10. 10. 2026)

## Skutečně provedeno v cloud workspace

| Ověření | Výsledek |
| --- | --- |
| Původní aplikace / moduly / importy / `start.bat` | Obsah shodný se záložním commitem; původních 33 testů prochází |
| Instalace Python služby | Instalováno; `pip check` bez porušených závislostí |
| Web / lockfile | `npm ci`, TypeScript, 13 analytických testů a produkční `next build` prošly |
| Databáze a API | Skutečný PostgreSQL 17.6, GoTrue 2.196.0, PostgREST 14.17; obě migrace aplikovány lokálně |
| Skutečný import | Dodaný Introduction sešit načten nezměněnou čtečkou, všech 18 podporovaných listů uloženo přes Supabase REST/RPC |
| Opakovaný import | Stejný snímek znovu použit; 186 prodejních řádků zůstalo 186, součet beze změny |
| Oddělení her a původů | Zkouška a jiná hra oddělené; Excel a OData samostatné projekce bez součtu |
| Auth / RLS | Skutečné přihlášení heslem; anonym a nečlen nečtou data; viewer nezmění nastavení; editor ho změní; uživatel nespustí worker RPC ani nevytvoří hru |
| Zámek | Druhý worker odmítnut; po expiraci převzetí s vyšší generací; opožděný původní worker nemůže publikovat |
| Výpadek / částečné čtení | Řízená chyba metadat i čtení zachovala poslední úspěšný snímek; chyba zaznamenána |
| Python cyklus | Proveden celý `sync --once` proti lokální DB s původním sešitem jako řízenou náhradou OData; 18/18 entit; prázdná pravidla zablokovala další publikování |
| Historie | Opakované snímky propojené s pokusy; výběr stavu do času; RLS platí i pro historickou funkci |
| Prohlížeč Chromium | Přihlášení, skutečné KPI, grafy, produkt/kanál filtry, změna nastavení, historie, CSRF odmítnutí a odhlášení; bez JavaScript výjimek |
| Preview ochrana | Server s production označením v preview zobrazil blokaci; preview POST nastavení vrátil 403 |
| Živý OData test bez účtu | `probe` vrátil HTTP 401 se srozumitelnou zprávou; tajné údaje se nevypisují |
| Docker služby | Obraz sestaven s ověřováním TLS a autoritativním CA bundle prostředí; běh pod běžným uživatelem, import skutečného sešitu a součet ověřen |
| Opakovatelnost setupu | Spuštění lokálního stacku podruhé zachovalo databázi a migrace |

Lokální stack je testovací kombinace skutečných Supabase komponent, nikoli váš hostovaný Supabase projekt. Docker build v tomto cloud workspace potřebuje jeho egress proxy a důvěryhodný CA bundle; helper `scripts/cloud_container_build.py` je předává podporovaným způsobem, bez vypnutí TLS a bez zapsání tajných údajů do obrazu.

## Porovnání na totožném Introduction exportu

Výpočty původních `erpsim.analytics.views` používají Decimal; web agreguje tyto projekce pomocí decimal.js. Technické ID se používá v rámci celého snímku, nikoli k inkrementálnímu sčítání stahování. Dva řádky stejné objednávky/položky s různým množstvím se neztratí.

| Ukazatel | Původní aplikace a nový web |
| --- | ---: |
| Objednané množství | 626 554 ST |
| NET_VALUE | 3 973 037,20 EUR |
| COST | 957 873,74 EUR |
| Příspěvek před režijními náklady | 3 015 163,46 EUR |
| Nejnovější skutečný PROFIT | 2 148 215,54 EUR |
| Bankovní hotovost | 3 718 307,00 EUR |
| Hodnota firmy | 85 928 621,60 EUR |

Stejné množství/tržby/náklady byly ověřeny také původními testy na jednotlivých prodejních exportech. Nové testy dokazují nepárování jiného regionu, kanálu, měny, jednotky, kola a období; shodný popis různých výrobků také zneplatní tržní srovnání. Umělé rozšíření produktu a kanálu testuje obecnost filtru, **nepředstavuje ověření skutečného Extended**.

## Co musí být ještě ověřeno na vašich zařízeních a účtech

- Založení **production a staging Supabase**; aplikace migrací, reální členové týmu, RLS a obnovování přihlášení proti skutečnému projektu.
- **Vercel GitHub integrace, stabilní URL, preview nasazení a oddělení staging**. Projekty podle vašeho sdělení nejsou založené. Hodnota `SUPABASE_DATA_ENV=staging` je kontrola konfigurace; sama neprokazuje použití jiné databáze.
- Oprávněný přístup do **Manufacturing Extended**, pravidla skutečného scénáře, všechna období/kanály/produkty, výrobní a finanční hodnoty, receptury, časové jednotky. Introduction se do soutěžní hry nepředvyplňuje.
- Interval ~30 s na skutečné velikosti a rychlosti OData. Test lokálního exportu neprokazuje dobu vzdáleného čtení ani serverové limity.
- Přístup do OData ze **zvoleného trvalého hostingu**; takový hosting ani ERPsim účet tu není dostupný. Windows připojení již podle vás funguje, zachovaný klient používá stejný způsob.
- Nové **BAT spouštěče ve Windows**. Byly připraveny, odpovídající Python/Node příkazy ověřeny v Linuxu; samotné BAT nebylo možné zde spustit.
- Velikost produkčního dashboardu a latence: první verze posílá členům týmu úplné projekce vybraných zdrojů. Otestujte skutečný Extended objem proti limitům paměti a odpovědi Vercelu (Functions mají omezenou velikost odpovědi). Pro větší data bude potřebná stránkovaná diagnostika a serverové souhrny; neověřené objemy nejsou označeny za podporované.

Reprodukce testů a nasazení: [web-setup.md](web-setup.md). GitHub Actions workflow je připravený; jeho běh na GitHubu se nedá zaměňovat za zde provedené lokální kontroly. Automatické cloudové nasazování začne fungovat po založení a propojení Vercel projektu.
