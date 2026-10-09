"""Structural checks for acquired daily prices; not independent accuracy verification."""

from datetime import date
import math


def validate_prices(rows: list[dict], ticker: str, start: date, cutoff: date) -> dict:
    errors, seen = [], set()
    if not rows:
        errors.append("No daily prices returned")
    for i, row in enumerate(rows):
        prefix = f"Row {i}"
        try:
            session_date = date.fromisoformat(row["date"])
            if not start <= session_date <= cutoff:
                errors.append(f"{prefix}: date outside completed-day range")
            if session_date in seen:
                errors.append(f"{prefix}: duplicate session date")
            seen.add(session_date)
        except (KeyError, TypeError, ValueError):
            errors.append(f"{prefix}: invalid date")
        if row.get("ticker") != ticker:
            errors.append(f"{prefix}: ticker mismatch")
        numbers = [row.get(f) for f in ("open", "high", "low", "close")]
        if any(not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v) or v <= 0 for v in numbers):
            errors.append(f"{prefix}: missing or invalid OHLC")
        else:
            opening, high, low, closing = numbers
            if not low <= min(opening, closing) <= max(opening, closing) <= high:
                errors.append(f"{prefix}: inconsistent OHLC range")
        volume = row.get("volume")
        if not isinstance(volume, (int, float)) or isinstance(volume, bool) or not math.isfinite(volume) or volume < 0 or int(volume) != volume:
            errors.append(f"{prefix}: invalid volume")
    return {"valid": not errors, "row_count": len(rows), "errors": errors,
            "warnings": ["Prices have not been cross-checked against an independent source.",
                         "Yahoo OHLC adjustment basis is not yet verified; do not describe it as raw/adjusted or total return.",
                         "All current-day observations are excluded conservatively, including after market close."]}
