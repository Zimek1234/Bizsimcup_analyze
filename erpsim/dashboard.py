"""Streamlit presentation and controls. Data handling lives in independent modules."""
from datetime import datetime
from pathlib import Path
import os
import time
import pandas as pd
import plotly.express as px
import streamlit as st
from .analytics import views, select, aggregate, numeric_frame
from .loaders import read_file, read_workbook, sheet_names
from .odata import ODataClient, DEFAULT_URL
from .schema import ENTITIES, EXPORTS, SYNC_ENTITIES, DEFAULT_SYNC, ROOT, product_code
from .storage import Store
from .sync import refresh
from .alerts import DEFAULTS, evaluate
from .odata import ODataError
from .rules import catalogue, parameter
from decimal import Decimal

LABELS = {"product": "Produkt", "description": "Popis", "area": "Oblast", "organization": "Organizace",
          "currency": "Měna", "unit": "Jednotka", "round": "Kolo", "step": "Den", "period": "Perioda",
          "game_date": "Herní datum", "elapsed_steps": "Uplynulé herní kroky", "location": "Skladová lokace",
          "channel": "Distribuční kanál", "ordered": "Objednané / vykázané množství", "delivered": "Dodáno",
          "revenue": "Čistá hodnota", "cost": "COST", "contribution": "NET_VALUE − COST",
          "price": "Cena", "quantity": "Množství", "weighted_price": "Hodnota / množství",
          "margin_pct": "Příspěvek (%)", "stock": "Zásoba", "reserved": "Reserved (export)",
          "restricted": "RESTRICTED (OData)", "category": "Kategorie", "marketing": "Marketing",
          "order": "Objednávka", "line": "Položka", "orders": "Počet objednávek",
          "target": "Plánované množství", "confirmed": "Potvrzené množství", "setup": "Vykázaný SETUP_TIME",
          "production_order": "Výrobní příkaz", "component": "Komponenta", "begin_round": "Počáteční kolo",
          "begin_step": "Počáteční den", "end_round": "Koncové kolo", "end_step": "Koncový den"}
SOURCE_LABELS = {"Sales": "Úplný snímek OData / sešitu Sales", "SalesExport": "Detailní Sales report.xlsx",
                 "SummarySalesExport": "Summary Sales order report.xlsx", "InventoryExport": "inventory.xlsx",
                 "Current_Inventory": "OData aktuální zásoby", "Inventory": "OData počáteční zásoby dne"}


def table(frame):
    if isinstance(frame, list):
        frame = pd.DataFrame(frame)
    st.dataframe(numeric_frame(frame).rename(columns=LABELS), hide_index=True, width="stretch")


def chart(frame, x, y, title, color=None):
    if frame.empty:
        return
    frame = numeric_frame(frame)
    if frame[y].notna().any():
        st.plotly_chart(px.bar(frame, x=x, y=y, color=color, barmode="group", title=title, labels=LABELS),
                        width="stretch")


def formatted_time(value):
    # UTC is explicit; game date never goes through datetime parsing.
    return datetime.fromisoformat(value).strftime("%d.%m.%Y %H:%M:%S UTC") if value else "Dosud žádná"


def render():
    st.set_page_config(page_title="ERPsim · Analytika", page_icon="📊", layout="wide")
    if "pending_game_select" in st.session_state:
        st.session_state["game_select"] = st.session_state.pop("pending_game_select")
    store = Store(os.environ.get("ERPSIM_DB_PATH", str(ROOT / "data/analytics.sqlite")))
    st.title("ERPsim Manufacturing")
    st.caption("Lokální analytika • vlastní prodeje a trh odděleně • pouze čtení ze SAP")
    with st.sidebar:
        st.header("Hra")
        with st.expander("Založit novou hru", expanded=not store.games()):
            with st.form("new_game"):
                name = st.text_input("Název hry", placeholder="Školní kolo · tým AA · 10. 10.")
                purpose = st.selectbox("Účel hry", ["Soutěžní · Manufacturing Extended", "Testovací / jiná"])
                if st.form_submit_button("Založit hru"):
                    try:
                        new_id = store.create_game(name)
                        store.save_settings(new_id, {"purpose": "competition" if purpose.startswith("Soutěžní") else "test"})
                        st.session_state["game_select"] = new_id
                        st.rerun()
                    except ValueError as e:
                        st.error(str(e))
        games = store.games()
        if not games:
            st.info("Založte hru před importem. Nová simulace patří vždy do nové hry.")
            st.stop()
        names = {g["id"]: g["name"] for g in games}
        game = st.selectbox("Aktivní hra", list(names), format_func=names.get, key="game_select")
        st.caption(f"ID: {game}")
        st.warning("Při restartu simulace založte novou hru. Stejné číselné objednávky v jiné hře mají vlastní historii.")
    runs = store.runs(game)
    successful = [r for r in runs if r["status"] == "success"]
    with st.sidebar:
        choices = [None] + [r["id"] for r in successful]
        as_of = st.selectbox("Stav k aktualizaci", choices, format_func=lambda x: "Aktuální" if x is None else
                            f"#{x} · {next(r['dataset'] for r in successful if r['id']==x)}", key=f"asof_{game}")
    data = {d: views(d, store.records(game, d, as_of)) for d in (*EXPORTS, *SYNC_ENTITIES)
            if d not in {"Financial_Postings", "Company_Valuation", "Current_Game_Rules"}}
    settings = DEFAULTS | store.settings(game)
    rules = store.records(game, "Current_Game_Rules", as_of)
    catalog = catalogue(rules)
    scenario = ", ".join(catalog["scenarios"]) if rules else "Neznámý · Current_Game_Rules dosud nenačteny"
    st.caption(f"Scénář podle pravidel aktivní hry: {scenario}")
    if settings.get("purpose") == "trial":
        st.warning("ZKUŠEBNÍ INTRODUCTION · ověřování importů a základních výpočtů. Tato hra není soutěžní Extended.")
    elif settings.get("purpose") == "competition" and rules and any(s != "Extended" for s in catalog["scenarios"]):
        st.warning("Hra je označená jako soutěžní Extended, ale načtená pravidla uvádějí jiný scénář. Ověřte URL a aktivní hru.")
    if settings["area_mapping"]:
        for rows in data.values():
            for row in rows:
                row["area"] = {"NO": "North", "SO": "South", "WE": "West"}.get(row["area"], row["area"])
    with st.sidebar:
        sale_sources = [d for d in ("Sales", "SalesExport", "SummarySalesExport") if data[d]]
        sale_source = st.selectbox("Zdroj vlastních prodejů", sale_sources or ["Sales"], format_func=SOURCE_LABELS.get)
        stock_sources = [d for d in ("Current_Inventory", "InventoryExport", "Inventory") if data[d]]
        stock_source = st.selectbox("Zdroj zásob", stock_sources or ["Current_Inventory"], format_func=SOURCE_LABELS.get)
        st.caption("Prodejní zdroje jsou alternativní pohledy. Nesčítáme je navzájem.")
    options = {field: sorted({r[field] for rows in data.values() for r in rows})
               for field in ("organization", "product", "area", "round", "step", "channel", "currency", "unit")}
    options["product"] = sorted(set(options["product"]) | set(catalog["products"]))
    options["channel"] = sorted(set(options["channel"]) | set(catalog["channels"]))
    with st.sidebar:
        st.header("Filtry")
        filters = {f: st.multiselect(LABELS[f], vals, key=f"filter_{game}_{f}") for f, vals in options.items()}
        st.caption("Prázdný výběr = všechny hodnoty. Organizace a oblast se u některých exportů nevyskytují.")
        # Snapshot sources without these dimensions must not be filtered out as if they had an area/date.
    def filtered(dataset):
        applicable = {k: v for k, v in filters.items() if k not in {
            "InventoryExport": {"organization", "area", "round", "currency"},
            "Current_Inventory": {"area", "round", "currency"},
            "Inventory": {"area", "currency"},
            "Current_Pricing_Conditions": {"area", "round", "unit"},
            "MarketExport": {"organization", "round", "currency", "unit"},
            "SalesExport": {"organization", "currency", "unit"},
            "SummarySalesExport": {"organization", "currency", "unit", "area", "channel"},
        }.get(dataset, set())}
        # A missing dimension must not pretend to be a measured value.
        applicable = {k: v for k, v in applicable.items()
                      if any(r.get(k) != "Neuvedeno" for r in data[dataset])}
        return select(data[dataset], applicable)

    def sales_rows():
        return filtered(sale_source)

    def stock_rows():
        rows = filtered(stock_source)
        if stock_source == "Inventory" and rows:
            def time_key(row):
                return (int(row["round"]), int(row["step"]))
            latest = max(time_key(r) for r in rows)
            rows = [r for r in rows if time_key(r) == latest]
        return rows

    last = max(successful, key=lambda r: r["finished_at"]) if successful else None
    st.info("Poslední úspěšná aktualizace (libovolný zdroj): " + formatted_time(last["finished_at"] if last else None))
    if as_of is not None:
        st.warning(f"Prohlížíte historii k aktualizaci #{as_of}. Automatické čtení je v historickém pohledu pozastavené.")
    latest_by_dataset = {}
    for r in runs:
        latest_by_dataset.setdefault(r["dataset"], r)
    failures = [r for r in latest_by_dataset.values() if r["status"] != "success"]
    for r in failures:
        st.warning(f"{r['dataset']}: {r['error'] or 'Aktualizace probíhá nebo byla přerušena.'} · "
                   "Dashboard používá poslední úplná úspěšná data.")

    with st.expander("Nastavení upozornění a oblastí", expanded=False):
        settings_controls(store, game, settings)
    st.subheader("Přehled aktivní hry")
    st.caption(f"Prodeje: {SOURCE_LABELS[sale_source]} · Zásoby: {SOURCE_LABELS[stock_source]} · Filtry platí pro celý dashboard.")
    rows = sales_rows()
    if rows:
        totals = aggregate(rows, ["currency", "unit"], ["ordered", "revenue", "cost", "contribution"])
        for item in totals.to_dict("records"):
            cols = st.columns(4)
            cols[0].metric(f"Množství · {item['unit']}", f"{item['ordered']:,.0f}".replace(",", " "))
            for col, field, label in zip(cols[1:], ["revenue", "cost", "contribution"], ["Čistá hodnota", "Vykázané náklady", "Příspěvek před režií"]):
                col.metric(f"{label} · {item['currency']}", f"{item[field]:,.2f}".replace(",", " "))
    else:
        st.info("Pro vybraný prodejní zdroj a filtry zatím nejsou data.")
    alerts = evaluate(sales_rows(), stock_rows(), filtered("Marketing_Expenses"), runs, settings)
    if alerts:
        st.warning(f"Aktivních upozornění: {len(alerts)}")
        table(alerts)
    elif settings["enabled"]:
        st.caption("Žádné upozornění v dostupných datech pro vybrané filtry. Chybějící zdroje tím nejsou ověřené.")
    tabs = st.tabs(["Prodeje", "Zásoby", "Trh a ceny", "Marketing", "Náklady a finance",
                    "Import a OData", "Historie", "Pravidla a zdroje", "Výroba a receptury"])
    with tabs[0]:
        st.subheader("Vlastní prodeje")
        rows = sales_rows()
        if not rows:
            st.info("Importujte některý prodejní export nebo načtěte OData Sales.")
        else:
            summary = aggregate(rows, ["organization", "currency", "unit"],
                                ["ordered", "delivered", "revenue", "cost", "contribution"])
            table(summary)
            group = aggregate(rows, ["organization", "product", "area", "channel", "currency", "unit"],
                              ["ordered", "delivered", "revenue", "cost", "contribution"])
            # Aggregate selected channels for area plots; retain channel in the separate channel analysis.
            area_group = aggregate(rows, ["organization", "product", "area", "currency", "unit"],
                                   ["ordered", "delivered", "revenue", "cost", "contribution"])
            for (org, currency, unit), part in area_group.groupby(["organization", "currency", "unit"], dropna=False):
                chart(part, "product", "revenue", f"Čistá hodnota objednávek · {org} · {currency} · {unit}", "area")
                chart(part, "product", "delivered", f"Dodané množství · {org} · {unit}", "area")
            table(group)
            st.write("Ceny a příspěvek podle distribučního kanálu")
            channel_group = aggregate(rows, ["organization", "product", "channel", "currency", "unit"],
                                      ["ordered", "revenue", "cost", "contribution"])
            table(channel_group)
            for (org, currency, unit), part in channel_group.groupby(["organization", "currency", "unit"], dropna=False):
                chart(part, "product", "weighted_price", f"Realizovaná cena (hodnota/množství) · {org} · {currency} · {unit}", "channel")
                chart(part, "product", "margin_pct", f"Příspěvek po COST (%) · {org} · {currency}", "channel")
            trend = aggregate(rows, ["organization", "round", "step", "currency", "unit"], ["revenue", "delivered"])
            st.write("Vývoj podle herního kola a dne")
            table(trend)
            for (org, currency, unit), part in trend.groupby(["organization", "currency", "unit"], dropna=False):
                part = part.copy()
                part["time_sort"] = part["round"].astype(int) * 10000 + part["step"].astype(int)
                part = part.sort_values("time_sort")
                part["Herní čas"] = part["round"] + "/" + part["step"]
                st.plotly_chart(px.line(numeric_frame(part), x="Herní čas", y="revenue", markers=True,
                                        title=f"Vývoj čisté hodnoty · {org} · {currency}", labels=LABELS), width="stretch")
            with st.expander("Položky objednávek"):
                table(rows)
        st.caption("QUANTITY = objednáno, QUANTITY_DELIVERED = skutečně dodáno. NET_VALUE je hodnota objednávky; "
                   "nejde automaticky o inkaso nebo výnos dodané části. NET_VALUE − COST je příspěvek před ostatními náklady, ne účetní zisk.")
        if sale_source != "Sales":
            st.caption("Tento export neobsahuje číslo objednávky, měnu, jednotku ani dodané množství. "
                       "Zobrazuje se pouze poslední celý importovaný snímek. Detailní a souhrnný export se nikdy nesčítají.")
    with tabs[1]:
        st.subheader("Zásoby")
        sources = [d for d in ("InventoryExport", "Current_Inventory", "Inventory") if data[d]]
        if not sources:
            st.info("Importujte inventory.xlsx nebo načtěte Current_Inventory.")
        else:
            source = stock_source
            rows = stock_rows()
            measures = ["stock"] + (["reserved"] if source == "InventoryExport" else ["restricted"] if source == "Current_Inventory" else [])
            group = aggregate(rows, ["organization", "product", "location", "unit"], measures)
            table(group)
            for (org, unit), part in group.groupby(["organization", "unit"], dropna=False):
                chart(part, "product", "stock", f"Zásoby · {org} · {unit}", "location")
            exhausted = [r for r in rows if r["stock"] == 0]
            if exhausted:
                st.warning(f"{len(exhausted)} skladových položek má nulovou zásobu. Pravidlo hry: bez zásob není prodej.")
            with st.expander("Detail zásob"):
                table(rows)
            st.caption("Inventory = historický počáteční stav dne. Current_Inventory a XLSX = poslední úplný snímek; "
                       "snímky se nesčítají. Reserved a RESTRICTED mají odlišný význam. Lokace 02/88 nejsou oblasti North/South/West. "
                       "Herní čas snímku bez SIM_* je neznámý, pokud jej nezadáte při načtení. "
                       "U Inventory zobrazujeme nejnovější vybraný herní den, nikoli součet dní.")
    with tabs[2]:
        st.subheader("Trh")
        market_sources = [d for d in ("MarketExport", "Market") if data[d]]
        if not market_sources:
            st.info("Importujte price market.xlsx nebo načtěte Market.")
        else:
            source = st.selectbox("Zdroj trhu", market_sources)
            rows = filtered(source)
            keys = ["organization", "product", "area", "game_date", "round", "period", "currency", "unit"]
            group = aggregate(rows, keys, ["quantity", "revenue"])
            table(group)
            for (org, currency, unit), part in group.groupby(["organization", "currency", "unit"], dropna=False):
                # Price/Quantity/Value are period aggregates; no cumulative-download summing.
                summary = aggregate([r for r in rows if (r["organization"], r["currency"], r["unit"]) == (org, currency, unit)],
                                    ["product", "area", "currency", "unit"], ["quantity", "revenue"])
                chart(summary, "product", "weighted_price", f"Hodnota / množství trhu · {org} · {currency} · {unit}", "area")
            st.caption("Tržní souhrny nejsou vlastní prodeje. V XLSX není měna ani jednotka: aplikace je nedoplňuje. "
                       "Simulation Date (např. 01/05) je herní označení, ne kalendářní datum. "
                       "Cena souhrnu = součet Value / součet Quantity, nikoli prostý průměr Price.")
        st.subheader("Vlastní cenové podmínky")
        prices = filtered("Current_Pricing_Conditions")
        if prices:
            table(prices)
            for (org, currency), part in pd.DataFrame(prices).groupby(["organization", "currency"], dropna=False):
                chart(part, "product", "price", f"Cena podle distribučního kanálu · {org} · {currency}", "channel")
        else:
            st.info("Cenové podmínky Current_Pricing_Conditions dosud nejsou načteny.")
        st.caption("Distribuční kanál není geografická oblast. Ceny z různých kanálů nepřiřazujeme automaticky k regionům.")
    with tabs[3]:
        st.subheader("Marketing podle produktů a oblastí")
        rows = filtered("Marketing_Expenses")
        if rows:
            group = aggregate(rows, ["organization", "product", "area", "currency"], ["marketing"])
            table(group)
            for (org, currency), part in group.groupby(["organization", "currency"], dropna=False):
                chart(part, "product", "marketing", f"Marketing · {org} · {currency}", "area")
            table(aggregate(rows, ["organization", "round", "step", "currency"], ["marketing"]))
        else:
            st.info("Marketing není v přiložených XLSX. Načtěte Marketing_Expenses; chybějící částky nejsou nuly.")
        st.caption("Výdaje jsou vykázané hodnoty AMOUNT. Z těchto dat samotných nelze dokázat kauzální návratnost reklamy.")
    with tabs[4]:
        st.subheader("Náklady položek prodeje")
        sales = sales_rows()
        if sales:
            group = aggregate(sales, ["organization", "product", "area", "currency", "unit"], ["cost", "revenue", "contribution"])
            table(group)
            for (org, currency, unit), part in group.groupby(["organization", "currency", "unit"], dropna=False):
                chart(part, "product", "cost", f"COST podle produktu a oblasti · {org} · {currency} · {unit}", "area")
            negative = group[group["contribution"] < 0]
            if not negative.empty:
                st.warning("Některé skupiny mají NET_VALUE nižší než COST. Zkontrolujte náklady a nastavení ceny v SAP.")
        else:
            st.info("Náklady vyžadují prodejní export nebo Sales. Z tržních cen nelze vlastní náklady odvodit.")
        st.subheader("Finanční výkazy a ocenění")
        for dataset in ("Financial_Postings", "Company_Valuation"):
            rows = store.records(game, dataset, as_of)
            rows = [r for r in rows if (not filters["organization"] or r.get("COMPANY_CODE") in filters["organization"])
                    and (not filters["round"] or r.get("SIM_ROUND") in filters["round"])
                    and (not filters["currency"] or r.get("CURRENCY") in filters["currency"])]
            if rows:
                with st.expander(dataset, expanded=True):
                    table(rows)
                    if dataset == "Company_Valuation":
                        finance_charts(rows)
        st.caption("Finanční účty bez produktové/oblastní dimenze se na produkty nerozpočítávají. "
                   "PROFIT a COMPANY_VALUATION zobrazujeme jako vykázané stavy, nesčítáme je přes dny. "
                   "Fixní náklady z prezentace jsou pravidla scénáře, nikoli skutečně zaúčtované částky.")
    with tabs[5]:
        import_controls(store, game)
        odata_controls(store, game, as_of)
    with tabs[6]:
        st.subheader("Historie načtení")
        st.caption("Čas stažení je UTC. SIM_* a ručně zadaný herní čas jsou samostatné údaje. "
                   "Historie pozorování se nikdy nesčítá do tržeb. Stav running po přerušení nemění uložená data.")
        table(runs)
        status = []
        for dataset in sorted(latest_by_dataset):
            last_ok = next((r for r in runs if r["dataset"] == dataset and r["status"] == "success"), None)
            status.append({"Zdroj": dataset, "Poslední pokus": latest_by_dataset[dataset]["status"],
                           "Poslední úspěch": formatted_time(last_ok["finished_at"] if last_ok else None),
                           "Herní čas snímku": last_ok["game_time"] if last_ok else None})
        table(status)
        st.download_button("Záloha SQLite (všechny hry)", store.backup(), "erpsim-backup.sqlite", "application/octet-stream")
    with tabs[7]:
        rules = store.records(game, "Current_Game_Rules", as_of)
        if rules:
            st.subheader("Parametry aktivní hry z Current_Game_Rules")
            table(rules)
        else:
            st.info("Pravidla nejsou dostupná. Parametry hry nedoplňujeme ze zkušební Introduction ani z prezentace.")
        with st.expander("Kontext z prezentace · není konfigurace aktuální hry"):
            st.markdown((ROOT / "docs/rules.md").read_text(encoding="utf-8"))
        st.markdown((ROOT / "docs/verification.md").read_text(encoding="utf-8"))
        with st.expander("Skutečné sloupce z přiložených metadat"):
            entity = st.selectbox("Entita", list(ENTITIES))
            st.dataframe(pd.DataFrame([{"Pole": f, "Typ": t, "Popisek SAP": ENTITIES[entity].labels[f]}
                                       for f, t in ENTITIES[entity].fields.items()]), hide_index=True)

    with tabs[8]:
        production_view(store, game, as_of, rules, filters, filtered)


def import_controls(store, game):
    st.subheader("Import XLSX / CSV")
    file = st.file_uploader("Soubor", type=["xlsx", "csv"], key=f"file_{game}")
    dataset = st.selectbox("Datová sada", ["Auto", *EXPORTS, *SYNC_ENTITIES])
    sheet = None
    if file is not None and file.name.lower().endswith(".xlsx"):
        try:
            sheet = st.selectbox("List XLSX", sheet_names(file.getvalue()))
            if st.button("Importovat všechny podporované OData listy do aktivní hry"):
                bundle, skipped = read_workbook(file.getvalue(), file.name)
                for name, values in bundle.items():
                    store.import_rows(game, name, values, "workbook")
                st.session_state["import_result"] = f"Načteno {len(bundle)} listů. Ostatní listy: {', '.join(skipped)}."
                st.rerun()
        except Exception as e:
            st.error(f"Sešit nelze načíst: {e}")
    cols = st.columns(3)
    sep = cols[0].selectbox("CSV oddělovač", [";", ",", "\t"])
    decimal = cols[1].selectbox("CSV desetinný oddělovač", [".", ","])
    encoding = cols[2].selectbox("CSV kódování", ["utf-8-sig", "cp1250"])
    game_time = st.text_input("Herní čas snímku bez SIM_* (volitelný)", placeholder="Např. kolo 1 / den 5")
    if file is not None:
        try:
            chosen = sheet if dataset == "Auto" and sheet in SYNC_ENTITIES else dataset
            detected, rows = read_file(file.getvalue(), file.name, chosen, sheet or None, sep, decimal, encoding)
            st.caption(f"Rozpoznáno: {detected} · {len(rows)} jednoznačných řádků")
            table(rows[:30])
            if st.button("Uložit import do aktivní hry", type="primary"):
                result = store.import_rows(game, detected, rows, "file", game_time or None)
                st.session_state["import_result"] = f"Uloženo {result['rows']} řádků, změněno {result['changed']} identit."
                st.rerun()
        except Exception as e:
            st.error(f"Import odmítnut: {e}")
    if "import_result" in st.session_state:
        st.success(st.session_state.pop("import_result"))
    with st.expander("Načíst přiložené exporty pro vybranou hru"):
        st.caption("Jde o čtyři skutečně dodané soubory. Detailní a souhrnné prodeje jsou alternativní zdroje se shodnými celkovými součty.")
        if st.button("Importovat čtyři přiložené XLSX"):
            for filename in ("inventory.xlsx", "price market.xlsx", "Sales report.xlsx", "Summary Sales order report.xlsx"):
                dataset, rows = read_file((ROOT / "samples" / filename).read_bytes(), filename)
                store.import_rows(game, dataset, rows, "attached_export", game_time or None)
            st.session_state["import_result"] = "Přiložené exporty byly načteny."
            st.rerun()
    with st.expander("Zkušební hra z dodaného vícelistového sešitu"):
        st.caption("Načte podporované OData listy do nové samostatné hry. Zkušební data se tak nesmíchají s živou simulací.")
        if st.button("Založit a načíst zkušební hru"):
            filename = "BIZ SIM data ze zkušebky.xlsx"
            bundle, skipped = read_workbook((ROOT / "samples" / filename).read_bytes(), filename)
            new_game = store.create_game("Zkušební hra · Introduction · AA")
            store.save_settings(new_game, {"purpose": "trial"})
            for name, rows in bundle.items():
                store.import_rows(new_game, name, rows, "trial_workbook")
            st.session_state["pending_game_select"] = new_game
            st.session_state["import_result"] = f"Načtena zkušební hra ({len(bundle)} zdrojů). Ostatní listy: {', '.join(skipped)}."
            st.rerun()


def odata_controls(store, game, as_of):
    st.subheader("OData · pouze GET")
    st.caption("Přihlašovací údaje zůstávají pouze v paměti relace nebo v lokálních proměnných prostředí; neukládají se do SQLite.")
    url = st.text_input("Adresa služby", os.environ.get("ERPSIM_ODATA_URL", DEFAULT_URL), key="odata_url")
    username = st.text_input("Uživatel (pokud je vyžadován)", os.environ.get("ERPSIM_ODATA_USER", ""), key="odata_user")
    password = st.text_input("Heslo", os.environ.get("ERPSIM_ODATA_PASSWORD", ""), type="password", key="odata_password")
    datasets = st.multiselect("Čtené entity", list(SYNC_ENTITIES),
                              default=list(DEFAULT_SYNC), key="odata_entities")
    st.caption("Každá aktualizace nejprve načítá Current_Game_Rules, i když nejsou ve výběru. "
               "Dostupnost entit se ověřuje podle živých metadat. Produkty ani kanály nejsou omezené na Introduction.")
    snapshot_time = st.text_input("Herní čas aktuálních snímků (volitelný)", key="odata_game_time")
    automatic = st.checkbox("Pravidelně číst OData, dokud je aplikace otevřená", key=f"odata_auto_{game}")
    seconds = st.number_input("Interval čtení (sekundy)", min_value=30, max_value=3600, value=60, step=30)
    st.caption("Čtení se zastaví zavřením aplikace. Při změně hry začne nový interval. "
               "Po výpadku přijde další pokus v následujícím intervalu; starší data zůstávají viditelná.")
    if st.button("Otestovat připojení", disabled=not datasets):
        try:
            with st.spinner("Ověřuji metadata a krátké čtení…"):
                client = ODataClient(url, username, password)
                try:
                    result = client.probe(datasets[0])
                finally:
                    client.close()
            st.success(f"Připojení funguje: {result['entities']} entit v metadatech, čtení {result['dataset']} dostupné "
                       f"({result['sample_rows']} ověřených vzorových řádků). Test nezměnil data v dashboardu.")
            if result["sample_rows"] == 0:
                st.info("Kolekce je prázdná: přístup funguje, ale hodnoty ani import skutečných prodejů tím nejsou ověřené.")
        except (ODataError, ValueError) as e:
            st.error(f"Připojení se nepodařilo: {e}")
            st.info("Na notebooku ověřte školní síť nebo VPN, správnou adresu služby a přístupové údaje. "
                    "Při 401/403 ověřte oprávnění; při timeoutu dostupnost serveru. Kontrolu TLS nevypínejte. "
                    "Importované soubory a poslední uložená data zůstávají dostupná.")

    @st.fragment(run_every=f"{int(seconds)}s" if automatic and as_of is None else None)
    def poll():
        manual = st.button("Načíst nyní", disabled=not datasets or as_of is not None)
        signature = (game, url, tuple(datasets), username, snapshot_time)
        previous_signature = st.session_state.get("poll_signature")
        previous = st.session_state.get("last_poll_monotonic", 0)
        if previous_signature != signature:
            previous = 0
        due = automatic and as_of is None and bool(datasets) and time.monotonic() - previous >= seconds
        if manual or due:
            st.session_state["poll_signature"] = signature
            st.session_state["last_poll_monotonic"] = time.monotonic()
            try:
                with st.spinner("Čtu úplné OData kolekce…"):
                    client = ODataClient(url, username, password)
                    try:
                        result = refresh(store, game, client, datasets, snapshot_time or None)
                    finally:
                        client.close()
                st.session_state[f"sync_result_{game}"] = result
                st.session_state["last_poll_monotonic"] = time.monotonic()
            except ValueError as e:
                st.error(str(e))
                return
            st.rerun()
        if f"sync_result_{game}" in st.session_state:
            st.write("Výsledek posledního čtení")
            table([{"Zdroj": name, **result} for name, result in st.session_state[f"sync_result_{game}"].items()])
    poll()


def settings_controls(store, game, cfg):
    with st.form(f"alerts_{game}"):
        enabled = st.checkbox("Zapnout upozornění v dashboardu", value=cfg["enabled"])
        cols = st.columns(3)
        with cols[0]:
            stock_enabled = st.checkbox("Nízké zásoby", value=cfg["stock_enabled"])
            stock_limit = st.number_input("Limit zásoby (≤)", min_value=0.0, value=float(cfg["stock_limit"]))
            stock_unit = st.text_input("Jednotka pro limit zásob", value=cfg["stock_unit"])
        with cols[1]:
            margin_enabled = st.checkbox("Nízký příspěvek po COST", value=cfg["margin_enabled"])
            margin_limit = st.number_input("Limit příspěvku (%)", min_value=-1000.0, max_value=100.0, value=float(cfg["margin_limit"]))
            stale_enabled = st.checkbox("Zastaralá OData data", value=cfg["stale_enabled"])
            stale_minutes = st.number_input("Maximální stáří (minuty)", min_value=1.0, value=float(cfg["stale_minutes"]))
        with cols[2]:
            marketing_enabled = st.checkbox("Vysoký marketing za herní den", value=cfg["marketing_enabled"])
            marketing_limit = st.number_input("Limit marketingu (>)", min_value=0.0, value=float(cfg["marketing_limit"]))
            marketing_currency = st.text_input("Měna pro limit marketingu", value=cfg["marketing_currency"])
        mapping = st.checkbox("Potvrzuji mapování oblastí NO → North, SO → South, WE → West", value=cfg["area_mapping"])
        st.caption("Limity se vztahují na vybrané zdroje a filtry. Marketingový limit platí pro produkt/oblast/den. "
                   "Nastavení se ukládá samostatně pro každou hru; upozornění nic nemění v SAP.")
        if st.form_submit_button("Uložit nastavení"):
            store.save_settings(game, cfg | dict(enabled=enabled, stock_enabled=stock_enabled, stock_limit=stock_limit,
                                          stock_unit=stock_unit.strip(), margin_enabled=margin_enabled, margin_limit=margin_limit,
                                          stale_enabled=stale_enabled, stale_minutes=stale_minutes,
                                          marketing_enabled=marketing_enabled, marketing_limit=marketing_limit,
                                          marketing_currency=marketing_currency.strip(), area_mapping=mapping))
            st.rerun()


def finance_charts(rows):
    st.write("Vývoj vykázaných finančních stavů")
    names = {"PROFIT": "Účetní zisk", "BANK_CASH_ACCOUNT": "Bankovní hotovost", "BANK_LOAN": "Bankovní půjčka",
             "ACCOUNTS_RECEIVABLE": "Pohledávky", "ACCOUNTS_PAYABLE": "Závazky", "COMPANY_VALUATION": "Hodnota společnosti"}
    available = [field for field in names if any(r.get(field) is not None for r in rows)]
    selected = st.multiselect("Finanční ukazatele", available, default=[f for f in ("PROFIT", "BANK_CASH_ACCOUNT", "BANK_LOAN") if f in available],
                              format_func=names.get)
    frame = pd.DataFrame(rows)
    frame["time_sort"] = frame["SIM_ROUND"].astype(int) * 10000 + frame["SIM_STEP"].astype(int)
    frame["Herní čas"] = frame["SIM_ROUND"] + "/" + frame["SIM_STEP"]
    for (company, currency), part in frame.groupby(["COMPANY_CODE", "CURRENCY"], dropna=False):
        part = part.sort_values("time_sort")
        for field in selected:
            plot = part[["Herní čas", field]].copy()
            plot[field] = pd.to_numeric(plot[field], errors="coerce")
            st.plotly_chart(px.line(plot, x="Herní čas", y=field, markers=True,
                                   title=f"{names[field]} · {company} · {currency}", labels={field: names[field]}), width="stretch")
    st.caption("Jde o vykázané stavy po herních dnech, nikoli součet opakovaných aktualizací. Kapacita ani náklady nejsou odvozené z Introduction.")


def production_view(store, game, as_of, rules, filters, filtered):
    st.subheader("Výroba, kapacita a přestavby")
    parameters = [r for r in rules if r["ELEMENT"] == "Production"
                  and (not filters["organization"] or r["COMPANY_CODE"] in filters["organization"])]
    if parameters:
        st.write("Výrobní parametry uvedené v aktuálních pravidlech")
        table(parameters)
        for company in sorted({r["COMPANY_CODE"] for r in parameters}):
            capacity = parameter(rules, company, "Production", "Daily Production Capacity")
            setup = parameter(rules, company, "Production", "Setup Time")
            cols = st.columns(2)
            if capacity is not None:
                cols[0].metric(f"Kapacita podle pravidel · {company}", str(capacity))
            if setup is not None:
                cols[1].metric(f"Setup Time podle pravidel · {company}", str(setup))
        st.caption("Hodnoty pocházejí z Current_Game_Rules. Aktuální pravidla nemusí popisovat historickou kapacitu po investicích; "
                   "nevypočítáváme z nich zpětně využití ani aktuální kapacitu z neověřeného účtu.")
    else:
        st.info("Výrobní kapacita ani čas přestaveb nejsou v dostupných pravidlech uvedené. Výchozí čísla z Introduction nedoplňujeme.")
    production = filtered("Production")
    if production:
        st.write("Skutečně vykázaná výroba YIELD")
        group = aggregate(production, ["organization", "product", "round", "step", "unit"], ["quantity"])
        table(group)
        daily = aggregate(production, ["organization", "round", "step", "unit"], ["quantity"])
        for (company, unit), part in daily.groupby(["organization", "unit"], dropna=False):
            part = part.copy()
            part["time_sort"] = part["round"].astype(int) * 10000 + part["step"].astype(int)
            part = part.sort_values("time_sort")
            part["Herní čas"] = part["round"] + "/" + part["step"]
            chart(part, "Herní čas", "quantity", f"Výroba po dnech · {company} · {unit}")
    else:
        st.info("Production není načtená nebo nemá řádky pro vybrané filtry.")
    orders = filtered("Production_Orders")
    if orders:
        st.write("Výrobní příkazy a vykázané časy přestaveb")
        table(orders)
        for (company, unit), part in pd.DataFrame(orders).groupby(["organization", "unit"], dropna=False):
            chart(part, "production_order", "setup", f"Vykázaný SETUP_TIME · {company}", "product")
            # Order totals can aggregate quantities, but do not infer elapsed runtime from start/end step.
            table(aggregate(part.to_dict("records"), ["organization", "product", "unit"], ["target", "confirmed"]))
        st.caption("SETUP_TIME zobrazujeme z výrobních příkazů. Jednotku a změny při investicích ověřte v aktuálních pravidlech Extended. "
                   "Začátek/konec příkazu jsou herní kroky, ne skutečná časová razítka.")
    st.subheader("Změny receptur (BOM_Changes)")
    changes = filtered("BOM_Changes")
    if changes:
        table(changes)
        for (company, unit), part in pd.DataFrame(changes).groupby(["organization", "unit"], dropna=False):
            part = part.copy()
            part["time_sort"] = part["round"].astype(int) * 10000 + part["step"].astype(int)
            part = part.sort_values("time_sort")
            part["Herní čas"] = part["round"] + "/" + part["step"]
            part["Složka / produkt"] = part["component"] + " / " + part["product"]
            st.plotly_chart(px.scatter(numeric_frame(part), x="Herní čas", y="quantity", color="Složka / produkt",
                                      title=f"Vykázané změny komponent · {company} · {unit}", labels=LABELS), width="stretch")
        st.caption("Ukazujeme zaznamenané změny komponent a množství. Z tohoto pohledu nelze odvodit úplný výchozí kusovník "
                   "ani procentní složení či výrobní náklady bez chybějícího základu.")
    else:
        st.info("BOM_Changes nemá dostupné změny. Prázdný list Introduction neověřuje chování změn receptur v Extended.")
