#!/usr/bin/python
#-*- coding: utf-8 -*-
# =========================================================================
#   Program:   Sen12Mosaicker
#
#   Copyright (c) Thetaspace GmbH. All rights reserved.
#
#   See LICENSE for details.
#
#   This software is distributed WITHOUT ANY WARRANTY; without even
#   the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
#   PURPOSE.  See the above copyright notices for more information.
#
# =========================================================================
#
# Author: Zayd Mahmoud Hamdi (Thetaspace)
#
# =========================================================================


"""
This module contains a script to build georeferenced time series of {S1,S2} images for any given footprint.

Steps:

  1- Queries all the available S2 and S1 products according to the search keywords (area, date, cloud cover, ...)
  2- Chunks the products according to the provided time interval 
  3- For each interval, selects the S1 and S2 scenes covering the whole (or a tolerated min_coverage) area of interest. S2 scenes with the least cloud cover and nodata are prioritized
  4- S2 and S1 pairs are downloaded to disk
  5- Calibrate the S1 images to gamma0
  6- Removes Thermal Noise
  7- Applies orbit file
  8- Performs Terrain Correction
  9- Subsets the current s1 scene to the footprint to guarentee the fastest processing possible
  10- Converts from linear to dB and saves Tiff files (vv, vh) on disk
  11- mosaics the processed S2 and S1 to cover the AOI

 Parameters have to be set by the user in the config.yaml file
"""
import logging
import yaml
from src.utils import *
import os
import glob
from src.S1Processor import S1Processor

logger = logging.getLogger('LoggerS12Mosaicker')
logging.basicConfig(level=logging.INFO)

class Sen12Mosaicker():
  def __init__(self, conf_yaml):
    self.conf_yaml = conf_yaml

    self.ts_intervals = []

    self.products_s2 = None
    self.products_s1 = None
    self.list_ts_pairs = []

    self.output_folder, \
    self.min_coverage,\
    self.min_date,\
    self.max_date,\
    self.ts_delta,\
    self.creds_json,\
    self.geojson_file = read_main_config(self.conf_yaml)

    self.footprint = geojson_to_footprint(self.geojson_file)

    self.api = authenticate_oah(self.creds_json)

  def get_intervals(self):
    self.min_date = datetime.datetime.strptime(self.min_date, "%Y%m%d")
    self.max_date = datetime.datetime.strptime(self.max_date, "%Y%m%d")
    self.ts_intervals = chunk_dates(self.min_date, self.max_date, self.ts_delta)

  def get_products(self):
    self.products_s2, self.products_s1 = query_products(self.api, (self.min_date, self.max_date), self.conf_yaml, self.footprint)

  def get_scenes_todownload(self):
      """
      returns:
          - two lists of s2 and s1 scenes to download
      """
      if (not self.products_s1.empty) and (not self.products_s2.empty):  
        products_chunks_s2 = get_products_chunks(self.products_s2, self.ts_intervals)
        products_chunks_s1 = get_products_chunks(self.products_s1, self.ts_intervals)

        for i in range(len(self.ts_intervals)):    #len(self.ts_intervals = len(product_chunks))
          
          if (not products_chunks_s1[i].empty) and (not products_chunks_s2[i].empty):
            s2_coverage, s1_coverage = get_complete_coverage_of_AOI(products=products_chunks_s2[i], aoi_fp=self.footprint, logger=logger), get_complete_coverage_of_AOI(products=products_chunks_s1[i], aoi_fp=self.footprint, logger=logger)
            
            if not isinstance(s2_coverage[-1],str):
              self.list_ts_pairs.append((self.ts_intervals[i],s2_coverage, s1_coverage))
            else:
              logger.info('incomplete mosaic in this interval... skipping')

      else:
        logger.info('No products meeting requirements available')

  
  def download_scenes(self):
    if not os.path.exists(self.output_folder):
      os.mkdir(self.output_folder)
    
    for pair in self.list_ts_pairs:
      interval, s2_list, s1_list = pair

      min_date = datetime.datetime.strftime(interval[0], "%Y%m%d")
      max_date = datetime.datetime.strftime(interval[1], "%Y%m%d")
      folder_path = self.output_folder + '/{0}_{1}'.format(min_date,max_date)
      os.mkdir(folder_path)
      os.mkdir(folder_path + '/S1')
      os.mkdir(folder_path + '/S2')
      
      for s2 in s2_list:
        self.api.download(s2['uuid'], folder_path + '/S2')
      for s1 in s1_list:
        self.api.download(s1['uuid'], folder_path + '/S1')





