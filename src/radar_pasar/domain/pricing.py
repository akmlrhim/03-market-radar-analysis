"""Normalisasi dan statistik harga kompetitor."""

from __future__ import annotations

import pandas as pd

COMPETITOR_COLUMNS = ["nama", "kategori", "segmen_target"]


def normalize_monthly(
    harga_idr: float | int | None,
    periode: str | None,
    model_harga: str | None,
) -> float | None:
    """Ekuivalen bulanan sebuah paket; ``None`` jika tidak bisa dibandingkan."""
    if harga_idr is None or pd.isna(harga_idr):
        return None
    try:
        value = float(harga_idr)
    except (TypeError, ValueError):
        return None
    if value <= 0:
        return None

    period = str(periode or "").strip().lower()
    model = str(model_harga or "").strip().lower()

    if "tahun" in period or period in {"yearly", "annual"}:
        return value / 12
    if "bulan" in period or period in {"monthly"}:
        return value
    if "sekali" in period or "sekali" in model or "proyek" in model:
        return None
    return None


def price_frame(kompetitor: pd.DataFrame, harga: pd.DataFrame) -> pd.DataFrame:
    """Gabungkan harga dengan kompetitor dan hitung ekuivalen bulanan."""
    frame = harga.copy()

    for column in ["id", "kompetitor_id", "nama_paket", "model_harga", "harga_idr", "periode"]:
        if column not in frame.columns:
            frame[column] = pd.NA

    if kompetitor.empty:
        for column in COMPETITOR_COLUMNS:
            frame[column] = pd.NA
    else:
        reference = kompetitor[["id", *COMPETITOR_COLUMNS]].rename(columns={"id": "_kompetitor_ref"})
        frame = frame.merge(
            reference,
            left_on="kompetitor_id",
            right_on="_kompetitor_ref",
            how="left",
        ).drop(columns=["_kompetitor_ref"])

    frame["harga_bulanan"] = [
        normalize_monthly(harga, periode, model)
        for harga, periode, model in zip(
            frame["harga_idr"], frame["periode"], frame["model_harga"], strict=False
        )
    ]
    return frame


def monthly_prices(kompetitor: pd.DataFrame, harga: pd.DataFrame) -> pd.DataFrame:
    """Hanya paket yang memiliki ekuivalen bulanan."""
    frame = price_frame(kompetitor, harga)
    if frame.empty:
        return frame
    result = frame[frame["harga_bulanan"].notna()].copy()
    result["harga_bulanan"] = result["harga_bulanan"].astype(float)
    return result.reset_index(drop=True)


def price_stats(kompetitor: pd.DataFrame, harga: pd.DataFrame) -> dict[str, float | int | None]:
    """Ringkasan harga bulanan: jumlah paket, termurah, median, tertinggi, cakupan."""
    monthly = monthly_prices(kompetitor, harga)
    total_kompetitor = len(kompetitor)

    if monthly.empty:
        return {
            "count": 0,
            "cheapest": None,
            "median": None,
            "expensive": None,
            "coverage": 0.0,
        }

    values = monthly["harga_bulanan"]
    dengan_harga = monthly["kompetitor_id"].nunique()
    coverage = float(dengan_harga / total_kompetitor) if total_kompetitor else 0.0

    return {
        "count": int(len(monthly)),
        "cheapest": float(values.min()),
        "median": float(values.median()),
        "expensive": float(values.max()),
        "coverage": coverage,
    }


def public_price_coverage(kompetitor: pd.DataFrame, harga: pd.DataFrame) -> tuple[int, int]:
    """(jumlah kompetitor dengan harga bulanan, total kompetitor)."""
    monthly = monthly_prices(kompetitor, harga)
    if monthly.empty:
        return 0, len(kompetitor)
    return int(monthly["kompetitor_id"].nunique()), len(kompetitor)


def price_percentile(monthly: pd.DataFrame, value: float) -> float:
    """Persentase paket bulanan yang harganya di bawah atau sama dengan ``value``."""
    if monthly.empty or "harga_bulanan" not in monthly.columns:
        return 0.0
    series = monthly["harga_bulanan"].dropna()
    if series.empty:
        return 0.0
    return float((series <= value).mean() * 100)


def nearest_package(monthly: pd.DataFrame, value: float) -> dict[str, object] | None:
    """Paket dengan harga terdekat dari ``value``."""
    if monthly.empty or "harga_bulanan" not in monthly.columns:
        return None
    series = monthly["harga_bulanan"].dropna()
    if series.empty:
        return None
    index = (series - value).abs().idxmin()
    row = monthly.loc[index]
    return {
        "nama": row.get("nama"),
        "nama_paket": row.get("nama_paket"),
        "kategori": row.get("kategori"),
        "harga_bulanan": float(row["harga_bulanan"]),
        "selisih": float(row["harga_bulanan"] - value),
    }


def position_label(percentile: float) -> str:
    """Label posisi harga terhadap sebaran pasar."""
    if percentile <= 25:
        return "Paling murah"
    if percentile <= 50:
        return "Di bawah median"
    if percentile <= 75:
        return "Di atas median"
    return "Premium"


def _round_price(value: float) -> int:
    """Bulatkan ke kelipatan Rp10.000 terdekat."""
    if value <= 0:
        return 10_000
    return int(round(value / 10_000) * 10_000)


def recommended_tiers(kompetitor: pd.DataFrame, harga: pd.DataFrame) -> list[dict[str, object]]:
    """Rentang harga dari persentil pasar, bukan dari survei kemauan bayar."""
    monthly = monthly_prices(kompetitor, harga)
    if monthly.empty:
        return []

    values = monthly["harga_bulanan"]
    quotas = [("Starter", 0.25), ("Pro", 0.50), ("Business", 0.75)]
    prices: list[int] = []
    for _, quota in quotas:
        price = _round_price(float(values.quantile(quota)))
        if prices and price <= prices[-1]:
            price = prices[-1] + 10_000
        prices.append(price)

    return [
        {
            "paket": paket,
            "harga": price,
            "persentil": quota * 100,
            "posisi": position_label(price_percentile(monthly, price)),
        }
        for (paket, quota), price in zip(quotas, prices, strict=True)
    ]
