# Migrace do webové aplikace

Původní aplikace: větev `main` a záloha `backup/streamlit-local`, commit `713dbe68aa7c3d96e984e7478f2af720add8e21a`. Původní Python moduly, importy a OData klient se nemění. Nová implementace vzniká ve větvi `feat/web-supabase`.

1. Supabase ukládá celé snímky zvlášť podle hry, entity a původu (Excel / OData), historii pokusů, pravidla a nastavení. Žádné sčítání předchozích stažení ani alternativních exportů.
2. Samostatný Python synchronizátor používá původní ODataClient a normalizaci. Zámek hry s obnovovanou platností a kontrolou vlastníka při zápisu zabraňuje souběžnému publikování dat. Import používá původní XLSX/CSV načítání.
3. Next.js server ověřuje přihlášení přes Supabase Auth a čte data s uživatelským tokenem. RLS omezuje data na členy týmu. V prohlížeči ani ve Vercelu není ERPsim heslo ani service-role klíč.
4. Česká hlavní obrazovka používá nejvýše pět KPI a tři upozornění. PROFIT je skutečný vykázaný účetní zisk; příspěvek NET_VALUE−COST má jiný název. Odhady jsou výslovně označené a nepoužívají neověřené časové převody.
5. Preview Vercelu musí mít samostatnou staging databázi a čte data bez zápisu; produkce má vlastní konfiguraci. Synchronizátor neběží ve Vercel Function ani pro jednotlivé návštěvníky.

Externí cloudové Supabase/Vercel přístupy zatím v prostředí nejsou. Do jejich poskytnutí se ověřuje lokální databáze/API a vlastní exporty; skutečné cloudové ukládání a nasazení nejsou prokázané.
