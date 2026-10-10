"""Pure calculations over deduplicated facts; never sum observations/downloads."""
from decimal import Decimal
import pandas as pd
from .schema import product_code


def value(row, field):
    x = row.get(field)
    return Decimal(str(x)) if x is not None else None


def views(dataset: str, rows: list[dict]) -> list[dict]:
    result = []
    for r in rows:
        item = {
            "product": product_code(r.get("MATERIAL_NUMBER", r.get("Material", ""))),
            "description": r.get("MATERIAL_DESCRIPTION", r.get("Description", "Neuvedeno")),
            "area": r.get("AREA", r.get("Area", "Neuvedeno")),
            "organization": r.get("SALES_ORGANIZATION", r.get("COMPANY_CODE", r.get("PLANT", "Neuvedeno"))),
            "currency": r.get("CURRENCY") or "Měna neuvedena",
            "unit": r.get("UNIT", r.get("Unit")) or "Jednotka neuvedena",
            "round": r.get("SIM_ROUND", r.get("Round")) or "Neuvedeno",
            "step": r.get("SIM_STEP", r.get("Day")) or "Neuvedeno",
            "game_date": r.get("SIM_DATE", r.get("Simulation Date")) or "Neuvedeno",
            "period": r.get("SIM_PERIOD") or "Neuvedeno",
            "elapsed_steps": r.get("SIM_ELAPSED_STEPS"),
            "location": r.get("STORAGE_LOCATION", r.get("Location", "Neuvedeno")),
            "channel": r.get("DISTRIBUTION_CHANNEL", r.get("D. Channel")) or "Neuvedeno",
        }
        if dataset == "Sales":
            item.update(ordered=value(r, "QUANTITY"), delivered=value(r, "QUANTITY_DELIVERED"),
                        revenue=value(r, "NET_VALUE"), cost=value(r, "COST"), price=value(r, "NET_PRICE"),
                        order=r.get("SALES_ORDER_NUMBER"), line=r.get("LINE_ITEM"))
            item["contribution"] = item["revenue"] - item["cost"]
        elif dataset in {"SalesExport", "SummarySalesExport"}:
            item.update(ordered=value(r, "Quantity"), delivered=None, revenue=value(r, "Net Value"),
                        cost=value(r, "Cost"), price=value(r, "Net Price"), orders=value(r, "Orders"))
            item["contribution"] = item["revenue"] - item["cost"]
        elif dataset in {"MarketExport", "Market"}:
            item.update(quantity=value(r, "Quantity" if dataset == "MarketExport" else "QUANTITY"),
                        revenue=value(r, "Value" if dataset == "MarketExport" else "NET_VALUE"),
                        price=value(r, "Price" if dataset == "MarketExport" else "AVERAGE_PRICE"))
            if dataset == "Market":
                # No material number exists in Market; never fabricate one from another game's catalogue.
                item["product"] = item["description"]
        elif dataset in {"Current_Inventory", "InventoryExport", "Inventory"}:
            stock_field = {"Current_Inventory": "STOCK", "InventoryExport": "Stock", "Inventory": "INVENTORY_OPENING_BALANCE"}[dataset]
            item.update(stock=value(r, stock_field), reserved=value(r, "Reserved"),
                        restricted=value(r, "RESTRICTED"), category=r.get("Category", "Neuvedeno"))
        elif dataset == "Marketing_Expenses":
            item["marketing"] = value(r, "AMOUNT")
        elif dataset == "Current_Pricing_Conditions":
            item["price"] = value(r, "PRICE")
        elif dataset == "Production":
            item["quantity"] = value(r, "YIELD")
        elif dataset == "Production_Orders":
            item.update(target=value(r, "TARGET_QUANTITY"), confirmed=value(r, "CONFIRMED_QUANTITY"),
                        setup=value(r, "SETUP_TIME"), production_order=r.get("PRODUCTION_ORDER"),
                        begin_round=r.get("BEGIN_ROUND"), begin_step=r.get("BEGIN_STEP"),
                        end_round=r.get("END_ROUND"), end_step=r.get("END_STEP"))
        elif dataset == "BOM_Changes":
            item.update(component=r.get("COMPONENT"), quantity=value(r, "QUANTITY"))
        result.append(item)
    return result


def select(rows: list[dict], filters: dict) -> list[dict]:
    return [r for r in rows if all(not choices or r.get(field) in choices for field, choices in filters.items())]


def aggregate(rows: list[dict], groups: list[str], measures: list[str]) -> pd.DataFrame:
    """Decimal sums; currency/unit must be explicit group keys for monetary/quantity measures."""
    money = {"revenue", "cost", "contribution", "marketing"}
    quantity = {"ordered", "delivered", "quantity", "stock", "reserved", "restricted", "target", "confirmed"}
    if money.intersection(measures) and "currency" not in groups:
        raise ValueError("Peněžní agregace vyžaduje oddělení měn.")
    if quantity.intersection(measures) and "unit" not in groups:
        raise ValueError("Agregace množství vyžaduje oddělení jednotek.")
    buckets = {}
    for row in rows:
        key = tuple(row.get(g, "Neuvedeno") for g in groups)
        acc = buckets.setdefault(key, {m: None for m in measures})
        for m in measures:
            if row.get(m) is not None:
                acc[m] = (acc[m] or Decimal(0)) + row[m]
    output = []
    for key, sums in buckets.items():
        item = dict(zip(groups, key)) | sums
        if "revenue" in sums and ("quantity" in sums or "ordered" in sums):
            qty = sums.get("quantity", sums.get("ordered"))
            item["weighted_price"] = sums["revenue"] / qty if qty else None
        if "contribution" in sums and "revenue" in sums:
            item["margin_pct"] = 100 * sums["contribution"] / sums["revenue"] if sums["revenue"] else None
        output.append(item)
    return pd.DataFrame(output, columns=groups + measures + (
        ["weighted_price"] if "revenue" in measures and ({"quantity", "ordered"} & set(measures)) else []) + (
        ["margin_pct"] if "contribution" in measures and "revenue" in measures else []))


def numeric_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Convert only for rendering. Stored values and calculation sums retain decimal precision."""
    return frame.map(lambda x: float(x) if isinstance(x, Decimal) else x)
