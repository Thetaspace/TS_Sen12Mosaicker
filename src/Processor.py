import os
import shutil
from src.utils import merge_rasters
import numpy as np

class Processor(object):
    def __init__(self, zips_path, footprint):
        self.zips_path = zips_path
        self.footprint = footprint
        self.paths_to_merge = []
        self.dtype = None
        self.suffix = ''

    def merge(self):
        output_folder = os.path.join(self.zips_path, '..')
        file_string = os.path.basename(os.path.dirname(self.zips_path)) + self.suffix
        if self.suffix == 'S1':        
            if len(self.paths_to_merge)>1:
                merge_rasters(self.paths_to_merge, output_folder, file_string, self.dtype)
            elif len(self.paths_to_merge) == 1:
                shutil.copy(self.paths_to_merge[0], output_folder + '/{0}.tif'.format(file_string))
        
        elif self.suffix == 'S2':
            group_lambda = lambda x, key: [dic[key] for dic in x]
            if len(self.paths_to_merge) > 1:
                for key in self.paths_to_merge[0].keys():
                    list_bands_to_merge = group_lambda(self.paths_to_merge, key)
                    file_string2 = '{0}_'.format(key) + file_string
                    merge_rasters(list_bands_to_merge, output_folder, file_string2, self.dtype)

            elif len(self.paths_to_merge) == 1:
                for key in self.paths_to_merge[0].keys():
                    file_string2 = '{0}_'.format(key) + file_string
                    shutil.copy(self.paths_to_merge[0][key], output_folder + '/{0}.tif'.format(file_string2))
