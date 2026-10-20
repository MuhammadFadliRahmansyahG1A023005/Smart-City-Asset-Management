"""
Main Execution Script
=====================
Menjalankan pipeline analisis spasial pemetaan buffer jangkauan fasilitas publik
Smart City Asset Management (Default Demo & Comprehensive Dataset).
"""

import sys
import os

# Tambahkan root path ke sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.spatial_analysis import create_urban_assets_pipeline

if __name__ == "__main__":
    print("\n[INFO] Menjalankan Pipeline Standar dengan Data Contoh (3 Titik Aset)...")
    res_default = create_urban_assets_pipeline(
        data_source=None,
        buffer_meters=500.0,
        output_path="output_urban_assets_map.html"
    )
    
    # Jalankan juga untuk dataset komprehensif 10 titik fasilitas publik Kota Bengkulu
    csv_path = os.path.join("data", "urban_assets.csv")
    if os.path.exists(csv_path):
        print("\n[INFO] Menjalankan Pipeline Lanjutan dengan Dataset Komprehensif (data/urban_assets.csv)...")
        res_full = create_urban_assets_pipeline(
            data_source=csv_path,
            buffer_meters=500.0,
            output_path="output_urban_assets_comprehensive.html"
        )
    
    print("\n[SUKSES] Seluruh pipeline analisis spasial dan WebGIS selesai diproses!")
