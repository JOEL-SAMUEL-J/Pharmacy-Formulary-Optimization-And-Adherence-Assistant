"""Deterministic header and value normalization."""
import re
from decimal import Decimal, InvalidOperation

def column_name(value: str) -> str:
    value = value.replace("\ufeff", "").strip().lower()
    return re.sub(r"[^a-z0-9]+", "_", value).strip("_")

def normalize_row(raw, aliases):
    return {aliases.get(column_name(k or ""), column_name(k or "")): (v or "").strip()
            for k, v in raw.items()}

def canonical_value(value: str, kind: str) -> str:
    if not value:
        return ""
    try:
        if kind == "integer":
            number = Decimal(value)
            return str(int(number)) if number == number.to_integral_value() else value
        if kind == "decimal":
            return format(Decimal(value), "f")
    except (InvalidOperation, ValueError):
        pass
    return value
