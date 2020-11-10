# extended from https://github.com/wajuqi/Sentinel-1-preprocessing-using-Snappy

import snappy
from snappy import ProductIO
from snappy import HashMap
from snappy import GPF
import os
import zipfile
import logging

logger = logging.getLogger('S1ProcessorLogger')
logging.basicConfig(level=logging.INFO)

class S1Processor():
    def __init__(self, zip_path, footprint):
        logger.info('Instanciating S1 processor for {0}'.format(zip_path))

        self.footprint = footprint
        self.zip_path = zip_path
        self.safe_folder = self.dir_path = self.basename = None
        self.pols = None

    def unzip(self):

        ######




        ######
        self.dir_path = os.path.dirname(self.zip_path)
        self.basename = os.path.basename(self.zip_path)[:-4]
        self.safe_folder = os.path.join(self.dir_path, self.basename) + '.SAFE'
               
        with zipfile.ZipFile(self.zip_path, 'r') as f:
            f.extractall(self.dir_path)

    def apply_orbit_file(self, source):
        logger.info('\tApplying orbit file')
        parameters = HashMap()
        parameters.put('Apply-Orbit-File', True)
        output = GPF.createProduct('Apply-Orbit-File', parameters, source)
        return output

    def get_meta(self):
        modestamp = self.safe_folder.split("_")[1]
        productstamp = self.safe_folder.split("_")[2]
        polstamp = self.safe_folder.split("_")[3]
        self.polarization = polstamp[2:4]

        if self.polarization == 'DV':
            self.pols = 'VH,VV'
        elif self.polarization == 'DH':
            self.pols = 'HH,HV'
        elif self.polarization == 'SH' or polarization == 'HH':
            self.pols = 'HH'
        elif self.polarization == 'SV':
            self.pols = 'VV'
        else:
            logger.info("Polarization error!")

    def remove_thermal_noise(self, source):
        logger.info('\tThermal noise removal')
        parameters = HashMap()
        parameters.put('removeThermalNoise', True)
        output = GPF.createProduct('ThermalNoiseRemoval', parameters, source)
        return output

    def calibrate(self, source):
        logger.info('\tCalibration')
        parameters = HashMap()
        parameters.put('outputSigmaBand', True)
        parameters.put('selectedPolarisations', self.pols)
        parameters.put('outputImageScaleInDb', False)
        parameters.put('auxFile', 'Product Auxiliary File')
        parameters.put('outputImageInComplex', False)
        parameters.put('outputGammaBand', False)
        parameters.put('outputBetaBand', False)
        if self.polarization == 'DH':
            parameters.put('sourceBands', 'Intensity_HH,Intensity_HV')
        elif self.polarization == 'DV':
            parameters.put('sourceBands', 'Intensity_VH,Intensity_VV')
        elif self.polarization == 'SH' or polarization == 'HH':
            parameters.put('sourceBands', 'Intensity_HH')
        elif self.polarization == 'SV':
            parameters.put('sourceBands', 'Intensity_VV')
        else:
            logger.info("Unknown polarization")

        output = GPF.createProduct("Calibration", parameters, source)
        return output


    def multi_temporal_despeckling(self):
        pass
        return


    def terrain_correction(self, source):
        logger.info('\tTerrain correction...')
        parameters = HashMap()
        parameters.put('demName', 'SRTM 3Sec')
        parameters.put('imgResamplingMethod', 'BILINEAR_INTERPOLATION')
        parameters.put('mapProjection', 'AUTO:42001')       # comment this line if no need to convert to UTM/WGS84, default is WGS84
        parameters.put('saveProjectedLocalIncidenceAngle', True)
        parameters.put('saveSelectedSourceBand', True)
        parameters.put('pixelSpacingInMeter', 10.0)
        parameters.put('pixelSpacingInDegree', 8.983152841195215E-5)
        parameters.put('alignToStandardGrid', False)
        parameters.put('standardGridOriginX', 0.0)
        parameters.put('standardGridOriginXY', 0.0)
        parameters.put('nodataValueAtSea', True)
        parameters.put('saveDEM', False)
        parameters.put('saveSelectedSourceBand', True)
        parameters.put('incidenceAngleForSigma0', 'Use projected local incidence angle from DEM')
        parameters.put('auxFile', 'Latest Auxiliary File')
        
        output = GPF.createProduct('Terrain-Correction', parameters, source)
        return output

    def subset(self, source):
        logger.info('\tClipping to AOI')
        parameters = HashMap()
        parameters.put('geoRegion', self.footprint)
        output = GPF.createProduct('Subset', parameters, source)
        return output


    def scale_db(self, source):
        logger.info('\tScaling to dB')
        parameters = HashMap()
        parameters.put('sourceBands', 'Sigma0_VV,Sigma0_VH')
        output = GPF.createProduct("LinearToFromdB", parameters, source)
        return output


    def process(self):


        self.unzip()
        self.get_meta()

        scene = ProductIO.readProduct(self.safe_folder + '/manifest.safe')   
        applyorbit = self.apply_orbit_file(scene)
        thermaremoved = self.remove_thermal_noise(applyorbit)
        calibrated = self.calibrate(thermaremoved)
        tercorrected = self.terrain_correction(calibrated)

        # subset here
        if self.footprint:
            tercorrected = self.subset(tercorrected)

        scaled_db = self.scale_db(tercorrected)

        output_path = os.path.join(self.dir_path, self.basename) + '_VV_VH_dB.tif'
        ProductIO.writeProduct(scaled_db, output_path, 'GeoTIFF-BigTIFF')