"""Titik masuk Radar Pasar.

Jalankan dari folder proyek:

    streamlit run app.py

Data dibaca dari CSV di folder data/. Untuk memperbarui data, ganti berkas CSV
(misalnya hasil penarikan lewat MCP) lalu tekan "Muat ulang data" di sidebar.
"""

from __future__ import annotations

import streamlit as st

from radar_pasar.config import APP_ICON, APP_TITLE
from radar_pasar.data import repository
from radar_pasar.presentation.pages import (
    analisis_harga,
    peta_kompetitor,
    ringkasan,
)

st.set_page_config(
    page_title=APP_TITLE,
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)

pages = st.navigation(
    {
        "": [
            st.Page(
                ringkasan.render,
                title="Ringkasan",
                icon=":material/dashboard:",
                help="Kartu metrik utama, temuan, rekomendasi, dan status pembaruan data.",
                default=True,
            ),
        ],
        "Riset": [
            st.Page(
                peta_kompetitor.render,
                title="Peta kompetitor",
                icon=":material/storefront:",
                help="Filter kompetitor, baca detail, dan bandingkan matriks fitur.",
                url_path="peta-kompetitor",
            ),
            st.Page(
                analisis_harga.render,
                title="Analisis harga",
                icon=":material/sell:",
                help="Bandingkan harga paket, biaya tersembunyi, dan simulasikan harga Impost.",
                url_path="analisis-harga",
            ),
        ],
    },
    position="sidebar",
)

with st.sidebar:
    if st.button("Muat ulang data", icon=":material/refresh:", width="stretch"):
        repository.refresh()
        st.rerun()

    quality = repository.quality_report()
    last_checked = quality["last_checked"]
    st.caption("Data terakhir dicek")
    st.markdown(f"**{last_checked.strftime('%d %b %Y') if last_checked else 'Belum ada'}**")
    st.caption(
        f"{quality['competitor_count']} kompetitor · "
        f"{quality['competitors_with_price']} dengan harga tercatat"
    )
    if quality["unverified_count"]:
        st.caption(f":orange[{quality['unverified_count']} belum terverifikasi]")
    if quality["stale_count"]:
        st.caption(f":red[{quality['stale_count']} baris > 30 hari]")
    st.caption(
        "Sumber: situs resmi kompetitor, Kementerian UMKM, BPS, dan survei publik."
    )

st.title(pages.title, icon=pages.icon)
pages.run()
