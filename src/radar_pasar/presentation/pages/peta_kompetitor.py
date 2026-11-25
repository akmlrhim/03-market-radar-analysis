"""Halaman Peta kompetitor."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from radar_pasar.data import repository
from radar_pasar.domain.features import feature_counts, feature_matrix
from radar_pasar.presentation import charts, components


def _filtered(
    kompetitor: pd.DataFrame,
    search: str,
    kategori: list[str],
    segmen: list[str],
    kota: str,
    hanya_bahasa: bool,
) -> pd.DataFrame:
    frame = kompetitor.copy()
    if search.strip():
        frame = frame[frame["nama"].fillna("").str.contains(search.strip(), case=False, regex=False)]
    if kategori:
        frame = frame[frame["kategori"].isin(kategori)]
    if segmen:
        frame = frame[frame["segmen_target"].isin(segmen)]
    if kota != "Semua kota":
        frame = frame[frame["kota_basis"] == kota]
    if hanya_bahasa:
        frame = frame[frame["bahasa_indonesia"].fillna(False).astype(bool)]
    return frame.reset_index(drop=True)


def _table(frame: pd.DataFrame) -> None:
    counts = feature_counts(frame)
    view = pd.DataFrame(
        {
            "Kompetitor": frame["nama"].fillna("").astype(str),
            "Kategori": frame["kategori"].fillna("").astype(str),
            "Segmen": frame["segmen_target"].fillna("").astype(str),
            "Kota": frame["kota_basis"].fillna("").astype(str),
            "Tahun berdiri": frame["tahun_berdiri"].map(
                lambda value: str(int(value)) if pd.notna(value) else "—"
            ),
            "Fitur": frame["id"].map(lambda value: counts.get(int(value), 0) if pd.notna(value) else 0),
            "Situs": frame["website"].fillna("").astype(str),
        }
    )
    st.dataframe(
        view,
        hide_index=True,
        width="stretch",
        column_config={
            "Situs": st.column_config.LinkColumn("Situs", display_text="Buka"),
        },
        alt="Tabel kompetitor hasil filter",
    )


def render() -> None:
    data = repository.load_all()
    kompetitor = data["kompetitor"]

    components.quality_notice()
    components.intro(
        "Filter kompetitor berdasarkan kategori, segmen, kota, dan dukungan Bahasa Indonesia. "
        "Pilih satu kompetitor untuk membaca detail dan sumbernya."
    )

    if kompetitor.empty:
        components.empty_state("Belum ada data kompetitor. Isi CSV di folder data/ lalu muat ulang.")
        return

    with st.container(border=True):
        baris_pertama = st.columns([2, 2, 2], gap="medium")
        with baris_pertama[0]:
            search = st.text_input("Cari nama", placeholder="Mis. Cekat atau Wablas")
        with baris_pertama[1]:
            kategori = st.pills(
                "Kategori",
                sorted(kompetitor["kategori"].dropna().unique().tolist()),
                selection_mode="multi",
                wrap=True,
            )
        with baris_pertama[2]:
            segmen = st.pills(
                "Segmen",
                sorted(kompetitor["segmen_target"].dropna().unique().tolist()),
                selection_mode="multi",
                wrap=True,
            )

        baris_kedua = st.columns([2, 2, 2], gap="medium")
        with baris_kedua[0]:
            kota = st.selectbox(
                "Kota basis",
                ["Semua kota", *sorted(kompetitor["kota_basis"].dropna().unique().tolist())],
            )
        with baris_kedua[1]:
            hanya_bahasa = st.toggle("Hanya yang mendukung Bahasa Indonesia", value=False)
        with baris_kedua[2]:
            st.caption("Filter berlaku untuk tabel, detail, dan matriks fitur.")

    frame = _filtered(kompetitor, search, kategori or [], segmen or [], kota, hanya_bahasa)
    if frame.empty:
        components.empty_state("Tidak ada kompetitor yang cocok dengan filter. Longgarkan pilihan.")
        return

    st.caption(f"{len(frame)} dari {len(kompetitor)} kompetitor ditampilkan.")
    _table(frame)

    st.divider()

    st.subheader("Detail kompetitor")
    pilihan = st.selectbox("Pilih kompetitor", frame["nama"].tolist())
    row = frame.loc[frame["nama"] == pilihan].iloc[0]
    components.render_competitor_detail(row)

    st.divider()

    st.subheader("Matriks perbandingan fitur")
    matrix, summary = feature_matrix(frame)
    if matrix.empty or summary.empty:
        components.empty_state("Fitur utama belum diisi untuk kompetitor yang dipilih.")
        return

    chart = charts.feature_coverage(summary, total=len(frame))
    if chart is not None:
        st.altair_chart(chart, alt="Fitur yang paling banyak dimiliki kompetitor terpilih")

    fitur = [column for column in matrix.columns if column not in ("id", "nama")]
    display = matrix.drop(columns=["id"]).rename(columns={"nama": "Kompetitor"})
    for column in fitur:
        display[column] = display[column].map(lambda value: "✓" if value else "—")

    with st.expander("Lihat matriks lengkap", expanded=True):
        st.dataframe(
            display,
            hide_index=True,
            width="stretch",
            alt="Matriks centang fitur per kompetitor",
        )
