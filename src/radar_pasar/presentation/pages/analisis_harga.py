"""Halaman Analisis harga."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from radar_pasar.data import repository
from radar_pasar.domain.features import with_feature_counts
from radar_pasar.domain.formatting import rupiah
from radar_pasar.domain.pricing import (
    monthly_prices,
    nearest_package,
    position_label,
    price_frame,
    price_percentile,
    public_price_coverage,
)
from radar_pasar.presentation import charts, components


def _stats(monthly: pd.DataFrame) -> dict[str, object]:
    if monthly.empty:
        return {"count": 0, "cheapest": None, "median": None, "expensive": None, "dengan_harga": 0}
    values = pd.to_numeric(monthly["harga_bulanan"], errors="coerce").dropna()
    return {
        "count": int(len(values)),
        "cheapest": float(values.min()),
        "median": float(values.median()),
        "expensive": float(values.max()),
        "dengan_harga": int(monthly["kompetitor_id"].nunique()),
    }


def _nearest_text(monthly: pd.DataFrame, rencana: float) -> str:
    nearest = nearest_package(monthly, rencana)
    if nearest is None:
        return "Belum ada pembanding."
    selisih = float(nearest["selisih"])
    arah = "lebih mahal" if selisih > 0 else "lebih murah"
    return (
        f"Paling dekat: {nearest['nama']} · {nearest['nama_paket']} "
        f"({rupiah(nearest['harga_bulanan'])}, {rupiah(abs(selisih))} {arah})."
    )


def render() -> None:
    data = repository.load_all()
    kompetitor = data["kompetitor"]
    harga = data["harga"]

    components.quality_notice()
    components.intro(
        "Bandingkan harga paket, hitung ekuivalen bulanan, dan lihat posisi rencana harga Impost. "
        "Harga tahunan dan sekali bayar dinormalisasi agar bisa dibandingkan."
    )

    if kompetitor.empty or harga.empty:
        components.empty_state("Belum ada data kompetitor atau harga. Isi CSV di folder data/.")
        return

    kategori_semua = sorted(kompetitor["kategori"].dropna().unique().tolist())
    kategori_pilihan = st.pills("Kategori", kategori_semua, selection_mode="multi")
    kategori = kategori_pilihan or kategori_semua

    prices = price_frame(kompetitor, harga)
    prices = prices[prices["kategori"].isin(kategori)] if kategori else prices
    monthly = monthly_prices(kompetitor, harga)
    monthly = monthly[monthly["kategori"].isin(kategori)] if kategori else monthly
    stats = _stats(monthly)

    if stats["count"] == 0:
        components.empty_state(
            "Tidak ada paket dengan ekuivalen bulanan pada kategori ini. "
            "Kompetitor mungkin memilih jalur sales."
        )
        components.render_price_table(
            prices,
            caption="Semua paket yang tercatat, termasuk harga non-bulanan.",
        )
        return

    with st.container(horizontal=True):
        components.price_kpi(
            "Paket bulanan",
            str(stats["count"]),
            "Hanya paket yang bisa disetarakan per bulan.",
        )
        components.price_kpi("Termurah", rupiah(stats["cheapest"]))
        components.price_kpi("Median", rupiah(stats["median"]))
        components.price_kpi("Tertinggi", rupiah(stats["expensive"]))
        with_price, total = public_price_coverage(kompetitor, harga)
        components.price_kpi(
            "Cakupan harga",
            f"{with_price}/{total}",
            "Kompetitor dengan setidaknya satu harga bulanan numerik.",
        )

    if len(kategori) > 1:
        st.caption(
            ":orange[Statistik mencampur beberapa kategori.] Gateway dan POS dijual dengan model "
            "berbeda dari AI agent; pilih kategori tunggal sebelum menarik kesimpulan harga."
        )

    with st.container(border=True):
        st.subheader("Daftar harga paket")
        st.caption(
            "Seluruh harga dalam rupiah. Paket tanpa nominal publik ditandai 'Hubungi sales'; "
            "ekuivalen bulanan kosong berarti harga tidak bisa disetarakan per bulan."
        )
        components.render_package_price_table(
            prices.sort_values("harga_bulanan", na_position="last")
        )

    kiri, kanan = st.columns(2, gap="medium")
    with kiri, st.container(border=True):
        st.subheader("Harga bulanan per paket")
        chart = charts.price_bar(monthly)
        if chart is not None:
            st.altair_chart(chart, alt="Perbandingan harga bulanan setiap paket kompetitor")
    with kanan, st.container(border=True):
        st.subheader("Harga versus jumlah fitur")
        berfitur = with_feature_counts(monthly, kompetitor)
        chart = charts.price_scatter(berfitur)
        if chart is not None:
            st.altair_chart(chart, alt="Sebaran harga bulanan dibanding jumlah fitur utama")
        else:
            components.empty_state("Jumlah fitur belum bisa dihitung.")

    with st.container(border=True):
        st.subheader("Rentang harga per kategori")
        chart = charts.price_box(monthly)
        if chart is not None:
            st.altair_chart(chart, alt="Box plot harga bulanan untuk setiap kategori")
        else:
            components.empty_state("Data harga belum cukup untuk box plot.")

    with st.container(border=True):
        st.subheader("Rincian biaya efektif")
        components.render_effective_cost_table(
            prices.sort_values("harga_bulanan", na_position="last"),
            caption=(
                "Estimasi total bulanan memakai harga langganan sebagai batas bawah. "
                "Biaya pesan, kuota, agen tambahan, PPN, dan implementasi baru bisa "
                "dinilai setelah jumlah pemakaian ditentukan."
            ),
        )

    with st.container(border=True):
        st.subheader("Simulator harga Impost")
        rencana = st.number_input(
            "Harga bulanan paket Impost (Rp)",
            min_value=10_000,
            max_value=20_000_000,
            value=149_000,
            step=10_000,
        )
        persentil = price_percentile(monthly, float(rencana))
        label = position_label(persentil)
        with st.container(horizontal=True):
            st.metric("Posisi", label, border=True)
            st.metric("Persentil", f"{persentil:.0f}", border=True)
            st.metric("Paket pembanding", str(stats["count"]), border=True)
        st.caption(
            f"Harga {rupiah(rencana)} berada di atas atau sama dengan {persentil:.0f}% paket bulanan. "
            "Persentil dihitung dari harga paket, bukan dari kemauan bayar."
        )
        st.caption(_nearest_text(monthly, float(rencana)))
        chart = charts.price_position(monthly, float(rencana))
        if chart is not None:
            st.altair_chart(chart, alt="Posisi harga rencana dibanding sebaran harga kompetitor")

    with st.expander("Lihat semua paket dan ekuivalen bulanan"):
        components.render_price_table(
            prices.sort_values("harga_bulanan", na_position="last"),
            caption="Paket tanpa ekuivalen bulanan tetap ditampilkan sebagai pembanding.",
        )
