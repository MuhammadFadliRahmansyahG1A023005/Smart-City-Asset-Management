"""
GIS & Spatial Analytics: Urban Asset Management Pipeline
======================================================
Pemetaan & Analisis Buffer Spasial Aset Fasilitas Publik Kota (Smart City Asset Management)

Terinspirasi dari sistem manajemen aset perkotaan di Christchurch (City Care Property)
dan pelaporan warga (Snap Send Solve), proyek ini membangun alur kerja otomatisasi analisis
data geospasial menggunakan ekosistem Open Source Python (GeoPandas, Shapely, Folium).

Tujuan: Melakukan analisis jangkauan layanan (buffer analysis 500m) dari titik aset fasilitas publik
dan mengekspor hasilnya menjadi peta interaktif WebGIS (.html) berbasis cloud-ready.
"""

import os
import argparse
from typing import Dict, Any, Optional
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import folium
from folium.plugins import MiniMap, Fullscreen, MeasureControl


# Skema warna dan ikon berdasarkan kategori fasilitas
CATEGORY_STYLE = {
    "Fasilitas Publik": {"color": "green", "icon": "leaf", "fillColor": "#2ca25f"},
    "Kesehatan": {"color": "red", "icon": "plus", "fillColor": "#e34a33"},
    "Pendidikan": {"color": "blue", "icon": "book", "fillColor": "#3182bd"},
    "Pemerintahan": {"color": "purple", "icon": "university", "fillColor": "#756bb1"},
    "Fasilitas Ibadah": {"color": "orange", "icon": "star", "fillColor": "#feb24c"},
    "Ruang Publik & Wisata": {"color": "cadetblue", "icon": "camera", "fillColor": "#41b6c4"},
    "Olahraga & Publik": {"color": "darkgreen", "icon": "heart", "fillColor": "#31a354"},
    "Layanan Darurat": {"color": "darkred", "icon": "bell", "fillColor": "#de2d26"},
    "Lainnya": {"color": "gray", "icon": "info-sign", "fillColor": "#636363"}
}


def get_default_dataset() -> Dict[str, list]:
    """Mengembalikan dataset bawaan aset fasilitas publik Kota Bengkulu."""
    return {
        "asset_id": ["AST001", "AST002", "AST003"],
        "asset_name": ["Taman Kota Bengkulu", "RSUD M. Yunus", "SMAN 1 Kota Bengkulu"],
        "category": ["Fasilitas Publik", "Kesehatan", "Pendidikan"],
        "latitude": [-3.7928, -3.8231, -3.7889],
        "longitude": [102.2608, 102.2981, 102.2662]
    }


def load_spatial_data(data_source: Optional[str] = None) -> gpd.GeoDataFrame:
    """
    Memuat data titik aset dan mengonversi ke GeoDataFrame dengan CRS EPSG:4326 (WGS84).
    
    Parameters:
        data_source (str, optional): Path ke file CSV atau GeoJSON. Jika None, gunakan data default.
        
    Returns:
        gpd.GeoDataFrame: GeoDataFrame dengan koordinat spasial WGS84.
    """
    if data_source and os.path.exists(data_source):
        print(f"[Spatial Data Ingestion] Membaca data dari: {data_source}")
        if data_source.endswith('.csv'):
            df = pd.read_csv(data_source)
            geometry = [Point(xy) for xy in zip(df["longitude"], df["latitude"])]
            gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")
        else:
            gdf = gpd.read_file(data_source)
            if gdf.crs is None or gdf.crs.to_epsg() != 4326:
                gdf = gdf.to_crs(epsg=4326)
    else:
        # Gunakan data default sesuai spesifikasi proyek
        data = get_default_dataset()
        geometry = [Point(xy) for xy in zip(data["longitude"], data["latitude"])]
        gdf = gpd.GeoDataFrame(data, geometry=geometry, crs="EPSG:4326")
        
    print(f"[Spatial Data Ingestion] Berhasil memuat {len(gdf)} titik aset.")
    return gdf


def calculate_buffer_zones(gdf: gpd.GeoDataFrame, 
                           buffer_meters: float = 500.0, 
                           epsg_metric: int = 32748) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """
    Melakukan transformasi proyeksi ke sistem koordinat metrik (UTM Zone 48S / EPSG:32748)
    untuk menghitung buffer radius secara akurat dalam satuan meter, kemudian dikembalikan
    ke EPSG:4326 untuk keperluan WebGIS rendering.
    
    Parameters:
        gdf (gpd.GeoDataFrame): Data aset dalam EPSG:4326.
        buffer_meters (float): Radius buffer dalam meter (default: 500m).
        epsg_metric (int): Kode EPSG metrik lokal (default: 32748 untuk Bengkulu/Sumatera Selatan).
        
    Returns:
        tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]: (gdf_utm, gdf_buffer_wgs84)
    """
    print(f"[Spatial Analytics] Transformasi CRS ke EPSG:{epsg_metric} (UTM Zone 48S)...")
    gdf_utm = gdf.to_crs(epsg=epsg_metric)
    
    print(f"[Spatial Analytics] Menghitung jangkauan buffer {buffer_meters} meter...")
    gdf_utm["buffer_geom"] = gdf_utm.geometry.buffer(buffer_meters)
    gdf_utm["area_sqm"] = gdf_utm["buffer_geom"].area
    gdf_utm["area_hectares"] = gdf_utm["area_sqm"] / 10000.0
    
    # Kembalikan geometri buffer ke WGS84 untuk visualisasi Folium
    gdf_buffer = gdf_utm.set_geometry("buffer_geom").to_crs(epsg=4326)
    return gdf_utm, gdf_buffer


def build_interactive_webgis(gdf: gpd.GeoDataFrame, 
                             gdf_buffer: gpd.GeoDataFrame, 
                             buffer_meters: float = 500.0,
                             output_path: str = "output_urban_assets_map.html") -> folium.Map:
    """
    Membangun peta interaktif WebGIS berbasis Folium dengan kontrol layer,
    styling kustom per kategori, popup detail, mini-map, dan tombol fullscreen.
    
    Parameters:
        gdf (gpd.GeoDataFrame): Titik aset dalam EPSG:4326.
        gdf_buffer (gpd.GeoDataFrame): Poligon buffer dalam EPSG:4326.
        buffer_meters (float): Radius buffer dalam meter.
        output_path (str): Lokasi file output HTML.
        
    Returns:
        folium.Map: Objek peta interaktif Folium.
    """
    # Menentukan titik tengah peta secara dinamis
    avg_lat = float(gdf["latitude"].mean())
    avg_lon = float(gdf["longitude"].mean())
    map_center = [avg_lat, avg_lon]
    
    m = folium.Map(
        location=map_center, 
        zoom_start=13, 
        tiles="OpenStreetMap"
    )
    
    # Tambahkan layer basemap alternatif
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri World Imagery",
        name="Satelit (Esri World Imagery)",
        control=True
    ).add_to(m)
    
    folium.TileLayer(
        tiles="https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
        attr="OpenTopoMap",
        name="Topografi (OpenTopoMap)",
        control=True
    ).add_to(m)
    
    # Feature Group untuk Layer Buffer
    buffer_group = folium.FeatureGroup(name=f"Area Jangkauan Layanan (Buffer {int(buffer_meters)}m)")
    
    for idx, row in gdf_buffer.iterrows():
        cat = row.get("category", "Lainnya")
        style = CATEGORY_STYLE.get(cat, CATEGORY_STYLE["Lainnya"])
        fill_color = style["fillColor"]
        
        geo_json_data = folium.GeoJson(
            row["buffer_geom"],
            style_function=lambda x, fc=fill_color: {
                "fillColor": fc,
                "color": "#1c4e80",
                "weight": 1.8,
                "fillOpacity": 0.25,
                "dashArray": "3, 6"
            },
            tooltip=folium.Tooltip(
                f"<b>Radius Layanan:</b> {int(buffer_meters)}m<br>"
                f"<b>Aset:</b> {row['asset_name']}<br>"
                f"<b>Kategori:</b> {row['category']}<br>"
                f"<b>Luas Layanan:</b> ~{row.get('area_hectares', 78.54):.2f} Ha"
            )
        )
        geo_json_data.add_to(buffer_group)
        
    buffer_group.add_to(m)
    
    # Feature Group untuk Titik Aset Fasilitas Publik
    asset_group = folium.FeatureGroup(name="Titik Fasilitas Publik (Public Assets)")
    
    for idx, row in gdf.iterrows():
        cat = row.get("category", "Lainnya")
        style = CATEGORY_STYLE.get(cat, CATEGORY_STYLE["Lainnya"])
        
        # HTML Popup dengan styling responsif
        popup_html = f"""
        <div style="font-family: Arial, sans-serif; font-size: 12px; min-width: 220px;">
            <h4 style="margin: 0 0 8px 0; color: #1f2937; border-bottom: 2px solid {style['fillColor']}; padding-bottom: 4px;">
                {row['asset_name']}
            </h4>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="font-weight: bold; padding: 2px 0; color: #4b5563;">ID Aset:</td>
                    <td style="padding: 2px 0; color: #111827;"><code>{row['asset_id']}</code></td>
                </tr>
                <tr>
                    <td style="font-weight: bold; padding: 2px 0; color: #4b5563;">Kategori:</td>
                    <td style="padding: 2px 0; color: #111827;">
                        <span style="background-color: {style['fillColor']}; color: white; padding: 2px 6px; border-radius: 4px; font-size: 11px;">
                            {row['category']}
                        </span>
                    </td>
                </tr>
                <tr>
                    <td style="font-weight: bold; padding: 2px 0; color: #4b5563;">Koordinat:</td>
                    <td style="padding: 2px 0; color: #111827;">{row['latitude']:.4f}, {row['longitude']:.4f}</td>
                </tr>
                <tr>
                    <td style="font-weight: bold; padding: 2px 0; color: #4b5563;">Buffer Layanan:</td>
                    <td style="padding: 2px 0; color: #059669;">{int(buffer_meters)} meter</td>
                </tr>
            </table>
            <div style="margin-top: 8px; font-size: 10px; color: #9ca3af; text-align: right;">
                Smart City Asset Management
            </div>
        </div>
        """
        
        folium.Marker(
            location=[row["latitude"], row["longitude"]],
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=f"{row['asset_name']} ({row['category']})",
            icon=folium.Icon(color=style["color"], icon=style["icon"], prefix="fa" if style["icon"] in ["leaf", "book", "university", "camera", "heart", "bell"] else "glyphicon")
        ).add_to(asset_group)
        
    asset_group.add_to(m)
    
    # Plugin Tambahan: MiniMap, Fullscreen, MeasureControl, LayerControl
    MiniMap(toggle_display=True, position="bottomright").add_to(m)
    Fullscreen(position="topleft").add_to(m)
    MeasureControl(position="topleft", primary_length_unit="meters", secondary_length_unit="kilometers").add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)
    
    # Judul / Legend Banner pada WebMap
    title_html = f'''
    <div style="position: fixed; 
                bottom: 30px; left: 30px; width: 330px; 
                background-color: rgba(255, 255, 255, 0.95);
                border: 2px solid #2563eb; z-index: 9999; 
                font-family: Arial, sans-serif;
                border-radius: 8px; padding: 12px;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);">
        <h4 style="margin: 0 0 6px 0; color: #1e3a8a; font-size: 14px; font-weight: bold;">
            Smart City Asset Management
        </h4>
        <p style="margin: 0 0 8px 0; font-size: 11px; color: #4b5563; line-height: 1.4;">
            Analisis jangkauan layanan spasial (Buffer {int(buffer_meters)}m) fasilitas publik Kota Bengkulu (WGS84 & UTM Zone 48S).
        </p>
        <div style="font-size: 11px; color: #374151;">
            <b>Legenda Titik & Jangkauan:</b><br>
            <span style="color: #2ca25f;">&#9632;</span> Fasilitas Publik &nbsp;|&nbsp;
            <span style="color: #e34a33;">&#9632;</span> Kesehatan &nbsp;|&nbsp;
            <span style="color: #3182bd;">&#9632;</span> Pendidikan
        </div>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(title_html))
    
    # Simpan sebagai File HTML WebMap
    m.save(output_path)
    print(f"[WebGIS Deployment] Peta interaktif berhasil dibuat: {output_path}")
    return m


def create_urban_assets_pipeline(data_source: Optional[str] = None,
                                 buffer_meters: float = 500.0,
                                 output_path: str = "output_urban_assets_map.html",
                                 epsg_metric: int = 32748) -> Dict[str, Any]:
    """
    Fungsi utama pipeline: Melakukan ekstraksi data, transformasi CRS metrik,
    kalkulasi buffer 500m, dan ekspor WebGIS interaktif.
    """
    print("=== GIS & Spatial Analytics: Urban Asset Management Pipeline ===")
    
    # 1. Inisialisasi Data Aset Kota (Koordinat Bujur & Lintang)
    gdf = load_spatial_data(data_source)
    
    # 2. Analisis Spasial: Buffer Zone (Proyeksi Metrik EPSG:32748 - UTM Zone 48S)
    gdf_utm, gdf_buffer = calculate_buffer_zones(
        gdf=gdf, 
        buffer_meters=buffer_meters, 
        epsg_metric=epsg_metric
    )
    
    # 3. Visualisasi WebGIS Interaktif (Folium)
    interactive_map = build_interactive_webgis(
        gdf=gdf, 
        gdf_buffer=gdf_buffer, 
        buffer_meters=buffer_meters,
        output_path=output_path
    )
    
    # Hitung Statistik Ringkasan
    total_assets = len(gdf)
    total_coverage_sqkm = (gdf_utm["area_sqm"].sum()) / 1_000_000.0
    
    # Hitung gabungan area tanpa double-counting (Dissolved Buffer)
    dissolved_buffer = gdf_utm["buffer_geom"].union_all()
    net_coverage_sqkm = dissolved_buffer.area / 1_000_000.0
    overlap_area_sqkm = total_coverage_sqkm - net_coverage_sqkm
    
    print("\n--- Ringkasan Analisis Spasial Aset Publik ---")
    print(f"Total Titik Aset          : {total_assets} unit")
    print(f"Radius Buffer Layanan     : {buffer_meters:.1f} meter")
    print(f"Total Akumulasi Area      : {total_coverage_sqkm:.3f} km²")
    print(f"Cakupan Bersih (Dissolved): {net_coverage_sqkm:.3f} km²")
    print(f"Area Tumpang Tindih       : {overlap_area_sqkm:.3f} km² (Overlap)")
    print(f"File Output WebGIS        : {os.path.abspath(output_path)}")
    print("=================================================================\n")
    
    return {
        "gdf": gdf,
        "gdf_utm": gdf_utm,
        "gdf_buffer": gdf_buffer,
        "map": interactive_map,
        "total_assets": total_assets,
        "buffer_radius_m": buffer_meters,
        "net_coverage_sqkm": net_coverage_sqkm,
        "output_path": output_path
    }


def main():
    parser = argparse.ArgumentParser(
        description="Smart City Asset Management: Pemetaan & Analisis Buffer Spasial Aset Fasilitas Publik"
    )
    parser.add_argument(
        "--data", "-d", 
        type=str, 
        default=None, 
        help="Path ke file dataset CSV atau GeoJSON (opsional, jika tidak dispesifikasikan memakai default demo)"
    )
    parser.add_argument(
        "--buffer", "-b", 
        type=float, 
        default=500.0, 
        help="Jarak radius buffer dalam meter (default: 500)"
    )
    parser.add_argument(
        "--output", "-o", 
        type=str, 
        default="output_urban_assets_map.html", 
        help="Nama file HTML output untuk peta WebGIS (default: output_urban_assets_map.html)"
    )
    parser.add_argument(
        "--epsg", 
        type=int, 
        default=32748, 
        help="Kode EPSG untuk proyeksi metrik (default: 32748 - WGS 84 / UTM Zone 48S)"
    )
    
    args = parser.parse_args()
    create_urban_assets_pipeline(
        data_source=args.data,
        buffer_meters=args.buffer,
        output_path=args.output,
        epsg_metric=args.epsg
    )


if __name__ == "__main__":
    main()
