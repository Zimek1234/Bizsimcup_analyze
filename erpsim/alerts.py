"""Configurable in-app alerts. No email, SAP writes or guessed unit conversion."""
from datetime import datetime, timezone
from decimal import Decimal
from .analytics import aggregate

DEFAULTS = {"enabled": True, "stock_enabled": True, "stock_limit": 1000.0, "stock_unit": "ST",
            "margin_enabled": True, "margin_limit": 10.0,
            "marketing_enabled": False, "marketing_limit": 10000.0, "marketing_currency": "EUR",
            "stale_enabled": True, "stale_minutes": 10.0, "area_mapping": False}


def evaluate(sales, inventory, marketing, runs, settings, now=None):
    cfg = DEFAULTS | settings
    if not cfg["enabled"]:
        return []
    alerts = []
    if cfg["stock_enabled"]:
        for row in inventory:
            if row["unit"] == cfg["stock_unit"] and row["stock"] is not None and row["stock"] <= Decimal(str(cfg["stock_limit"])):
                alerts.append({"Typ": "Zásoba", "Detail": f"{row['product']} · lokace {row['location']}: "
                               f"{row['stock']} {row['unit']} ≤ {cfg['stock_limit']}"})
    if cfg["margin_enabled"] and sales:
        group = aggregate(sales, ["organization", "product", "area", "channel", "currency", "unit"], ["revenue", "contribution"])
        for row in group.to_dict("records"):
            margin = row["margin_pct"]
            if margin is not None and margin < Decimal(str(cfg["margin_limit"])):
                alerts.append({"Typ": "Příspěvek", "Detail": f"{row['product']} · {row['area']} · kanál {row['channel']} · {row['currency']}: "
                               f"(NET_VALUE − COST) / NET_VALUE = {margin:.2f}% < {cfg['margin_limit']}%"})
    if cfg["marketing_enabled"] and marketing:
        group = aggregate(marketing, ["organization", "product", "area", "round", "step", "currency"], ["marketing"])
        for row in group.to_dict("records"):
            if row["currency"] == cfg["marketing_currency"] and row["marketing"] > Decimal(str(cfg["marketing_limit"])):
                alerts.append({"Typ": "Marketing", "Detail": f"{row['product']} · {row['area']} · "
                               f"kolo {row['round']}/den {row['step']}: {row['marketing']} {row['currency']} > {cfg['marketing_limit']}"})
    if cfg["stale_enabled"]:
        now = now or datetime.now(timezone.utc)
        latest = {}
        success = {}
        for run in runs:
            latest.setdefault(run["dataset"], run)
            if run["status"] == "success":
                success.setdefault(run["dataset"], run)
        for dataset, last in latest.items():
            if last["source"] != "odata":
                continue  # Historical files do not pretend to be live feeds.
            ok = success.get(dataset)
            if ok is None:
                alerts.append({"Typ": "Aktualizace", "Detail": f"{dataset}: zatím žádné úspěšné čtení."})
            elif (now - datetime.fromisoformat(ok["finished_at"])).total_seconds() > cfg["stale_minutes"] * 60:
                alerts.append({"Typ": "Aktualizace", "Detail": f"{dataset}: data starší než {cfg['stale_minutes']} minut."})
    return alerts
