### Pravidla podle prezentace BIZ SIM CUP 2026

Podklad: dodaná prezentace, 21 stran. Část pravidel je vložená jako obrázky; byly přečteny i tyto stránky. Prezentace popisuje Introduction i Extended. Konkrétní běžící scénář může mít jiné parametry; ověřte je v `Current_Game_Rules` a u organizátora.

- **Bez zásob není prodej** (str. 7). Preference zákazníků se během jedné hry nemění. Neodvozujeme konkrétní regionální preference bez dat.
- Vítězí firma s nejvyšší hodnotou společnosti na konci simulace (str. 7). Zásoby na konci hry se oceňují nákladovou cenou; prezentace doporučuje neprodávat pod náklady.
- **North, South, West jsou geografické oblasti** (str. 5). Kanály DC10, DC12, DC14 jsou typy odběratelů, nikoli oblasti.
- DC10 nakupuje 1kg balení, DC12 obě velikosti, DC14 500g (str. 9). Kanály mají rozdílnou citlivost na cenu, reklamu a různé platební lhůty. Čistá hodnota objednávky tedy není okamžité inkaso.
- Extended: výchozí kapacita 24 000 kusů/den a přenastavení 8 hodin (str. 10, 12). Kapacita = zůstatek účtu 110000 / 1000 (str. 14). Čas přenastavení = 2 + 6 × 250 000 / (250 000 + zůstatek účtu 478000) (str. 18).
- Str. 10 uvádí kapacity skladování: hotové výrobky 250 000 krabic, suroviny 250 000 kg, obaly 750 000 kusů. Příplatky za dalších 50 000 jednotek/den: 500 €, 1 000 €, 100 €. Fixní náklady placené po pěti dnech zahrnují práci 20 000 €, výrobní režii 15 000 €, S,G&A 40 000 €, odpis budovy 1 250 € a odpis vybavení 50 000 €; poslední závisí na investicích.
- Hodnota firmy (str. 6) vychází z anualizovaného zisku a součtu tržní a firemní rizikové sazby. Aplikace zobrazuje vykázané `COMPANY_VALUATION`, nepřepočítává je z neúplných tržeb ani nezaměňuje příspěvek `NET_VALUE − COST` za účetní `PROFIT`.
- Kusovník se může měnit (str. 20–21). Náklady nelze spolehlivě dopočítat ze statického receptu a tržní ceny.

Tato verze nemění ceny, marketing, výrobu, kusovníky ani investice v SAP. Přehled pravidel je vysvětlení podkladů, nikoli pokyn k provádění transakcí z prezentace.
