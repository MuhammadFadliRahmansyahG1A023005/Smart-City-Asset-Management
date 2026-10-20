"""
Unit Tests for Spatial Analysis Pipeline
"""

import unittest
import os
import geopandas as gpd
from src.spatial_analysis import (
    load_spatial_data,
    calculate_buffer_zones,
    build_interactive_webgis,
    create_urban_assets_pipeline
)

class TestUrbanAssetsPipeline(unittest.TestCase):
    def setUp(self):
        self.test_output = "test_output_map.html"

    def tearDown(self):
        if os.path.exists(self.test_output):
            os.remove(self.test_output)

    def test_load_spatial_data_default(self):
        gdf = load_spatial_data(None)
        self.assertEqual(len(gdf), 3)
        self.assertEqual(gdf.crs.to_epsg(), 4326)
        self.assertIn("asset_name", gdf.columns)
        self.assertIn("geometry", gdf.columns)

    def test_calculate_buffer_zones(self):
        gdf = load_spatial_data(None)
        gdf_utm, gdf_buffer = calculate_buffer_zones(gdf, buffer_meters=500.0, epsg_metric=32748)
        self.assertEqual(gdf_utm.crs.to_epsg(), 32748)
        self.assertEqual(gdf_buffer.crs.to_epsg(), 4326)
        # 500m radius circle area = pi * 500^2 ~= 785,398 m2
        for area in gdf_utm["area_sqm"]:
            self.assertAlmostEqual(area, 785398.16, delta=5000.0)

    def test_pipeline_execution(self):
        res = create_urban_assets_pipeline(
            data_source=None,
            buffer_meters=500.0,
            output_path=self.test_output
        )
        self.assertTrue(os.path.exists(self.test_output))
        self.assertGreater(os.path.getsize(self.test_output), 1000)
        self.assertEqual(res["total_assets"], 3)
        self.assertGreater(res["net_coverage_sqkm"], 0.0)


if __name__ == "__main__":
    unittest.main()
