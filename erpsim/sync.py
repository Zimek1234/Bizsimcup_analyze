"""Refresh orchestration independent of the dashboard."""
from .schema import REQUIRED, ENTITIES
from .odata import ODataError


def refresh(store, game: str, client, datasets: list[str], game_time: str | None = None) -> dict:
    results = {}
    datasets = list(dict.fromkeys(["Current_Game_Rules", *datasets]))
    try:
        live = client.metadata()
    except Exception as exc:
        message = str(exc) if isinstance(exc, ODataError) else "Metadata nebyla načtena."
        for dataset in datasets:
            run = store.begin(game, dataset, "odata", game_time)
            store.fail(run, message)
            results[dataset] = {"error": message}
        return results
    # Scenario/parameters come from the connected service, never from the trial workbook.
    for dataset in datasets:
        run = store.begin(game, dataset, "odata", game_time)
        try:
            if dataset not in live:
                raise ODataError("Entita není v živých metadatech dostupná; příslušné ukazatele nelze zobrazit.")
            if any(f not in live[dataset].fields or live[dataset].fields[f] != ENTITIES[dataset].fields[f]
                   for f in REQUIRED.get(dataset, ())):
                raise ODataError("Živá metadata se liší od podporovaného schématu; zkontrolujte mapování.")
            rows = client.read(dataset)
            results[dataset] = store.finish(run, rows)
        except Exception as exc:
            # Do not log arbitrary server contents or sensitive URLs.
            message = str(exc) if isinstance(exc, ODataError) else "Data neprošla validací; zkontrolujte schéma a typy."
            store.fail(run, message)
            results[dataset] = {"error": message}
    return results
