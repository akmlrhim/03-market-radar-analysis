# Radar Pasar

Dashboard riset kompetitor, pasar, dan harga untuk produk digital dan AI agent
Impost Teknologi Indonesia. Target segmen: UMKM dan freelancer.

Dibangun dengan Streamlit + pandas + Altair. Data disimpan sebagai CSV di
`data/` dan hanya dibaca oleh aplikasi: pembaruan dilakukan di luar dashboard
(misalnya hasil penarikan lewat MCP), lalu dimuat ulang.

## Menjalankan

```powershell
# dari folder proyek
.\.venv\Scripts\activate
pip install -e .
streamlit run app.py
```

Atau langsung:

```powershell
.\.venv\Scripts\streamlit.exe run app.py
```

Buka `http://localhost:8501`. Tidak ada login: dashboard dijalankan lokal atau di
VPS internal.

Jika muncul `ModuleNotFoundError: No module named 'radar_pasar'`, berarti
perintah `streamlit` berasal dari Python global, bukan dari `.venv`. Jalankan
`.\.venv\Scripts\streamlit.exe run app.py`, atau pasang paket di environment
yang aktif dengan `pip install -e .`.

### Pengembangan

```powershell
pip install -e ".[dev]"
python -m pytest -q
ruff check .
```

## Halaman

| Halaman | Isi |
| --- | --- |
| Ringkasan | Metrik utama, tiga temuan, tiga rekomendasi, status data |
| Peta kompetitor | Filter, detail per kompetitor, matriks fitur |
| Analisis harga | Bar, scatter, box plot, biaya tersembunyi, simulator harga |
| Potensi pasar | TAM/SAM/SOM dengan slider, distribusi UMKM, sumber |
| Gap dan rekomendasi | Celah pasar otomatis, posisi harga vs fitur, rekomendasi paket |

## Data

Data awal diisi dari riset 25-26 November 2026: **22 kompetitor** dan **68 baris
harga**. Sumber utama:

- Halaman harga dan produk resmi kompetitor (Cekat.ai, Mekari Qontak, Qiscus,
  Botika, Canggih.AI, Dripsender, Kata.ai, Meeting.ai/Bahasa.ai, Sagara
  Technology, Kelas.com, Wablas, majoo, Convia, Weaku, FirstCRM, Core
  Freelancers, Templatku.com, MySkill, Sahut, Spicelab, Mahirusaha, Mobichat).
- Kementerian UMKM / SIDT-UMKM melalui publikasi Kadin: 30,21 juta UMKM
  non-pertanian per 31 Desember 2025.
- BPS Sakernas Agustus 2025: 36 juta pekerja bebas/freelancer.
- Survei UKMINDONESIA x ICCI 2025: 67,65% dari 204 responden UMKM memakai AI
  (sampel kecil, cenderung melek digital).

Setiap baris kompetitor dan harga menyimpan `sumber_url` dan `tanggal_cek`.

### Aturan verifikasi

- **Hanya data terverifikasi yang masuk dataset.** Baris yang tidak bisa
  dipertanggungjawabkan dihapus, bukan ditandai "Belum". Contoh: AdoloChat
  dikeluarkan karena domainnya tidak aktif dan harganya hanya dari artikel
  pihak ketiga.
- `scripts/seed_data.py` menolak menulis bila ada kompetitor berstatus belum
  terverifikasi, dan `tests/test_data.py` memeriksa hal yang sama pada CSV.
- Paket yang nominalnya tidak dipublikasikan tetap dicatat sebagai
  "hubungi sales" agar keterbukaan harga bisa diukur.

### Catatan penting

- **Harga berubah cepat.** Cek ulang halaman resmi sebelum memakai angka.
- **16 dari 22 kompetitor** memiliki harga bulanan numerik; sisanya memilih
  jalur sales. Median paket bulanan Rp369.500. Paket bulanan termurah Rp22.000
  (Wablas Nano); ekuivalen bulanan terendah Rp14.917 berasal dari paket tahunan
  promo MySkill. Paket tertinggi Rp15.000.000 (Spicelab Enterprise, harga
  mulai dari).
- **Kategori tidak selalu sebanding.** Wablas (WhatsApp Gateway), majoo
  (POS UMKM), Templatku.com (produk digital sekali beli), dan MySkill
  (e-learning) dijual dengan model berbeda dari langganan AI agent. Gunakan
  filter kategori di halaman Analisis harga sebelum membandingkan.
- **Verifikasi 26 November 2026.** Competitor baru diambil hanya dari halaman
  harga resmi masing-masing: Convia, Weaku, FirstCRM, Core Freelancers,
  Templatku.com, MySkill, Sahut, Spicelab, Mahirusaha, dan Mobichat. Tidak ada
  angka dari artikel pihak ketiga.
- **Angka UMKM memiliki dua seri.** SIDT-UMKM 2025 (30,21 juta, non-pertanian)
  berbeda dari seri lama 65,4 juta yang masih umum dikutip. Jangan campur.
- **Rekomendasi harga** dihitung dari persentil harga kompetitor, bukan survei
  kemauan bayar. Validasi sebelum dipublikasikan.

### Kolom tambahan di luar PRD

- `pasar.sumber_url` untuk melacak URL sumber.

### Memperbarui data

Dashboard tidak memiliki formulir isian, unggah, atau ekspor. Alurnya:

1. Tarik data baru (mis. lewat MCP) dan tulis ulang CSV di `data/`.
2. Pastikan `sumber_url` dan `tanggal_cek` terisi serta statusnya
   `Terverifikasi`.
3. Jalankan `python -m pytest -q` untuk memastikan integritas data.
4. Tekan **Muat ulang data** di sidebar (cache dibersihkan, data dibaca ulang).

Untuk mengembalikan data awal:

```powershell
.\.venv\Scripts\python.exe scripts\seed_data.py
```

Perintah itu menimpa seluruh CSV di `data/` dan gagal bila ada baris belum
terverifikasi.

## Struktur

```
.
├── app.py                        # entrypoint: page config + st.navigation
├── pyproject.toml                # paket, dependensi, konfigurasi ruff/pytest
├── requirements.txt              # -e .
├── data/
│   ├── kompetitor.csv
│   ├── harga.csv
│   └── pasar.csv
├── src/radar_pasar/
│   ├── config.py                 # path data, judul, ambang data kedaluwarsa
│   ├── data/
│   │   ├── schema.py             # kolom wajib, tipe, nilai yang diizinkan
│   │   └── repository.py         # baca CSV (cache), laporan kualitas data
│   ├── domain/                   # murni Python, tanpa Streamlit
│   │   ├── formatting.py
│   │   ├── pricing.py
│   │   ├── features.py
│   │   ├── market.py
│   │   └── gaps.py
│   └── presentation/
│       ├── charts.py             # chart Altair
│       ├── components.py         # komponen UI bersama
│       └── pages/                # fungsi render() per halaman
│           ├── ringkasan.py
│           ├── peta_kompetitor.py
│           ├── analisis_harga.py
│           ├── potensi_pasar.py
│           └── gap_rekomendasi.py
├── scripts/seed_data.py
├── tests/
│   ├── test_pricing.py
│   ├── test_market.py
│   ├── test_schema.py
│   └── test_data.py
├── .streamlit/config.toml        # tema
└── README.md
```

## Implementasi

- Layout `src/` dengan `pyproject.toml`; jalankan `pip install -e .` sekali
  agar paket `radar_pasar` bisa diimpor.
- Navigasi memakai `st.navigation` + `st.Page(callable)`, bukan folder `pages/`
  yang dideteksi otomatis. Tidak ada import relatif yang rawan rusak.
- Lapisan `domain/` tidak menyentuh Streamlit sehingga bisa diuji tanpa
  runtime; hanya `data/repository.py` dan `presentation/` yang memakai API
  Streamlit, termasuk `st.cache_data` (TTL 5 menit + tombol muat ulang).
- Visualisasi memakai Altair, mengikuti panduan skill
  `developing-with-streamlit`: chart mengikuti tema terang/gelap dan tidak
  perlu Plotly untuk chart 2D.
- Tema diatur lewat `.streamlit/config.toml` (tanpa CSS kustom).

## Deploy

Opsi paling sederhana: Streamlit Community Cloud dengan entry point `app.py`.
Pastikan dependensi terpasang (`pip install -e .` atau
`pip install -r requirements.txt`).

Untuk VPS Ubuntu:

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/streamlit run app.py --server.port 8501 --server.headless true
```

Jalankan lewat systemd dan taruh Nginx di depannya. Folder `data/` hanya perlu
dibaca; pembaruan dilakukan di luar layanan.
