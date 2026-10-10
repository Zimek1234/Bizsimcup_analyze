from decimal import Decimal
import sqlite3
import pytest
from erpsim.analytics import views, aggregate, select
from erpsim.loaders import read_file
from erpsim.schema import ROOT, ENTITIES, normalize
from erpsim.rules import catalogue, parameter
from erpsim.alerts import evaluate


@pytest.mark.parametrize("name,dataset,count", [
    ("inventory.xlsx", "InventoryExport", 22), ("price market.xlsx", "MarketExport", 285),
    ("Sales report.xlsx", "SalesExport", 186), ("Summary Sales order report.xlsx", "SummarySalesExport", 732)])
def test_real_exports(name, dataset, count):
    detected, rows = read_file((ROOT / "samples" / name).read_bytes(), name)
    assert detected == dataset and len(rows) == count


def totals(dataset, rows):
    frame = aggregate(views(dataset, rows), ["currency", "unit"], ["ordered", "revenue", "cost"])
    return tuple(frame.iloc[0][f] for f in ("ordered", "revenue", "cost"))


def test_three_sales_sources_agree(trial):
    expected = (Decimal("626554"), Decimal("3973037.2"), Decimal("957873.74"))
    assert totals("Sales", trial["Sales"]) == expected
    for name in ("Sales report.xlsx", "Summary Sales order report.xlsx"):
        dataset, rows = read_file((ROOT / "samples" / name).read_bytes(), name)
        assert totals(dataset, rows) == expected
    # The workbook exposes genuine conflicting business keys: all 186 rows must survive.
    same_item = [r for r in trial["Sales"] if r["SALES_ORDER_NUMBER"] == "535" and r["LINE_ITEM"] == "2"]
    assert len(same_item) == 2 and same_item[0]["QUANTITY"] != same_item[1]["QUANTITY"]


def test_snapshot_repeat_revision_history_and_game_isolation(store, sales):
    game = store.create_game("Introduction")
    other = store.create_game("Soutěž Extended")
    store.import_rows(game, "Sales", sales)
    first = store.runs(game)[0]["id"]
    store.import_rows(game, "Sales", sales)
    assert store.runs(game)[0]["changed_count"] == 0
    assert totals("Sales", store.records(game, "Sales")) == totals("Sales", sales)
    revised = [r.copy() for r in sales]
    revised[0]["NET_VALUE"] = "999"
    # Reassigned aggregate IDs cannot make old and new snapshots add together.
    for i, row in enumerate(revised):
        row["ID"] = f"new-{i}"
    store.import_rows(game, "Sales", revised)
    assert len(store.records(game, "Sales")) == 186
    assert sorted(store.records(game, "Sales", first), key=lambda r: r["ID"]) == sorted(sales, key=lambda r: r["ID"])
    assert store.records(other, "Sales") == []
    store.import_rows(other, "Sales", sales)
    assert len(store.records(other, "Sales")) == 186


def test_snapshot_detail_preserves_equal_legitimate_rows(store):
    name = "Sales report.xlsx"
    dataset, rows = read_file((ROOT / "samples" / name).read_bytes(), name)
    duplicate_rows = [rows[0], rows[0]]
    game = store.create_game("g")
    store.import_rows(game, dataset, duplicate_rows)
    store.import_rows(game, dataset, duplicate_rows)
    assert len(store.records(game, dataset)) == 2
    assert totals(dataset, store.records(game, dataset))[0] == 2 * Decimal(rows[0]["Quantity"])


def test_empty_snapshot_and_concurrent_reads(store, sales):
    game = store.create_game("g")
    older = store.begin(game, "Sales", "odata")
    newer = store.begin(game, "Sales", "odata")
    store.finish(newer, sales)
    store.finish(older, [])
    assert len(store.records(game, "Sales")) == 186
    store.import_rows(game, "Sales", [])
    assert store.records(game, "Sales") == []


def test_validation_failure_keeps_data(store, sales):
    game = store.create_game("g")
    store.import_rows(game, "Sales", sales)
    damaged = [sales[0].copy()]
    damaged[0]["COST"] = "nonsense"
    with pytest.raises(ValueError):
        store.import_rows(game, "Sales", damaged)
    assert len(store.records(game, "Sales")) == 186
    assert store.runs(game)[0]["status"] == "failed"


def test_csv_exact_columns_decimal_comma_and_leading_zeros():
    content = 'Location;Category;Material;Description;Stock;Reserved;Unit\n02;Finished Goods;AA-F01;Nut;1,25;0;ST\n'
    dataset, rows = read_file(content.encode(), "test.csv", separator=";", decimal=",")
    assert rows[0]["Location"] == "02" and rows[0]["Stock"] == "1.25"
    assert dataset == "InventoryExport"


def test_reject_unknown_missing_malformed_and_duplicate_columns():
    for content in ['Location,Location\n02,02', 'Whatever\n1',
                    'Location;Category;Material;Description;Stock;Reserved;Unit\n02;Finished Goods;AA-F01;Nut;1;0;ST;extra']:
        with pytest.raises(ValueError):
            read_file(content.encode(), "test.csv", separator=";" if ";" in content else ",")
    with pytest.raises(ValueError):
        read_file(b'ID,SALES_ORGANIZATION\n', "empty.csv", "Sales", separator=",")


def test_weighted_price_decimal_and_zero_quantity():
    rows = views("MarketExport", normalize("MarketExport", [
        {"Simulation Date": "01/05", "Material": "F01", "Description": "Nut", "Area": "West", "Price": 3, "Quantity": 1, "Value": "0.1"},
        {"Simulation Date": "01/10", "Material": "F01", "Description": "Nut", "Area": "West", "Price": 5, "Quantity": 9, "Value": "0.2"}]))
    summary = aggregate(rows, ["currency", "unit"], ["quantity", "revenue"])
    assert summary.iloc[0]["revenue"] == Decimal("0.3")
    assert summary.iloc[0]["weighted_price"] == Decimal("0.03")
    rows[0]["quantity"] = Decimal(0)
    summary = aggregate(rows[:1], ["currency", "unit"], ["quantity", "revenue"])
    assert summary.iloc[0]["weighted_price"] is None
    with pytest.raises(ValueError):
        aggregate(rows, ["product"], ["quantity", "revenue"])


def test_unknown_currency_unit_and_reserved_are_not_guessed():
    d, rows = read_file((ROOT / "samples/inventory.xlsx").read_bytes(), "inventory.xlsx")
    assert views(d, rows)[0]["restricted"] is None
    d, rows = read_file((ROOT / "samples/price market.xlsx").read_bytes(), "market.xlsx")
    v = views(d, rows)[0]
    assert v["currency"] == "Měna neuvedena" and v["unit"] == "Jednotka neuvedena"


def test_dynamic_scenario_parameters_not_limited_to_introduction(trial):
    rules = trial["Current_Game_Rules"]
    assert catalogue(rules)["scenarios"] == ["Introduction"]
    assert parameter(rules, "AA", "Production", "Daily Production Capacity") == Decimal(16000)
    # Synthetic schema test only, not proof of live Extended values.
    extended = [{**r, "SCENARIO": "Extended"} for r in rules]
    extended += [{**rules[0], "DETAIL": "10", "VALUE": "Test channel"},
                 {**rules[0], "DETAIL": "14", "VALUE": "Test channel"},
                 {**rules[5], "ELEMENT": "AA-F99", "DETAIL": "New product", "SCENARIO": "Extended"}]
    cat = catalogue(extended)
    assert "F99" in cat["products"] and {"10", "12", "14"} <= set(cat["channels"])
    assert parameter([], "AA", "Production", "Daily Production Capacity") is None


def test_alerts_respect_units_currencies_and_settings(trial, store):
    stock = views("Current_Inventory", trial["Current_Inventory"])
    alerts = evaluate([], stock, [], [], {"stock_limit": 0, "stock_unit": "ST"})
    assert alerts and all(a["Typ"] == "Zásoba" for a in alerts)
    assert evaluate([], stock, [], [], {"stock_unit": "unknown"}) == []
    assert evaluate([], stock, [], [], {"enabled": False}) == []
    a, b = store.create_game("a"), store.create_game("b")
    store.save_settings(a, {"stock_limit": 42, "purpose": "trial"})
    assert store.settings(a)["stock_limit"] == 42 and store.settings(b) == {}


def test_backup_contains_committed_history(store, sales, tmp_path):
    game = store.create_game("g")
    store.import_rows(game, "Sales", sales)
    path = tmp_path / "restored.sqlite"
    path.write_bytes(store.backup())
    with sqlite3.connect(path) as db:
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert db.execute("SELECT count(*) FROM observations").fetchone()[0] == 186
