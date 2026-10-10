# Datový kontrakt a průzkum podkladů

## Přiložené exporty

Čtyři samostatné XLSX mají jediný list `SAPUI5 Export`.

| Soubor | Počet datových řádků | Přesná hlavička |
|---|---:|---|
| inventory.xlsx | 22 | Location, Category, Material, Description, Stock, Reserved, Unit |
| price market.xlsx | 285 | Simulation Date, Material, Description, Area, Price, Quantity, Value |
| Sales report.xlsx | 186 | Round, Day, Area, Location, D. Channel, Material, Description, Net Price, Quantity, Net Value, Cost |
| Summary Sales order report.xlsx | 732 | Round, Day, Material, Description, Orders, Quantity, Net Value, Cost |

Inventory obsahuje lokace `02`, `88`, hotové výrobky, suroviny a obaly. Kódy výrobků jsou např. `AA-F01`. Tržní export obsahuje `F01`–`F06`, `F11`–`F16`, oblasti North/South/West a herní označení od `01/05` do `03/20`. Neobsahuje firmu, měnu, jednotku, vlastní náklady ani marketing. `Simulation Date` uchováváme jako text; nepřevádíme na kalendářní den, neodvozujeme bez potvrzení číslo periody. MarketExport je samostatný zdroj a jeho množství se nepřičítá k Sales ani k OData Market.

`AA-F01` a `F01` mají společný zobrazovací kód `F01`. Původní hodnota zůstává uložená. Organizace a lokace jsou samostatné dimenze; kód produktu se nepoužívá jako identita prodeje.

Prodejní reporty mají shodné součty: Quantity **626 554**, Net Value **3 973 037,20**, Cost **957 873,74**. Detail má 133 kombinací kolo/den/oblast/lokace/kanál/produkt/cena, ale 186 legitimních řádků. Souhrn má 732 řádků, z nich 102 s nenulovým množstvím; obsahuje i nulové řádky ve 4. kole. Detailní export nemá číslo objednávky a položky. Tyto dva exporty ani OData Sales se nikdy nesčítají dohromady. Měna, jednotka a skutečně dodané množství v samostatných reportech chybějí.

### Zkušební sešit

`BIZ SIM data ze zkušebky.xlsx` je **Introduction**, firma AA. Jeho Sales má 186 řádků se stejnými součty jako prodejní reporty, skutečnou měnu EUR, jednotku ST a dodané množství. Pravidla nejsou soutěžní konfigurace Extended.

Další ověřené počty: Marketing_Expenses 98, Current_Inventory 22, Inventory 1342, Current_Pricing_Conditions 12, Market 285, Financial_Postings 454, Company_Valuation 60, Current_Game_Rules 50, Production 50, Production_Orders 34, Purchase_Orders 20, Current_Inventory_KPI 12, Current_Suppliers_Prices 10, Independent_Requirements 8. BOM_Changes, Carbon_Emissions a Stock_Transfers jsou prázdné. Sheet1 a List1 nejsou datové entity. Importer zpracuje 18 pojmenovaných OData listů; prázdné entity jsou platné snímky.

## OData metadata

Přiložená metadata jsou OData v2, namespace `ZCDS_ODATA_SIMULATION_SRV`. Obsahují 18 EntitySet; všechny mají `creatable/updatable/deletable=false`. U 17 agregovaných entit je klíč `ID`, u Current_Game_Rules je `ROW_ID`. Většina pohledů je SAP `semantics=aggregate`. `ID` slouží k rozlišení řádků uvnitř úplného snímku, ale nikdy se na něm nestaví přičítání prodejů napříč staženími.

Podporovaná čtení:

| Entita | Význam a důležitá skutečná pole |
|---|---|
| Sales | SALES_ORGANIZATION, SALES_ORDER_NUMBER, LINE_ITEM, MATERIAL_NUMBER, AREA, DISTRIBUTION_CHANNEL, QUANTITY, QUANTITY_DELIVERED, NET_PRICE, NET_VALUE, COST, CURRENCY, UNIT, SIM_* |
| Marketing_Expenses | SALES_ORGANIZATION, MATERIAL_NUMBER, AREA, AMOUNT, CURRENCY, SIM_* |
| Current_Inventory | PLANT, STORAGE_LOCATION, MATERIAL_NUMBER, STOCK, RESTRICTED, UNIT; bez SIM_* |
| Inventory | INVENTORY_OPENING_BALANCE a SIM_*; počáteční zásoba herního dne, ne aktuální stav |
| Current_Pricing_Conditions | SALES_ORGANIZATION, MATERIAL_NUMBER, DISTRIBUTION_CHANNEL, DC_NAME, PRICE, CURRENCY; bez AREA a SIM_* |
| Market | COMPANY_CODE, SALES_ORGANIZATION, SIM_ROUND, SIM_PERIOD, MATERIAL_DESCRIPTION, DISTRIBUTION_CHANNEL, AREA, QUANTITY, AVERAGE_PRICE, NET_VALUE, UNIT, CURRENCY; **bez MATERIAL_NUMBER, SIM_DATE, SIM_STEP** |
| Financial_Postings | COMPANY_CODE, GL_ACCOUNT_NUMBER, GL_ACCOUNT_NAME, FS_LEVEL_1 až FS_LEVEL_4, DEBIT_CREDIT_INDICATOR, AMOUNT, CURRENCY, SIM_* |
| Company_Valuation | COMPANY_CODE, PROFIT, COMPANY_VALUATION, bankovní a rizikové ukazatele, CURRENCY, SIM_* |
| Current_Game_Rules | COMPANY_CODE, GAME, SCENARIO, CATEGORY, ELEMENT, DETAIL, VALUE |

Pro Extended navíc: Production (YIELD, UNIT, SIM_*), Production_Orders (PRODUCTION_ORDER, TARGET_QUANTITY, CONFIRMED_QUANTITY, SETUP_TIME, BEGIN_*/END_*), BOM_Changes (MATERIAL_NUMBER, COMPONENT, QUANTITY, UNIT, SIM_*). K importu a volitelnému čtení jsou dostupné všechny entity z metadat. Výchozí synchronizace zahrnuje pravidla, Sales, marketing, aktuální zásoby/ceny, Market, finance, Production, Production_Orders a BOM_Changes. Při každé aktualizaci se vždy nejprve čtou Current_Game_Rules; ostatní dostupnost určí živá metadata. Neexistující nebo nepřístupný zdroj je označen jako nedostupný, data nejsou nahrazena odhadem. Čteme plné kolekce bez `$select` a `$filter`, aby se nezměnila agregace. Před čtením kontrolujeme živé metadata. Při změně schématu nebo konfliktu identity se dávka odmítne místo nejasného přičítání.

## Identity, čas a historie

- Hra má lokální UUID a ručně zvolený název. Endpoint `/792` ani název scénáře nejsou jednoznačné ID herní relace. Reset simulace musí uživatel zaznamenat založením nové hry; automatická detekce by mohla zaměnit výpadek za reset.
- **Úplné snímky všech datových zdrojů:** dashboard bere právě poslední úplný úspěšný snímek daného zdroje pro danou hru; předchozí snímky slouží k historickému prohlížení, nikdy se nepřičítají. Při stránkování se stahuje celá kolekce, ne přírůstky.
- **Skutečná granularita Sales:** v zkušebním sešitu se opakuje `(AA, objednávka 535, položka 2)` se stejným produktem AA-F13, ale množstvími 3516 a 3482. Sloučení podle objednávky/položky by ztratilo prodej. Používáme skutečný klíč `ID` z metadat **uvnitř snímku**. Jeho přečíslování mezi staženími nezdvojnásobí součty, protože starý snímek se nesečte s novým. Konfliktní záznamy stejného ID v jedné kolekci se odmítnou.
- **SalesExport bez ID:** každý řádek snímku včetně násobnosti je zachován. Identické řádky mohou znamenat různé prodeje, proto je uvnitř souboru svévolně nemažeme. Znovu importovaný soubor vytvoří další snímek, dashboard zobrazuje jen jeden. Souhrnné a detailní reporty jsou alternativy, nikoli nezávislé prodeje.
- OData řádky používají při dostupnosti ID; u Current_Game_Rules se použije obsahová identita kategorie/pravidla/detailu. U exportů: MarketExport `(Simulation Date, Material, Area)`, SummarySalesExport `(Round, Day, Material)`, InventoryExport `(Location, Material, Unit)`. V rámci těchto agregovaných exportů se identické řádky zredukují, konfliktní hodnoty stejné identity se odmítnou.
- Herní `SIM_ROUND`, `SIM_STEP`, `SIM_DATE`, `SIM_PERIOD`, `SIM_ELAPSED_STEPS` zůstávají původními poli. `started_at`, `finished_at` jsou systémové UTC časy čtení. U aktuálních snímků bez herního času lze přidat ruční poznámku `game_time`, která není kalendářní čas ani odvozený údaj.
- Current_Inventory, InventoryExport, Current_Pricing_Conditions a Current_Game_Rules zobrazují poslední **úplný úspěšný snímek**. I prázdný úspěšný snímek je platný. Historické inventury různých dní se nesčítají.
- Pokud server omezí rozsah historie nebo uživatel importuje jen částečný soubor, aktuální pohled odpovídá právě tomuto rozsahu. Nezachováváme zmizelé řádky v aktuálním součtu a neodhadujeme přírůstky. Úplné starší snímky zůstávají pro obnovu/prohlížení. Aktuální autoritou je poslední úspěšně načtený úplný soubor/kolekce; starý report importovaný později tedy změní aktuální snímek. Pro práci se zkušebními nebo starými daty používejte samostatnou hru.
- Každá entita má vlastní atomickou aktualizaci. Přes všechny entity nelze garantovat stejný okamžik SAP při běžící hře; dashboard ukazuje stav a poslední úspěch každého zdroje. Živý snímek může při stránkování zachytit změny; konflikty odmítáme, ale služba negarantuje transakční snapshot.
- Stav k aktualizaci rekonstruuje známé revize k lokálnímu číslu dávky. Dříve dokončená data nejsou nahrazena později dokončeným starším souběžným čtením.

SQLite tabulky: `games`, `runs`, `observations` (neměnná historie), `facts` (poslední projekce). Dashboard čte poslední úplný snímek daného zdroje, nikdy součet snímků. `settings` ukládá účel hry a nastavení upozornění; žádná hesla. Každé spojení zapíná cizí klíče, transakce a timeout; databáze používá WAL. Záloha v UI používá SQLite backup API, včetně potvrzených dat ve WAL.

## Výpočty a chybějící data

Peněžní hodnoty se ukládají jako desetinné řetězce a sčítají s Decimal. Na float se převádí až pro grafy. Měny a jednotky se nesčítají dohromady. Vážená cena = součet NET_VALUE/Value dělený součtem QUANTITY/Quantity. Nulový jmenovatel dává neznámou hodnotu.

Sales `NET_VALUE − COST` je rozdíl vykázaných polí, bez automatické alokace marketingu, fixních nákladů, daní nebo inkasa. Pole COST je zobrazené jako vykázaná částka; nepřepočítává se z receptury. Marketing nemá v metadatech UNIT. Chybějící data nejsou nuly, Reserved není RESTRICTED, skladová lokace není oblast a distribuční kanál není oblast. Účetní zisk a ocenění se berou pouze ze samostatných vykázaných dat.

CSV: UTF-8 s BOM nebo Windows-1250, explicitní oddělovač a desetinná tečka/čárka. Čísla nemají oddělovače tisíců. Identifikátory jsou text, včetně vedoucích nul. Auto rozpozná čtyři dodané formáty a listy pojmenované podle OData entit; vícelistový import nejprve ověří všechny podporované listy. OData export vyžaduje explicitní entitu; přijímá skutečné technické názvy nebo jednoznačné SAP popisky z metadat, další sloupce odmítá. Měna a jednotka musí být uvedené v příslušných OData datech.

## Dynamické parametry Extended

Katalog produktů a kanálů vzniká z aktuálních řádků i Current_Game_Rules, ne z pevného seznamu. Aktuální scénář se zobrazuje z SCENARIO; soutěžní hra s jiným scénářem má upozornění. Číselné parametry Production / Daily Production Capacity a Production / Setup Time se zobrazí jen při jednoznačné číselné hodnotě příslušného pravidla firmy. Tyto skutečné názvy ELEMENT/DETAIL byly nalezeny ve zkušebním sešitu; jejich dostupnost a význam v Extended vyžaduje místní ověření. Neznámé/další parametry zůstávají v tabulce pravidel.

Kapacitu po investicích ani historické využití neodvozujeme z neověřených účtů nebo konstant Introduction. Z Production zobrazujeme YIELD po dnech, z Production_Orders cílové/potvrzené množství a vykázaný SETUP_TIME. Z BOM_Changes zobrazujeme komponenty a změny množství; bez počátečního kusovníku nesestavujeme úplnou recepturu ani nepočítáme její cenu. Finanční stavy Company_Valuation se vykreslují po herních dnech, nesčítají se jako tok.

Upozornění jsou uživatelské prahy, nikoli pravidla scénáře: nízká zásoba v zvolené jednotce, nízký příspěvek po COST podle produktu/oblasti/kanálu, marketingový limit ve zvolené měně za produkt/oblast/herní den, stáří OData aktualizací. Nastavení se ukládá pro každou hru zvlášť. Volitelné mapování NO/SO/WE musí uživatel zapnout; původní oblasti zůstávají v databázi.
