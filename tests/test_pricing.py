"""Uji normalisasi dan statistik harga."""

from __future__ import annotations

import pandas as pd

from radar_pasar.domain.pricing import (
    monthly_prices,
    normalize_monthly,
    price_percentile,
    price_stats,
    recommended_tiers,
)


def _frames() -> tuple[pd.DataFrame, pd.DataFrame]:
    kompetitor = pd.DataFrame(
        [
            {"id": 1, "nama": "Murah", "kategori": "Chatbot WA", "segmen_target": "UMKM"},
            {"id": 2, "nama": "Mahal", "kategori": "CRM AI", "segmen_target": "Keduanya"},
        ]
    )
    harga = pd.DataFrame(
        [
            {
                "id": 1,
                "kompetitor_id": 1,
                "nama_paket": "Lite",
                "model_harga": "Langganan",
                "harga_idr": 100_000,
                "periode": "Bulanan",
                "batasan": "",
                "biaya_tambahan": "Biaya pesan",
                "sumber_url": "",
                "tanggal_cek": None,
            },
            {
                "id": 2,
                "kompetitor_id": 2,
                "nama_paket": "Tahunan",
                "model_harga": "Langganan",
                "harga_idr": 2_400_000,
                "periode": "Tahunan",
                "batasan": "",
                "biaya_tambahan": "",
                "sumber_url": "",
                "tanggal_cek": None,
            },
            {
                "id": 3,
                "kompetitor_id": 2,
                "nama_paket": "Proyek",
                "model_harga": "Proyek",
                "harga_idr": 5_000_000,
                "periode": "Sekali",
                "batasan": "",
                "biaya_tambahan": "",
                "sumber_url": "",
                "tanggal_cek": None,
            },
        ]
    )
    return kompetitor, harga


def test_normalize_monthly_handles_each_period() -> None:
    assert normalize_monthly(1_200_000, "Tahunan", "Langganan") == 100_000
    assert normalize_monthly(150_000, "Bulanan", "Langganan") == 150_000
    assert normalize_monthly(500_000, "Sekali", "Sekali bayar") is None
    assert normalize_monthly(5_000_000, "Sekali", "Proyek") is None
    assert normalize_monthly(None, "Bulanan", "Langganan") is None
    assert normalize_monthly(0, "Bulanan", "Langganan") is None


def test_monthly_prices_only_keeps_comparable_packages() -> None:
    kompetitor, harga = _frames()
    df = monthly_prices(kompetitor, harga)

    assert len(df) == 2
    assert set(df["nama_paket"]) == {"Lite", "Tahunan"}
    assert df.loc[df["nama_paket"] == "Tahunan", "harga_bulanan"].iloc[0] == 200_000


def test_price_stats_summarises_market() -> None:
    kompetitor, harga = _frames()
    stats = price_stats(kompetitor, harga)

    assert stats["count"] == 2
    assert stats["cheapest"] == 100_000
    assert stats["expensive"] == 200_000
    assert stats["median"] == 150_000
    assert stats["coverage"] == 1.0


def test_price_percentile_counts_packages_at_or_below() -> None:
    kompetitor, harga = _frames()
    df = monthly_prices(kompetitor, harga)

    assert price_percentile(df, 50_000) == 0.0
    assert price_percentile(df, 100_000) == 50.0
    assert price_percentile(df, 10_000_000) == 100.0


def test_recommended_tiers_are_ordered_and_rounded() -> None:
    kompetitor, harga = _frames()
    tiers = recommended_tiers(kompetitor, harga)

    assert [tier["paket"] for tier in tiers] == ["Starter", "Pro", "Business"]
    prices = [tier["harga"] for tier in tiers]
    assert prices == sorted(prices)
    assert len(set(prices)) == len(prices)
    assert all(price % 10_000 == 0 for price in prices)


def test_recommended_tiers_empty_without_prices() -> None:
    kompetitor, _ = _frames()
    empty = pd.DataFrame(columns=["id", "kompetitor_id", "harga_idr", "periode", "model_harga"])

    assert recommended_tiers(kompetitor, empty) == []
