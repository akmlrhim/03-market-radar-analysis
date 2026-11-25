"""Pecah dan bandingkan fitur utama kompetitor."""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

import pandas as pd

SPLIT_PATTERN = re.compile(r"[|;,]")


def feature_tokens(value: Any) -> list[str]:
    """Ambil daftar fitur dari kolom yang dipisah '|', ';', atau koma."""
    if value is None or (not isinstance(value, (list, tuple)) and pd.isna(value)):
        return []

    seen: set[str] = set()
    tokens: list[str] = []
    for part in SPLIT_PATTERN.split(str(value)):
        token = part.strip()
        if not token:
            continue
        key = token.lower()
        if key in seen:
            continue
        seen.add(key)
        tokens.append(token)
    return tokens


def feature_matrix(kompetitor: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(matriks boolean per kompetitor, ringkasan jumlah pemilik fitur)."""
    columns = ["id", "nama"]
    if kompetitor.empty:
        return pd.DataFrame(columns=columns), pd.DataFrame(columns=["fitur", "jumlah"])

    per_competitor: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    for _, row in kompetitor.iterrows():
        tokens = feature_tokens(row.get("fitur_utama"))
        counts.update(tokens)
        record: dict[str, Any] = {"id": row.get("id"), "nama": row.get("nama")}
        record.update(dict.fromkeys(tokens, True))
        per_competitor.append(record)

    features = sorted(counts, key=lambda fitur: (-counts[fitur], fitur.lower()))
    matrix = pd.DataFrame(per_competitor, columns=[*columns, *features])
    for feature in features:
        matrix[feature] = matrix[feature].eq(True)

    summary = (
        pd.DataFrame({"fitur": list(counts), "jumlah": list(counts.values())})
        .sort_values(["jumlah", "fitur"], ascending=[False, True])
        .reset_index(drop=True)
    )
    return matrix, summary


def feature_counts(kompetitor: pd.DataFrame) -> dict[int, int]:
    """Jumlah fitur per id kompetitor."""
    if kompetitor.empty:
        return {}
    return {
        int(row["id"]): len(feature_tokens(row.get("fitur_utama")))
        for _, row in kompetitor.iterrows()
        if pd.notna(row.get("id"))
    }


def with_feature_counts(monthly: pd.DataFrame, kompetitor: pd.DataFrame) -> pd.DataFrame:
    """Tempelkan jumlah fitur ke tabel harga bulanan."""
    if monthly.empty:
        return monthly.copy()
    counts = feature_counts(kompetitor)
    result = monthly.copy()
    result["jumlah_fitur"] = result["kompetitor_id"].map(
        lambda value: counts.get(int(value), 0) if pd.notna(value) else 0
    ).astype(int)
    return result
