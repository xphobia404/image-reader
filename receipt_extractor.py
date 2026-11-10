"""
Module untuk ekstraksi data bukti tol dan struk transaksi menggunakan AI Vision (Google Gemini)
serta fallback OCR lokal dengan output terstruktur.
"""

import os
import json
import re
from typing import List, Optional
from pydantic import BaseModel, Field
from PIL import Image
import io

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False


class ReceiptItem(BaseModel):
    tanggal: str = Field(description="Tanggal transaksi dalam format DD/MM/YYYY (contoh: 07/06/2026)")
    waktu: str = Field(description="Waktu transaksi dalam format HH:MM:SS atau HH:MM (contoh: 11:35:57)")
    kategori: str = Field(description="Kategori pengeluaran: 'TOL', 'PARKIR', 'BBM', atau 'LAINNYA'")
    operator: str = Field(description="Nama penyedia jasa / operator, misal: Jasamarga, Mandiri e-Toll, Pertamina, Angkasa Pura, dsb")
    lokasi_gerbang: str = Field(description="Nama gerbang tol, lokasi parkir, atau nama SPBU (misal: 'Cengkareng', 'Kamal 3 Integrasi', 'T3 Internasional Soetta', 'SPBU Margasatwa')")
    golongan: Optional[str] = Field(default="-", description="Golongan kendaraan jika ada, misal 'GOL-1', 'Mobil'")
    metode_bayar: Optional[str] = Field(default="e-Toll", description="Metode bayar, misal 'e-Toll Mandiri', 'Flazz BCA', 'Brizzi', 'Mastercard'")
    nomor_kartu_seri: Optional[str] = Field(default="-", description="Nomor kartu e-money atau nomor seri transaksi")
    tarif_rp: int = Field(description="Nominal tarif atau total biaya yang dibayar dalam Rupiah (angka murni tanpa titik/koma/Rp)")
    sisa_saldo_rp: Optional[int] = Field(default=None, description="Sisa saldo kartu setelah transaksi jika tertera di struk, atau null")
    keterangan: Optional[str] = Field(default="", description="Catatan detail tambahan, misal nomor pompa / liter bensin / durasi parkir / no mutasi")


class ExtractionResult(BaseModel):
    items: List[ReceiptItem] = Field(description="Daftar seluruh transaksi yang ditemukan dalam gambar struk")


EXTRACTION_PROMPT = """
Anda adalah asisten ahli pembaca bukti pembayaran, struk tol, bukti parkir, dan kwitansi perjalanan dinas/operasional di Indonesia.
Tugas Anda adalah membaca gambar struk yang diberikan dan mengekstrak SEMUA transaksi secara akurat ke dalam format terstruktur.

PANDUAN PENTING:
1. Jika dalam 1 foto terdapat LEBIH DARI SATU STRUK (misalnya ada 2 atau 4 struk ditempel di satu kertas A4), Anda WAJIB mengekstrak SETIAP struk menjadi item terpisah di dalam list 'items'.
2. Jika struk berupa STRUK MUTASI / DETAIL TRANSAKSI MANDIRI E-TOLL (daftar deretan transaksi dengan kolom TANGGAL/JAM, TID, AMOUNT, SALDO), ekstrak SETIAP BARIS transaksi SALE menjadi satu item tersendiri!
   - Contoh: "SALE 220526 08:24 30060100 17.000 350.000" -> Tanggal: 22/05/2026, Waktu: 08:24:00, Operator: Mandiri e-Toll, Lokasi/TID: 30060100, Tarif: 17000, Saldo: 350000.
3. Kategori:
   - 'TOL' untuk gerbang tol (Jasa Marga, Citra Marga, mutasi e-toll, dll).
   - 'PARKIR' untuk tiket/struk parkir (Bandara, gedung, stasiun).
   - 'BBM' untuk pengisian bensin / SPBU Pertamina / Shell / BP.
   - 'LAINNYA' jika di luar itu.
4. Format Angka 'tarif_rp' dan 'sisa_saldo_rp':
   - Wajib berupa bilangan bulat integer murni (misal Rp 8.500 menjadi 8500, Rp 25.500 menjadi 25500, Rp 300.000 menjadi 300000).
   - Jangan gunakan koma atau titik pada angka rupiah.
5. Format Tanggal:
   - Gunakan format DD/MM/YYYY (contoh: jika tertera 07/06/2026 atau 07 Jun 2026 maka tulis '07/06/2026').
   - Jika tahun 2 digit (misal 220526 = 22 Mei 2026), tulis '22/05/2026'.
6. Pastikan tidak ada transaksi yang terlewatkan.
"""


def extract_receipt_data_with_gemini(pil_image: Image.Image, api_key: str, filename: str = "") -> List[dict]:
    """
    Mengekstrak data transaksi dari gambar menggunakan Gemini 2.5 Flash via Google GenAI SDK.
    """
    if not GENAI_AVAILABLE:
        raise ImportError("Package 'google-genai' belum terinstall.")
        
    if not api_key:
        raise ValueError("Google Gemini API Key belum diset. Silakan masukkan API Key Anda.")

    client = genai.Client(api_key=api_key)
    
    # Pastikan format RGB
    if pil_image.mode != "RGB":
        pil_image = pil_image.convert("RGB")
        
    models_to_try = ["gemini-3.5-flash", "gemini-3.8-flash", "gemini-3.1-flash-lite", "gemini-2.5-flash"]
    last_err = None

    for model_name in models_to_try:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=[pil_image, EXTRACTION_PROMPT],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ExtractionResult,
                    temperature=0.1,
                ),
            )
            
            parsed_result = json.loads(response.text)
            items = parsed_result.get("items", [])
            
            # Tambahkan metadata nama file sumber untuk kemudahan tracking
            result_list = []
            for idx, item in enumerate(items, 1):
                item["file_sumber"] = filename
                result_list.append(item)
                
            return result_list
        except Exception as e:
            last_err = e
            continue

    raise RuntimeError(f"Gagal memproses gambar dengan Gemini API: {str(last_err)}")


def extract_receipt_data_mock(filename: str = "") -> List[dict]:
    """
    Fungsi demo/fallback jika user ingin mencoba aplikasi sebelum memasukkan API key.
    Mengembalikan data contoh berdasarkan kasus umum struk tol.
    """
    return [
        {
            "tanggal": "07/06/2026",
            "waktu": "11:35:57",
            "kategori": "TOL",
            "operator": "Jasamarga",
            "lokasi_gerbang": "CENGKARENG",
            "golongan": "GOL-1",
            "metode_bayar": "e-Toll Mandiri",
            "nomor_kartu_seri": "6032982128272307",
            "tarif_rp": 8500,
            "sisa_saldo_rp": 137500,
            "keterangan": "No seri: 611107 180665/240751",
            "file_sumber": filename or "sample.jpg"
        },
        {
            "tanggal": "07/06/2026",
            "waktu": "13:18:19",
            "kategori": "TOL",
            "operator": "Jasamarga",
            "lokasi_gerbang": "KAMAL 3 INTEGRASI",
            "golongan": "GOL-1",
            "metode_bayar": "e-Toll Mandiri",
            "nomor_kartu_seri": "6032982128272307",
            "tarif_rp": 25500,
            "sisa_saldo_rp": 89000,
            "keterangan": "No seri: 809059 180674/151480",
            "file_sumber": filename or "sample.jpg"
        }
    ]
