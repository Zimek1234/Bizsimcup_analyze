"""Names and types come from the supplied SAP metadata, not inferred columns."""
from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import re
from decimal import Decimal, InvalidOperation
from defusedxml import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SAP = "{http://www.sap.com/Protocols/SAPData}"
EDM = "{http://schemas.microsoft.com/ado/2008/09/edm}"


@dataclass(frozen=True)
class Entity:
    name: str
    fields: dict
    labels: dict
    dimensions: tuple


def parse_metadata(content: bytes) -> dict[str, Entity]:
    root = ET.fromstring(content)
    types = {}
    for node in root.iter(EDM + "EntityType"):
        props = list(node.findall(EDM + "Property"))
        types[node.attrib["Name"]] = Entity(
            node.attrib["Name"],
            {p.attrib["Name"]: p.attrib["Type"] for p in props},
            {p.attrib["Name"]: p.attrib.get(SAP + "label", p.attrib["Name"]) for p in props},
            tuple(p.attrib["Name"] for p in props
                  if p.attrib.get(SAP + "aggregation-role") == "dimension"
                  and p.attrib["Name"] not in {"ROW_ID", "MATERIAL_DESCRIPTION", "NET_PRICE"}),
        )
    entities = {}
    for node in root.iter(EDM + "EntitySet"):
        name = node.attrib["Name"]
        typ = types.get(node.attrib["EntityType"].split(".")[-1])
        if typ:
            entities[name] = Entity(name, typ.fields, typ.labels, typ.dimensions)
    if not entities:
        raise ValueError("Metadata neobsahují podporované EntitySet (OData v2).")
    return entities


ENTITIES = parse_metadata((ROOT / "resources/metadata.xml").read_bytes())
SYNC_ENTITIES = tuple(ENTITIES)
DEFAULT_SYNC = ("Current_Game_Rules", "Sales", "Marketing_Expenses", "Current_Inventory",
                "Current_Pricing_Conditions", "Market", "Financial_Postings", "Company_Valuation",
                "Production", "Production_Orders", "BOM_Changes")
EXPORTS = {
    "InventoryExport": {"Location": "Edm.String", "Category": "Edm.String", "Material": "Edm.String",
                        "Description": "Edm.String", "Stock": "Edm.Decimal", "Reserved": "Edm.Decimal", "Unit": "Edm.String"},
    "MarketExport": {"Simulation Date": "Edm.String", "Material": "Edm.String", "Description": "Edm.String",
                     "Area": "Edm.String", "Price": "Edm.Decimal", "Quantity": "Edm.Decimal", "Value": "Edm.Decimal"},
    "SalesExport": {"Round": "Edm.String", "Day": "Edm.String", "Area": "Edm.String", "Location": "Edm.String",
                    "D. Channel": "Edm.String", "Material": "Edm.String", "Description": "Edm.String",
                    "Net Price": "Edm.Decimal", "Quantity": "Edm.Decimal", "Net Value": "Edm.Decimal", "Cost": "Edm.Decimal"},
    "SummarySalesExport": {"Round": "Edm.String", "Day": "Edm.String", "Material": "Edm.String", "Description": "Edm.String",
                           "Orders": "Edm.Int32", "Quantity": "Edm.Decimal", "Net Value": "Edm.Decimal", "Cost": "Edm.Decimal"},
}
REQUIRED = {
    "Sales": ("ID", "SALES_ORGANIZATION", "SALES_ORDER_NUMBER", "LINE_ITEM", "MATERIAL_NUMBER", "AREA",
              "SIM_ROUND", "SIM_STEP", "QUANTITY", "QUANTITY_DELIVERED", "NET_VALUE", "COST", "CURRENCY", "UNIT"),
    "Marketing_Expenses": ("SALES_ORGANIZATION", "SIM_ROUND", "SIM_STEP", "MATERIAL_NUMBER", "AREA", "AMOUNT", "CURRENCY"),
    "Current_Inventory": ("PLANT", "STORAGE_LOCATION", "MATERIAL_NUMBER", "STOCK", "RESTRICTED", "UNIT"),
    "Current_Pricing_Conditions": ("SALES_ORGANIZATION", "MATERIAL_NUMBER", "DISTRIBUTION_CHANNEL", "PRICE", "CURRENCY"),
    "Market": ("COMPANY_CODE", "SALES_ORGANIZATION", "SIM_ROUND", "SIM_PERIOD", "MATERIAL_DESCRIPTION",
               "DISTRIBUTION_CHANNEL", "AREA", "QUANTITY", "NET_VALUE", "AVERAGE_PRICE", "UNIT", "CURRENCY"),
    "Inventory": ("PLANT", "SIM_ROUND", "SIM_STEP", "STORAGE_LOCATION", "MATERIAL_NUMBER", "INVENTORY_OPENING_BALANCE", "UNIT"),
    "Financial_Postings": ("COMPANY_CODE", "SIM_ROUND", "SIM_STEP", "GL_ACCOUNT_NUMBER", "AMOUNT", "CURRENCY"),
    "Company_Valuation": ("COMPANY_CODE", "SIM_ROUND", "SIM_STEP", "PROFIT", "COMPANY_VALUATION", "CURRENCY"),
    "Current_Game_Rules": ("COMPANY_CODE", "GAME", "SCENARIO", "CATEGORY", "ELEMENT", "VALUE"),
    "Production": ("COMPANY_CODE", "SIM_ROUND", "SIM_STEP", "MATERIAL_NUMBER", "YIELD", "UNIT"),
    "Production_Orders": ("COMPANY_CODE", "PRODUCTION_ORDER", "MATERIAL_NUMBER", "TARGET_QUANTITY", "CONFIRMED_QUANTITY", "SETUP_TIME", "UNIT"),
    "BOM_Changes": ("PLANT", "SIM_ROUND", "SIM_STEP", "MATERIAL_NUMBER", "COMPONENT", "QUANTITY", "UNIT"),
}


def number(value, field: str) -> str:
    # Never guess thousands/decimal separators: XLSX is numeric; CSV uses explicit convention.
    try:
        d = Decimal(str(value).strip())
        if not d.is_finite():
            raise InvalidOperation
        return format(d.normalize(), "f")
    except (InvalidOperation, ValueError):
        raise ValueError(f"Pole {field}: neplatné číslo {value!r}.") from None


def normalize(dataset: str, rows: list[dict]) -> list[dict]:
    fields = EXPORTS.get(dataset) or ENTITIES[dataset].fields
    required = tuple(EXPORTS[dataset]) if dataset in EXPORTS else REQUIRED.get(dataset, ())
    result = []
    seen = {}
    for index, raw in enumerate(rows, 2):
        missing = [c for c in required if c not in raw or raw[c] is None or str(raw[c]).strip() == ""]
        if missing:
            raise ValueError(f"Řádek {index}: chybí povinná pole {', '.join(missing)}.")
        row = {}
        for key, value in raw.items():
            if key == "__metadata":
                continue
            if key not in fields:
                raise ValueError(f"Neznámé pole {key!r} pro {dataset}.")
            if value is None or str(value).strip() == "":
                row[key] = None
            elif fields[key] in {"Edm.Decimal", "Edm.Double", "Edm.Int32", "Edm.Int16", "Edm.Int64"}:
                row[key] = number(value, key)
            else:
                row[key] = str(value).strip()
            if key in {"Round", "Day", "SIM_ROUND", "SIM_STEP", "BEGIN_ROUND", "BEGIN_STEP", "END_ROUND", "END_STEP"} and row[key] is not None:
                if not row[key].isdigit():
                    raise ValueError(f"Pole {key}: herní kolo/den musí být číselné označení.")
        key = natural_key(dataset, row)
        if dataset == "SalesExport":
            # No order/item ID exists here. Equal rows can be separate legitimate sales.
            # Preserve multiplicity inside a file; deduplication is at complete-snapshot level.
            result.append(row)
            continue
        if key in seen:
            meaningful = lambda r: {k: v for k, v in r.items() if k not in {"ID", "ROW_ID"}}
            if meaningful(seen[key]) != meaningful(row):
                raise ValueError(f"Řádek {index}: konfliktní hodnoty stejné identity; import nebyl uložen.")
            continue
        seen[key] = row
        result.append(row)
    return result


def natural_key(dataset: str, row: dict) -> str:
    if dataset in ENTITIES and row.get("ID"):
        keys = ("ID",)
    elif dataset == "Sales":
        # The real workbook has different rows with the same order/item, even same material.
        # Use the metadata's primary key inside ONE complete snapshot, never across snapshots.
        keys = ("ID",)
    elif dataset == "InventoryExport":
        keys = ("Location", "Material", "Unit")
    elif dataset == "MarketExport":
        keys = ("Simulation Date", "Material", "Area")
    elif dataset == "SummarySalesExport":
        keys = ("Round", "Day", "Material")
    elif dataset == "SalesExport":
        keys = tuple(EXPORTS[dataset])
    elif dataset == "Current_Game_Rules":
        keys = ("COMPANY_CODE", "GAME", "SCENARIO", "CATEGORY", "ELEMENT", "DETAIL")
    else:
        keys = ENTITIES[dataset].dimensions
    identity = {k: row.get(k) for k in keys}
    # Market has no MATERIAL_NUMBER in supplied metadata: description is part of identity.
    if dataset == "Market" and not row.get("ID"):
        identity["MATERIAL_DESCRIPTION"] = row["MATERIAL_DESCRIPTION"]
    return hashlib.sha256(json.dumps(identity, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def product_code(material: str) -> str:
    """Display-only join code: AA-F01 and F01 share F01; raw material is retained."""
    match = re.fullmatch(r"(?:[A-Z0-9]{2}-)?(F\d{2})", material or "")
    return match.group(1) if match else material or "Neuvedeno"
