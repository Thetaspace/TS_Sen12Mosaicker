import functools
import os
import glob
import zipfile
import logging
import xml.etree.ElementTree as ET
import numpy as np
import shapely.wkt
import rasterio
from src.utils import clip_to_aoi
from src.Processor import Processor

logger = logging.getLogger('S2ProcessorLogger')
logging.basicConfig(level=logging.INFO)

class S2Processor(Processor):
    def __init__(self, path_S2, footprint):
        super(S2Processor, self).__init__(path_S2, footprint)
        logger.info('Instanciating S2 processor for S2 files in {0}'.format(self.zips_path))
        
        self.suffix = 'S2'
        self.dtype = np.uint16
        # The zip files in one S2 folder (of one time series point)
        self.zip_files = glob.glob(self.zips_path + '/S2*.zip')
        self.unzip_folders = []
        self.jp2_paths = []
        self.footprint = footprint
    
    def unzip_files(self):
        for zip_file in self.zip_files:
            with zipfile.ZipFile(zip_file, 'r') as ff:
                ff.extractall(os.path.dirname(zip_file))
        
            self.unzip_folders.append(zip_file[:-4] + '.SAFE')

    def get_jp2_paths(self):
        for unzip_folder in self.unzip_folders:
            manifest = unzip_folder + '/manifest.safe'
            tree = ET.parse(manifest)
            root = tree.getroot()
            
            red = blue = green = nir = tci = None
            
            for r in root.iter('fileLocation'):
                href = r.attrib['href']
                if 'B02.jp2' in href or 'B02_10m.jp2' in href:
                    blue = os.path.join(unzip_folder,href)
                elif 'B03.jp2' in href or 'B03_10m.jp2' in href:
                    green = os.path.join(unzip_folder,href)
                elif 'B04.jp2' in href or 'B04_10m.jp2' in href:
                    red = os.path.join(unzip_folder,href)
                elif 'B08.jp2' in href or 'B08_10m.jp2' in href:
                    nir = os.path.join(unzip_folder,href)
                elif 'TCI.jp2' in href or 'TCI_10m.jp2' in href:
                    tci = os.path.join(unzip_folder,href)
                    
            self.jp2_paths.append({'red':red, 'green':green, 'blue':blue, 'nir':nir, 'tci':tci})


    def clip_all_to_aoi(self):
        clip_partial = functools.partial(clip_to_aoi, footprint=self.footprint)
        clip_lambda = lambda x: dict(zip(x.keys(), map(clip_partial, x.values())))

        self.paths_to_merge = [clip_lambda(jp2_paths) for jp2_paths in self.jp2_paths]
    
    def process(self):
        self.unzip_files()
        self.get_jp2_paths()
        self.clip_all_to_aoi()
        self.merge()
  