"""Baca CSV (cache) dan laporan kualitas data."""

from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from radar_pasar.config import DATA_DIR, STALE_DAYS, TABLE_FILES
from radar_pasar.data.schema import TABLE_COLUMNS, coerce_table, empty_frame


@st.cache_data(ttl=300, show_spinner=False)
def load_table(name: str) -> pd.DataFrame:
    """Baca satu tabel CSV dan sesuaikan tipenya."""
    path = DATA_DIR / TABLE_FILES[name]
    if not path.exists():
        return empty_frame(name)

    raw = pd.read_csv(
        path,
        dtype=str,
        keep_default_na=False,
        na_values=[""],
        encoding="utf-8-sig",
    )
    return coerce_table(name, raw)


def load_all() -> dict[str, pd.DataFrame]:
    """Semua tabel sekaligus, memakai cache per tabel."""
    return {name: load_table(name) for name in TABLE_COLUMNS}


def refresh() -> None:
    """Bersihkan cache agar CSV dibaca ulang."""
    load_table.clear()


def last_checked() -> date | None:
    """Tanggal cek terbaru dari seluruh dataset."""
    dates: list[date] = []
    for table in ("kompetitor", "harga"):
        frame = load_table(table)
        if frame.empty or "tanggal_cek" not in frame.columns:
            continue
        parsed = pd.to_datetime(frame["tanggal_cek"], errors="coerce").dropna()
        if not parsed.empty:
            dates.append(parsed.max().date())
    return max(dates) if dates else None


def stale_rows() -> pd.DataFrame:
    """Baris yang tanggal ceknya kosong atau lebih tua dari ``STALE_DAYS``."""
    today = pd.Timestamp.today().normalize()
    kompetitor = load_table("kompetitor")
    names: dict[int, str] = {}
    if not kompetitor.empty:
        names = {
            int(row_id): str(nama)
            for row_id, nama in zip(kompetitor["id"], kompetitor["nama"], strict=False)
            if pd.notna(row_id)
        }

    records: list[dict[str, object]] = []
    for table in ("kompetitor", "harga"):
        frame = load_table(table)
        if frame.empty:
            continue
        dates = pd.to_datetime(frame["tanggal_cek"], errors="coerce")
        ages = (today - dates).dt.days
        for index in frame.index[dates.isna() | (ages > STALE_DAYS)]:
            row = frame.loc[index]
            if table == "kompetitor":
                label = str(row["nama"])
            else:
                pemilik = names.get(int(row["kompetitor_id"]), "?")
                label = f"{pemilik} · {row['nama_paket']}"
            umur = ages.loc[index]
            records.append(
                {
                    "tabel": table,
                    "id": int(row["id"]) if pd.notna(row["id"]) else None,
                    "label": label,
                    "tanggal_cek": row["tanggal_cek"],
                    "umur_hari": int(umur) if pd.notna(umur) else None,
                }
            )

    if not records:
        return pd.DataFrame(columns=["tabel", "id", "label", "tanggal_cek", "umur_hari"])
    return pd.DataFrame(records)


def table_summary() -> pd.DataFrame:
    """Jumlah baris dan kolom tiap tabel."""
    return pd.DataFrame(
        [
            {
                "tabel": name,
                "baris": len(load_table(name)),
                "kolom": len(load_table(name).columns),
            }
            for name in TABLE_COLUMNS
        ]
    )


def quality_report() -> dict[str, object]:
    """Ringkasan singkat untuk sidebar dan halaman ringkasan."""
    kompetitor = load_table("kompetitor")
    harga = load_table("harga")

    unverified = 0
    if not kompetitor.empty:
        unverified = int((kompetitor["status_verifikasi"] != "Terverifikasi").sum())

    dengan_harga = int(harga["kompetitor_id"].nunique()) if not harga.empty else 0

    return {
        "last_checked": last_checked(),
        "competitor_count": len(kompetitor),
        "competitors_with_price": dengan_harga,
        "unverified_count": unverified,
        "stale_count": len(stale_rows()),
    }
