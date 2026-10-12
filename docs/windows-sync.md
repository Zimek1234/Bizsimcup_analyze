# Samostatný synchronizátor na Windows 11

Synchronizátor používá vlastní **`.venv-sync`**, nikoli `.venv` původního dashboardu. `requirements-service.txt` neodkazuje na `requirements.txt`: obsahuje pandas 3.0.1, openpyxl 3.1.5, requests 2.34.2, defusedxml 0.7.1 a python-dotenv 1.2.2. Pandas a NumPy potřebujeme pro současné čtečky/výpočty; pyarrow, Streamlit ani Plotly nejsou potřeba. `requirements.txt`, `start.bat` a původní aplikace zůstávají se svými dosavadními závislostmi.

Původní `requirements-service.txt` zahrnoval závislosti dashboardu. Streamlit instaloval pyarrow a pandas může přítomný pyarrow načíst i bez explicitního Arrow datového typu. Pouhé odinstalování pyarrow ve sdíleném prostředí nebylo trvalé řešení, protože spouštěcí BAT znovu instalovaly Streamlit. Nové spouštěče nikdy nevolají pip ani nevytvářejí prostředí; to dělá pouze `install-sync.bat`.

## Aktualizace existujícího notebooku

Zastavte běžící synchronizátor (Ctrl+C) a případnou úlohu v Plánovači úloh. Otevřete **cmd** v kořeni své pracovní kopie. Příkazy nečtou, nevypisují ani nepřepisují `service/.env`; nekopírujte přes něj `.env.example`. Nepoužívejte `git clean`, `git reset --hard` ani instalaci do starého sdíleného prostředí.

Po sloučení opravy do produkční větve:

```bat
git status --short
git fetch origin
git switch feat/web-supabase
git pull --ff-only
install-sync.bat 3.13
.venv-sync\Scripts\python.exe scripts\check_sync_install.py
test-odata.bat
start-sync.bat --once
```

Pokud chcete opravu testovat před sloučením, místo přepnutí/pull produkční větve použijte:

```bat
git fetch origin
git switch fix/windows-sync-dependencies
git pull --ff-only origin fix/windows-sync-dependencies
```

Při vlastních změnách sledovaných souborů (například ručně upravené requirements) je nejprve zálohujte mimo repozitář a vyřešte jejich zachování. Pokud Git přepnutí odmítne, zastavte; nevynucujte je. Ignorovaný `service/.env` při běžném přepnutí a pull zůstává na místě. Starou `.venv` není nutné mazat ani z ní odinstalovávat balíčky.

Instalátor požaduje **64bit Python 3.13**, dostupný přes `py -3.13`. Podporuje také `install-sync.bat 3.12`; kontroluje, že již existující `.venv-sync` odpovídá zvolené verzi. Pro změnu verze nebo již znečištěné `.venv-sync` ji po zastavení procesů přejmenujte na dosud neexistující záložní složku, například `.venv-sync-old`, a instalátor spusťte znovu. Záložní prostředí nedávejte do Gitu. `service/.env` je mimo virtuální prostředí a zůstává zachován.

Instalátor vyžaduje hotové wheel balíčky (`--only-binary=:all:`), provede kontrolu závislostí a importů. Kontrola importů nečte `.env`, nevolá OData a nezapisuje do databáze. Při přítomném pyarrow/Streamlitu/Plotly odmítne znečištěné prostředí. Není to obcházení Smart App Control: pandas a NumPy obsahují nativní moduly, které může Windows samostatně blokovat.

## Jak poznat úspěch

- `check_sync_install.py`: zpráva „Importy synchronizátoru OK“, Python 3.13 a pandas 3.0.1, bez Streamlitu a pyarrow.
- `test-odata.bat`: „OData připojení a schéma ověřeno“. Čte metadata a vzorek; do Supabase nezapisuje. Na konci čeká na klávesu.
- `start-sync.bat --once`: úspěšný počet `N/N` zdrojů (na dosavadním notebooku 18/18; skutečný počet závisí na metadatech). Použije stávající hru z `ERPSIM_GAME_ID` v zachovaném `.env` a uloží úplné snímky do vašeho Supabase.
- Na webu vyberte správnou hru a Živé OData, ověřte posunutou poslední úspěšnou aktualizaci a stav posledního pokusu. Úspěšný import balíčků sám neprokazuje úspěšnou synchronizaci.

Potom lze spustit `start-sync.bat` pro pravidelný běh. V Plánovači úloh změňte pouze cestu programu z `.venv\Scripts\python.exe` na **`.venv-sync\Scripts\python.exe`**. Argumenty `scripts\worker_launcher.py sync`, pracovní složka repozitáře a stávající `.env` zůstávají. Neplánujte instalátor a nespouštějte více synchronizátorů současně.

Pokud Smart App Control zablokuje další `.pyd`, zaznamenejte přesný název souboru a balíčku. Oprava nezaručuje důvěryhodnost všech nativních modulů na konkrétním notebooku; ochranu nevypínejte. Neposílejte obsah `.env`, hesla nebo klíče. Změna Pythonu na 3.12 může mít jiný wheel, ale bez místního testu není zárukou průchodu.

## Rozsah ověření

Kontroly v Linuxovém prostředí a dostupnost Windows wheels prokazují kompatibilitu závislostí a funkčnost čteček/výpočtů, nikoli průchod Windows Smart App Control. Nová CI matice připravuje testy Pythonu 3.12/3.13 na Linuxu i Windows; samotné přidání workflow neznamená úspěšný běh. Autentizované živé OData, váš Supabase a vaše Windows prostředí je nutné ověřit výše uvedenými místními příkazy. Dosavadních 18/18 na původním notebooku je výsledek uvedený uživatelem.
