# Během kola

Nový pohled je doplněk k Přehledu, Podrobnostem a samostatnému Trhu. Vychází z `feat/web-supabase` po PR #5 (`9f5f205`). Pouze web: není nutná SQL migrace ani aktualizace synchronizátoru; analytické funkce, zdrojové snímky a `.env` se nemění.

## Rozložení a data

- Čtyři kompaktní ukazatele: tržby, vykázaný zisk, hotovost, hodnota firmy. Zisk/hotovost/hodnota jsou za celou společnost z posledního finančního výkazu; tržby respektují vybraný rozsah prodejní analýzy.
- Aktuální sklad a trh vedle sebe od šířky **1440 CSS px**. Pod touto šířkou jsou pod sebou; rozhoduje skutečný viewport, nikoli fyzické rozlišení monitoru. Nový pohled využívá dostupnou šířku do 2240 CSS px s okrajem 12 px.
- Sdílené InventoryTable a MarketTable mají kompaktní režim. Sklad zachovává všechny materiálové typy, nuly a skutečné jednotky; jednotka/oblast/prodejní filtr neomezuje sklad. Dodatečné údaje, typ a lokace jsou v detailu. Rozpory lokací zůstávají označené.
- Trh je nezávislý na vlastních prodejích. Má samostatné období (výchozí nejnovější), vlastní produkt/oblast/kanál filtry a stejné seskupení a přesné ceny jako samostatný pohled. Vybrané tržní období přetrvá při aktualizaci i otevření úplného Trhu. Při změně hry/původu/společnosti se resetuje. Kód/název jsou v jedné buňce na začátku skupiny; u všech období je v ní navíc označen první řádek období.
- Obě tabulky mají vlastní svislý posuv s výškou `clamp(220px, 30vh, 340px)` a sticky záhlaví. Kompaktní sloupce mají minimum 620/680 px; horizontální posuv zůstává pro data, která se bez ztráty čitelnosti nevejdou. Zkušební data ho v požadovaných notebookových velikostech nepotřebují.
- Odkazy Úplný sklad / Úplný trh přepnou na původní pohled a posunou se k příslušné tabulce.
- Grafy ve dvou sloupcích: tržby v herním čase + oblasti; výrobky + marketing podle oblastí. Nakonec **jeden** finanční graf přes celou šířku, dvě řady hotovost a zisk. Původní grafy zůstávají. Finance nemají interpolovanou vstupní animaci, aby se aktuální hodnoty při obnovení zobrazily okamžitě a screenshot zachycoval skutečné řady.

Filtry prodejní analýzy jsou společné pro staré a nové pohledy; v Během kola jsou sbalené. Aktivní kolo/oblast/kanál/výrobek, společnost, měna a jednotka jsou vypsané. Default zůstává stejný jako v původním dashboardu (všechna dostupná kola); pohled tato data nevydává za výsledek samotného aktuálního kola. Aktuální sklad má vlastní čas snímku, trh vlastní kolo/období. Finanční graf používá skutečný herní čas finančních výkazů a nesmí se číst jako regionální výsledek.

## Detail výrobku

Plošná tabulka „Ceny a příspěvek podle kanálu a oblasti“ byla odstraněna z Podrobností. Místo ní jsou rozbalovací detaily výrobků se stejnými vypočtenými údaji a všemi dimenzemi: oblast, kanál, kolo/období, měna, jednotka, vlastní realizovaná cena, tržní cena, příspěvek %. V Během kola lze tento detail otevřít kliknutím na název ve skladu. Výběr stanoví konkrétní výrobek a skutečnou jednotku skladové položky; ostatní prodejní filtry se zachovají. Používá se stále stejná compute funkce, bez nových vzorců či konverze jednotek.

## Ověření

`npm --prefix web test`, `npm --prefix web run typecheck`, `npm --prefix web run build` a `node web/scripts/during-round-smoke.mjs` nad existujícím localhost demo stackem. Data pocházejí z původního Introduction sešitu. Browser test ověřuje:

- 2240 × 1400 a 1493 × 800 CSS px: dvě tabulky vedle sebe, využitou šířku, interní posuv a pevná záhlaví, žádný horizontální posuv stránky ani zkušebních tabulek, začátek grafů v prvním viewportu;
- KPI a zásoby vůči skutečnému exportu, známou vlastní cenu/příspěvek v detailu výrobku, jediný celoplošný finanční graf se dvěma řadami;
- oddělení regionálních/kolových/jednotkových filtrů prodejů od skladu/trhu a celofiremního zisku; chybějící prodej KG se nestává nulou;
- přetrvání tržního období při skutečném 15s refreshi a otevření úplného pohledu, úplný sklad, zachované grafy Podrobností a odstranění původní plošné tabulky;
- přechod tabulek pod sebe při 1280 × 800 CSS px.

**Mobil byl výslovně vyřazen uživatelem a není pro tento úkol upravován ani testován.** Browser test používá lokální demo a pouze čte data. Produkční Extended/OData a konkrétní Vercel deployment tím nejsou ověřené.

Screenshoty celého pohledu (v tabulkách je vidět posuvné okno, nikoli všechny řádky najednou):

[2240 × 1400 CSS px](during-round-2240.png) · [1493 × 800 CSS px](during-round-1493.png)
