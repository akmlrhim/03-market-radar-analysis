"""Uji tampilan tabel harga paket."""

from __future__ import annotations

import pandas as pd

from radar_pasar.presentation.components import price_table_view


def test_price_table_view_formats_rupiah_and_monthly_equivalent() -> None:
    frame = pd.DataFrame(
        [
            {
                "nama": "Contoh",
                "kategori": "Chatbot WA",
                "nama_paket": "Lite",
                "model_harga": "Langganan",
                "harga_idr": 1_234_500,
                "periode": "Bulanan",
                "harga_bulanan": 1_234_500.0,
            }
        ]
    )

    view = price_table_view(frame)

    assert view["Harga"].iloc[0] == "Rp1.234.500"
    assert view["Ekuivalen bulanan"].iloc[0] == "Rp1.234.500"


def test_price_table_view_marks_missing_prices() -> None:
    frame = pd.DataFrame(
        [
            {
                "nama": "Contoh",
                "nama_paket": "Enterprise",
                "harga_idr": None,
                "harga_bulanan": None,
            }
        ]
    )

    view = price_table_view(frame)

    assert view["Harga"].iloc[0] == "Hubungi sales"
    assert view["Ekuivalen bulanan"].iloc[0] == "—"
