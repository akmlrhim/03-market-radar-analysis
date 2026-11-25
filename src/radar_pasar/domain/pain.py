"""Peringkat masalah, kemauan bayar, dan analisis Van Westendorp."""

from __future__ import annotations

import numpy as np
import pandas as pd

WTP_LABELS = [
    "≤50 rb",
    "50-100 rb",
    "100-150 rb",
    "150-250 rb",
    "250-400 rb",
    "400-600 rb",
    "600 rb-1 jt",
    ">1 jt",
]

_WTP_LIMITS = [50_000, 100_000, 150_000, 250_000, 400_000, 600_000, 1_000_000]

VW_COLUMNS = ["harga_terlalu_murah", "harga_murah", "harga_mahal", "harga_terlalu_mahal"]
VW_CURVES = ["Terlalu murah", "Murah", "Mahal", "Terlalu mahal"]
MIN_RESPONDEN = 3


def _wtp_bucket(value: float) -> str:
    """Kelompokkan budget bulanan ke rentang yang tampil di sumbu."""
    for label, limit in zip(WTP_LABELS, _WTP_LIMITS, strict=False):
        if value <= limit:
            return label
    return WTP_LABELS[-1]


def _wtp_empty() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "segmen": pd.Series(dtype="object"),
            "rentang": pd.Series(pd.Categorical([], categories=WTP_LABELS, ordered=True)),
            "jumlah": pd.Series(dtype="int64"),
        }
    )


def pain_rankings(pain: pd.DataFrame) -> pd.DataFrame:
    """Peringkat tema masalah; jatuh ke kolom ``masalah`` bila tema kosong."""
    columns = ["masalah", "jumlah"]
    if pain.empty:
        return pd.DataFrame(columns=columns)

    tema = pain["tema"].astype(str).str.strip() if "tema" in pain.columns else pd.Series("", index=pain.index)
    masalah = (
        pain["masalah"].astype(str).str.strip()
        if "masalah" in pain.columns
        else pd.Series("", index=pain.index)
    )
    label = tema.where(tema.ne("") & tema.ne("nan"), masalah)
    label = label[label.ne("") & label.ne("nan")]
    if label.empty:
        return pd.DataFrame(columns=columns)

    ranking = label.value_counts().rename_axis("masalah").reset_index(name="jumlah")
    return ranking.sort_values(["jumlah", "masalah"], ascending=[False, True]).reset_index(drop=True)


def hambatan_counts(pain: pd.DataFrame) -> pd.DataFrame:
    """Jumlah responden per hambatan adopsi, terbanyak lebih dulu."""
    columns = ["hambatan", "jumlah"]
    if pain.empty or "hambatan" not in pain.columns:
        return pd.DataFrame(columns=columns)

    label = pain["hambatan"].astype(str).str.strip()
    label = label[label.ne("") & label.ne("nan")]
    if label.empty:
        return pd.DataFrame(columns=columns)

    counts = label.value_counts().rename_axis("hambatan").reset_index(name="jumlah")
    return counts.sort_values(["jumlah", "hambatan"], ascending=[False, True]).reset_index(drop=True)


def wtp_by_segment(pain: pd.DataFrame) -> pd.DataFrame:
    """Sebaran kemauan bayar bulanan per segmen dalam delapan rentang tetap."""
    if pain.empty or "budget_bulanan_idr" not in pain.columns:
        return _wtp_empty()

    budget = pd.to_numeric(pain["budget_bulanan_idr"], errors="coerce")
    mask = budget.notna()
    if not mask.any():
        return _wtp_empty()

    segmen = (
        pain["segmen"].astype(str).str.strip()
        if "segmen" in pain.columns
        else pd.Series("", index=pain.index)
    )
    frame = pd.DataFrame(
        {
            "segmen": segmen[mask].to_numpy(),
            "rentang": pd.Categorical(budget[mask].map(_wtp_bucket), categories=WTP_LABELS, ordered=True),
        }
    )
    return (
        frame.groupby(["segmen", "rentang"], observed=False)
        .size()
        .rename("jumlah")
        .reset_index()
    )


def _complete_rows(pain: pd.DataFrame) -> pd.DataFrame:
    """Baris dengan empat titik harga Van Westendorp yang lengkap dan positif."""
    if pain.empty or any(column not in pain.columns for column in VW_COLUMNS):
        return pd.DataFrame(columns=VW_COLUMNS)

    frame = pain[VW_COLUMNS].apply(pd.to_numeric, errors="coerce")
    frame = frame[(frame > 0).all(axis=1)].dropna()
    return frame.reset_index(drop=True)


def _curves(frame: pd.DataFrame) -> pd.DataFrame:
    """Empat kurva kumulatif pada titik harga yang diamati."""
    anchors = np.unique(frame.to_numpy(dtype=float).ravel())
    grid = np.unique(np.concatenate(([0.0], anchors)))
    terlalu_murah, murah, mahal, terlalu_mahal = (
        frame[column].to_numpy(dtype=float) for column in VW_COLUMNS
    )

    rows: list[dict[str, object]] = []
    for harga in grid:
        values = {
            "Terlalu murah": float((terlalu_murah >= harga).mean() * 100),
            "Murah": float((murah >= harga).mean() * 100),
            "Mahal": float((mahal <= harga).mean() * 100),
            "Terlalu mahal": float((terlalu_mahal <= harga).mean() * 100),
        }
        for kurva, persen in values.items():
            rows.append({"harga": float(harga), "kurva": kurva, "persen": persen})
    return pd.DataFrame(rows, columns=["harga", "kurva", "persen"])


def _crossing(grid: np.ndarray, first: np.ndarray, second: np.ndarray) -> float | None:
    """Titik potong dua kurva, diinterpolasi melewati dataran nol."""
    diff = first - second
    previous: tuple[float, float] | None = None
    for harga, value in zip(grid, diff, strict=True):
        if value == 0:
            continue
        if previous is not None and (previous[1] > 0) != (value > 0):
            x0, d0 = previous
            return float(x0 + (harga - x0) * (-d0) / (value - d0))
        previous = (float(harga), float(value))
    return None


def _median_points(frame: pd.DataFrame) -> dict[str, float]:
    """Titik cadangan dari median, dipakai saat kurva tidak berpotongan."""
    terlalu_murah, murah, mahal, terlalu_mahal = (
        float(frame[column].median()) for column in VW_COLUMNS
    )
    return {
        "PMC": float(np.sqrt(terlalu_murah * murah)),
        "OPP": float(np.sqrt(murah * mahal)),
        "IDP": mahal,
        "PME": float(np.sqrt(mahal * terlalu_mahal)),
    }


def _round_price(value: float) -> int:
    return int(round(value / 1_000) * 1_000)


def van_westendorp(pain: pd.DataFrame) -> dict[str, object] | None:
    """Titik PMC, OPP, IDP, dan PME beserta kurvanya.

    ``None`` bila responden lengkap kurang dari tiga, karena kurva yang
    digambar dari satu-dua jawaban tidak bisa ditafsirkan.
    """
    frame = _complete_rows(pain)
    if len(frame) < MIN_RESPONDEN:
        return None

    curves = _curves(frame)
    grid = np.unique(curves["harga"].to_numpy(dtype=float))
    terlalu_murah, murah, mahal, terlalu_mahal = [
        np.array([(frame[column].to_numpy(dtype=float) >= harga).mean() for harga in grid])
        for column in VW_COLUMNS
    ]

    points = {
        "PMC": _crossing(grid, terlalu_murah, 1 - murah),
        "OPP": _crossing(grid, terlalu_murah, terlalu_mahal),
        "IDP": _crossing(grid, murah, mahal),
        "PME": _crossing(grid, 1 - mahal, terlalu_mahal),
    }
    fallback = _median_points(frame)
    resolved = {
        key: value if value is not None and value > 0 else fallback[key]
        for key, value in points.items()
    }

    if not (0 < resolved["PMC"] < resolved["OPP"] < resolved["PME"]):
        resolved = fallback
    if not (resolved["OPP"] < resolved["IDP"] < resolved["PME"]):
        resolved["IDP"] = float(np.sqrt(resolved["OPP"] * resolved["PME"]))

    return {
        "responden": int(len(frame)),
        "points": {key: _round_price(value) for key, value in resolved.items()},
        "curves": curves,
    }
