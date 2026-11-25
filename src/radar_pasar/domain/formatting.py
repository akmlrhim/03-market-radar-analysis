"""Format angka dan rupiah dengan gaya Indonesia."""

from __future__ import annotations

import pandas as pd


def _clean(value: float | int | None) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)


def _grouped(value: float, decimals: int = 0) -> str:
    text = f"{value:,.{decimals}f}"
    return text.replace(",", "_").replace(".", ",").replace("_", ".")


def rupiah(value: float | int | None) -> str:
    """Rupiah tanpa desimal, pemisah ribuan titik."""
    number_value = _clean(value)
    if number_value is None:
        return "—"
    return f"Rp{_grouped(round(number_value))}"


def rupiah_compact(value: float | int | None) -> str:
    """Rupiah ringkas: rb, jt, M, T dengan koma desimal."""
    number_value = _clean(value)
    if number_value is None:
        return "—"

    magnitude = abs(number_value)
    for threshold, suffix in ((1e12, "T"), (1e9, "M"), (1e6, "jt"), (1e3, "rb")):
        if magnitude >= threshold:
            scaled = number_value / threshold
            text = f"{scaled:.2f}".rstrip("0").rstrip(".")
            return f"Rp{text.replace('.', ',')} {suffix}"
    return rupiah(number_value)


def number(value: float | int | None, decimals: int = 0) -> str:
    """Angka dengan pemisah ribuan titik."""
    number_value = _clean(value)
    if number_value is None:
        return "—"
    return _grouped(number_value, decimals)


def decimal(value: float | int | None, places: int = 2) -> str:
    """Angka desimal dengan koma sebagai pemisah."""
    number_value = _clean(value)
    if number_value is None:
        return "—"
    return f"{number_value:.{places}f}".replace(".", ",")
