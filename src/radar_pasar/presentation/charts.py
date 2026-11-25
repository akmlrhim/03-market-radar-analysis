"""Chart Altair untuk halaman Radar Pasar."""

from __future__ import annotations

from typing import Any

import altair as alt
import numpy as np
import pandas as pd

from radar_pasar.domain.market import MarketModel, stage_rows

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


def market_stage_bar(model: MarketModel) -> alt.Chart | None:
    """Corong pasar dengan sumbu log agar tahap kecil tetap terbaca."""
    stages = stage_rows(model)
    if not stages:
        return None

    frame = pd.DataFrame(stages, columns=["tahap", "jumlah"])
    frame["mulai"] = 1.0
    base = alt.Chart(frame).encode(
        y=alt.Y("tahap:N", sort=None, title=None),
        x=alt.X("mulai:Q", scale=LOG_PRICE, title="Jumlah pengguna (skala log)"),
        x2="jumlah:Q",
    )
    bars = base.mark_bar(cornerRadiusEnd=4, color="#4c78a8").encode(
        tooltip=[
            alt.Tooltip("tahap:N", title="Tahap"),
            alt.Tooltip("jumlah:Q", title="Jumlah", format=",.0f"),
        ]
    )
    labels = (
        alt.Chart(frame)
        .mark_text(align="left", dx=6, fontSize=11)
        .encode(
            y=alt.Y("tahap:N", sort=None),
            x=alt.X("jumlah:Q", scale=LOG_PRICE),
            text=alt.Text("jumlah:Q", format=",.0f"),
        )
    )
    return (bars + labels).properties(height=280)


def indicator_bar(frame: pd.DataFrame) -> alt.Chart | None:
    """Batang indikator pasar yang sudah diseleksi halaman."""
    if frame.empty or not {"indikator", "nilai"}.issubset(frame.columns):
        return None

    data = frame.copy()
    data["nilai"] = pd.to_numeric(data["nilai"], errors="coerce")
    data = data[data["nilai"].notna()]
    if data.empty:
        return None

    tooltip: list[Any] = [
        alt.Tooltip("indikator:N", title="Indikator"),
        alt.Tooltip("nilai:Q", title="Nilai", format=",.2f"),
    ]
    color: dict[str, Any] = {}
    if "satuan" in data.columns:
        data["satuan"] = data["satuan"].fillna("").astype(str)
        color["color"] = alt.Color("satuan:N", title="Satuan")
        tooltip.append(alt.Tooltip("satuan:N", title="Satuan"))

    return (
        alt.Chart(data)
        .mark_bar(cornerRadiusEnd=4)
        .encode(
            y=alt.Y("indikator:N", sort="-x", title=None),
            x=alt.X("nilai:Q", title="Nilai"),
            tooltip=tooltip,
            **color,
        )
        .properties(height=max(220, 28 * len(data)))
    )


def vw_line(curves: pd.DataFrame, points: dict[str, float] | None = None) -> alt.Chart | None:
    """Kurva Van Westendorp beserta garis titik potongnya."""
    if curves.empty or not {"harga", "kurva", "persen"}.issubset(curves.columns):
        return None

    frame = curves.copy()
    frame["harga"] = _numeric(frame, "harga")
    frame["persen"] = _numeric(frame, "persen")
    frame = frame[(frame["harga"] > 0) & frame["persen"].notna()]
    if frame.empty:
        return None

    lines = (
        alt.Chart(frame)
        .mark_line(strokeWidth=2)
        .encode(
            x=alt.X("harga:Q", scale=LOG_PRICE, title="Harga (Rp, skala log)"),
            y=alt.Y("persen:Q", title="Responden (%)"),
            color=alt.Color("kurva:N", title=None),
            tooltip=[
                alt.Tooltip("kurva:N", title="Kurva"),
                alt.Tooltip("harga:Q", title="Harga", format=",.0f"),
                alt.Tooltip("persen:Q", title="Responden", format=".1f"),
            ],
        )
    )

    if not points:
        return lines.properties(height=340)

    rules = pd.DataFrame([{"harga": price, "label": label} for label, price in points.items()])
    markers = (
        alt.Chart(rules)
        .mark_rule(strokeDash=[4, 4], opacity=0.45)
        .encode(
            x=alt.X("harga:Q", scale=LOG_PRICE),
            color=alt.Color("label:N", legend=None),
        )
    )
    return (markers + lines).properties(height=340)


def wtp_bar(wtp: pd.DataFrame) -> alt.Chart | None:
    """Kemauan bayar per segmen dalam rentang yang tetap."""
    if wtp.empty or not {"segmen", "rentang", "jumlah"}.issubset(wtp.columns):
        return None

    frame = wtp.copy()
    frame["jumlah"] = pd.to_numeric(frame["jumlah"], errors="coerce").fillna(0)
    if frame["jumlah"].sum() <= 0:
        return None

    order = [label for label in frame["rentang"].astype(str).unique()]
    return (
        alt.Chart(frame)
        .mark_bar()
        .encode(
            x=alt.X("rentang:N", sort=order, title="Kemauan bayar per bulan"),
            y=alt.Y("jumlah:Q", title="Responden", stack="zero"),
            color=alt.Color("segmen:N", title="Segmen"),
            tooltip=[
                alt.Tooltip("segmen:N", title="Segmen"),
                alt.Tooltip("rentang:N", title="Rentang"),
                alt.Tooltip("jumlah:Q", title="Responden"),
            ],
        )
        .properties(height=320)
    )


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


def price_band_chart(tiers: list[dict[str, object]] | pd.DataFrame) -> alt.Chart | None:
    """Rentang harga rekomendasi per paket Impost."""
    frame = tiers.copy() if isinstance(tiers, pd.DataFrame) else pd.DataFrame(tiers)
    if frame.empty or not {"paket", "harga"}.issubset(frame.columns):
        return None

    frame["harga"] = pd.to_numeric(frame["harga"], errors="coerce")
    frame = frame[frame["harga"].notna()]
    if frame.empty:
        return None

    color: dict[str, Any] = {}
    tooltip: list[Any] = [
        alt.Tooltip("paket:N", title="Paket"),
        alt.Tooltip("harga:Q", title="Harga/bulan", format=",.0f"),
    ]
    if "posisi" in frame.columns:
        frame["posisi"] = frame["posisi"].fillna("").astype(str)
        color["color"] = alt.Color("posisi:N", title="Posisi pasar")
        tooltip.append(alt.Tooltip("posisi:N", title="Posisi"))

    base = alt.Chart(frame).encode(
        y=alt.Y("paket:N", sort=None, title=None),
        x=alt.X("harga:Q", scale=alt.Scale(zero=False), title="Harga bulanan (Rp)"),
    )
    bars = base.mark_bar(cornerRadiusEnd=6, size=26).encode(tooltip=tooltip, **color)
    labels = base.mark_text(align="left", dx=6, fontSize=11).encode(text=alt.Text("harga:Q", format=",.0f"))
    return (bars + labels).properties(height=200)
