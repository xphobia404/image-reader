"""
Command Line Interface (CLI) untuk pemrosesan gambar struk tol/bukti transaksi ke Excel/CSV.
Contoh penggunaan:
    python cli.py --input contoh-invoice --output rekap_tol.xlsx
    python cli.py --input "contoh-invoice/WhatsApp Image 2026-11-10 at 11.09.54 AM.jpeg" --format csv
"""

import os
import sys
import argparse
from glob import glob
from dotenv import load_dotenv

from image_utils import load_image, enhance_contrast
from receipt_extractor import extract_receipt_data_with_gemini, extract_receipt_data_mock
from excel_exporter import create_styled_excel, export_to_csv, append_to_existing_excel


def main():
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="Ekstraksi Bukti Tol / Invoice ke Excel/CSV")
    parser.add_argument("--input", "-i", required=True, help="Path ke file gambar atau folder berisi gambar struk")
    parser.add_argument("--output", "-o", default="rekap_transaksi_tol.xlsx", help="Path file output Excel/CSV")
    parser.add_argument("--format", "-f", choices=["excel", "csv"], default="excel", help="Format output (excel atau csv)")
    parser.add_argument("--append", "-a", action="store_true", help="Tambahkan (append) ke file Excel yang sudah ada")
    parser.add_argument("--demo", action="store_true", help="Jalankan mode demo tanpa API key")
    parser.add_argument("--api-key", help="Google Gemini API Key (bisa juga via environment variable GEMINI_API_KEY)")
    
    args = parser.parse_args()

    api_key = args.api_key or os.getenv("GEMINI_API_KEY")
    
    # Kumpulkan daftar file gambar yang akan diproses (hindari duplikasi di Windows)
    image_files = []
    if os.path.isdir(args.input):
        valid_exts = ("*.jpg", "*.jpeg", "*.png", "*.webp", "*.bmp")
        found = set()
        for ext in valid_exts:
            for p in glob(os.path.join(args.input, ext)):
                found.add(os.path.abspath(p))
            for p in glob(os.path.join(args.input, ext.upper())):
                found.add(os.path.abspath(p))
        image_files = sorted(list(found))
    elif os.path.isfile(args.input):
        image_files.append(os.path.abspath(args.input))
    else:
        print(f"[ERROR] Path input '{args.input}' tidak ditemukan.")
        sys.exit(1)

    if not image_files:
        print(f"[WARN] Tidak ada file gambar yang ditemukan di '{args.input}'.")
        sys.exit(0)

    print(f"=== Toll Receipt Image Processor ===")
    print(f"Ditemukan {len(image_files)} file gambar untuk diproses.")
    
    if not api_key:
        if args.demo:
            print("[INFO] Menjalankan dalam mode DEMO simulasi.")
        else:
            print("[PERINGATAN] GEMINI_API_KEY tidak ditemukan.")
            print("Untuk hasil nyata dari foto struk Anda, silakan sediakan API Key Gemini.")
            print("Anda bisa mendapatkan API key gratis di: https://aistudio.google.com/")
            print("Menjalankan dengan data simulasi (--demo)...")

    all_extracted_items = []

    for idx, img_path in enumerate(image_files, start=1):
        filename = os.path.basename(img_path)
        print(f"\n[{idx}/{len(image_files)}] Memproses: {filename}...")

        try:
            _, pil_img = load_image(img_path)
            
            if api_key:
                items = extract_receipt_data_with_gemini(pil_img, api_key, filename=filename)
            else:
                items = extract_receipt_data_mock(filename=filename)

            print(f"  -> Berhasil mendeteksi {len(items)} transaksi:")
            for item in items:
                print(f"     * [{item.get('kategori', 'TOL')}] {item.get('tanggal')} {item.get('waktu')} | "
                      f"{item.get('lokasi_gerbang')} | Rp {item.get('tarif_rp', 0):,}")

            all_extracted_items.extend(items)

        except Exception as e:
            print(f"  [ERROR] Gagal memproses {filename}: {str(e)}")

    if not all_extracted_items:
        print("\nTidak ada transaksi yang berhasil diekstrak.")
        sys.exit(0)

    # Ekspor ke Excel / CSV
    out_path = args.output
    if args.format == "csv" or out_path.endswith(".csv"):
        if not out_path.endswith(".csv"):
            out_path += ".csv"
        export_to_csv(all_extracted_items, out_path)
        print(f"\n[SUKSES] Seluruh data berhasil disimpan ke CSV: {os.path.abspath(out_path)}")
    else:
        if not out_path.endswith(".xlsx"):
            out_path += ".xlsx"
        if args.append and os.path.exists(out_path):
            append_to_existing_excel(all_extracted_items, out_path)
            print(f"\n[SUKSES] Data baru berhasil ditambahkan (append) ke Excel: {os.path.abspath(out_path)}")
        else:
            create_styled_excel(all_extracted_items, out_path)
            print(f"\n[SUKSES] Berkas Excel baru berhasil dibuat: {os.path.abspath(out_path)}")

    print(f"Total {len(all_extracted_items)} transaksi berhasil direkap.")


if __name__ == "__main__":
    main()
