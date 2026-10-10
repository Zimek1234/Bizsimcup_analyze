from streamlit.testing.v1 import AppTest
from erpsim.storage import Store
from erpsim.schema import ROOT


def button(app, label):
    return next(b for b in app.button if b.label == label)


def test_trial_dashboard_navigation_filters_and_separate_game(tmp_path, monkeypatch):
    path = tmp_path / "ui.sqlite"
    monkeypatch.setenv("ERPSIM_DB_PATH", str(path))
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
    assert not app.exception
    app.text_input[0].set_value("Soutěžní Extended")
    button(app, "Založit hru").click().run()
    assert not app.exception
    competition = Store(path).games()[0]["id"]
    button(app, "Založit a načíst zkušební hru").click().run()
    assert not app.exception
    games = Store(path).games()
    assert len(games) == 2
    trial = games[1]["id"]
    assert Store(path).settings(trial)["purpose"] == "trial"
    assert len(Store(path).records(trial, "Sales")) == 186
    assert Store(path).records(competition, "Sales") == []

    assert any("ZKUŠEBNÍ INTRODUCTION" in w.value for w in app.warning)
    assert any("3 973 037.20" == m.value for m in app.metric)
    product = next(w for w in app.multiselect if w.label == "Produkt")
    product.set_value(["F01"]).run()
    assert not app.exception
    assert app.metric[0].value == "78 000"
    button(app, "Uložit nastavení").click().run()
    assert not app.exception
    assert Store(path).settings(trial)["purpose"] == "trial"
    # Visit historic snapshot, then a different game: never borrow trial data.
    history = next(w for w in app.selectbox if w.label == "Stav k aktualizaci")
    history.select_index(1).run()
    assert not app.exception
    active = next(w for w in app.selectbox if w.label == "Aktivní hra")
    active.set_value(competition).run()
    assert not app.exception
    assert Store(path).records(competition, "Sales") == []


def test_synthetic_extended_channels_parameters_bom_and_connection_message(tmp_path, monkeypatch, trial):
    from unittest.mock import Mock
    from erpsim.odata import ODataError
    import erpsim.dashboard

    path = tmp_path / "extended-ui.sqlite"
    monkeypatch.setenv("ERPSIM_DB_PATH", str(path))
    store = Store(path)
    game = store.create_game("Syntetický Extended · test schématu")
    store.save_settings(game, {"purpose": "competition"})
    rules = [{**r, "SCENARIO": "Extended"} for r in trial["Current_Game_Rules"]]
    for row in rules:
        if row["DETAIL"] == "Daily Production Capacity":
            row["VALUE"] = "45000"
    for channel in ["10", "14"]:
        rules.append({**rules[0], "DETAIL": channel, "VALUE": "Synthetic test channel"})
    rows = [{**r, "ID": f"synthetic-{i}", "DISTRIBUTION_CHANNEL": channel}
            for i, (r, channel) in enumerate(zip(trial["Sales"][:2], ["10", "14"]))]
    rows.append({**rows[0], "ID": "synthetic-new-product", "MATERIAL_NUMBER": "AA-F99"})
    store.import_rows(game, "Current_Game_Rules", rules)
    store.import_rows(game, "Sales", rows)
    store.import_rows(game, "Production_Orders", trial["Production_Orders"])
    store.import_rows(game, "BOM_Changes", [{"ID": "synthetic-bom", "PLANT": "AA", "SIM_ROUND": "01",
                      "SIM_STEP": "02", "MATERIAL_NUMBER": "AA-F99", "COMPONENT": "AA-R99", "QUANTITY": "0.2", "UNIT": "KG"}])
    fake = Mock()
    fake.probe.side_effect = ODataError("HTTP 401: ověřte přístup, přihlášení a síťové povolení.")
    monkeypatch.setattr(erpsim.dashboard, "ODataClient", Mock(return_value=fake))
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
    assert not app.exception
    assert any(m.value == "45000" for m in app.metric)
    assert {"10", "14"} <= set(next(w for w in app.multiselect if w.label == "Distribuční kanál").options)
    assert "F99" in next(w for w in app.multiselect if w.label == "Produkt").options
    button(app, "Otestovat připojení").click().run()
    assert not app.exception
    assert any("HTTP 401" in e.value for e in app.error)
    assert len(store.records(game, "Sales")) == 3
