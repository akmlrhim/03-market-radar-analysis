"""Halaman Pain point dan persepsi pengguna."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from radar_pasar.data import repository
from radar_pasar.domain.formatting import decimal, number, rupiah
from radar_pasar.domain.pain import (
    hambatan_counts,
    pain_rankings,
    van_westendorp,
    wtp_by_segment,
)
from radar_pasar.presentation import charts, components


def _porsi(value: float, total: int) -> str:
    return f"{decimal(value / total * 100, 0)}%" if total else "—"


def _ranking_table(ranking: pd.DataFrame, label: str) -> None:
    total = int(ranking["jumlah"].sum())
    column = label if label in ranking.columns else ranking.columns[0]
    view = pd.DataFrame(
        {
            label.capitalize(): ranking[column],
            "Jumlah": ranking["jumlah"],
            "Porsi": ranking["jumlah"].map(lambda value: _porsi(value, total)),
        }
    )
    st.dataframe(view, hide_index=True, width="stretch", alt=f"Tabel peringkat {label}")


def render() -> None:
    data = repository.load_all()
    pain = data["pain_point"]

    components.quality_notice()
    components.intro(
        "Peringkat masalah, kemauan bayar, hambatan adopsi, dan titik harga Van Westendorp. "
        "Semua angka berasal dari data survei di data/pain_point.csv."
    )

    if pain.empty:
        components.empty_state("Belum ada data pain point. Isi data/pain_point.csv lalu muat ulang.")
        return

    sumber = pain["sumber"].fillna("").astype(str)
    if sumber.str.contains("Contoh", case=False, na=False).any():
        st.warning(
            f"{len(pain)} baris masih berlabel contoh. Ganti dengan hasil wawancara atau kuesioner "
            "sebelum angka di halaman ini dipakai untuk keputusan produk.",
            title="Data pain point belum final",
            icon=":material/science:",
        )

    budget = pd.to_numeric(pain["budget_bulanan_idr"], errors="coerce")
    segmen = pain["segmen"].replace("", pd.NA).dropna()
    with st.container(horizontal=True):
        st.metric("Responden", number(len(pain)), border=True)
        st.metric("Segmen", number(segmen.nunique()), border=True)
        st.metric("Median budget", rupiah(budget.median()), border=True, help="Kemauan bayar bulanan.")

    ranking = pain_rankings(pain)
    hambatan = hambatan_counts(pain)
    wtp = wtp_by_segment(pain)

    kiri, kanan = st.columns(2, gap="medium")
    with kiri, st.container(border=True):
        st.subheader("Masalah paling sering muncul")
        chart = charts.ranking_bar(ranking)
        if chart is not None:
            st.altair_chart(chart, alt="Peringkat tema masalah yang paling sering disebut")
            _ranking_table(ranking, "masalah")
        else:
            components.empty_state("Kolom tema atau masalah belum diisi.")

    with kanan, st.container(border=True):
        st.subheader("Hambatan adopsi")
        chart = charts.ranking_bar(hambatan, label="hambatan")
        if chart is not None:
            st.altair_chart(chart, alt="Peringkat hambatan adopsi yang disebut responden")
            _ranking_table(hambatan, "hambatan")
        else:
            components.empty_state("Kolom hambatan belum diisi.")

    with st.container(border=True):
        st.subheader("Kemauan bayar per segmen")
        chart = charts.wtp_bar(wtp)
        if chart is not None:
            st.altair_chart(chart, alt="Sebaran kemauan bayar bulanan per segmen")
            st.caption(
                "Rentang mengikuti budget bulanan yang disebut responden, bukan harga paket kompetitor."
            )
        else:
            components.empty_state("Budget bulanan responden belum diisi.")

    with st.container(border=True):
        st.subheader("Van Westendorp")
        hasil = van_westendorp(pain)
        if hasil is None:
            components.empty_state(
                "Analisis butuh minimal tiga responden dengan empat titik harga yang lengkap "
                "(terlalu murah, murah, mahal, terlalu mahal)."
            )
        else:
            points = hasil["points"]
            with st.container(horizontal=True):
                st.metric("Terlalu murah (PMC)", rupiah(points["PMC"]), border=True)
                st.metric("Optimal (OPP)", rupiah(points["OPP"]), border=True)
                st.metric("Indiferen (IDP)", rupiah(points["IDP"]), border=True)
                st.metric("Terlalu mahal (PME)", rupiah(points["PME"]), border=True)
            chart = charts.vw_line(hasil["curves"], points)
            if chart is not None:
                st.altair_chart(chart, alt="Kurva Van Westendorp dengan garis titik harga kunci")
            st.caption(
                f"Dihitung dari {hasil['responden']} responden lengkap. Titik potong kurva "
                "menunjukkan batas harga yang dianggap terlalu murah, optimal, dan terlalu mahal. "
                "Dengan sampel kecil, anggap ini indikasi arah, bukan angka final."
            )

    with st.expander("Lihat jawaban responden"):
        kolom = [
            column
            for column in [
                "responden",
                "segmen",
                "masalah",
                "budget_bulanan_idr",
                "hambatan",
                "sumber",
            ]
            if column in pain.columns
        ]
        st.dataframe(pain[kolom], hide_index=True, width="stretch", alt="Tabel jawaban pain point")
