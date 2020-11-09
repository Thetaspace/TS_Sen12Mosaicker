import os
import zipfile
import logging
import xml.etree.ElementTree as ET
import numpy as np
import shapely.wkt
import rasterio
from rasterio.mask import mask
import geopandas as gpd
from shapely.geometry import box

logger = logging.getLogger('S2ProcessorLogger')
logging.basicConfig(level=logging.INFO)

class S2Processor():
    def __init__(self, path_zip):
        self.path_zip = path_zip
    
    def unzip(self):
        with zipfile.ZipFile(self.path_zip, 'r') as ff:
            ff.extractall(os.path.dirname(self.path_zip))
        
        self.unzip_folder = self.path_zip[:-4] + '.SAFE'

    def get_jp2_paths(self):
        manifest = self.unzip_folder + '/manifest.safe'
        tree = ET.parse(manifest)
        root = tree.getroot()
        
        red = blue = green = nir = tci = None
        
        for r in root.iter('fileLocation'):
            href = r.attrib['href']
            if 'B02.jp2' in href or 'B02_10m.jp2' in href:
                blue = os.path.join(self.unzip_folder,href)
            elif 'B03.jp2' in href or 'B03_10m.jp2' in href:
                green = os.path.join(self.unzip_folder,href)
            elif 'B04.jp2' in href or 'B04_10m.jp2' in href:
                red = os.path.join(self.unzip_folder,href)
            elif 'B08.jp2' in href or 'B08_10m.jp2' in href:
                nir = os.path.join(self.unzip_folder,href)
            elif 'TCI.jp2' in href or 'TCI_10m.jp2' in href:
                tci = os.path.join(self.unzip_folder,href)
                    
        return {'red':red, 'green':green, 'blue':blue, 'nir':nir, 'tci':tci}

    def getFeatures(self, gdf):
        """Function to parse features from GeoDataFrame in such a manner that rasterio wants them"""
        import json
        return [json.loads(gdf.to_json())['features'][0]['geometry']]

    def clip_to_aoi(self, path_jp2, footprint):
        dataset = rasterio.open(path_jp2)
        fp = shapely.wkt.loads(footprint)
        
        # create new footprint from the intersection of raster and footprint
        dataset_bbox = dataset.bounds
        geo_dataset = gpd.GeoDataFrame({'geometry': box(dataset_bbox[0], dataset_bbox[1], dataset_bbox[2], dataset_bbox[3])}, index=[0], crs=dataset.crs)
        geo_fp = gpd.GeoDataFrame({'geometry': box(fp.bounds[0],fp.bounds[1],fp.bounds[2],fp.bounds[3])}, index=[0], crs={'init':'epsg:4326'})
        geo_dataset = geo_dataset.to_crs(crs={'init':'epsg:4326'})
        coords = getFeatures(geo_dataset.intersection(geo_fp).to_crs(dataset.crs.data))
        
        rect,g_rect = mask(dataset, coords, all_touched=True, crop=True)
        
        out_meta = dataset.meta.copy()
        out_meta.update({"driver": "GTiff",
                "height": rect.shape[1],
                "width": rect.shape[2],
                "transform": g_rect}
            )
        output_path = path_jp2[:-4] + '_clipped.tif'
        with rasterio.open(output_path, 'w', **out_meta) as dst:
            dst.write(rect.astype(np.uint16))      
        return output_path








    def clip_all_bands_to_aoi(self):
        pass


    def merge_rasters(list_clipped_rasters_paths, output_folder, suffix):
        rec, rec_g = merge(list_clipped_rasters_paths)
        out_meta = rasterio.open(list_clipped_rasters_paths[0]).meta.copy()
        out_meta.update({"driver": "GTiff",
                "height": rec.shape[1],
                "width": rec.shape[2],
                "transform": g_rec})
        
        output_path = output_folder + 'Mosaic_{0}.tif'.format(suffix)
        with rasterio.open(output_path, 'w', **out_meta) as dst:
            dst.write(rect.astype(np.uint16))   

    