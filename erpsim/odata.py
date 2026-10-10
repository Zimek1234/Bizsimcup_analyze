"""OData v2 JSON reader. GET only, verified TLS, bounded same-service pagination."""
from urllib.parse import urlsplit, urljoin, unquote
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from .schema import parse_metadata, ENTITIES, REQUIRED, normalize

DEFAULT_URL = "https://r75p.ucc.cloud/odata/792"


class ODataError(RuntimeError):
    pass


class ODataClient:
    def __init__(self, base_url: str = DEFAULT_URL, username: str = "", password: str = "", session=None):
        self.base = base_url.strip().rstrip("/") + "/"
        parts = urlsplit(self.base)
        if parts.scheme != "https" or not parts.hostname or parts.username or parts.password or parts.query or parts.fragment:
            raise ValueError("OData URL musí být HTTPS bez hesla, dotazu a fragmentu.")
        self.session = session or requests.Session()
        if username:
            self.session.auth = (username, password)
        if session is None:
            retry = Retry(total=2, connect=2, read=2, status=2, backoff_factor=0.5,
                          status_forcelist=[429, 502, 503, 504], allowed_methods={"GET"},
                          respect_retry_after_header=False)
            self.session.mount("https://", HTTPAdapter(max_retries=retry))

    def safe_url(self, url: str) -> str:
        resolved = urljoin(self.base, url)
        base, target = urlsplit(self.base), urlsplit(resolved)
        path = unquote(target.path)
        if (target.scheme, target.hostname, target.port) != (base.scheme, base.hostname, base.port) or (
            target.username or target.password or not path.startswith(base.path)
            or ".." in path.split("/") or "\\" in path or target.fragment
        ):
            raise ODataError("Odmítnut odkaz na stránku mimo původní OData službu.")
        return resolved

    def get(self, url: str, accept: str):
        try:
            response = self.session.get(self.safe_url(url), headers={"Accept": accept},
                                        timeout=(5, 20), allow_redirects=False)
            if response.status_code in (401, 403):
                raise ODataError(f"HTTP {response.status_code}: ověřte přístup, přihlášení a síťové povolení.")
            if 300 <= response.status_code < 400:
                raise ODataError("Služba přesměrovává. Zadejte přímou HTTPS adresu OData, ne přihlašovací portál.")
            if response.status_code != 200:
                raise ODataError(f"OData vrací HTTP {response.status_code}; předchozí data zachována.")
            return response
        except requests.exceptions.SSLError:
            raise ODataError("Chyba ověření TLS certifikátu. Kontrola certifikátu zůstává zapnutá.") from None
        except requests.exceptions.RequestException:
            # Exception text may contain credentials or URL parameters: do not persist it.
            raise ODataError("Síťový výpadek nebo timeout; předchozí data zachována.") from None

    def metadata(self):
        try:
            return parse_metadata(self.get("$metadata", "application/xml").content)
        except ODataError:
            raise
        except Exception:
            raise ODataError("Služba nevrátila platná podporovaná XML metadata.") from None

    def read(self, dataset: str, max_pages: int = 1000, max_rows: int = 250000) -> list[dict]:
        if dataset not in ENTITIES:
            raise ODataError("Entita není v přiložených metadatech.")
        url = self.safe_url(dataset + "?$format=json")
        seen = set()
        rows = []
        for _ in range(max_pages):
            if url in seen:
                raise ODataError("OData stránkování obsahuje cyklus; neúplná data nebyla uložena.")
            seen.add(url)
            response = self.get(url, "application/json")
            try:
                payload = response.json()
                body = payload["d"]
                page = body["results"] if isinstance(body, dict) else body
                if not isinstance(page, list) or any(not isinstance(r, dict) for r in page):
                    raise ValueError
                rows.extend(page)
                next_link = body.get("__next") if isinstance(body, dict) else None
            except (ValueError, KeyError, TypeError):
                raise ODataError("Neplatná odpověď OData v2 JSON; neúplná data nebyla uložena.") from None
            if len(rows) > max_rows:
                raise ODataError("Překročen limit řádků; data nebyla uložena. Zkraťte zdrojový rozsah.")
            if not next_link:
                return normalize(dataset, rows)
            if not isinstance(next_link, str):
                raise ODataError("Neplatný odkaz na další stránku.")
            # Resolve query-only links relative to the current page, then enforce service boundary.
            url = self.safe_url(urljoin(url, next_link))
        raise ODataError("Překročen limit stránek; neúplná data nebyla uložena.")

    def close(self):
        self.session.close()

    def probe(self, dataset: str) -> dict:
        """Check live schema and a real read without importing or updating analytics."""
        live = self.metadata()
        if dataset not in ENTITIES or dataset not in live:
            raise ODataError("Vybraná entita není ve službě dostupná.")
        if any(live[dataset].fields.get(f) != ENTITIES[dataset].fields[f] for f in REQUIRED.get(dataset, ())):
            raise ODataError("Živá metadata vybrané entity neodpovídají podporovanému schématu.")
        try:
            payload = self.get(dataset + "?$top=1&$format=json", "application/json").json()["d"]
            rows = payload["results"] if isinstance(payload, dict) else payload
            if not isinstance(rows, list) or any(not isinstance(r, dict) for r in rows):
                raise ValueError
            normalize(dataset, rows[:1])
        except ODataError:
            raise
        except (ValueError, KeyError, TypeError):
            raise ODataError("Služba nevrátila očekávaná data vybrané entity. Ověřte URL a schéma.") from None
        return {"entities": len(live), "sample_rows": min(len(rows), 1), "dataset": dataset}
