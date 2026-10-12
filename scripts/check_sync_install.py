"""Offline worker import check; never loads .env or contacts a database/OData."""
from importlib.util import find_spec
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    # pandas may import Arrow when it is installed, even without an Arrow dtype.
    unwanted = [name for name in ("streamlit", "pyarrow", "plotly") if find_spec(name)]
    if unwanted:
        print("Prostředí obsahuje balíčky dashboardu: " + ", ".join(unwanted))
        print("Použijte nové samostatné .venv-sync podle docs/windows-sync.md.")
        return 1
    import pandas
    import openpyxl
    import requests
    import defusedxml
    import dotenv
    from service.cli import parser

    parser().parse_args(["probe"])
    assert not any(name in sys.modules for name in ("streamlit", "pyarrow", "plotly"))
    print(f"Importy synchronizátoru OK: Python {sys.version_info.major}.{sys.version_info.minor}, pandas {pandas.__version__}; bez Streamlitu a pyarrow.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
