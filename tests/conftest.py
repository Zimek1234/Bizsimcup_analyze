from pathlib import Path
import pytest
from erpsim.loaders import read_file, read_workbook
from erpsim.schema import ROOT
from erpsim.storage import Store


@pytest.fixture
def store(tmp_path):
    return Store(tmp_path / "analytics.sqlite")


@pytest.fixture(scope="session")
def trial():
    name = "BIZ SIM data ze zkušebky.xlsx"
    return read_workbook((ROOT / "samples" / name).read_bytes(), name)[0]


@pytest.fixture
def sales(trial):
    return [r.copy() for r in trial["Sales"]]
