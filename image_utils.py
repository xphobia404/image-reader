"""
Module untuk Image Processing dan Preprocessing Bukti Transaksi Tol / Struk.
Menggunakan OpenCV dan Pillow untuk rotasi, peningkatan kontras, dan segmentasi struk.
"""

import cv2
import numpy as np
from PIL import Image, ImageOps
import io
import os


def load_image(image_input):
    """
    Memuat gambar dari path file, bytes, atau PIL Image menjadi format OpenCV (BGR) dan PIL Image.
    """
    if isinstance(image_input, str):
        if not os.path.exists(image_input):
            raise FileNotFoundError(f"File tidak ditemukan: {image_input}")
        pil_img = Image.open(image_input)
        # Menangani orientasi EXIF (misal foto dari HP yang terbalik/miring)
        pil_img = ImageOps.exif_transpose(pil_img)
        cv_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        return cv_img, pil_img
    elif isinstance(image_input, bytes):
        pil_img = Image.open(io.BytesIO(image_input))
        pil_img = ImageOps.exif_transpose(pil_img)
        cv_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        return cv_img, pil_img
    elif isinstance(image_input, Image.Image):
        pil_img = ImageOps.exif_transpose(image_input)
        cv_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        return cv_img, pil_img
    else:
        raise ValueError("Format input gambar tidak didukung")


def enhance_contrast(cv_img):
    """
    Meningkatkan kontras gambar struk menggunakan CLAHE (Contrast Limited Adaptive Histogram Equalization).
    Sangat berguna untuk struk termal yang tintanya tipis atau pudar.
    """
    # Ubah ke LAB color space
    lab = cv2.cvtColor(cv_img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    
    # Terapkan CLAHE ke channel L (Luminance)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    cl = clahe.apply(l)
    
    # Gabungkan kembali
    limg = cv2.merge((cl, a, b))
    enhanced_bgr = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
    return enhanced_bgr


def preprocess_for_ocr(cv_img):
    """
    Preprocessing lengkap untuk memudahkan OCR lokal:
    Grayscale -> Noise Removal -> Adaptive Thresholding
    """
    gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
    
    # Noise reduction dengan Gaussian blur halus
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    
    # Adaptive thresholding untuk memisahkan teks dari latar belakang struk
    thresh = cv2.adaptiveThreshold(
        blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )
    return thresh


def detect_and_crop_receipts(cv_img, min_area_ratio=0.03):
    """
    Mendeteksi kotak struk jika dalam 1 lembar terdapat beberapa struk yang ditempel.
    Mengembalikan list berisi crop image (OpenCV BGR) dan bounding box (x, y, w, h).
    Jika tidak ada struk terpisah yang signifikan, mengembalikan seluruh gambar asli.
    """
    h_img, w_img = cv_img.shape[:2]
    total_area = h_img * w_img
    min_area = total_area * min_area_ratio

    gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Edge detection
    edged = cv2.Canny(blurred, 50, 200)
    
    # Dilasi untuk menyambungkan kontur struk kertas
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
    dilated = cv2.dilate(edged, kernel, iterations=2)
    
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    receipt_boxes = []
    for c in contours:
        area = cv2.contourArea(c)
        if area > min_area:
            x, y, w, h = cv2.boundingRect(c)
            # Filter rasio aspek yang masuk akal untuk struk
            aspect_ratio = float(w) / h
            if 0.15 < aspect_ratio < 4.0:
                receipt_boxes.append((x, y, w, h))
                
    # Urutkan berdasarkan posisi Y (dari atas ke bawah) lalu X
    receipt_boxes.sort(key=lambda b: (b[1] // 100, b[0]))
    
    cropped_images = []
    if not receipt_boxes:
        return [cv_img]
        
    for x, y, w, h in receipt_boxes:
        # Tambahkan sedikit margin/padding jika memungkinkan
        pad_x = int(w * 0.02)
        pad_y = int(h * 0.02)
        x1 = max(0, x - pad_x)
        y1 = max(0, y - pad_y)
        x2 = min(w_img, x + w + pad_x)
        y2 = min(h_img, y + h + pad_y)
        
        crop = cv_img[y1:y2, x1:x2]
        cropped_images.append(crop)
        
    return cropped_images
