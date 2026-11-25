"""Uji kontrak data dan deteksi gap."""

from __future__ import annotations

import pandas as pd

from radar_pasar.data.schema import TABLE_COLUMNS, coerce_table, empty_frame
from radar_pasar.domain.features import feature_matrix, feature_tokens
from radar_pasar.domain.gaps import gap_findings


def test_empty_frame_has_full_schema() -> None:
    frame = empty_frame("harga")

    assert list(frame.columns) == TABLE_COLUMNS["harga"]
    assert frame.empty


def test_coerce_table_fills_missing_columns_and_types() -> None:
    raw = pd.DataFrame(
        [
            {
                "id": "1",
                "nama": "Contoh",
                "bahasa_indonesia": "ya",
                "tanggal_cek": "2026-11-25",
                "tahun_berdiri": "2020",
            }
        ]
    )
    frame = coerce_table("kompetitor", raw)

    assert list(frame.columns) == TABLE_COLUMNS["kompetitor"]
    assert frame.loc[0, "nama"] == "Contoh"
    assert frame.loc[0, "website"] == ""
    assert bool(frame.loc[0, "bahasa_indonesia"]) is True
    assert frame.loc[0, "tahun_berdiri"] == 2020
    assert str(frame.loc[0, "tanggal_cek"]) == "2026-11-25"


def test_coerce_table_maps_boolean_variants() -> None:
    raw = pd.DataFrame(
        [{"id": "1", "nama": "A", "bahasa_indonesia": "tidak"}, {"id": "2", "nama": "B"}]
    )
    frame = coerce_table("kompetitor", raw)

    assert bool(frame.loc[0, "bahasa_indonesia"]) is False
    assert pd.isna(frame.loc[1, "bahasa_indonesia"])


def test_feature_tokens_deduplicates_and_splits() -> None:
    tokens = feature_tokens("AI agent | Broadcast; AI agent, WABA")

    assert tokens == ["AI agent", "Broadcast", "WABA"]
    assert feature_tokens(None) == []


def test_feature_matrix_counts_owners() -> None:
    kompetitor = pd.DataFrame(
        [
            {"id": 1, "nama": "A", "fitur_utama": "Chat | Broadcast"},
            {"id": 2, "nama": "B", "fitur_utama": "Chat"},
        ]
    )
    matrix, summary = feature_matrix(kompetitor)

    assert list(matrix["nama"]) == ["A", "B"]
    assert bool(matrix.loc[0, "Chat"]) is True
    assert bool(matrix.loc[1, "Broadcast"]) is False
    assert summary.iloc[0]["fitur"] == "Chat"
    assert int(summary.iloc[0]["jumlah"]) == 2


def test_gap_findings_flags_hidden_costs_and_unpriced_competitors() -> None:
    kompetitor = pd.DataFrame(
        [
            {
                "id": 1,
                "nama": "A",
                "fitur_utama": "Chat",
                "segmen_target": "UMKM",
                "kategori": "Chatbot WA",
            },
            {
                "id": 2,
                "nama": "B",
                "fitur_utama": "Chat",
                "segmen_target": "Enterprise",
                "kategori": "CRM AI",
            },
        ]
    )
    harga = pd.DataFrame(
        [
            {
                "id": 1,
                "kompetitor_id": 1,
                "nama_paket": "Lite",
                "harga_idr": 100_000,
                "periode": "Bulanan",
                "model_harga": "Langganan",
                "biaya_tambahan": "Biaya pesan",
            },
            {
                "id": 2,
                "kompetitor_id": 2,
                "nama_paket": "Sales",
                "harga_idr": None,
                "periode": "Bulanan",
                "model_harga": "Langganan",
                "biaya_tambahan": "",
            },
        ]
    )
    gaps = gap_findings(kompetitor, harga)

    assert not gaps.empty
    labels = set(gaps["gap"])
    assert "Harga publik yang transparan" in labels
    assert "Paket khusus freelancer" in labels
    assert set(gaps["prioritas"]) <= {"Tinggi", "Sedang", "Rendah"}


def test_gap_findings_without_competitors() -> None:
    empty = pd.DataFrame(columns=TABLE_COLUMNS["kompetitor"])

    assert gap_findings(empty, pd.DataFrame()).empty
