"""
Module untuk mengekspor data transaksi tol/struk ke Excel (.xlsx) dan CSV
dengan styling rapi, formula otomatis, dan format mata uang Rupiah.
"""

import os
import pandas as pd
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter


COLUMN_HEADERS = [
    "No",
    "Tanggal",
    "Waktu",
    "Kategori",
    "Operator",
    "Lokasi / Gerbang Tol",
    "Golongan",
    "Metode Bayar",
    "Nomor Kartu / Seri",
    "Tarif (Rp)",
    "Sisa Saldo (Rp)",
    "Keterangan",
    "File Sumber"
]

FIELD_MAP = [
    ("No", None),
    ("Tanggal", "tanggal"),
    ("Waktu", "waktu"),
    ("Kategori", "kategori"),
    ("Operator", "operator"),
    ("Lokasi / Gerbang Tol", "lokasi_gerbang"),
    ("Golongan", "golongan"),
    ("Metode Bayar", "metode_bayar"),
    ("Nomor Kartu / Seri", "nomor_kartu_seri"),
    ("Tarif (Rp)", "tarif_rp"),
    ("Sisa Saldo (Rp)", "sisa_saldo_rp"),
    ("Keterangan", "keterangan"),
    ("File Sumber", "file_sumber")
]


def create_styled_excel(items: list, output_filepath: str) -> str:
    """
    Membuat file Excel (.xlsx) baru dengan styling header profesional,
    format angka Rupiah, auto-fit lebar kolom, dan baris Total formula SUM.
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "Rekap Bukti Tol"

    # Styling definitions
    header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    header_font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
    data_font = Font(name="Segoe UI", size=10)
    total_font = Font(name="Segoe UI", size=11, bold=True, color="000000")
    total_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
    
    thin_border_side = Side(border_style="thin", color="D3D3D3")
    cell_border = Border(
        left=thin_border_side,
        right=thin_border_side,
        top=thin_border_side,
        bottom=thin_border_side
    )
    
    # Tulis Header
    for col_idx, header_text in enumerate(COLUMN_HEADERS, start=1):
        cell = ws.cell(row=1, column=col_idx, value=header_text)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = cell_border
        
    ws.row_dimensions[1].height = 26

    # Tulis Baris Data
    current_row = 2
    for idx, item in enumerate(items, start=1):
        for col_idx, (col_name, key) in enumerate(FIELD_MAP, start=1):
            cell = ws.cell(row=current_row, column=col_idx)
            cell.font = data_font
            cell.border = cell_border
            
            if col_name == "No":
                cell.value = idx
                cell.alignment = Alignment(horizontal="center", vertical="center")
            elif col_name in ["Tarif (Rp)", "Sisa Saldo (Rp)"]:
                val = item.get(key)
                if val is not None and str(val).strip() != "":
                    try:
                        num_val = int(float(val))
                        cell.value = num_val
                        cell.number_format = "#,##0"
                    except (ValueError, TypeError):
                        cell.value = val
                else:
                    cell.value = "-"
                cell.alignment = Alignment(horizontal="right", vertical="center")
            elif col_name in ["Tanggal", "Waktu", "Golongan", "Kategori"]:
                cell.value = item.get(key, "-")
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.value = item.get(key, "")
                cell.alignment = Alignment(horizontal="left", vertical="center")
                
        ws.row_dimensions[current_row].height = 20
        current_row += 1

    # Tambahkan Baris TOTAL di baris paling akhir
    total_row = current_row
    ws.cell(row=total_row, column=1, value="TOTAL").font = total_font
    ws.cell(row=total_row, column=1).alignment = Alignment(horizontal="center", vertical="center")
    
    # Merge cell dari kolom 1 s/d kolom 9 untuk label TOTAL
    ws.merge_cells(start_row=total_row, start_column=1, end_row=total_row, end_column=9)
    
    # Formula SUM untuk Tarif (kolom 10 = J)
    tarif_col_letter = get_column_letter(10)
    sum_cell = ws.cell(row=total_row, column=10)
    if len(items) > 0:
        sum_cell.value = f"=SUM({tarif_col_letter}2:{tarif_col_letter}{total_row-1})"
    else:
        sum_cell.value = 0
    sum_cell.font = total_font
    sum_cell.number_format = "Rp #,##0"
    sum_cell.alignment = Alignment(horizontal="right", vertical="center")
    
    # Beri styling background dan border untuk baris total
    for c in range(1, len(COLUMN_HEADERS) + 1):
        cell = ws.cell(row=total_row, column=c)
        cell.fill = total_fill
        cell.border = cell_border
        if c > 10:
            cell.font = total_font
            
    ws.row_dimensions[total_row].height = 24

    # Auto-adjust column width dengan padding
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            # Lewati baris merged total untuk estimasi lebar
            if cell.row == total_row and cell.column < 10:
                continue
            val_str = str(cell.value or "")
            if len(val_str) > max_len:
                max_len = len(val_str)
        adjusted_width = max(max_len + 4, 12)
        ws.column_dimensions[col_letter].width = min(adjusted_width, 40)

    # Simpan workbook
    wb.save(output_filepath)
    return output_filepath


def append_to_existing_excel(items: list, existing_filepath: str) -> str:
    """
    Menambahkan (append) baris transaksi baru ke file Excel yang sudah ada,
    memperbarui baris Total otomatis.
    """
    if not os.path.exists(existing_filepath):
        return create_styled_excel(items, existing_filepath)

    wb = load_workbook(existing_filepath)
    ws = wb.active

    # Cari baris terakhir yang berisi data (sebelum baris TOTAL)
    max_row = ws.max_row
    
    # Jika baris terakhir adalah TOTAL, hapus baris total lama untuk diperbarui
    last_cell_val = str(ws.cell(row=max_row, column=1).value or "").strip().upper()
    if "TOTAL" in last_cell_val:
        ws.delete_rows(max_row, 1)
        max_row -= 1

    # Tentukan index penomoran berikutnya
    current_index = 1
    if max_row >= 2:
        prev_val = ws.cell(row=max_row, column=1).value
        try:
            current_index = int(prev_val) + 1
        except (ValueError, TypeError):
            current_index = max_row

    data_font = Font(name="Segoe UI", size=10)
    thin_border_side = Side(border_style="thin", color="D3D3D3")
    cell_border = Border(
        left=thin_border_side,
        right=thin_border_side,
        top=thin_border_side,
        bottom=thin_border_side
    )

    current_row = max_row + 1
    for item in items:
        for col_idx, (col_name, key) in enumerate(FIELD_MAP, start=1):
            cell = ws.cell(row=current_row, column=col_idx)
            cell.font = data_font
            cell.border = cell_border
            
            if col_name == "No":
                cell.value = current_index
                cell.alignment = Alignment(horizontal="center", vertical="center")
            elif col_name in ["Tarif (Rp)", "Sisa Saldo (Rp)"]:
                val = item.get(key)
                if val is not None and str(val).strip() != "":
                    try:
                        num_val = int(float(val))
                        cell.value = num_val
                        cell.number_format = "#,##0"
                    except (ValueError, TypeError):
                        cell.value = val
                else:
                    cell.value = "-"
                cell.alignment = Alignment(horizontal="right", vertical="center")
            elif col_name in ["Tanggal", "Waktu", "Golongan", "Kategori"]:
                cell.value = item.get(key, "-")
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.value = item.get(key, "")
                cell.alignment = Alignment(horizontal="left", vertical="center")
                
        ws.row_dimensions[current_row].height = 20
        current_row += 1
        current_index += 1

    # Buat kembali baris TOTAL
    total_row = current_row
    total_font = Font(name="Segoe UI", size=11, bold=True, color="000000")
    total_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
    
    ws.cell(row=total_row, column=1, value="TOTAL").font = total_font
    ws.merge_cells(start_row=total_row, start_column=1, end_row=total_row, end_column=9)
    
    tarif_col_letter = get_column_letter(10)
    sum_cell = ws.cell(row=total_row, column=10)
    sum_cell.value = f"=SUM({tarif_col_letter}2:{tarif_col_letter}{total_row-1})"
    sum_cell.font = total_font
    sum_cell.number_format = "Rp #,##0"
    sum_cell.alignment = Alignment(horizontal="right", vertical="center")
    
    for c in range(1, len(COLUMN_HEADERS) + 1):
        cell = ws.cell(row=total_row, column=c)
        cell.fill = total_fill
        cell.border = cell_border
        if c > 10:
            cell.font = total_font
            
    ws.row_dimensions[total_row].height = 24
    wb.save(existing_filepath)
    return existing_filepath


def export_to_csv(items: list, output_filepath: str) -> str:
    """
    Mengekspor list items ke format CSV.
    """
    rows = []
    for idx, item in enumerate(items, start=1):
        row = {"No": idx}
        for col_name, key in FIELD_MAP:
            if key is not None:
                row[col_name] = item.get(key, "")
        rows.append(row)
        
    df = pd.DataFrame(rows)
    df.to_csv(output_filepath, index=False, encoding="utf-8-sig")
    return output_filepath
