"""Deteksi celah pasar dari data kompetitor dan harga."""

from __future__ import annotations

import pandas as pd

from radar_pasar.domain.features import feature_matrix
from radar_pasar.domain.pricing import monthly_prices, public_price_coverage

GAP_COLUMNS = ["gap", "temuan", "prioritas", "bukti"]
_PRIORITY_ORDER = {"Tinggi": 0, "Sedang": 1, "Rendah": 2}
_EMPTY_COSTS = {"", "-", "none", "nan", "tidak ada"}


def _empty() -> pd.DataFrame:
    return pd.DataFrame(columns=GAP_COLUMNS)


def _text(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.strip()


def _names(frame: pd.DataFrame) -> list[str]:
    if "nama" not in frame.columns:
        return []
    return [name for name in _text(frame["nama"]).tolist() if name]


def _preview(names: list[str], limit: int = 3) -> str:
    shown = ", ".join(names[:limit])
    if len(names) > limit:
        shown += f", +{len(names) - limit} lainnya"
    return shown


def _transparency(kompetitor: pd.DataFrame, harga: pd.DataFrame) -> list[dict[str, object]]:
    """Kompetitor tanpa harga numerik dan paket yang menyembunyikan biaya."""
    total = len(kompetitor)
    with_price, _ = public_price_coverage(kompetitor, harga)
    gaps: list[dict[str, object]] = []

    if with_price < total:
        monthly = monthly_prices(kompetitor, harga)
        priced = set(monthly["kompetitor_id"].dropna().astype(int)) if not monthly.empty else set()
        unpriced = [
            str(row["nama"])
            for _, row in kompetitor.iterrows()
            if pd.notna(row.get("id")) and int(row["id"]) not in priced
        ]
        share = (total - with_price) / total
        gaps.append(
            {
                "gap": "Harga publik yang transparan",
                "temuan": (
                    f"{total - with_price} dari {total} kompetitor tidak mencantumkan harga "
                    "bulanan numerik, sehingga pembanding harga tidak lengkap."
                ),
                "prioritas": "Tinggi" if share >= 0.25 else "Sedang",
                "bukti": f"Tanpa harga numerik: {_preview(unpriced)}.",
            }
        )

    if not harga.empty and "biaya_tambahan" in harga.columns:
        extra = _text(harga["biaya_tambahan"])
        hidden = harga[~extra.str.lower().isin(_EMPTY_COSTS)]
        if not hidden.empty:
            paket = _text(hidden["nama_paket"]).tolist() if "nama_paket" in hidden.columns else []
            gaps.append(
                {
                    "gap": "Rincian biaya tambahan",
                    "temuan": (
                        f"{len(hidden)} paket menambahkan biaya pesan, kuota, atau implementasi "
                        "di luar harga langganan."
                    ),
                    "prioritas": "Sedang",
                    "bukti": f"Contoh paket: {_preview(paket)}.",
                }
            )

    return gaps


def _freelancer(kompetitor: pd.DataFrame) -> dict[str, object] | None:
    if "segmen_target" not in kompetitor.columns:
        return None
    segmen = _text(kompetitor["segmen_target"]).str.lower()
    if segmen.str.contains("freelancer", na=False).any():
        return None
    tercatat = sorted({value for value in _text(kompetitor["segmen_target"]).tolist() if value})
    return {
        "gap": "Paket khusus freelancer",
        "temuan": (
            "Tidak ada kompetitor yang menempatkan freelancer sebagai segmen utama; "
            "kebutuhan administrasi dan harga kecil belum dilayani secara eksplisit."
        ),
        "prioritas": "Tinggi",
        "bukti": f"Segmen yang tercatat: {', '.join(tercatat) if tercatat else 'belum diisi'}.",
    }


def _annual(harga: pd.DataFrame) -> dict[str, object] | None:
    if harga.empty or "periode" not in harga.columns:
        return None
    periode = _text(harga["periode"]).str.lower()
    if periode.str.contains("tahun", na=False).any():
        return None
    return {
        "gap": "Opsi langganan tahunan",
        "temuan": (
            "Semua paket yang tercatat dijual bulanan atau sekali bayar; belum ada opsi "
            "tahunan yang bisa mengunci retensi dan memberi diskon."
        ),
        "prioritas": "Rendah",
        "bukti": f"{len(harga)} baris harga, tanpa periode tahunan.",
    }


def _trial(kompetitor: pd.DataFrame, harga: pd.DataFrame) -> dict[str, object] | None:
    kolom = [column for column in ("nama_paket", "batasan", "model_harga") if column in harga.columns]
    if harga.empty or not kolom:
        return None
    teks = _text(harga[kolom[0]])
    for column in kolom[1:]:
        teks = teks + " " + _text(harga[column])
    if teks.str.lower().str.contains("gratis|free|trial|uji coba", regex=True, na=False).any():
        return None
    return {
        "gap": "Uji coba gratis",
        "temuan": (
            "Tidak ada paket uji coba gratis yang dipublikasikan; calon pengguna harus "
            "membayar sebelum bisa menilai kecocokan produk."
        ),
        "prioritas": "Sedang",
        "bukti": f"{len(harga)} paket diperiksa, tidak ada label gratis atau trial.",
    }


def _language(kompetitor: pd.DataFrame) -> dict[str, object] | None:
    if "bahasa_indonesia" not in kompetitor.columns:
        return None
    supported = kompetitor["bahasa_indonesia"].fillna(False).astype(bool)
    missing = int((~supported).sum())
    if not missing:
        return None
    tanpa = _text(kompetitor.loc[~supported, "nama"]).tolist() if "nama" in kompetitor.columns else []
    return {
        "gap": "Antarmuka Bahasa Indonesia",
        "temuan": f"{missing} kompetitor belum menyatakan dukungan Bahasa Indonesia.",
        "prioritas": "Sedang",
        "bukti": f"Belum mendukung: {_preview(tanpa)}.",
    }


def _feature_whitespace(kompetitor: pd.DataFrame) -> list[dict[str, object]]:
    """Fitur yang hanya dimiliki segelintir kompetitor sebagai ruang diferensiasi."""
    total = len(kompetitor)
    if total < 3:
        return []

    matrix, summary = feature_matrix(kompetitor)
    if summary.empty:
        return []

    threshold = max(1, int(total * 0.2))
    rare = summary[summary["jumlah"] <= threshold].head(2)
    findings: list[dict[str, object]] = []
    for _, row in rare.iterrows():
        fitur = str(row["fitur"])
        if fitur not in matrix.columns:
            continue
        owners = _text(matrix.loc[matrix[fitur].astype(bool), "nama"]).tolist()
        findings.append(
            {
                "gap": f"Celah fitur: {fitur}",
                "temuan": (
                    f"Hanya {len(owners)} dari {total} kompetitor menawarkan {fitur}; "
                    "fitur ini masih bisa jadi pembeda."
                ),
                "prioritas": "Sedang",
                "bukti": f"Pemilik fitur: {_preview(owners)}.",
            }
        )
    return findings


def gap_findings(kompetitor: pd.DataFrame, harga: pd.DataFrame) -> pd.DataFrame:
    """Daftar celah beserta bukti dan prioritas yang bisa ditindaklanjuti."""
    if kompetitor.empty:
        return _empty()

    findings: list[dict[str, object]] = []
    findings.extend(_transparency(kompetitor, harga))

    for finding in (
        _freelancer(kompetitor),
        _annual(harga),
        _trial(kompetitor, harga),
        _language(kompetitor),
    ):
        if finding is not None:
            findings.append(finding)

    findings.extend(_feature_whitespace(kompetitor))

    if not findings:
        return _empty()

    frame = pd.DataFrame(findings, columns=GAP_COLUMNS)
    frame["_order"] = frame["prioritas"].map(_PRIORITY_ORDER).fillna(len(_PRIORITY_ORDER))
    frame = frame.sort_values("_order", kind="stable").drop(columns="_order")
    return frame.reset_index(drop=True)
