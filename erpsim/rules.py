"""Scenario catalogue and parameters from actual Current_Game_Rules rows."""
from decimal import Decimal, InvalidOperation
from .schema import product_code


def catalogue(rows: list[dict]) -> dict:
    return {
        "scenarios": sorted({r["SCENARIO"] for r in rows}),
        "products": sorted({product_code(r["ELEMENT"]) for r in rows if r["CATEGORY"] == "Product"}),
        "channels": sorted({r["DETAIL"] for r in rows if r["CATEGORY"] == "Organizational_Element"
                            and r["ELEMENT"] == "Distribution_Channel" and r.get("DETAIL")}),
    }


def parameter(rows: list[dict], company: str, element: str, detail: str):
    values = {r["VALUE"] for r in rows if r["COMPANY_CODE"] == company
              and r["ELEMENT"] == element and r.get("DETAIL") == detail}
    if len(values) != 1:
        return None
    try:
        value = Decimal(next(iter(values)))
        return value if value.is_finite() else None
    except InvalidOperation:
        return None
