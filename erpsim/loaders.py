"""File readers; explicit schemas, encoding and numeric conventions."""
from io import BytesIO, StringIO
import csv
import pandas as pd
from .schema import ENTITIES, EXPORTS, REQUIRED, normalize
from .schema import SYNC_ENTITIES


def sheet_names(content: bytes) -> list[str]:
    with pd.ExcelFile(BytesIO(content), engine="openpyxl") as book:
        return list(book.sheet_names)


def read_workbook(content: bytes, filename: str) -> tuple[dict, list[str]]:
    """Validate all supported sheets before importing any of them."""
    names = sheet_names(content)
    datasets = {name: read_file(content, filename, name, name)[1] for name in names if name in SYNC_ENTITIES}
    if not datasets:
        raise ValueError("Sešit nemá listy pojmenované podle podporovaných OData entit.")
    return datasets, [name for name in names if name not in SYNC_ENTITIES]


def read_file(content: bytes, filename: str, dataset: str = "Auto", sheet: str | None = None,
              separator: str = ";", decimal: str = ".", encoding: str = "utf-8-sig") -> tuple[str, list[dict]]:
    if filename.lower().endswith(".xlsx"):
        frame = pd.read_excel(BytesIO(content), sheet_name=sheet or 0, dtype=object, engine="openpyxl")
    elif filename.lower().endswith(".csv"):
        text = content.decode(encoding)
        reader = csv.DictReader(StringIO(text), delimiter=separator)
        if not reader.fieldnames or len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError("CSV nemá jednoznačnou hlavičku.")
        raw = list(reader)
        if any(None in r or any(v is None for v in r.values()) for r in raw):
            raise ValueError("CSV má řádky s jiným počtem sloupců než hlavička.")
        frame = pd.DataFrame(raw, columns=reader.fieldnames)
    else:
        raise ValueError("Podporované formáty jsou XLSX a CSV.")
    frame.columns = [str(x).strip() for x in frame.columns]
    if len(frame.columns) != len(set(frame.columns)):
        raise ValueError("Duplicitní názvy sloupců.")
    if dataset == "Auto":
        matches = [name for name, fields in EXPORTS.items() if set(frame.columns) == set(fields)]
        if len(matches) != 1:
            raise ValueError("Formát neodpovídá přiloženým exportům. Vyberte OData entitu explicitně.")
        dataset = matches[0]
    if dataset not in EXPORTS and dataset not in ENTITIES:
        raise ValueError("Nepodporovaná datová sada.")
    if dataset in ENTITIES:
        entity = ENTITIES[dataset]
        aliases = {label: name for name, label in entity.labels.items()
                   if list(entity.labels.values()).count(label) == 1}
        frame = frame.rename(columns={col: aliases[col] for col in frame.columns
                                      if col not in entity.fields and col in aliases})
    if len(frame.columns) != len(set(frame.columns)):
        raise ValueError("Hlavičky po mapování označují stejné pole vícekrát.")
    fields = EXPORTS.get(dataset) or ENTITIES[dataset].fields
    unknown = set(frame.columns) - set(fields)
    if unknown:
        raise ValueError(f"Neznámé sloupce: {', '.join(sorted(unknown))}.")
    required = tuple(EXPORTS[dataset]) if dataset in EXPORTS else REQUIRED.get(dataset, ())
    missing = set(required) - set(frame.columns)
    if missing:
        raise ValueError(f"Chybějící sloupce: {', '.join(sorted(missing))}.")
    if filename.lower().endswith(".csv") and decimal == ",":
        for col in frame.columns:
            if fields[col] in {"Edm.Decimal", "Edm.Double"}:
                frame[col] = frame[col].map(lambda v: v.replace(",", ".") if isinstance(v, str) else v)
    records = frame.where(pd.notna(frame), None).to_dict("records")
    return dataset, normalize(dataset, records)
