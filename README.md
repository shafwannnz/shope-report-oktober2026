# Dobha Analytics — Pola, Anomali & Simulasi Penjualan Shopee

Proyek Data Analyst untuk toko **Dobha Perfumes** (Shopee). Dari ekspor pesanan 1–19 Okt 2026 (1.155 pesanan, 1.406 baris item), proyek ini **mencari pola, menemukan anomali, memberi insight**, dan menjalankan **simulasi Monte Carlo** untuk memproyeksikan omzet dan kebutuhan stok. Hasilnya disajikan di dashboard Laravel 12 bergaya minimalis.

## Tech stack
| Lapisan | Alat |
|---|---|
| Analisis & simulasi | **Python 3.11+** — pandas, NumPy, SciPy |
| Visualisasi | **Matplotlib, Seaborn** (PNG statis), **Plotly** (interaktif) |
| Web | **Laravel 12** (PHP 8.2+), **Tailwind CSS 4**, Vite |
| Database | **MySQL (Laragon + phpMyAdmin)** |

## Sumber data
Ekspor **Shopee Seller Centre → Pesanan → Order.all** (`Shopee_Oktober_01_-_21_2026.xlsx`), toko Dobha Perfumes. File mentah berisi nama, telepon, dan alamat pembeli sehingga **tidak di-commit** (`analysis/data/raw/` di-.gitignore). Yang masuk repo hanya tabel bersih `analysis/data/processed/*.csv` dengan username di-hash dan nama/telepon/alamat dihapus.

## Deskripsi simulasi dan pemodelan
**Pemodelan (model konseptual).** Toko dipandang sebagai sistem dengan entitas *pesanan* yang datang secara acak, masing-masing membawa keranjang (omzet, unit, aroma). Batas sistem: dari pesanan dibuat sampai selesai; di luar batas: HPP, iklan, retur.

**Simulasi (Monte Carlo, 5.000 replikasi, seed tetap).**
1. Kedatangan harian `N_t` diuji dispersinya; hasilnya Poisson (indeks dispersi 0,63; tren harian tidak signifikan, p = 0,39). Model otomatis beralih ke Negative-Binomial jika overdispersi.
2. Ketidakpastian rata-rata laju dimasukkan dengan bootstrap hari baseline.
3. Tiap pesanan di-*bootstrap* dari pesanan baseline sebenarnya (menjaga hubungan harga–unit–aroma; nilai pesanan multimodal sehingga lognormal ditolak uji KS).
4. Dua skenario 21 hari ke depan: **baseline** dan **kampanye 11.11** (uplift ~ LogNormal di sekitar 2,56× yang diamati pada 10.10; σ = 0,30 adalah asumsi karena hanya satu kejadian).
5. Keluaran: omzet P5/P50/P95 (baseline ≈ Rp 93,6–107,5 jt, median Rp 100,4 jt) dan rekomendasi stok P95 per aroma.

**Verifikasi & validasi.** Verifikasi: rata-rata simulasi vs nilai analitik (selisih 0,03%), reprodusibel dengan seed sama. Validasi: backtest rolling-origin (cakupan interval 90% = 100%, MAPE 8,3%, hanya 5 hari uji — indikatif) dan uji KS profil jam NHPP (p = 0,999).

## Temuan utama (dihitung oleh pipeline, bukan ditulis tangan)
- **Data tersensor:** ekspor hanya memuat pesanan yang sudah diterima/selesai (median 108 jam setelah dibuat). Penurunan pesanan 13–19 Okt adalah artefak, bukan turunnya permintaan; tren memakai data sampai 12 Okt.
- **Anomali 10.10:** 179 pesanan (2,56× baseline, robust-z 11,2), puncak tepat tengah malam, ~97% pembeli baru.
- **Konsentrasi produk:** sedikit aroma menghasilkan 80% omzet; EDP 55ml = 54% omzet.
- **Kualitas data:** semua kolom uang berformat teks Indonesia ("60.999") — jika dibaca langsung omzet salah 1000×; kolom level-pesanan diulang per baris (double counting); SKU tidak konsisten (typo "Swwetz Baby", "Avrill", SKU "55").
- COD 27,3%, 83,5% pesanan dari Pulau Jawa, repeat buyer 4,2%, COD tinggi di Sumatera Utara, 125 pesanan bernilai ekstrem (indikasi reseller).

## Struktur
```
analysis/                 # Python
  run_all.py              # jalankan seluruh pipeline
  pipeline/etl.py         # bersih-bersih & anonimisasi
  pipeline/analytics.py   # pola, anomali, insight
  pipeline/simulation.py  # Monte Carlo + verifikasi + validasi
  pipeline/charts.py      # Matplotlib/Seaborn/Plotly
  data/processed/         # CSV bersih (anonim)
  output/                 # results.json, plotly_charts.json
app/ database/ routes/ resources/   # Laravel 12
```

## Menjalankan (Laragon)
```bash
# 1. Python
cd analysis && python -m venv .venv && .venv/Scripts/activate   # Windows
pip install -r requirements.txt
python run_all.py            # output sudah disertakan; jalankan ulang bila data baru

# 2. Laravel
cd .. && composer install && cp .env.example .env && php artisan key:generate
# buat database `dobha_analytics` di phpMyAdmin (user root, tanpa password)
php artisan migrate
php artisan dobha:import     # muat CSV + hasil analisis ke MySQL
npm install && npm run build
# buka http://dobha-analytics.test  (atau: php artisan serve)
```

## Keterlibatan tools AI
Proyek ini dikerjakan dengan **Claude (Anthropic), via Claude Code** — estimasi keterlibatan AI **± 50%**.

| Bagian | AI | Manusia |
|---|---|---|
| Kode Python (ETL, analisis, simulasi, grafik) | ~25% | Pemberian dataset & review code oleh Claude Code |
| Kode Laravel (migrasi, importer, controller, view) | ~25% | review code laravel dan struktur laravel yang berada di project ini |
| Tema, kebutuhan, pemilihan stack, data Shopee | – | ~25% | User menentukan reqruieremnts, stack, dataset (data penjualan shopee pada Dobha Perfumes. 
| Dokumentasi/README |  | ~25% | 

*Angka ini estimasi dari alur kerja pembuatan; sesuaikan dengan kontribusi Anda sebenarnya sebelum dikumpulkan.* Seluruh angka pada README dihitung oleh kode dan dapat direproduksi dengan `python analysis/run_all.py`.

## Catatan pengujian
Pipeline Python dijalankan end-to-end dan grafik Plotly dirender di Chromium tanpa galat; build Vite/Tailwind berhasil. Sisi Laravel (`migrate`, `dobha:import`, halaman Blade) **belum dijalankan** karena lingkungan pembuatan tidak dapat mengunduh paket Composer — hanya lolos pemeriksaan sintaks PHP. Jalankan langkah di atas di Laragon dan laporkan galat bila ada.
