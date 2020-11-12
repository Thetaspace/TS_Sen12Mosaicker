# extended from https://github.com/wajuqi/Sentinel-1-preprocessing-using-Snappy

import snappy
from snappy import ProductIO
from snappy import HashMap
from snappy import GPF
import os
import zipfile
import logging
import glob
from src.Processor import Processor

logger = logging.getLogger('S1ProcessorLogger')
logging.basicConfig(level=logging.INFO)

class S1Processor(Processor):
    def __init__(self, zips_path, footprint):
        super(S1Processor, self).__init__(zips_path, footprint)
        logger.info('Instanciating S1 processor for S1 files in {0}'.format(self.zips_path))

        self.suffix = 'S1'
        self.dtype = np.float32
        self.safe_folders = []
        self.basenames = []
        self.pols = []
        self.polarizations = []

    def unzip(self):

        for zip_file in glob.glob(self.zips_path + '/S1*.zip'):
                    
            basename = os.path.basename(zip_file)[:-4]
            self.basenames.append(basename)
            self.safe_folders.append(os.path.join(self.zips_path, basename) + '.SAFE')

            with zipfile.ZipFile(zip_file, 'r') as f:
                f.extractall(self.zips_path)   


    def apply_orbit_file(self, source):
        logger.info('\tApplying orbit file')
        parameters = HashMap()
        parameters.put('Apply-Orbit-File', True)
        output = GPF.createProduct('Apply-Orbit-File', parameters, source)
        return output

    def get_meta(self):
        for i in range(len(self.safe_folders)):
            modestamp = self.safe_folders[i].split("_")[1]
            productstamp = self.safe_folders[i].split("_")[2]
            polstamp = self.safe_folders[i].split("_")[3]
            polarization = polstamp[2:4]
            self.polarizations.append(polarization)

            if polarization == 'DV':
                self.pols.append('VH,VV')
            elif polarization == 'DH':
                self.pols.append('HH,HV')
            elif polarization == 'SH' or polarization == 'HH':
                self.pols.append('HH')
            elif polarization == 'SV':
                self.pols.append('VV')
            else:
                self.pols.append('NaN')
                logger.info("Polarization error!")

    def remove_thermal_noise(self, source):
        logger.info('\tThermal noise removal')
        parameters = HashMap()
        parameters.put('removeThermalNoise', True)
        output = GPF.createProduct('ThermalNoiseRemoval', parameters, source)
        return output

    def calibrate(self, source, pol, polarization):
        logger.info('\tCalibration')
        parameters = HashMap()
        parameters.put('outputSigmaBand', True)
        parameters.put('selectedPolarisations', pol)
        parameters.put('outputImageScaleInDb', False)
        parameters.put('auxFile', 'Product Auxiliary File')
        parameters.put('outputImageInComplex', False)
        parameters.put('outputGammaBand', False)
        parameters.put('outputBetaBand', False)
        if polarization == 'DH':
            parameters.put('sourceBands', 'Intensity_HH,Intensity_HV')
        elif polarization == 'DV':
            parameters.put('sourceBands', 'Intensity_VH,Intensity_VV')
        elif polarization == 'SH' or polarization == 'HH':
            parameters.put('sourceBands', 'Intensity_HH')
        elif polarization == 'SV':
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

        for i, safe_folder in enumerate(self.safe_folders):

            scene = ProductIO.readProduct(safe_folder + '/manifest.safe')   
            applyorbit = self.apply_orbit_file(scene)
            thermaremoved = self.remove_thermal_noise(applyorbit)
            calibrated = self.calibrate(thermaremoved, self.pols[i], self.polarizations[i])
            tercorrected = self.terrain_correction(calibrated)

            # subset here
            if self.footprint:
                tercorrected = self.subset(tercorrected)

            scaled_db = self.scale_db(tercorrected)

            output_path = os.path.join(self.zips_path, self.basenames[i]) + '_VV_VH_dB.tif'
            ProductIO.writeProduct(scaled_db, output_path, 'GeoTIFF-BigTIFF')
            self.paths_to_merge.append(output_path)
