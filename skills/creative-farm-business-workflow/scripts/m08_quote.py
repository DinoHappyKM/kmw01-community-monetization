"""Decimal cost arithmetic only. No market pricing, quote approval or external writes."""
import argparse
import json
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

def amount(value):
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError("boolean is not a price or quantity")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError):
        raise ValueError("invalid numeric value")
    if not result.is_finite() or result < 0:
        raise ValueError("values must be finite and nonnegative")
    return result

def formatted(value):
    if value is None:
        return None
    return str(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

def calculate(data):
    if not isinstance(data, dict) or not isinstance(data.get("items"), list) or not data["items"]:
        raise ValueError("provide a nonempty items list")
    cash = Decimal(0)
    labor = Decimal(0)
    hours = Decimal(0)
    hours_unknown = False
    missing = []
    for item in data["items"]:
        if item.get("kind") not in {"cash", "labor"} or not item.get("name"):
            raise ValueError("each item needs name and kind cash/labor")
        quantity = amount(item.get("quantity"))
        unit_cost = amount(item.get("unit_cost"))
        if item["kind"] == "labor":
            if quantity is None:
                hours_unknown = True
            else:
                hours += quantity
        if quantity is None or unit_cost is None:
            missing.append(item["name"])
            continue
        subtotal = quantity * unit_cost
        if item["kind"] == "labor":
            labor += subtotal
        else:
            cash += subtotal
    price = amount(data.get("price"))
    complete = not missing
    total = cash + labor if complete else None
    balance = price - total if price is not None and total is not None else None
    valid_hours = complete and not hours_unknown and hours > 0
    return {
        "status": "scenario_costs_complete" if complete else "incomplete_costs",
        "cash_known_subtotal": formatted(cash),
        "labor_known_subtotal": formatted(labor),
        "known_subtotal": formatted(cash + labor),
        "total_cost": formatted(total),
        "price": formatted(price),
        "balance_after_labor": formatted(balance),
        "balance_rate_percent": formatted(balance / price * 100) if balance is not None and price > 0 else None,
        "total_hours": None if hours_unknown else formatted(hours),
        "cash_return_per_hour_before_labor": formatted((price-cash)/hours) if valid_hours and price is not None else None,
        "balance_per_hour_after_labor": formatted(balance/hours) if valid_hours and balance is not None else None,
        "missing_costs": missing,
        "exclusions": data.get("exclusions", []),
        "scope": "arithmetic_only_not_formal_quote_or_net_profit"
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    args = parser.parse_args()
    try:
        result = calculate(json.loads(Path(args.input).read_text(encoding="utf-8")))
    except (ValueError, OSError, TypeError) as error:
        print(json.dumps({"status":"invalid_input","error":str(error)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
