"""Uji model TAM/SAM/SOM."""

from __future__ import annotations

import pandas as pd
import pytest

from radar_pasar.domain.market import market_model, market_value, stage_rows


def test_market_value_reads_first_matching_indicator() -> None:
    pasar = pd.DataFrame(
        [
            {"indikator": "Jumlah UMKM non-pertanian", "nilai": 30.21},
            {"indikator": "Budget software UMKM", "nilai": 150_000},
        ]
    )

    assert market_value(pasar, "Jumlah UMKM") == 30.21
    assert market_value(pasar, "Budget software") == 150_000
    assert market_value(pasar, "tidak ada") is None
    assert market_value(pd.DataFrame(), "Jumlah UMKM") is None


def test_market_model_nests_each_stage() -> None:
    model = market_model(
        umkm_millions=30.0,
        target_pct=10.0,
        digital_pct=50.0,
        ai_pct=20.0,
        arpu=100_000,
        share_pct=5.0,
    )

    assert model.total_umkm == pytest.approx(30_000_000)
    assert model.target_umkm == pytest.approx(3_000_000)
    assert model.digital_umkm == pytest.approx(1_500_000)
    assert model.ai_ready_umkm == pytest.approx(300_000)
    assert model.som_customers == pytest.approx(15_000)
    assert model.tam == pytest.approx(30_000_000 * 100_000 * 12)
    assert model.som == pytest.approx(15_000 * 100_000 * 12)
    assert model.tam > model.sam > model.som


def test_stage_rows_keep_funnel_order() -> None:
    model = market_model(30.0, 20.0, 50.0, 60.0, 150_000, 2.0)
    stages = stage_rows(model)

    assert [label for label, _ in stages] == [
        "Total UMKM",
        "Target segmen",
        "Siap digital",
        "Siap AI",
        "Pengguna SOM",
    ]
    values = [value for _, value in stages]
    assert values == sorted(values, reverse=True)


def test_market_model_rejects_zero_division_in_share() -> None:
    model = market_model(30.0, 20.0, 50.0, 60.0, 150_000, 0.0)

    assert model.som == 0
    assert model.tam > 0
