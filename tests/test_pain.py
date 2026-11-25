"""Uji analisis pain point."""

from __future__ import annotations

import pandas as pd

from radar_pasar.domain.pain import (
    hambatan_counts,
    pain_rankings,
    van_westendorp,
    wtp_by_segment,
)


def _pain() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "segmen": "UMKM",
                "tema": "Respons chat lambat",
                "masalah": "Membalas chat terlalu lama",
                "budget_bulanan_idr": 100_000,
                "hambatan": "Harga",
                "harga_terlalu_murah": 50_000,
                "harga_murah": 150_000,
                "harga_mahal": 400_000,
                "harga_terlalu_mahal": 750_000,
            },
            {
                "segmen": "UMKM",
                "tema": "Respons chat lambat",
                "masalah": "Chat masuk di luar jam kerja",
                "budget_bulanan_idr": 150_000,
                "hambatan": "Harga",
                "harga_terlalu_murah": 75_000,
                "harga_murah": 200_000,
                "harga_mahal": 500_000,
                "harga_terlalu_mahal": 1_000_000,
            },
            {
                "segmen": "Freelancer",
                "tema": "Administrasi manual",
                "masalah": "Membuat invoice manual",
                "budget_bulanan_idr": 75_000,
                "hambatan": "Ribet setup",
                "harga_terlalu_murah": 40_000,
                "harga_murah": 120_000,
                "harga_mahal": 350_000,
                "harga_terlalu_mahal": 700_000,
            },
        ]
    )


def test_pain_rankings_group_by_theme() -> None:
    ranking = pain_rankings(_pain())

    assert ranking.iloc[0]["masalah"] == "Respons chat lambat"
    assert int(ranking.iloc[0]["jumlah"]) == 2


def test_pain_rankings_falls_back_to_masalah_column() -> None:
    pain = _pain().drop(columns=["tema"])
    ranking = pain_rankings(pain)

    assert len(ranking) == 3


def test_pain_rankings_empty_frame() -> None:
    assert pain_rankings(pd.DataFrame()).empty


def test_hambatan_counts_sorted_descending() -> None:
    counts = hambatan_counts(_pain())

    assert counts.iloc[0]["hambatan"] == "Harga"
    assert int(counts.iloc[0]["jumlah"]) == 2


def test_wtp_by_segment_buckets_budget() -> None:
    wtp = wtp_by_segment(_pain())

    assert set(wtp["segmen"]) == {"UMKM", "Freelancer"}
    assert int(wtp["jumlah"].sum()) == 3


def test_van_westendorp_returns_ordered_points() -> None:
    result = van_westendorp(_pain())

    assert result is not None
    assert result["responden"] == 3
    points = result["points"]
    assert points["PMC"] is not None
    assert points["PME"] is not None
    assert points["PMC"] < points["PME"]
    assert 0 < points["OPP"] < points["PME"]
    assert set(result["curves"]["kurva"]) == {
        "Terlalu murah",
        "Murah",
        "Mahal",
        "Terlalu mahal",
    }


def test_van_westendorp_needs_three_respondents() -> None:
    pain = _pain().head(2)

    assert van_westendorp(pain) is None


def test_van_westendorp_ignores_incomplete_rows() -> None:
    pain = _pain()
    pain.loc[0, "harga_mahal"] = None

    # Dua responden lengkap masih di bawah ambang minimal tiga.
    assert van_westendorp(pain) is None


def test_wtp_labels_are_stable() -> None:
    wtp = wtp_by_segment(_pain())
    labels = list(wtp["rentang"].cat.categories)

    assert labels[0] == "≤50 rb"
    assert labels[-1] == ">1 jt"
    assert len(labels) == 8
