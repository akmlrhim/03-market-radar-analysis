"""Model TAM/SAM/SOM dari jumlah usaha dan ARPU bulanan."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


def market_value(pasar: pd.DataFrame, indikator: str) -> float | None:
    """Nilai indikator pertama yang cocok (pencarian substring)."""
    if pasar.empty or "indikator" not in pasar.columns:
        return None
    match = pasar[pasar["indikator"].astype(str).str.contains(indikator, case=False, na=False, regex=False)]
    if match.empty:
        return None
    value = pd.to_numeric(match.iloc[0]["nilai"], errors="coerce")
    if pd.isna(value):
        return None
    return float(value)


@dataclass(frozen=True)
class MarketModel:
    """Hasil perhitungan berjenjang, semuanya dalam satuan yang sama."""

    total_umkm: float
    target_umkm: float
    digital_umkm: float
    ai_ready_umkm: float
    som_customers: float
    arpu: float
    tam: float
    sam: float
    som: float
    target_pct: float
    digital_pct: float
    ai_pct: float
    share_pct: float


def _share(value: float, pct: float) -> float:
    return value * (pct / 100)


def market_model(
    umkm_millions: float,
    target_pct: float,
    digital_pct: float,
    ai_pct: float,
    arpu: float,
    share_pct: float,
) -> MarketModel:
    """Hitung TAM, SAM, dan SOM dari jumlah UMKM (juta) dan ARPU bulanan."""
    total = max(float(umkm_millions), 0.0) * 1_000_000
    target = _share(total, max(target_pct, 0.0))
    digital = _share(target, max(digital_pct, 0.0))
    ai_ready = _share(digital, max(ai_pct, 0.0))
    som_customers = _share(ai_ready, max(share_pct, 0.0))

    return MarketModel(
        total_umkm=total,
        target_umkm=target,
        digital_umkm=digital,
        ai_ready_umkm=ai_ready,
        som_customers=som_customers,
        arpu=float(arpu),
        tam=total * arpu * 12,
        sam=digital * arpu * 12,
        som=som_customers * arpu * 12,
        target_pct=target_pct,
        digital_pct=digital_pct,
        ai_pct=ai_pct,
        share_pct=share_pct,
    )


def stage_rows(model: MarketModel) -> list[tuple[str, float]]:
    """Tahapan corong pasar dari total UMKM sampai pengguna SOM."""
    return [
        ("Total UMKM", model.total_umkm),
        ("Target segmen", model.target_umkm),
        ("Siap digital", model.digital_umkm),
        ("Siap AI", model.ai_ready_umkm),
        ("Pengguna SOM", model.som_customers),
    ]
