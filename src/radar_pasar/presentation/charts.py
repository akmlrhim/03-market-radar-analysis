"""Chart Altair untuk halaman Radar Pasar."""

from __future__ import annotations

import altair as alt
import numpy as np
import pandas as pd

LOG_PRICE = alt.Scale(type="log", base=10)


def _numeric(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(np.nan, index=frame.index, dtype="float64")
    return pd.to_numeric(frame[column], errors="coerce")


def _price_label(frame: pd.DataFrame) -> pd.Series:
    nama = (
        frame["nama"].fillna("").astype(str)
        if "nama" in frame.columns
        else pd.Series("", index=frame.index)
    )
    paket = (
        frame["nama_paket"].fillna("").astype(str)
        if "nama_paket" in frame.columns
        else pd.Series("", index=frame.index)
    )
    return (nama + " · " + paket).str.strip(" ·")


def _category(frame: pd.DataFrame) -> pd.Series:
    if "kategori" not in frame.columns:
        return pd.Series("Lainnya", index=frame.index, dtype="object")
    return frame["kategori"].fillna("Lainnya").astype(str)


def price_bar(monthly: pd.DataFrame) -> alt.Chart | None:
    """Batang horizontal harga bulanan, diurutkan dari termahal."""
    if monthly.empty or "harga_bulanan" not in monthly.columns:
        return None

    frame = monthly.copy()
    frame["harga_bulanan"] = _numeric(frame, "harga_bulanan")
    frame = frame[frame["harga_bulanan"] > 0]
    if frame.empty:
        return None

    frame["label"] = _price_label(frame)
    frame = frame.sort_values("harga_bulanan", ascending=False).head(20)
    frame["kategori"] = _category(frame)

    return (
        alt.Chart(frame)
        .mark_bar(cornerRadiusEnd=4)
        .encode(
            y=alt.Y("label:N", sort="-x", title=None, axis=alt.Axis(labelLimit=180)),
            x=alt.X("harga_bulanan:Q", title="Harga bulanan (Rp)"),
            color=alt.Color("kategori:N", title="Kategori"),
            tooltip=[
                alt.Tooltip("nama:N", title="Kompetitor"),
                alt.Tooltip("nama_paket:N", title="Paket"),
                alt.Tooltip("harga_bulanan:Q", title="Harga/bulan", format=",.0f"),
                alt.Tooltip("kategori:N", title="Kategori"),
            ],
        )
        .properties(height=max(260, 24 * len(frame)))
    )


def price_scatter(monthly: pd.DataFrame) -> alt.Chart | None:
    """Sebaran harga bulanan versus jumlah fitur utama."""
    if monthly.empty or "jumlah_fitur" not in monthly.columns:
        return None

    frame = monthly.copy()
    frame["harga_bulanan"] = _numeric(frame, "harga_bulanan")
    frame["jumlah_fitur"] = _numeric(frame, "jumlah_fitur")
    frame = frame[(frame["harga_bulanan"] > 0) & frame["jumlah_fitur"].notna()]
    if frame.empty:
        return None

    frame["kategori"] = _category(frame)
    return (
        alt.Chart(frame)
        .mark_circle(size=110, opacity=0.75)
        .encode(
            x=alt.X("harga_bulanan:Q", scale=LOG_PRICE, title="Harga bulanan (Rp, skala log)"),
            y=alt.Y("jumlah_fitur:Q", title="Jumlah fitur utama"),
            color=alt.Color("kategori:N", title="Kategori"),
            tooltip=[
                alt.Tooltip("nama:N", title="Kompetitor"),
                alt.Tooltip("nama_paket:N", title="Paket"),
                alt.Tooltip("harga_bulanan:Q", title="Harga/bulan", format=",.0f"),
                alt.Tooltip("jumlah_fitur:Q", title="Fitur"),
            ],
        )
        .properties(height=340)
    )


def price_box(monthly: pd.DataFrame) -> alt.Chart | None:
    """Box plot harga bulanan per kategori."""
    if monthly.empty or "harga_bulanan" not in monthly.columns:
        return None

    frame = monthly.copy()
    frame["harga_bulanan"] = _numeric(frame, "harga_bulanan")
    frame = frame[frame["harga_bulanan"] > 0]
    if frame.empty:
        return None

    frame["kategori"] = _category(frame)
    return (
        alt.Chart(frame)
        .mark_boxplot(extent="min-max", size=36)
        .encode(
            x=alt.X("kategori:N", title=None),
            y=alt.Y("harga_bulanan:Q", scale=LOG_PRICE, title="Harga bulanan (Rp, skala log)"),
            color=alt.Color("kategori:N", legend=None),
            tooltip=[
                alt.Tooltip("kategori:N", title="Kategori"),
                alt.Tooltip("harga_bulanan:Q", title="Harga/bulan", format=",.0f"),
            ],
        )
        .properties(height=340)
    )


def price_position(monthly: pd.DataFrame, value: float) -> alt.Chart | None:
    """Posisi harga rencana terhadap sebaran paket kompetitor."""
    if monthly.empty or "harga_bulanan" not in monthly.columns or value <= 0:
        return None

    frame = monthly.copy()
    frame["harga_bulanan"] = _numeric(frame, "harga_bulanan")
    frame = frame[frame["harga_bulanan"] > 0]
    if frame.empty:
        return None

    frame["kategori"] = _category(frame)
    points = (
        alt.Chart(frame)
        .mark_circle(size=90, opacity=0.65)
        .encode(
            x=alt.X("harga_bulanan:Q", scale=LOG_PRICE, title="Harga bulanan (Rp, skala log)"),
            y=alt.Y("kategori:N", title=None),
            color=alt.Color("kategori:N", legend=None),
            tooltip=[
                alt.Tooltip("nama:N", title="Kompetitor"),
                alt.Tooltip("nama_paket:N", title="Paket"),
                alt.Tooltip("harga_bulanan:Q", title="Harga/bulan", format=",.0f"),
            ],
        )
    )
    rule_frame = pd.DataFrame({"harga": [float(value)]})
    rule = (
        alt.Chart(rule_frame)
        .mark_rule(color="#e45756", strokeWidth=2, strokeDash=[6, 4])
        .encode(x=alt.X("harga:Q", scale=LOG_PRICE))
    )
    label = (
        alt.Chart(rule_frame)
        .mark_text(text="Harga rencana", align="left", dx=6, dy=-14, color="#e45756")
        .encode(x=alt.X("harga:Q", scale=LOG_PRICE))
    )
    return (points + rule + label).properties(height=280)


def ranking_bar(frame: pd.DataFrame, label: str = "masalah", value: str = "jumlah") -> alt.Chart | None:
    """Peringkat horizontal untuk tema masalah, hambatan, atau kategori."""
    if frame.empty or label not in frame.columns or value not in frame.columns:
        return None

    data = frame.copy()
    data[value] = pd.to_numeric(data[value], errors="coerce").fillna(0)
    data = data[data[value] > 0].sort_values(value, ascending=False).head(12)
    if data.empty:
        return None

    return (
        alt.Chart(data)
        .mark_bar(cornerRadiusEnd=4, color="#4c78a8")
        .encode(
            y=alt.Y(f"{label}:N", sort="-x", title=None, axis=alt.Axis(labelLimit=190)),
            x=alt.X(f"{value}:Q", title="Jumlah", axis=alt.Axis(tickMinStep=1, format="d")),
            tooltip=[
                alt.Tooltip(f"{label}:N", title=label.capitalize()),
                alt.Tooltip(f"{value}:Q", title=value.capitalize()),
            ],
        )
        .properties(height=max(200, 26 * len(data)))
    )


def price_vs_features(monthly: pd.DataFrame) -> alt.Chart | None:
    """Peta posisi harga versus kelengkapan fitur, dengan label nama."""
    if monthly.empty or "jumlah_fitur" not in monthly.columns:
        return None

    frame = monthly.copy()
    frame["harga_bulanan"] = _numeric(frame, "harga_bulanan")
    frame["jumlah_fitur"] = _numeric(frame, "jumlah_fitur")
    frame = frame[(frame["harga_bulanan"] > 0) & frame["jumlah_fitur"].notna()]
    if frame.empty:
        return None

    frame["kategori"] = _category(frame)
    base = alt.Chart(frame).encode(
        x=alt.X("harga_bulanan:Q", scale=LOG_PRICE, title="Harga bulanan (Rp, skala log)"),
        y=alt.Y("jumlah_fitur:Q", title="Jumlah fitur utama"),
    )
    points = base.mark_circle(size=130, opacity=0.75).encode(
        color=alt.Color("kategori:N", title="Kategori"),
        tooltip=[
            alt.Tooltip("nama:N", title="Kompetitor"),
            alt.Tooltip("nama_paket:N", title="Paket"),
            alt.Tooltip("harga_bulanan:Q", title="Harga/bulan", format=",.0f"),
            alt.Tooltip("jumlah_fitur:Q", title="Fitur"),
        ],
    )
    labels = base.mark_text(align="left", dx=9, fontSize=11).encode(text="nama:N")
    return (points + labels).properties(height=380)


def feature_coverage(summary: pd.DataFrame, total: int | None = None) -> alt.Chart | None:
    """Fitur yang paling banyak dan paling sedikit dimiliki kompetitor."""
    if summary.empty or not {"fitur", "jumlah"}.issubset(summary.columns):
        return None

    frame = summary.copy()
    frame["jumlah"] = pd.to_numeric(frame["jumlah"], errors="coerce").fillna(0)
    frame = frame.sort_values("jumlah", ascending=False).head(12)
    if frame.empty:
        return None

    if total:
        frame["persen"] = frame["jumlah"] / total * 100
        tooltip = [
            alt.Tooltip("fitur:N", title="Fitur"),
            alt.Tooltip("jumlah:Q", title="Kompetitor"),
            alt.Tooltip("persen:Q", title="Cakupan", format=".0f"),
        ]
    else:
        tooltip = [
            alt.Tooltip("fitur:N", title="Fitur"),
            alt.Tooltip("jumlah:Q", title="Kompetitor"),
        ]

    return (
        alt.Chart(frame)
        .mark_bar(cornerRadiusEnd=4, color="#72b7b2")
        .encode(
            y=alt.Y("fitur:N", sort="-x", title=None),
            x=alt.X("jumlah:Q", title="Jumlah kompetitor", axis=alt.Axis(tickMinStep=1, format="d")),
            tooltip=tooltip,
        )
        .properties(height=max(240, 24 * len(frame)))
    )


