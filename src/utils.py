#!/usr/bin/python
#-*- coding: utf-8 -*-


from sentinelsat import SentinelAPI, read_geojson, geojson_to_wkt
from datetime import date
import datetime
import pandas as pd

import json
import yaml

import shapely
from shapely.wkt import loads

import numpy as np
import rasterio
from rasterio.mask import mask
import geopandas as gpd
from shapely.geometry import box

def authenticate_oah(creds_json):
    """
    returns authenticated API 
    """
    with open(creds_json) as f:
        creds = json.load(f)['credentials']
        username = creds['username']
        password = creds['password']
        api = SentinelAPI(username, password)
    return api

def geojson_to_footprint(geojson_file):
    return geojson_to_wkt(read_geojson(geojson_file))

def read_main_config(conf_yaml):
   with open(conf_yaml, 'r') as stream:
        try:
            parse_ = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            pass ##### **** log exception
            
        return parse_['OUTPUT_FOLDER'], parse_['min_coverage'], parse_['DATE']['min_date'], parse_['DATE']['max_date'], parse_['DATE']['ts_interval'], parse_['OAH_CREDS'], parse_['FOOTPRINT']

def read_query_kwargs(conf_yaml):
    with open(conf_yaml, 'r') as stream:
        try:
            parse_ = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            pass ##### **** log exception
    
        s2_kwargs = {
        'cloudcoverpercentage' : (parse_['S2']['mincloudcover'], parse_['S2']['maxcloudcover']),
        'processinglevel' : parse_['S2']['processinglevel']
        }
        s1_kwargs = {
        'producttype' : parse_['S1']['producttype']
        }
        
        return s2_kwargs, s1_kwargs

def query_products(api, date_interval, conf_yaml, footprint):
    """
    date_interval: tuple of strings (min_date, max_date) 

    returns: two dicts of s2 and s1 products
    """
    #api = authenticate_oah(creds_json)
    
    s2_kwargs, s1_kwargs = read_query_kwargs(conf_yaml)
    
    s2_kwargs.update({'area':footprint, 'platformname': 'Sentinel-2', 'date' : date_interval})
    s1_kwargs.update({'area':footprint, 'platformname': 'Sentinel-1', 'date' : date_interval})

    return api.to_dataframe(api.query(**s2_kwargs)), api.to_dataframe(api.query(**s1_kwargs))

def get_intersection(footprint1, footprint2):
    fp1 = shapely.wkt.loads(footprint1)
    fp2 = shapely.wkt.loads(footprint2)
    return fp1.intersection(fp2)


def get_difference(footprint1, footprint2):
    fp1 = shapely.wkt.loads(footprint1)
    fp2 = shapely.wkt.loads(footprint2)
    return fp1.difference(fp2)

def get_sorted_scenes_by_intersection_aoi(products, aoi_fp):
    intersec_aoi = lambda x: round(get_intersection(x, aoi_fp).area, 2)
    products['intersection_AOI'] = products['footprint'].apply(intersec_aoi)
    if 'cloudcoverpercentage' in products.columns:
        return products.sort_values(['intersection_AOI', 'cloudcoverpercentage', 'size'], ascending=[False, True, False])
    else:
        return products.sort_values(['intersection_AOI'], ascending=False)


def get_complete_coverage_of_AOI(products, aoi_fp, logger, aoi_area=None, max_coverage=0.90):
    
    if aoi_area is None:
        aoi = shapely.wkt.loads(aoi_fp)
        aoi_area = aoi.area

    scenes = get_sorted_scenes_by_intersection_aoi(products, aoi_fp)

    top_scene = scenes.iloc[0]
    
    # has to return the flag incomplete aoi coverage 

    left_over_area = get_difference(aoi_fp, top_scene['footprint'])
    intersection_area = get_intersection(aoi_fp, top_scene['footprint']).area

    if intersection_area == 0:
        logger.info('the whole area could not be fully covered. Scenes are missing!')
        return []

    elif left_over_area.area < (1-max_coverage) * aoi_area:
        return [top_scene]
    else:
        logger.info('Looking for more scenes. Non covered area percentage until now = {0}%'.format(float((left_over_area.area/aoi_area))))
        new_aoi_fp = left_over_area.to_wkt()
        return [top_scene] + get_complete_coverage_of_AOI(products=products, aoi_fp=new_aoi_fp, logger=logger, aoi_area=aoi_area)


def chunk_dates(min_date, max_date, days):
    
    delta_days = datetime.timedelta(days)
    interval_width = max_date-min_date
    
    if interval_width <= delta_days:
        return [(min_date, max_date)]
    else:
        return [(min_date, min_date + delta_days)] + chunk_dates(min_date + delta_days, max_date, days)


def get_products_chunks(products_df, ts_intervals):
    """
    returns a list of length ts_intervals

    """
    ts_products_lists = []
    for (min_date, max_date) in ts_intervals:
        ts_products_lists.append(products_df[(products_df['beginposition']<=max_date) & (products_df['beginposition']>=min_date)])
    return ts_products_lists



def getFeatures(gdf):
    """Function to parse features from GeoDataFrame in such a manner that rasterio wants them"""
    import json
    return [json.loads(gdf.to_json())['features'][0]['geometry']]

def clip_to_aoi(path_jp2, footprint):
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