"""Halaman Gap dan rekomendasi."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from radar_pasar.data import repository
from radar_pasar.domain.features import feature_matrix, with_feature_counts
from radar_pasar.domain.formatting import decimal, rupiah
from radar_pasar.domain.gaps import gap_findings
from radar_pasar.domain.pricing import (
    monthly_prices,
    price_percentile,
    public_price_coverage,
    recommended_tiers,
)
from radar_pasar.presentation import charts, components


def render() -> None:
    data = repository.load_all()
    kompetitor = data["kompetitor"]
    harga = data["harga"]

    components.quality_notice()
    components.intro(
        "Celah yang belum diisi kompetitor, peta posisi harga versus fitur, dan usulan rentang "
        "harga Impost dari persentil pasar."
    )

    if kompetitor.empty:
        components.empty_state("Belum ada data kompetitor. Isi CSV di folder data/ lalu muat ulang.")
        return

    gaps = gap_findings(kompetitor, harga)
    with st.container(border=True):
        st.subheader("Celah pasar")
        if gaps.empty:
            components.empty_state("Tidak ada gap yang bisa disimpulkan dari data saat ini.")
        else:
            for _, row in gaps.iterrows():
                prioritas = str(row["prioritas"]).lower()
                st.markdown(f"**{row['gap']}** · Prioritas {prioritas}  \n{row['temuan']}")
                st.caption(row["bukti"])
            st.caption(
                "Prioritas tinggi berarti celah menyentuh banyak kompetitor atau segmen inti. "
                "Bukti menyebut nama dan jumlah baris yang bisa dicek ulang."
            )

    monthly = monthly_prices(kompetitor, harga)
    if monthly.empty:
        components.empty_state(
            "Belum ada paket dengan harga bulanan numerik, sehingga peta harga dan rekomendasi "
            "belum bisa dihitung."
        )
        return

    berfitur = with_feature_counts(monthly, kompetitor)
    kiri, kanan = st.columns(2, gap="medium")
    with kiri, st.container(border=True):
        st.subheader("Posisi harga versus fitur")
        chart = charts.price_scatter(berfitur)
        if chart is not None:
            st.altair_chart(chart, alt="Peta posisi harga dan jumlah fitur setiap paket")
            st.caption("Arahkan kursor ke titik untuk melihat nama kompetitor dan paketnya.")
        else:
            components.empty_state("Jumlah fitur belum bisa dihitung.")
    with kanan, st.container(border=True):
        st.subheader("Cakupan fitur")
        _, summary = feature_matrix(kompetitor)
        chart = charts.feature_coverage(summary, total=len(kompetitor))
        if chart is not None:
            st.altair_chart(chart, alt="Fitur yang paling banyak dan paling sedikit dimiliki")
        else:
            components.empty_state("Fitur utama kompetitor belum diisi.")

    tiers = recommended_tiers(kompetitor, harga)
    with st.container(border=True):
        st.subheader("Rekomendasi paket Impost")
        if not tiers:
            components.empty_state("Rekomendasi butuh minimal satu paket dengan harga bulanan.")
            return

        with_price, total = public_price_coverage(kompetitor, harga)
        st.caption(
            f"Dihitung dari {len(monthly)} paket bulanan milik {with_price} dari {total} kompetitor. "
            "Bukan hasil survei kemauan bayar; validasi sebelum dipublikasikan."
        )
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Paket": tier["paket"],
                        "Harga/bulan": rupiah(tier["harga"]),
                        "Persentil": f"{decimal(tier['persentil'], 0)}",
                        "Posisi": tier["posisi"],
                    }
                    for tier in tiers
                ]
            ),
            hide_index=True,
            width="stretch",
            alt="Rekomendasi rentang harga per paket",
        )
        chart = charts.price_band_chart(tiers)
        if chart is not None:
            st.altair_chart(chart, alt="Batang harga rekomendasi untuk paket Starter, Pro, dan Business")

        cheapest = float(monthly["harga_bulanan"].min())
        st.markdown(
            f"- **Starter** di persentil 25 mendekati harga masuk pasar ({rupiah(cheapest)} adalah "
            "paket termurah yang tercatat).\n"
            f"- **Pro** di median, posisi yang paling ramai dan mudah dibandingkan.\n"
            "- **Business** di persentil 75, untuk fitur dan dukungan yang lebih lengkap.\n"
            f"- Posisi harga dihitung ulang pada {len(monthly)} paket; "
            f"persentil paket Starter saat ini {decimal(price_percentile(monthly, tiers[0]['harga']), 0)}."
        )
