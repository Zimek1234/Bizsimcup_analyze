# ERPsim web

Next.js + TypeScript, Tailwind/shadcn komponenty a Recharts. Data čte pouze přihlášený člen týmu přes Supabase Auth a RLS. ERPsim připojení běží v samostatné Python službě, nikoli ve Vercelu.

- [První založení účtů, migrace a propojení](../docs/first-deployment.md)
- [Spuštění Windows, Supabase a Vercel](../docs/web-setup.md)
- [Provedené testy a hranice ověření Introduction/Extended](../docs/web-verification.md)
- [Architektura migrace](../docs/web-migration.md)

Původní aplikace zůstává na `main` a `backup/streamlit-local`. Cloudové projekty ještě nejsou založené; nic není označeno za nasazené.
