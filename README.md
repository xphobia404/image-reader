# 🚗 Aplikasi Pemindai Bukti Tol & Struk Otomatis ke Excel (Image Processing + AI Vision)

Aplikasi Python cerdas untuk mengekstrak data dari foto bukti pembayaran tol, tiket parkir, struk SPBU/BBM, serta struk mutasi transaksi e-Toll ke dalam format **Excel (`.xlsx`)** dan **CSV** secara otomatis.

---

## 🌟 Fitur Utama

1. **Multi-Receipt in One Photo (Satu Foto Banyak Struk)**:
   - Mampu mengenali lembaran kertas yang ditempeli beberapa struk sekaligus (seperti pada contoh struk Jasa Marga Cengkareng, Kamal 3 Integrasi, dan SPBU dalam 1 lembar foto).
   - Setiap struk otomatis diekstrak menjadi baris transaksi terpisah di Excel.
2. **Ekstraksi Struk Mutasi / Riwayat e-Toll**:
   - Mampu membaca struk rekap mutasi kartu (misalnya mutasi e-Money Mandiri dengan deretan baris transaksi tanggal, waktu, TID, nominal, dan sisa saldo) menjadi deretan baris Excel yang rapi.
3. **Kategorisasi Otomatis**:
   - Mengelompokkan transaksi ke dalam kategori: `TOL`, `PARKIR`, `BBM`, atau `LAINNYA`.
4. **Image Processing (OpenCV)**:
   - Koreksi orientasi EXIF (foto tegak/miring dari HP).
   - Contrast Enhancement dengan CLAHE untuk memperjelas cetakan struk termal yang pudar.
5. **Format Excel Rapi & Profesional**:
   - Kolom Tarif dan Saldo diformat sebagai Number Rupiah (`#,##0`).
   - Lebar kolom disesuaikan otomatis (auto-fit width) agar tidak ada teks terpotong (`###`).
   - Baris **TOTAL** otomatis menggunakan formula `=SUM(...)`.
   - Mendukung mode **Append** (menambahkan data transaksi baru ke berkas Excel master tanpa menimpa data lama).
6. **Antarmuka Web Interaktif (Streamlit)**:
   - Upload file (drag & drop, multi-file).
   - Ambil foto langsung melalui Kamera Webcam / HP.
   - **Editable Data Table**: Hasil ekstraksi bisa langsung dikoreksi atau diedit di browser sebelum diunduh ke Excel.
   - Ringkasan total biaya (Total Tol, Total Parkir, Total BBM, Total Keseluruhan).

---

## 📋 Struktur Kolom Excel yang Dihasilkan

| No | Tanggal | Waktu | Kategori | Operator | Lokasi / Gerbang Tol | Golongan | Metode Bayar | Nomor Kartu / Seri | Tarif (Rp) | Sisa Saldo (Rp) | Keterangan | File Sumber |
|:--:|:-------:|:-----:|:--------:|:--------:|:--------------------:|:--------:|:------------:|:------------------:|:----------:|:---------------:|:----------:|:-----------:|
| 1 | 07/06/2026 | 11:35:57 | TOL | Jasamarga | CENGKARENG | GOL-1 | e-Toll Mandiri | 6032982128272307 | 8.500 | 137.500 | No seri: 611107 | invoice_1.jpg |
| 2 | 07/06/2026 | 13:18:19 | TOL | Jasamarga | KAMAL 3 INTEGRASI | GOL-1 | e-Toll Mandiri | 6032982128272307 | 25.500 | 89.000 | No seri: 809059 | invoice_1.jpg |
| ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... |
| **TOTAL** | | | | | | | | | **=SUM(J2:J...)** | | | |

---

## 🚀 Cara Menjalankan

### 1. Persiapan Lingkungan & Dependensi
Paket dependensi sudah terinstal di sistem Anda. Jika ingin memastikan kembali:
```bash
pip install -r requirements.txt
```

### 2. Mengatur API Key Gemini (AI Vision)
Aplikasi menggunakan AI Vision Gemini yang sangat akurat membaca struk Indonesia. API Key bisa diperoleh secara **gratis**:
1. Kunjungi [Google AI Studio](https://aistudio.google.com/).
2. Login dengan akun Google Anda, klik **Get API key** lalu **Create API key**.
3. Buat file `.env` di folder ini (bisa salin dari `.env.example`):
   ```env
   GEMINI_API_KEY=AIzaSy...kunci_anda...
   ```
   *(Atau Anda juga bisa langsung memasukkan API key pada kolom di sidebar web app).*

---

### 3. Menjalankan Aplikasi Web (Streamlit UI)

Cukup klik ganda (double-click) file:
👉 **`jalankan_aplikasi.bat`**

Atau jalankan melalui terminal:
```bash
python -m streamlit run app.py
```
Aplikasi akan otomatis terbuka di browser Anda di alamat `http://localhost:8501`.

---

### 4. Menjalankan Melalui Command Line (CLI)

Anda juga dapat memproses satu foto atau satu folder secara langsung dari terminal:

**Memproses seluruh gambar dalam folder `contoh-invoice` ke file Excel:**
```bash
python cli.py --input contoh-invoice --output rekap_tol.xlsx
```

**Menambahkan (append) data foto baru ke file Excel yang sudah ada:**
```bash
python cli.py --input "contoh-invoice/WhatsApp Image 2026-11-10 at 11.09.54 AM.jpeg" --output rekap_tol.xlsx --append
```

**Ekspor ke format CSV:**
```bash
python cli.py --input contoh-invoice --output rekap_tol.csv --format csv
```

**Uji coba cepat dengan data simulasi (Demo Mode tanpa API Key):**
```bash
python cli.py --input contoh-invoice --output demo_rekap.xlsx --demo
```

---

## 📁 Struktur File Project

```text
image-reader/
├── app.py                    # Aplikasi Web Streamlit (GUI)
├── cli.py                    # Tool Command-Line Interface
├── image_utils.py            # Image processing (OpenCV, CLAHE, Kontras, Rotasi)
├── receipt_extractor.py      # Engine AI Vision ekstraksi data struk ke JSON
├── excel_exporter.py         # Formatter Excel (.xlsx) dengan styling & formula SUM
├── jalankan_aplikasi.bat     # Shortcut sekali klik untuk pengguna Windows
├── requirements.txt          # Daftar pustaka Python
├── .env.example              # Template konfigurasi environment variable
├── contoh-invoice/           # Folder berisi sampel foto struk
└── README.md                 # Dokumentasi panduan lengkap
```
