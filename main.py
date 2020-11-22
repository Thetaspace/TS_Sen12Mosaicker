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


import logging
from Sen12Mosaicker import Sen12Mosaicker
import os
import glob
from src.S1Processor import S1Processor
from src.S2Processor import S2Processor
from src.utils import clip_to_smallest

logger = logging.getLogger('MainLogger')
logging.basicConfig(level=logging.INFO)

def main():

  conf_yaml = 'config.yaml'

  mosaicker = Sen12Mosaicker(conf_yaml)
  mosaicker.get_products()

  if len(mosaicker.products_s1) >0 and len(mosaicker.products_s2)>0:
    logger.info('\t{0} S1 and {1} products found'.format(len(mosaicker.products_s1), len(mosaicker.products_s2)))
  else:
    logger.info('\tEither S1 or S2 queries returned no products')
    return 

  mosaicker.get_intervals()
  logger.info('\tTrying to list data to form time series of {0} points in time'.format(len(mosaicker.ts_intervals))) 

  mosaicker.get_scenes_todownload()
  logger.info('\tDownloading (or at least trying to) data to form time series of {0} points in time'.format(len(mosaicker.list_ts_pairs)))

  mosaicker.download_scenes()
  logger.info('\tfinished downloading')


  # Processing all files to form mosaicks for each time step
  s1_folders = glob.glob(mosaicker.output_folder + '/*/S1')
  s2_folders = glob.glob(mosaicker.output_folder + '/*/S2')
  
  for i in range(len(s2_folders)):
    s1_proc = S1Processor(s1_folders[i], mosaicker.footprint)
    s1_proc.process() # the "process" method runs the complete workflow: raster processing, clipping, mosaicking, readings and writings... 
                      # but of course each step can be executed individually e.g. s1_proc.unzip() or s2_proc.clip_all_to_aoi()  etc. 

    s2_proc = S2Processor(s2_folders[i], mosaicker.footprint)
    s2_proc.process()

    # DUE to different subsetting algorithms while processing S1 and S2
    # Discrepancy between extents might SOMETIMES require further post-processing
    # following step will cure it
    s2_list = glob.glob(os.path.join(s1_folders[i], '../*S2.tif'))
    if len(s2_list)>0:
      s1_ = glob.glob(os.path.join(s2_folders[i],'../*S1.tif'))[0]
      clip_to_smallest(s1_, s2_list)


if __name__ == "__main__":
    main()
