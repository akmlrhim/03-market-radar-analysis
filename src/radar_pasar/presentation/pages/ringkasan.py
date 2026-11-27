"""Halaman Ringkasan eksekutif."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from radar_pasar.data import repository
from radar_pasar.domain.formatting import decimal, number, rupiah
from radar_pasar.domain.pricing import (
    monthly_prices,
    price_stats,
    public_price_coverage,
    recommended_tiers,
)
from radar_pasar.presentation import charts, components


def _findings(kompetitor: pd.DataFrame, harga: pd.DataFrame, monthly: pd.DataFrame) -> list[str]:
    findings: list[str] = []
    with_price, total = public_price_coverage(kompetitor, harga)
    median = float(monthly["harga_bulanan"].median()) if not monthly.empty else None
    if median is not None:
        findings.append(
            f"{with_price} dari {total} kompetitor mencantumkan harga bulanan numerik; "
            f"median paket {rupiah(median)}."
        )

    if not kompetitor.empty and "kategori" in kompetitor.columns:
        kategori = kompetitor["kategori"].replace("", pd.NA).dropna()
        if not kategori.empty:
            top = kategori.value_counts()
            findings.append(
                f"Kategori {top.index[0]} paling ramai dengan {int(top.iloc[0])} dari "
                f"{len(kompetitor)} kompetitor."
            )

    if not monthly.empty:
        termurah = monthly.loc[monthly["harga_bulanan"].idxmin()]
        termahal = monthly.loc[monthly["harga_bulanan"].idxmax()]
        findings.append(
            f"Rentang harga bulanan {rupiah(termurah['harga_bulanan'])} "
            f"({termurah.get('nama', '?')}) sampai {rupiah(termahal['harga_bulanan'])} "
            f"({termahal.get('nama', '?')})."
        )
    return findings[:3]


def _recommendations(kompetitor: pd.DataFrame, harga: pd.DataFrame) -> list[str]:
    recommendations: list[str] = []

    tiers = recommended_tiers(kompetitor, harga)
    if tiers:
        ringkas = " · ".join(f"{tier['paket']} {rupiah(tier['harga'])}" for tier in tiers)
        recommendations.append(
            f"**Rentang harga awal** dari persentil pasar: {ringkas}. "
            "Validasi dengan kemauan bayar sebelum dipublikasikan."
        )

    if not recommendations:
        recommendations.append(
            "Lengkapi data kompetitor dan harga terlebih dahulu sebelum menyusun rekomendasi."
        )
    return recommendations[:3]


def _status_data(kompetitor: pd.DataFrame, harga: pd.DataFrame) -> None:
    with st.expander("Status dan keterbatasan data"):
        stale = repository.stale_rows()
        if stale.empty:
            st.caption("Semua baris kompetitor dan harga dicek dalam 30 hari terakhir.")
        else:
            st.markdown(f"**{len(stale)} baris perlu dicek ulang**")
            st.dataframe(
                stale[["tabel", "label", "tanggal_cek", "umur_hari"]],
                hide_index=True,
                width="stretch",
                alt="Baris data yang sudah lama belum diperbarui",
            )

        with_price, total = public_price_coverage(kompetitor, harga)
        if with_price < total:
            monthly = monthly_prices(kompetitor, harga)
            priced = set(monthly["kompetitor_id"].dropna().astype(int)) if not monthly.empty else set()
            tanpa_harga = [
                str(row["nama"])
                for _, row in kompetitor.iterrows()
                if pd.notna(row.get("id")) and int(row["id"]) not in priced
            ]
            st.markdown("**Tanpa harga bulanan numerik**")
            st.markdown(", ".join(tanpa_harga) if tanpa_harga else "—")


def render() -> None:
    data = repository.load_all()
    kompetitor = data["kompetitor"]
    harga = data["harga"]

    components.quality_notice()
    components.intro(
        "Riset kompetitor dan harga untuk produk digital dan AI agent "
        "Impost Teknologi Indonesia. Fokus segmen UMKM dan freelancer."
    )

    if kompetitor.empty:
        components.empty_state("Belum ada data kompetitor. Isi CSV di folder data/ lalu muat ulang.")
        return

    monthly = monthly_prices(kompetitor, harga)
    stats = price_stats(kompetitor, harga)
    dengan_harga = int(monthly["kompetitor_id"].nunique()) if not monthly.empty else 0

    with st.container(horizontal=True):
        st.metric("Kompetitor", number(len(kompetitor)), border=True)
        st.metric("Harga termurah", rupiah(stats["cheapest"]), border=True, help="Paket bulanan terendah.")
        st.metric("Harga median", rupiah(stats["median"]), border=True, help="Median paket bulanan.")
        st.metric("Harga tertinggi", rupiah(stats["expensive"]), border=True, help="Paket bulanan tertinggi.")

    kolom_temuan, kolom_rekomendasi = st.columns(2, gap="medium")
    with kolom_temuan, st.container(border=True):
        st.subheader("Temuan utama")
        for finding in _findings(kompetitor, harga, monthly):
            st.markdown(f"- {finding}")
        if monthly.empty:
            st.caption("Belum ada paket dengan ekuivalen bulanan yang bisa dibandingkan.")

    with kolom_rekomendasi, st.container(border=True):
        st.subheader("Rekomendasi")
        for recommendation in _recommendations(kompetitor, harga):
            st.markdown(f"- {recommendation}")

    kiri, kanan = st.columns([3, 2], gap="medium")
    with kiri, st.container(border=True):
        st.subheader("Sebaran kompetitor per kategori")
        kategori = (
            kompetitor["kategori"]
            .replace("", pd.NA)
            .dropna()
            .value_counts()
            .rename_axis("masalah")
            .reset_index(name="jumlah")
        )
        chart = charts.ranking_bar(kategori)
        if chart is not None:
            st.altair_chart(chart, alt="Jumlah kompetitor pada setiap kategori")
        else:
            components.empty_state("Kategori kompetitor belum diisi.")

    with kanan, st.container(border=True):
        st.subheader("Cakupan harga")
        st.metric(
            "Kompetitor dengan harga bulanan",
            f"{stats['count']} paket",
            border=False,
            help=f"{decimal(stats['coverage'] * 100, 0)}% kompetitor memiliki harga numerik.",
        )
        st.caption(
            f"{stats['count']} paket bulanan dari {dengan_harga} kompetitor. "
            "Sisanya memilih jalur sales sehingga tidak masuk median."
        )
        tiers = recommended_tiers(kompetitor, harga)
        if tiers:
            st.markdown("**Rentang harga dari persentil pasar**")
            st.dataframe(
                pd.DataFrame(
                    [
                        {"Paket": tier["paket"], "Harga": rupiah(tier["harga"]), "Posisi": tier["posisi"]}
                        for tier in tiers
                    ]
                ),
                hide_index=True,
                width="stretch",
                alt="Rentang harga rekomendasi per paket",
            )

    _status_data(kompetitor, harga)
