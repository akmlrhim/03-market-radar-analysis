"""Uji integritas dataset CSV: hanya data terverifikasi yang boleh dipakai."""

from __future__ import annotations

import pandas as pd
import pytest

from radar_pasar.config import DATA_DIR
from radar_pasar.data.schema import TABLE_COLUMNS


def _read(name: str) -> pd.DataFrame:
    path = DATA_DIR / f"{name}.csv"
    if not path.exists():
        pytest.skip(f"{path} belum ada")
    return pd.read_csv(path, dtype=str, keep_default_na=False, na_values=[""])


def test_competitor_columns_match_schema() -> None:
    frame = _read("kompetitor")

    assert list(frame.columns) == TABLE_COLUMNS["kompetitor"]


def test_all_competitors_are_verified() -> None:
    """Data yang tidak bisa dipertanggungjawabkan tidak boleh tampil di dashboard."""
    frame = _read("kompetitor")
    unverified = frame[frame["status_verifikasi"] != "Terverifikasi"]

    assert unverified.empty, "Kompetitor belum terverifikasi: " + ", ".join(
        unverified["nama"].tolist()
    )


def test_every_competitor_has_a_source_url() -> None:
    frame = _read("kompetitor")

    assert frame["sumber_url"].fillna("").str.startswith("http").all()
    assert frame["tanggal_cek"].notna().all()


def test_prices_reference_known_competitors() -> None:
    kompetitor = _read("kompetitor")
    harga = _read("harga")
    known = set(kompetitor["id"].astype(int))
    orphans = sorted(set(harga["kompetitor_id"].astype(int)) - known)

    assert orphans == [], f"kompetitor_id tanpa induk: {orphans}"


def test_price_rows_have_sources() -> None:
    harga = _read("harga")

    assert harga["sumber_url"].fillna("").str.startswith("http").all()


def test_every_competitor_has_at_least_one_price_row() -> None:
    kompetitor = _read("kompetitor")
    harga = _read("harga")
    priced = set(harga["kompetitor_id"].astype(int))
    missing = kompetitor[~kompetitor["id"].astype(int).isin(priced)]

    assert missing.empty, "Kompetitor tanpa baris harga: " + ", ".join(missing["nama"])
