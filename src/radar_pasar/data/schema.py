"""Kontrak kolom dan tipe untuk setiap tabel CSV.

Semua pembacaan CSV melewati :func:`coerce_table` agar halaman tidak perlu
menebak tipe data dan kolom yang hilang tetap muncul sebagai nilai kosong.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

TABLE_COLUMNS: dict[str, list[str]] = {
    "kompetitor": [
        "id",
        "nama",
        "website",
        "kategori",
        "segmen_target",
        "kota_basis",
        "tahun_berdiri",
        "fitur_utama",
        "bahasa_indonesia",
        "integrasi",
        "positioning",
        "kelemahan",
        "traksi",
        "sumber_url",
        "tanggal_cek",
        "status_verifikasi",
    ],
    "harga": [
        "id",
        "kompetitor_id",
        "nama_paket",
        "model_harga",
        "harga_idr",
        "periode",
        "batasan",
        "biaya_tambahan",
        "sumber_url",
        "tanggal_cek",
    ],
    "pasar": [
        "id",
        "indikator",
        "nilai",
        "satuan",
        "tahun",
        "sumber",
        "catatan",
        "sumber_url",
    ],
}

COLUMN_TYPES: dict[str, dict[str, str]] = {
    "kompetitor": {
        "id": "int",
        "nama": "text",
        "website": "text",
        "kategori": "text",
        "segmen_target": "text",
        "kota_basis": "text",
        "tahun_berdiri": "int",
        "fitur_utama": "text",
        "bahasa_indonesia": "bool",
        "integrasi": "text",
        "positioning": "text",
        "kelemahan": "text",
        "traksi": "text",
        "sumber_url": "text",
        "tanggal_cek": "date",
        "status_verifikasi": "text",
    },
    "harga": {
        "id": "int",
        "kompetitor_id": "int",
        "nama_paket": "text",
        "model_harga": "text",
        "harga_idr": "int",
        "periode": "text",
        "batasan": "text",
        "biaya_tambahan": "text",
        "sumber_url": "text",
        "tanggal_cek": "date",
    },
    "pasar": {
        "id": "int",
        "indikator": "text",
        "nilai": "float",
        "satuan": "text",
        "tahun": "int",
        "sumber": "text",
        "catatan": "text",
        "sumber_url": "text",
    },
}

TRUE_VALUES = {"ya", "true", "1", "yes", "y", "ada"}
FALSE_VALUES = {"tidak", "false", "0", "no", "n", "tidak ada"}

EMPTY_DTYPES = {
    "text": "object",
    "int": "Int64",
    "float": "Float64",
    "bool": "boolean",
    "date": "object",
}


def empty_frame(table: str) -> pd.DataFrame:
    """DataFrame kosong dengan kolom dan tipe sesuai kontrak tabel."""
    columns = TABLE_COLUMNS[table]
    types = COLUMN_TYPES[table]
    return pd.DataFrame({column: pd.Series(dtype=EMPTY_DTYPES[types[column]]) for column in columns})


def _to_bool(value: Any) -> bool | pd._libs.missing.NAType:
    """Terima variasi teks CSV untuk nilai boolean; selain itu NA."""
    if value is None or pd.isna(value):
        return pd.NA
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in TRUE_VALUES:
        return True
    if text in FALSE_VALUES:
        return False
    return pd.NA


def coerce_table(table: str, raw: pd.DataFrame) -> pd.DataFrame:
    """Lengkapi kolom yang hilang lalu sesuaikan tipe setiap kolom."""
    columns = TABLE_COLUMNS[table]
    types = COLUMN_TYPES[table]
    frame = raw.copy()

    for column in columns:
        if column not in frame.columns:
            frame[column] = pd.NA
    frame = frame[columns]

    for column in columns:
        series = frame[column]
        kind = types[column]
        if kind == "text":
            frame[column] = series.map(lambda value: "" if pd.isna(value) else str(value)).astype(object)
        elif kind == "int":
            frame[column] = pd.to_numeric(series, errors="coerce").astype("Int64")
        elif kind == "float":
            frame[column] = pd.to_numeric(series, errors="coerce").astype("Float64")
        elif kind == "bool":
            frame[column] = series.map(_to_bool).astype("boolean")
        elif kind == "date":
            parsed = pd.to_datetime(series, errors="coerce")
            frame[column] = parsed.dt.date if len(parsed) else pd.Series(dtype="object")

    return frame
