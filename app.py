"""
Aplikasi Web Interaktif Image Processing & AI Receipt Reader untuk Penginputan Bukti Tol ke Excel/CSV.
Dibuat dengan Streamlit, OpenCV, Google Gemini Vision, dan OpenPyXL.
"""

import os
import io
import pandas as pd
import streamlit as st
from PIL import Image
from dotenv import load_dotenv

from image_utils import load_image, enhance_contrast, detect_and_crop_receipts
from receipt_extractor import extract_receipt_data_with_gemini, extract_receipt_data_mock
from excel_exporter import create_styled_excel, export_to_csv, append_to_existing_excel

# Load file .env jika ada
load_dotenv()

# Konfigurasi Halaman Streamlit
st.set_page_config(
    page_title="Toll Receipt to Excel Converter",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS untuk tampilan modern
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #4B5563;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 1rem;
        text-align: center;
    }
    .stButton>button {
        border-radius: 6px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)


def init_session_state():
    if "extracted_data" not in st.session_state:
        st.session_state.extracted_data = []
    if "processed_files" not in st.session_state:
        st.session_state.processed_files = []


init_session_state()

# ==========================================
# SIDEBAR: PENGATURAN & API KEY
# ==========================================
with st.sidebar:
    st.image("https://img.icons8.com/color/96/tollbooth.png", width=64)
    st.title("Pengaturan")
    
    env_api_key = os.getenv("GEMINI_API_KEY", "")
    api_key_input = st.text_input(
        "Google Gemini API Key",
        value=env_api_key,
        type="password",
        help="Dapatkan API Key gratis di https://aistudio.google.com/ untuk AI Vision pembaca struk."
    )
    
    if not api_key_input:
        st.warning("⚠️ API Key belum diisi. Anda dapat menguji dengan mode **Demo / Simulasi**.")
        with st.expander("ℹ️ Cara dapatkan API Key Gratis"):
            st.markdown("""
            1. Buka [Google AI Studio](https://aistudio.google.com/).
            2. Login dengan akun Google.
            3. Klik tombol **Get API key** lalu **Create API key**.
            4. Salin kuncinya dan tempel di kolom atas.
            """)
    else:
        st.success("API Key siap digunakan! ✅")

    st.divider()
    st.subheader("Opsi Pemrosesan")
    use_enhancement = st.checkbox("Tingkatkan Kontras Gambar (CLAHE)", value=True, 
                                  help="Membantu memperjelas tulisan pada struk termal yang pudar")
    
    st.divider()
    st.subheader("File Master Excel")
    master_excel_name = st.text_input("Nama File Excel Master", value="rekap_transaksi_tol.xlsx")
    append_mode = st.checkbox("Tambah (Append) ke Excel Master yang ada", value=True,
                              help="Jika dicentang, data baru akan ditambahkan di baris akhir tanpa menghapus data sebelumnya.")
    
    st.caption("Aplikasi Image Processing Tol v1.0 • Python 3.13")

# ==========================================
# HEADER HALAMAN UTAMA
# ==========================================
st.markdown('<div class="main-header">🚗 Auto Toll Receipt to Excel</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Foto bukti tol, struk parkir, bensin, atau mutasi kartu e-Toll, dan sistem akan otomatis mengekstrak rinciannya langsung ke Excel / CSV.</div>', unsafe_allow_html=True)

# ==========================================
# INPUT GAMBAR: TABS
# ==========================================
tab_upload, tab_camera, tab_samples = st.tabs(["📁 Upload Foto Struk", "📷 Ambil Foto (Kamera)", "📂 Gunakan Sampel Bawaan"])

selected_images = []

with tab_upload:
    uploaded_files = st.file_uploader(
        "Pilih atau Tarik File Foto Struk (Bisa pilih banyak sekaligus)",
        type=["jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True
    )
    if uploaded_files:
        for uf in uploaded_files:
            selected_images.append({
                "name": uf.name,
                "bytes": uf.getvalue(),
                "pil": Image.open(io.BytesIO(uf.getvalue()))
            })

with tab_camera:
    camera_pic = st.camera_input("Ambil foto struk tol langsung dari kamera")
    if camera_pic:
        selected_images.append({
            "name": f"kamera_{camera_pic.name}",
            "bytes": camera_pic.getvalue(),
            "pil": Image.open(io.BytesIO(camera_pic.getvalue()))
        })

with tab_samples:
    st.write("Gunakan contoh struk asli dari folder `/contoh-invoice`:")
    sample_dir = "contoh-invoice"
    if os.path.exists(sample_dir):
        sample_files = [f for f in os.listdir(sample_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        if sample_files:
            sample_choice = st.multiselect(
                "Pilih contoh gambar:",
                options=sample_files,
                default=sample_files[:1]
            )
            for sf in sample_choice:
                full_path = os.path.join(sample_dir, sf)
                with open(full_path, "rb") as f:
                    b = f.read()
                    selected_images.append({
                        "name": sf,
                        "bytes": b,
                        "pil": Image.open(io.BytesIO(b))
                    })
    else:
        st.info("Folder contoh-invoice tidak ditemukan.")

# Pratinjau gambar yang dipilih
if selected_images:
    st.markdown(f"**{len(selected_images)} gambar siap diproses:**")
    cols = st.columns(min(len(selected_images), 4))
    for idx, img_info in enumerate(selected_images):
        with cols[idx % 4]:
            st.image(img_info["pil"], caption=img_info["name"][:25] + "...", use_container_width=True)

# ==========================================
# TOMBOL PROSES EKSTRAKSI
# ==========================================
st.write("")
col_btn1, col_btn2 = st.columns([2, 5])
with col_btn1:
    process_btn = st.button("⚡ Mulai Proses Gambar ke Excel", type="primary", use_container_width=True)

if process_btn:
    if not selected_images:
        st.warning("Silakan pilih atau upload foto struk terlebih dahulu.")
    else:
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        extracted_results = []
        total_imgs = len(selected_images)
        
        for idx, img_info in enumerate(selected_images):
            status_text.text(f"Memproses gambar {idx+1}/{total_imgs}: {img_info['name']}...")
            
            # Image Preprocessing (Contrast enhancement jika diaktifkan)
            pil_to_process = img_info["pil"]
            if use_enhancement:
                try:
                    cv_img, _ = load_image(img_info["bytes"])
                    enhanced_cv = enhance_contrast(cv_img)
                    import cv2
                    pil_to_process = Image.fromarray(cv2.cvtColor(enhanced_cv, cv2.COLOR_BGR2RGB))
                except Exception as e:
                    pass
            
            # Ekstraksi dengan AI Vision atau Mock
            try:
                if api_key_input:
                    items = extract_receipt_data_with_gemini(pil_to_process, api_key_input, filename=img_info["name"])
                else:
                    items = extract_receipt_data_mock(filename=img_info["name"])
                
                extracted_results.extend(items)
            except Exception as e:
                st.error(f"Gagal memproses {img_info['name']}: {str(e)}")
                
            progress_bar.progress((idx + 1) / total_imgs)
            
        status_text.empty()
        progress_bar.empty()
        
        if extracted_results:
            st.session_state.extracted_data = extracted_results
            st.success(f"Berhasil mengekstrak {len(extracted_results)} item transaksi dari {total_imgs} gambar! 🎉")

# ==========================================
# TAMPILAN DATA & DATA EDITOR (BISA DIEDIT)
# ==========================================
if st.session_state.extracted_data:
    st.divider()
    st.subheader("📋 Hasil Ekstraksi Data Transaksi")
    st.caption("Tip: Anda dapat langsung mengedit sel tabel di bawah ini jika ingin mengoreksi nama gerbang, nominal, dsb.")

    # Convert to DataFrame
    df = pd.DataFrame(st.session_state.extracted_data)
    
    # Rename kolom untuk tampilan rapi
    column_order = [
        "tanggal", "waktu", "kategori", "operator", "lokasi_gerbang",
        "golongan", "metode_bayar", "nomor_kartu_seri", "tarif_rp",
        "sisa_saldo_rp", "keterangan", "file_sumber"
    ]
    # Filter kolom yang ada
    available_cols = [c for c in column_order if c in df.columns]
    df = df[available_cols]

    # Metrics Summary
    total_nominal = df["tarif_rp"].sum() if "tarif_rp" in df.columns else 0
    total_tol = df[df["kategori"].str.upper() == "TOL"]["tarif_rp"].sum() if "kategori" in df.columns else 0
    total_parkir = df[df["kategori"].str.upper() == "PARKIR"]["tarif_rp"].sum() if "kategori" in df.columns else 0
    total_bbm = df[df["kategori"].str.upper() == "BBM"]["tarif_rp"].sum() if "kategori" in df.columns else 0

    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        st.metric("Total Transaksi", f"{len(df)} item")
    with m2:
        st.metric("Total Tol", f"Rp {total_tol:,.0f}".replace(",", "."))
    with m3:
        st.metric("Total Parkir", f"Rp {total_parkir:,.0f}".replace(",", "."))
    with m4:
        st.metric("Total BBM", f"Rp {total_bbm:,.0f}".replace(",", "."))
    with m5:
        st.metric("Total Keseluruhan", f"Rp {total_nominal:,.0f}".replace(",", "."), delta=None)

    # Interactive Table Editor
    edited_df = st.data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "tanggal": st.column_config.TextColumn("Tanggal (DD/MM/YYYY)"),
            "waktu": st.column_config.TextColumn("Waktu"),
            "kategori": st.column_config.SelectboxColumn("Kategori", options=["TOL", "PARKIR", "BBM", "LAINNYA"]),
            "operator": st.column_config.TextColumn("Operator / BUJT"),
            "lokasi_gerbang": st.column_config.TextColumn("Gerbang / Lokasi"),
            "golongan": st.column_config.TextColumn("Golongan"),
            "metode_bayar": st.column_config.TextColumn("Metode Bayar"),
            "nomor_kartu_seri": st.column_config.TextColumn("No Kartu / Seri"),
            "tarif_rp": st.column_config.NumberColumn("Tarif (Rp)", format="Rp %d"),
            "sisa_saldo_rp": st.column_config.NumberColumn("Sisa Saldo (Rp)", format="Rp %d"),
            "keterangan": st.column_config.TextColumn("Keterangan"),
            "file_sumber": st.column_config.TextColumn("File Sumber")
        }
    )

    # Simpan kembali editan pengguna ke session_state
    items_to_save = edited_df.to_dict(orient="records")

    st.write("")
    col_dl1, col_dl2, col_dl3 = st.columns(3)

    # Generate Excel in-memory untuk Download
    temp_excel_path = "temp_download.xlsx"
    create_styled_excel(items_to_save, temp_excel_path)
    with open(temp_excel_path, "rb") as f:
        excel_bytes = f.read()

    # Generate CSV in-memory
    csv_bytes = edited_df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")

    with col_dl1:
        st.download_button(
            label="📥 Download File Excel (.xlsx)",
            data=excel_bytes,
            file_name="rekap_bukti_tol.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    with col_dl2:
        st.download_button(
            label="📥 Download CSV",
            data=csv_bytes,
            file_name="rekap_bukti_tol.csv",
            mime="text/csv",
            use_container_width=True
        )

    with col_dl3:
        if st.button(f"💾 Simpan ke '{master_excel_name}'", use_container_width=True):
            if append_mode and os.path.exists(master_excel_name):
                append_to_existing_excel(items_to_save, master_excel_name)
                st.success(f"Data berhasil ditambahkan ke '{master_excel_name}'! ✅")
            else:
                create_styled_excel(items_to_save, master_excel_name)
                st.success(f"File master baru '{master_excel_name}' berhasil dibuat! ✅")
