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
import glob
from src.S1Processor import S1Processor

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

  s1_files = glob.glob(mosaicker.output_folder + '/*/S1/*.zip')
  
  for s1_zip in s1_files:
    s1_proc = S1Processor(s1_zip, self.footprint)
    s1_proc.process()


if __name__ == "__main__":
    main()