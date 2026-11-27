"""Uji tampilan tabel harga paket."""

from __future__ import annotations

import pandas as pd

from radar_pasar.presentation.components import effective_cost_view, price_table_view


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


def test_effective_cost_view_breaks_down_extra_costs() -> None:
    frame = pd.DataFrame(
        [
            {
                "nama": "Contoh",
                "nama_paket": "Lite",
                "harga_idr": 499_000,
                "harga_bulanan": 499_000.0,
                "periode": "Bulanan",
                "biaya_tambahan": "Belum termasuk PPN; biaya pesan WhatsApp; add-on agen Rp59.000",
            },
            {
                "nama": "Contoh",
                "nama_paket": "Pro",
                "harga_idr": 299_000,
                "harga_bulanan": 299_000.0,
                "periode": "Bulanan",
                "biaya_tambahan": "  ",
            },
        ]
    )

    view = effective_cost_view(frame)

    assert len(view) == 1
    assert view["Harga paket"].iloc[0] == "Rp499.000"
    assert view["Komponen di luar paket"].iloc[0] == "PPN, Pesan/kuota, Agen/add-on"
    assert view["Estimasi total bulanan"].iloc[0] == (
        "Rp499.000 + PPN, Pesan/kuota, Agen/add-on"
    )


def test_effective_cost_view_without_monthly_equivalent() -> None:
    frame = pd.DataFrame(
        [
            {
                "nama": "Contoh",
                "nama_paket": "Custom",
                "harga_idr": None,
                "harga_bulanan": None,
                "biaya_tambahan": "Harga via sales; implementasi terpisah",
            }
        ]
    )

    view = effective_cost_view(frame)

    assert view["Harga paket"].iloc[0] == "Hubungi sales"
    assert view["Estimasi total bulanan"].iloc[0] == "—"
