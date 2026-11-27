"""Komponen Streamlit yang dipakai lebih dari satu halaman."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from radar_pasar.data import repository
from radar_pasar.domain.formatting import rupiah

_MONTHS = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]


def intro(text: str) -> None:
    """Satu baris konteks di bawah judul halaman."""
    st.caption(text)


def empty_state(message: str, icon: str = ":material/info:") -> None:
    """Pesan netral saat filter tidak menyisakan data."""
    st.info(message, icon=icon)


def format_date(value: Any) -> str:
    """Tanggal gaya Indonesia, mis. ``25 Nov 2026``."""
    if value is None:
        return "—"
    if isinstance(value, str) and not value.strip():
        return "—"
    try:
        timestamp = pd.Timestamp(value)
    except (TypeError, ValueError):
        return "—"
    if pd.isna(timestamp):
        return "—"
    return f"{timestamp.day} {_MONTHS[timestamp.month - 1]} {timestamp.year}"


def quality_notice() -> None:
    """Peringatan singkat soal pembaruan dan status verifikasi data."""
    quality = repository.quality_report()
    parts = [
        f"Data dicek {format_date(quality['last_checked'])}",
        f"{quality['competitor_count']} kompetitor",
        f"{quality['competitors_with_price']} dengan harga tercatat",
    ]
    if quality["unverified_count"]:
        parts.append(f"{quality['unverified_count']} belum terverifikasi")
    if quality["stale_count"]:
        parts.append(f"{quality['stale_count']} baris lebih dari 30 hari")

    message = " · ".join(parts)
    if quality["unverified_count"] or quality["stale_count"]:
        st.warning(message, icon=":material/schedule:")
    else:
        st.caption(message)


def _column(frame: pd.DataFrame, name: str) -> pd.Series:
    if name in frame.columns:
        return frame[name]
    return pd.Series("", index=frame.index, dtype="object")


def _harga(value: Any) -> str:
    number_value = pd.to_numeric(value, errors="coerce")
    if pd.isna(number_value):
        return "Hubungi sales"
    return rupiah(float(number_value))


def _bulanan(value: Any) -> str:
    number_value = pd.to_numeric(value, errors="coerce")
    if pd.isna(number_value):
        return "—"
    return rupiah(float(number_value))


def _price_columns(frame: pd.DataFrame) -> dict[str, pd.Series]:
    """Kolom tabel harga yang dipakai baik tabel ringkas maupun tabel lengkap."""
    return {
        "Kompetitor": _column(frame, "nama").fillna("").astype(str),
        "Kategori": _column(frame, "kategori").fillna("").astype(str),
        "Paket": _column(frame, "nama_paket").fillna("").astype(str),
        "Model": _column(frame, "model_harga").fillna("").astype(str),
        "Harga": _column(frame, "harga_idr").map(_harga),
        "Periode": _column(frame, "periode").fillna("").astype(str),
        "Ekuivalen bulanan": _column(frame, "harga_bulanan").map(_bulanan),
    }


def price_table_view(frame: pd.DataFrame) -> pd.DataFrame:
    """Tabel harga paket dengan nominal dalam penulisan rupiah."""
    return pd.DataFrame(_price_columns(frame))


def render_package_price_table(frame: pd.DataFrame, caption: str | None = None) -> None:
    """Tabel ringkas harga paket, tampil langsung di halaman analisis harga."""
    if frame.empty:
        empty_state("Belum ada paket harga yang cocok dengan filter.")
        return

    if caption:
        st.caption(caption)
    st.dataframe(
        price_table_view(frame),
        hide_index=True,
        width="stretch",
        alt="Tabel harga paket kompetitor dalam rupiah",
    )


def render_price_table(frame: pd.DataFrame, caption: str | None = None) -> None:
    """Tabel paket harga dengan ekuivalen bulanan dan biaya tambahan."""
    if frame.empty:
        empty_state("Belum ada paket harga yang cocok dengan filter.")
        return

    view = pd.DataFrame(
        {
            **_price_columns(frame),
            "Batasan": _column(frame, "batasan").fillna("").astype(str),
            "Biaya tambahan": _column(frame, "biaya_tambahan").fillna("").astype(str),
        }
    )
    if caption:
        st.caption(caption)
    st.dataframe(
        view,
        hide_index=True,
        width="stretch",
        alt="Tabel paket harga kompetitor beserta biaya tambahan",
    )


def _biaya_tags(text: str) -> str:
    """Kelompokkan biaya di luar paket dari catatan berbasis teks."""
    value = text.lower()
    tags: list[str] = []
    if "ppn" in value or "pajak" in value:
        tags.append("PPN")
    if any(
        kata in value
        for kata in (
            "pesan",
            "percakapan",
            "waba",
            "broadcast",
            "kuota",
            "kredit",
            "coins",
            "top-up",
            "top up",
            "add-on",
            "iklan",
        )
    ):
        tags.append("Pesan/kuota")
    if any(
        kata in value
        for kata in ("agen", "pengguna", "user", "nomor", "karyawan", "function")
    ):
        tags.append("Agen/add-on")
    if any(
        kata in value
        for kata in ("implementasi", "integrasi", "setup", "perangkat", "maintenance", "development")
    ):
        tags.append("Implementasi")
    if "promo" in value or "diskon" in value:
        tags.append("Promo/diskon")
    if "via sales" in value or "tidak dipublikasikan" in value:
        tags.append("Harga via sales")
    return ", ".join(tags) if tags else "Lainnya"


def effective_cost_view(frame: pd.DataFrame) -> pd.DataFrame:
    """Rincian biaya efektif: harga paket, komponen di luar paket, dan batas bawahnya."""
    catatan = _column(frame, "biaya_tambahan").fillna("").astype(str).str.strip()
    selected = frame[catatan.ne("")]
    catatan = catatan.loc[selected.index]
    tags = catatan.map(_biaya_tags)
    bulanan = pd.to_numeric(_column(selected, "harga_bulanan"), errors="coerce")
    estimasi = [
        f"{rupiah(float(value))} + {label}" if pd.notna(value) else "—"
        for value, label in zip(bulanan, tags, strict=False)
    ]
    return pd.DataFrame(
        {
            "Kompetitor": _column(selected, "nama").fillna("").astype(str),
            "Paket": _column(selected, "nama_paket").fillna("").astype(str),
            "Harga paket": _column(selected, "harga_idr").map(_harga),
            "Ekuivalen bulanan": _column(selected, "harga_bulanan").map(_bulanan),
            "Estimasi total bulanan": estimasi,
            "Periode": _column(selected, "periode").fillna("").astype(str),
            "Komponen di luar paket": tags,
            "Rincian": catatan,
        }
    )


def render_effective_cost_table(frame: pd.DataFrame, caption: str | None = None) -> None:
    """Tabel rincian biaya efektif paket kompetitor."""
    view = effective_cost_view(frame)
    if view.empty:
        st.caption("Tidak ada biaya tambahan yang tercatat untuk filter ini.")
        return

    if caption:
        st.caption(caption)
    st.dataframe(
        view,
        hide_index=True,
        width="stretch",
        alt="Rincian biaya efektif paket kompetitor di luar harga langganan",
    )


def _yes_no(value: Any) -> str:
    if value is None or pd.isna(value):
        return "Belum dicatat"
    return "Ya" if bool(value) else "Tidak"


def render_competitor_detail(row: pd.Series) -> None:
    """Detail satu kompetitor: fitur, positioning, kelemahan, dan sumber."""
    nama = str(row.get("nama", "") or "Tanpa nama")
    kategori = str(row.get("kategori", "") or "—")
    segmen = str(row.get("segmen_target", "") or "—")
    kota = str(row.get("kota_basis", "") or "—")
    website = str(row.get("website", "") or "")
    sumber = str(row.get("sumber_url", "") or "")

    with st.container(border=True):
        st.subheader(nama)
        st.caption(f"{kategori} · {segmen} · {kota}")
        if website.startswith("http"):
            st.link_button("Buka situs", website, icon=":material/open_in_new:")

        st.markdown("**Fitur utama**")
        st.markdown(str(row.get("fitur_utama", "") or "Belum dicatat"))

        st.markdown("**Integrasi**")
        st.markdown(str(row.get("integrasi", "") or "Belum dicatat"))

        st.markdown("**Positioning**")
        st.markdown(str(row.get("positioning", "") or "Belum dicatat"))

        st.markdown("**Kelemahan**")
        st.markdown(str(row.get("kelemahan", "") or "Belum ada catatan"))

        st.markdown("**Traksi**")
        st.markdown(str(row.get("traksi", "") or "Belum ada catatan"))

        st.caption(
            f"Bahasa Indonesia: {_yes_no(row.get('bahasa_indonesia'))} · "
            f"Sumber: {sumber or '—'} · dicek {format_date(row.get('tanggal_cek'))}"
        )


def price_kpi(label: str, value: str, help: str | None = None) -> None:
    """Kartu metrik harga dengan bingkai."""
    st.metric(label, value, border=True, help=help)
