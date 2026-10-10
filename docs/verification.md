### Rozsah ověření

**Introduction – dodané exporty:** importy, základní prodejní/nákladové výpočty, pravidla, historie, zálohy a dashboard byly ověřeny na dodaném zkušebním sešitu a čtyřech reportech. Samostatná zkušební hra je označená v dashboardu.

**Extended – připravené funkce:** dynamický katalog a kanály z Current_Game_Rules i dostupných dat; cena a příspěvek po COST podle kanálu; marketing podle oblasti; Production, Production_Orders a BOM_Changes; parametry kapacity a přestaveb z pravidel; finanční vývoj. Data ani konstanty Introduction se nepřenášejí do soutěžní hry. Řízené testy více kanálů ověřují flexibilitu schématu, nikoli skutečná pravidla Extended.

**Lokálně dosud nutné ověřit:** Windows start.bat, skutečné OData přihlášení a oprávnění, aktuální Extended metadata a pravidla, všechny soutěžní kanály, případné investiční změny kapacity/přestaveb, skutečné změny receptur, úplnost a konzistence stránkování při běžící hře. Cloud proxy původně odmítl spojení před dosažením školního serveru; při závěrečném testu server odpověděl HTTP 401. Síťová cesta je ověřená, přihlášené čtení nikoli.

Na notebooku založte novou **soutěžní Extended** hru → Import a OData → Otestovat připojení → Načíst nyní. Zkontrolujte SCENARIO=Extended a skutečné parametry v Pravidla a zdroje. Test připojení ověřuje metadata a krátké čtení jedné entity; úplnost všech dat ověří až úspěšná aktualizace jednotlivých zdrojů. Pokud chybějí údaje o kapacitě nebo recepturách, dashboard je nedoplňuje odhadem.

Automatické ověření: 33 testů (pytest), včetně Streamlit AppTest: založení soutěžní hry, import zkušební hry do samostatného ID, výběr produktu, uložení upozornění, prohlížení historie a přepnutí zpět na prázdnou soutěžní hru. Testované prodejní součty: 626 554 ST, 3 973 037,20 EUR čisté hodnoty a 957 873,74 EUR COST ze sešitu; stejné číselné součty v prodejních reportech, jejichž měnu/jednotku nepředpokládáme. Empty BOM_Changes ověřuje import prázdné entity, ne skutečné změny receptur.

Doplňkový AppTest použil výslovně syntetická data v rámci známého schématu: kanály 10 a 14, produkt F99, parametr kapacity 45 000 a neprázdnou změnu BOM. Ověřil jejich zobrazení i srozumitelnou chybu připojení 401 bez změny uložených prodejů. Tato čísla jsou pouze testovací vstupy; nejsou součástí výchozí konfigurace ani odhadem soutěžního scénáře. Spuštěný Streamlit server v Linuxu prošel HTTP kontrolou root stránky a health endpointu (200/ok).
