from unittest.mock import Mock
import pytest
import requests
from erpsim.odata import ODataClient, ODataError
from erpsim.schema import ENTITIES, ROOT
from erpsim.sync import refresh


def response(data=None, status=200, content=b""):
    r = Mock(status_code=status, content=content)
    r.json.return_value = data
    return r


def test_pagination_get_only_and_full_snapshot(sales):
    session = Mock()
    session.get.side_effect = [response({"d": {"results": sales[:100], "__next": "Sales?$skiptoken=100"}}),
                               response({"d": {"results": sales[100:]}})]
    client = ODataClient(session=session)
    assert len(client.read("Sales")) == 186
    assert session.get.call_count == 2
    for call in session.get.call_args_list:
        assert call.kwargs["allow_redirects"] is False and call.kwargs["timeout"] == (5, 20)
        assert "$select" not in call.args[0] and "$filter" not in call.args[0]


@pytest.mark.parametrize("link", ["https://evil.example/steal", "http://r75p.ucc.cloud/odata/792/Sales", "/other/service", "../outside", "https://user:pass@r75p.ucc.cloud/odata/792/Sales"])
def test_reject_unsafe_pagination(link, sales):
    session = Mock()
    session.get.return_value = response({"d": {"results": sales[:1], "__next": link}})
    with pytest.raises(ODataError):
        ODataClient(session=session).read("Sales")
    assert session.get.call_count == 1


def test_page_failure_does_not_import_partial_data(store, sales):
    game = store.create_game("g")
    store.import_rows(game, "Sales", sales)
    session = Mock()
    session.get.side_effect = [response(content=(ROOT / "resources/metadata.xml").read_bytes()),
                               response({"d": {"results": []}}), # rules
                               response({"d": {"results": sales[:1], "__next": "Sales?$skiptoken=1"}}),
                               response(status=503)]
    result = refresh(store, game, ODataClient(session=session), ["Sales"])
    assert "error" in result["Sales"] and len(store.records(game, "Sales")) == 186
    assert store.runs(game)[0]["status"] == "failed"


@pytest.mark.parametrize("status", [401, 403, 302, 500])
def test_connection_error_explained_without_body_or_credentials(status):
    session = Mock()
    session.get.return_value = response(status=status, content=b"secret server response")
    with pytest.raises(ODataError) as exc:
        ODataClient(username="user", password="secret-password", session=session).probe("Sales")
    assert "secret" not in str(exc.value)


def test_network_timeout_and_tls_are_sanitized():
    for error in [requests.exceptions.Timeout("contains-secret"), requests.exceptions.SSLError("contains-secret")]:
        session = Mock()
        session.get.side_effect = error
        with pytest.raises(ODataError) as exc:
            ODataClient(session=session).metadata()
        assert "contains-secret" not in str(exc.value)


def test_probe_read_without_import(sales):
    session = Mock()
    session.get.side_effect = [response(content=(ROOT / "resources/metadata.xml").read_bytes()),
                               response({"d": {"results": sales[:1]}})]
    result = ODataClient(session=session).probe("Sales")
    assert result["entities"] == 18 and result["sample_rows"] == 1


def test_cycle_limit_and_invalid_response(sales):
    for payload in [{"d": {"results": sales[:1], "__next": "Sales?$format=json"}}, {"html": "login"}]:
        session = Mock()
        session.get.return_value = response(payload)
        with pytest.raises(ODataError):
            ODataClient(session=session).read("Sales")


def test_refresh_rules_and_extended_optional_entities(store, trial):
    game = store.create_game("Extended")
    client = Mock()
    client.metadata.return_value = ENTITIES
    def read(name):
        if name == "Current_Game_Rules":
            return [{**r, "SCENARIO": "Extended"} for r in trial[name]]
        return trial.get(name, [])
    client.read.side_effect = read
    result = refresh(store, game, client, ["Sales", "Production", "Production_Orders", "BOM_Changes"])
    assert client.read.call_args_list[0].args == ("Current_Game_Rules",)
    assert result["Sales"]["rows"] == 186 and result["Production_Orders"]["rows"] == 34
    assert store.records(game, "Current_Game_Rules")[0]["SCENARIO"] == "Extended"
    # This is a controlled schema/flow test using Introduction rows, not live Extended validation.
