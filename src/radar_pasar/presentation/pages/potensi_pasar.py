"""Halaman Potensi pasar."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from radar_pasar.data import repository
from radar_pasar.domain.formatting import decimal, number, rupiah, rupiah_compact
from radar_pasar.domain.market import market_model, market_value
from radar_pasar.presentation import charts, components


def _skala_umkm(pasar: pd.DataFrame) -> pd.DataFrame:
    skala = pasar[pasar["indikator"].astype(str).str.contains("UMKM skala", case=False, na=False)].copy()
    if skala.empty:
        return skala
    skala["nilai"] = pd.to_numeric(skala["nilai"], errors="coerce")
    total = market_value(pasar, "Jumlah UMKM") or skala["nilai"].sum()
    skala["porsi"] = skala["nilai"] / total * 100 if total else 0.0
    return skala


def _sumber_table(pasar: pd.DataFrame) -> None:
    view = pd.DataFrame(
        {
            "Indikator": pasar["indikator"].fillna("").astype(str),
            "Nilai": pasar["nilai"],
            "Satuan": pasar["satuan"].fillna("").astype(str),
            "Tahun": pasar["tahun"],
            "Sumber": pasar["sumber"].fillna("").astype(str),
            "Catatan": pasar["catatan"].fillna("").astype(str),
            "URL": pasar["sumber_url"].fillna("").astype(str),
        }
    )
    st.dataframe(
        view,
        hide_index=True,
        width="stretch",
        column_config={"URL": st.column_config.LinkColumn("URL", display_text="Buka")},
        alt="Tabel indikator pasar beserta sumber dan catatan",
    )


def render() -> None:
    data = repository.load_all()
    pasar = data["pasar"]

    components.quality_notice()
    components.intro(
        "Hitung TAM, SAM, dan SOM dari jumlah UMKM dan ARPU bulanan. Semua asumsi bisa diubah; "
        "nilai awalnya diambil dari CSV atau asumsi riset awal."
    )

    if pasar.empty:
        components.empty_state("Belum ada data pasar. Isi data/pasar.csv lalu muat ulang.")
        return

    umkm = market_value(pasar, "Jumlah UMKM") or 0.0
    budget = market_value(pasar, "Budget software UMKM") or 150_000
    adopsi = market_value(pasar, "Adopsi AI") or 50.0

    with st.container(border=True):
        st.subheader("Asumsi model")
        baris = st.columns(5, gap="medium")
        target = baris[0].slider(
            "Target segmen (%)",
            min_value=1,
            max_value=50,
            value=20,
            help="Porsi UMKM yang masuk kriteria produk, mis. usaha dengan chat pelanggan rutin.",
        )
        digital = baris[1].slider(
            "Siap digital (%)",
            min_value=10,
            max_value=100,
            value=50,
            help="Porsi target yang sudah memakai alat digital.",
        )
        ai = baris[2].slider(
            "Siap AI (%)",
            min_value=1,
            max_value=100,
            value=max(1, min(100, int(round(adopsi)))),
            help="Nilai awal mengikuti adopsi AI dari survei UMKM. Sampelnya kecil, jadi tetap asumsi.",
        )
        share = baris[3].slider(
            "Pangsa SOM (%)",
            min_value=0.1,
            max_value=20.0,
            value=2.0,
            step=0.1,
            help="Porsi pasar siap AI yang realistis direbut dalam periode rencana.",
        )
        arpu_default = max(10_000, min(2_000_000, int(budget) // 10_000 * 10_000))
        arpu = baris[4].slider(
            "ARPU bulanan (Rp)",
            min_value=10_000,
            max_value=2_000_000,
            value=arpu_default,
            step=10_000,
            format="Rp %d",
            help="Pendapatan rata-rata per pengguna per bulan.",
        )

    model = market_model(umkm, target, digital, ai, arpu, share)

    with st.container(horizontal=True):
        st.metric("TAM", rupiah_compact(model.tam), border=True, help="Seluruh UMKM × ARPU × 12.")
        st.metric("SAM", rupiah_compact(model.sam), border=True, help="Target segmen yang siap digital.")
        st.metric("SOM", rupiah_compact(model.som), border=True, help="Pangsa pasar yang direbut.")
        st.metric("Pelanggan SOM", number(model.som_customers), border=True)
        st.metric("ARPU", rupiah(model.arpu), border=True, help="Per bulan.")

    st.caption(
        "TAM = Total Addressable Market (seluruh pasar yang bisa dilayani) · "
        "SAM = Serviceable Available Market (bagian yang sesuai target dan siap digital) · "
        "SOM = Serviceable Obtainable Market (bagian yang realistis direbut)."
    )
    st.caption(
        "Rumus: jumlah UMKM × target × siap digital × siap AI × pangsa SOM. "
        "Nilai rupiah memakai ARPU bulanan × 12. Ini estimasi, bukan proyeksi pendapatan."
    )

    kiri, kanan = st.columns([3, 2], gap="medium")
    with kiri, st.container(border=True):
        st.subheader("Corong TAM, SAM, SOM")
        chart = charts.market_stage_bar(model)
        if chart is not None:
            st.altair_chart(chart, alt="Corong jumlah pengguna dari total UMKM sampai pengguna SOM")
    with kanan, st.container(border=True):
        st.subheader("Distribusi UMKM per skala")
        skala = _skala_umkm(pasar)
        if skala.empty:
            components.empty_state("Rincian UMKM per skala belum tersedia.")
        else:
            st.dataframe(
                pd.DataFrame(
                    {
                        "Skala": skala["indikator"].astype(str).str.replace("UMKM skala ", "", regex=False),
                        "Juta usaha": skala["nilai"].map(lambda value: decimal(value, 3)),
                        "Porsi": skala["porsi"].map(lambda value: f"{decimal(value, 2)}%"),
                    }
                ),
                hide_index=True,
                width="stretch",
                alt="Distribusi jumlah UMKM menurut skala usaha",
            )
            st.caption(
                "Hampir seluruh UMKM adalah usaha mikro. Produk yang masuk harus sesuai anggaran "
                "dan waktu setup segmen ini."
            )

    with st.container(border=True):
        st.subheader("Digitalisasi dan adopsi AI")
        persen = pasar[pasar["satuan"].astype(str).str.contains("Persen", case=False, na=False)]
        chart = charts.indicator_bar(persen[["indikator", "nilai", "satuan"]])
        if chart is not None:
            st.altair_chart(chart, alt="Persentase kontribusi PDB, adopsi AI, dan kesiapan bayar")
        else:
            components.empty_state("Indikator persentase belum tersedia.")
        st.caption(
            "Adopsi AI 67,65% berasal dari survei 204 responden yang cenderung melek digital. "
            "Jangan digeneralisasi ke seluruh 30,21 juta UMKM."
        )

    catatan_seri = pasar[
        pasar["catatan"].fillna("").astype(str).str.contains("Seri lama|65,4", case=False, regex=True)
    ]
    if not catatan_seri.empty:
        st.info(
            "Ada dua seri angka UMKM di sumber: SIDT-UMKM 2025 (30,21 juta, non-pertanian) dan "
            "seri lama 65,4 juta dengan basis berbeda. Dashboard memakai 30,21 juta.",
            icon=":material/warning:",
        )

    with st.expander("Sumber dan catatan semua indikator"):
        _sumber_table(pasar)
