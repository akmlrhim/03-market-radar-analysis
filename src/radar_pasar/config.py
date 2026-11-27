"""Konfigurasi global Radar Pasar: judul, lokasi data, dan ambang data lama."""

from __future__ import annotations

from pathlib import Path

APP_TITLE = "Radar Pasar"
APP_ICON = "📡"

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"

TABLE_FILES = {
    "kompetitor": "kompetitor.csv",
    "harga": "harga.csv",
}

# Data yang lebih lama dari ini dianggap perlu dicek ulang.
STALE_DAYS = 30
