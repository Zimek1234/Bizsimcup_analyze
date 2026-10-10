# ERPsim Manufacturing · lokální analytika

Analytika pro **Manufacturing Extended** s oddělenou zkušební Introduction. První verze pro Windows: Python, Streamlit, Plotly a SQLite. Ze SAP provádí pouze HTTPS GET. Importy a historie se zapisují do **lokální** databáze. Neposílá změny cen, marketingu ani výrobních příkazů.

## Spuštění ve Windows

1. Nainstalujte **64bit Python 3.12 nebo 3.13** z python.org. Při instalaci povolte Python Launcher nebo přidání Pythonu do PATH.
2. Rozbalte celou aplikaci do zapisovatelné složky, např. `Dokumenty\ERPsim`. Dvojklik na **start.bat** vytvoří `.venv`, nainstaluje závislosti a otevře dashboard v prohlížeči. První instalace vyžaduje internet na PyPI; další spuštění neměnící requirements použijí již nainstalované balíčky.
3. Pro soutěž založte novou hru s účelem **Soutěžní · Manufacturing Extended**. Hry spravujte v postranním panelu. V záložce **Import a OData** importujte XLSX/CSV nebo použijte vzorové exporty. Tlačítko **Založit a načíst zkušební hru** vytvoří oddělenou Introduction a načte dodaný vícelistový sešit. Nejsou vydávány za živá data.
4. Pro OData nejprve použijte **Otestovat připojení** (metadata + krátké GET jedné entity, bez importu). Pro OData ponechte `https://r75p.ucc.cloud/odata/792`, zadejte případné přihlášení lokálně, vyberte entity a stiskněte **Načíst nyní**. Volba pravidelného čtení obnovuje data každých 30–3600 sekund, dokud je aplikace otevřená. Nemusíte ručně obnovovat stránku. Čtení běží i při zvolené jiné záložce. Při zobrazení historického stavu je pozastavené.
5. Pro **každou novou simulaci/reset založte novou hru**, i když URL i tým zůstávají stejné. Před čtením ověřte aktivní hru. Filtr organizace odděluje firmy/týmy, pokud zdroj obsahuje více organizací.

Při aktualizaci se vždy načtou skutečná Current_Game_Rules. Ověřte **SCENARIO=Extended**; počet produktů, kanály, kapacita, náklady ani délka hry se nepřenášejí z Introduction. Další dostupné entity lze vybrat z živé služby.

Aplikace naslouchá pouze na `127.0.0.1:8501`. Okno terminálu musí zůstat otevřené. Ukončení: Ctrl+C. Pokud je port obsazený, ukončete předchozí instanci. Pro ruční start s jiným portem použijte `.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --server.port 8502 --browser.gatherUsageStats false`.

SQLite je v `data/analytics.sqlite`. Nepatří do Gitu. V záložce Historie stáhněte bezpečnou zálohu všech her; pro obnovení aplikaci ukončete, uchovejte původní data a nahraďte databázi zálohou (odstraňte staré odpovídající soubory `-wal`/`-shm` teprve po ukončení všech instancí). Databázi nesdílejte přes síťový disk. Importovaný soubor se neukládá jako soubor, hodnoty se ukládají do historie.

## Data a analytika

- Vlastní prodeje, dodané množství, vykázané náklady COST a příspěvek po produktech/oblastech/**kanálech**, interaktivní grafy a dynamické filtry.
- Poslední úplný snímek zásob, skladová lokace, jednotka, Reserved odděleně od RESTRICTED.
- Tržní souhrny a vážené ceny oddělené od vlastních prodejů; vlastní cenové podmínky po distribučních kanálech.
- Marketing po produktech, oblastech a herních dnech. Účetní data a ocenění bez vymyšleného rozdělení na produkty.
- Výroba YIELD, výrobní příkazy, SETUP_TIME a parametry kapacity z pravidel; změny komponent BOM_Changes pouze při dostupnosti skutečných dat.
- Nastavitelná upozornění na zásoby, příspěvek po nákladech, denní marketing a stáří aktualizací. Uložení pro každou hru.
- Poslední úspěšná aktualizace celkově i pro jednotlivé zdroje, chyby pokusů, historický stav k dávce a záloha SQLite.

Samostatné prodejní exporty a Sales ve zkušebním sešitu mají shodné součty. Dashboard mezi prodejními zdroji přepíná a **nikdy je nesčítá**. Úplné snímky předchozích stažení také nikdy nepřičítá. Zkušební sešit obsahuje marketing a finance, ale jeho pravidla jsou Introduction a nepoužívají se pro novou soutěžní hru. Dashboard chybějící metriky nenahrazuje nulami či odhady. Peněžní součty jsou oddělené podle měny, množství podle jednotky. Filtry se aplikují pouze na dimenze skutečně dostupné v daném zdroji.

Přesné nalezené hlavičky, granularita a omezení: [docs/data-contract.md](docs/data-contract.md). Pravidla načtená i z obrázkových snímků prezentace: [docs/rules.md](docs/rules.md). Metadata jsou uložena v `resources/metadata.xml`. Pro vlastní CSV použijte technické názvy nebo jednoznačné popisky SAP; zvolte správný oddělovač, kódování a desetinný oddělovač. Čísla bez oddělovačů tisíců. Nejednoznačná data aplikace odmítne ještě před změnou analytiky.

## Připojení a výpadky

Přihlášení je pouze v paměti aktuální Streamlit relace. Volitelně lze nastavit `ERPSIM_ODATA_URL`, `ERPSIM_ODATA_USER`, `ERPSIM_ODATA_PASSWORD`, `ERPSIM_DB_PATH` v lokálních proměnných prostředí. Hesla nezapisujte do repozitáře, CSV ani do start.bat. Používá se standardní HTTP Basic autentizace přes ověřené HTTPS, pokud služba přihlášení vyžaduje; automatické SSO/SAML přihlášení tato verze neumí. 401/403 vyžaduje ověření přístupu, 3xx může znamenat přihlašovací portál. TLS se nevypíná; případný školní certifikát nastavte podporovanou cestou `REQUESTS_CA_BUNDLE`.

Úplná kolekce se načte včetně OData v2 `d.results`/`__next`. Timeout, vadná stránka, změna schématu, cyklus nebo konflikt identity odmítne danou dávku. Poslední úspěšná data zůstanou dostupná; další interval provede nový pokus. Nezapisují se částečné kolekce ani text serverové odpovědi do chybových logů. Přihlašovací údaje se neposílají na cizí odkazy stránkování a automatické přesměrování je vypnuté.

Živý server při závěrečném testu odpověděl **HTTP 401**: síťová cesta funguje, ale bez lokálních přihlašovacích údajů nebylo čtení dat ověřeno. První pokus před povolením domény blokoval cloud proxy (403). Testy stránkování/výpadků běží s řízenými odpověďmi a neprokazují skutečná data Extended. Přesný rozsah: [docs/verification.md](docs/verification.md).

## Vývoj a ověření

Moduly: `loaders.py` (XLSX/CSV), `schema.py` (ověřené názvy/typy/identity), `odata.py` (GET a stránkování), `sync.py` (aktualizace), `storage.py` (SQLite historie), `analytics.py` (čisté výpočty), `rules.py` (pravidla), `alerts.py` (upozornění), `dashboard.py` (UI). `bootstrap.py` a `start.bat` řeší lokální spuštění.

```bat
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe -m pytest -q
```

Linux/cloud: `python3 -m venv .venv`, `.venv/bin/python -m pip install -r requirements-dev.txt`, `.venv/bin/python -m pytest -q`, `.venv/bin/python -m streamlit run app.py --server.address 127.0.0.1 --server.headless true --browser.gatherUsageStats false`.

Windows launcher je určený pro Windows, testy aplikace se spouštějí v Linux cloud prostředí. Před distribucí širšímu týmu ověřte první spuštění a skutečné OData přihlášení také na cílovém Windows.
