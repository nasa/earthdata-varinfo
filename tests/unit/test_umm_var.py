from os.path import exists
from shutil import rmtree
from tempfile import mkdtemp
from typing import Dict
from unittest import TestCase
from unittest.mock import patch, Mock
import json
import xml.etree.ElementTree as ET

from jsonschema import validate as validate_json, ValidationError
from netCDF4 import Dataset
from numpy import int32, float64
import requests
from requests.exceptions import RequestException
from cmr import CMR_UAT

from varinfo import CFConfig
from varinfo import VarInfoFromDmr, VarInfoFromNetCDF4, VariableFromDmr
from varinfo.exceptions import InvalidExportDirectory, UmmVarPublicationException
from varinfo.umm_var import (export_all_umm_var_to_json,
                             export_umm_var_to_json,get_all_umm_var,
                             get_dimension_information, get_dimension_size,
                             get_dimensions, get_fill_values,
                             get_first_matched_attribute,
                             get_json_serializable_value,
                             get_metadata_specification, get_umm_var,
                             get_umm_var_dtype, get_valid_ranges,
                             publish_umm_var, publish_all_umm_var)

from tests.utilities import is_dictionary_subset, write_skeleton_netcdf4


class TestUmmVar(TestCase):
    """ Tests for the varinfo.umm_var module, which generates UMM-Var JSON. """

    @classmethod
    def setUpClass(cls):
        """ Set up properties of the class that do not need to be reset between
            tests.

        """
        cls.atl03_varinfo = VarInfoFromDmr('tests/unit/data/ATL03_example.dmr',
                                           short_name='ATL03')
        cls.atl03_config = CFConfig('ICESat-2', 'ATL03',
                                      config_file='tests/unit/data/test_config.json')
        cls.gpm_varinfo = VarInfoFromDmr('tests/unit/data/GPM_3IMERGHH_example.dmr',
                                         short_name='GPM_3IMERGHH')
        cls.merra_varinfo = VarInfoFromDmr('tests/unit/data/M2I3NPASM_example.dmr',
                                           short_name='M2I3NPASM')
        with open('tests/unit/data/umm_var_json_schema_1.8.2.json', 'r') as schema_file:
            cls.umm_var_schema = json.load(schema_file)

    def setUp(self):
        """ Define test fixtures that should be unique per test. """
        self.tmp_dir = mkdtemp()

    def tearDown(self):
        """ Remove any test-specific fixtures. """
        if exists(self.tmp_dir):
            rmtree(self.tmp_dir)

    def is_valid_umm_var(self, umm_var_record: Dict) -> bool:
        """ Ensure the supplied object adheres to the UMM-Var schema. """
        try:
            validate_json(instance=umm_var_record, schema=self.umm_var_schema)
            return True
        except ValidationError as exception:
            print(str(exception))
            return False

    def test_get_all_umm_var(self):
        """ Ensure that UMM-Var JSON is produced for all variables in a given
            VarInfo instance.

        """
        all_records = get_all_umm_var(self.gpm_varinfo)
        self.assertEqual(len(all_records), 16)

        for umm_var_record in all_records.values():
            self.assertTrue(self.is_valid_umm_var(umm_var_record))

    def test_get_umm_var_all_fields(self):
        """ Ensure that a variable with all UMM-Var fields captured by
            earthdata-varinfo can translate that to a UMM-Var record. Also
            ensure that this record is valid according to the UMM-Var schema.

        """
        netcdf4_file = f'{self.tmp_dir}/input.nc4'
        with Dataset(netcdf4_file, 'w') as dataset:
            dataset.setncatts({'short_name': 'GPM_3IMERGHH-ish'})
            dataset.createDimension('lat', size=1800)
            dataset.createDimension('lon', size=3600)
            dataset.createDimension('time', size=1)
            lat = dataset.createVariable('lat', float64, dimensions=('lat', ))
            lat.setncatts({'long_name': 'latitude',
                           'standard_name': 'latitude',
                           'units': 'degrees_north'})
            lon = dataset.createVariable('lon', float64, dimensions=('lon', ))
            lon.setncatts({'long_name': 'longitude',
                           'standard_name': 'longitude',
                           'units': 'degrees_east'})
            time = dataset.createVariable('time', float64, dimensions=('time', ))
            time.setncatts({'long_name': 'time',
                            'units': 'seconds since 1970-01-01T00:00:00'})

            variable = dataset.createVariable(
                'precipitationCal', float64,
                dimensions=('time', 'lon', 'lat'), fill_value=-9999.9
            )
            # Note: values below are primarily to test all are found, may not
            # be scientifically valid.
            variable.setncatts({
                'description': 'Calibrated precipitation',
                'standard_name': 'CF Conventions standard name',
                'units': 'mm/hr',
                'scale': 1.0,
                'offset': 0.0,
                'valid_min': 0,
                'valid_max': 1000
            })

        nc_varinfo = VarInfoFromNetCDF4(netcdf4_file)
        umm_var_record = get_umm_var(
            nc_varinfo, nc_varinfo.get_variable('/precipitationCal')
        )

        # Ensure that the record adheres to the UMM-Var schema:
        self.assertTrue(self.is_valid_umm_var(umm_var_record))

        # Ensure that all expected keys are present:
        self.assertSetEqual(
            set(umm_var_record.keys()),
            {'Name', 'LongName', 'Definition', 'StandardName', 'DataType',
             'Dimensions', 'FillValues', 'Units', 'Scale', 'Offset',
             'ValidRanges', 'MetadataSpecification'}
        )

        # Ensure all data fields have expected values:
        self.assertTrue(
            is_dictionary_subset(
                {
                    'Name': 'precipitationCal',
                    'LongName': 'precipitationCal',
                    'Definition': 'Calibrated precipitation',
                    'StandardName': 'CF Conventions standard name',
                    'DataType': 'float64',
                    'Dimensions': [{
                        'Name': 'time',
                        'Size': 1,
                        'Type': 'TIME_DIMENSION'
                    }, {
                        'Name': 'lon',
                        'Size': 3600,
                        'Type': 'LONGITUDE_DIMENSION'
                    }, {
                        'Name': 'lat',
                        'Size': 1800,
                        'Type': 'LATITUDE_DIMENSION'
                    }],
                    'FillValues': [{
                        'Description': 'Extracted from _FillValue metadata attribute',
                        'Type': 'SCIENCE_FILLVALUE',
                        'Value': -9999.9
                    }],
                    'Units': 'mm/hr',
                    'Scale': 1.0,
                    'Offset': 0.0,
                    'ValidRanges': [{'Max': 1000, 'Min': 0}]
                },
                umm_var_record
            )
        )

        # Ensure the metadata specification has expected values, using a
        # regular expression for the schema version number:
        self.assertEqual(
            umm_var_record['MetadataSpecification']['Name'], 'UMM-Var'
        )
        self.assertRegex(
            umm_var_record['MetadataSpecification']['Version'],
            r'^\d+\.\d+\.\d+$'
        )
        self.assertRegex(
            umm_var_record['MetadataSpecification']['URL'],
            r'https://cdn.earthdata.nasa.gov/umm/variable/v\d+\.\d+\.\d+$'
        )

    def test_get_umm_var_absent_fields_removed(self):
        """ Ensure that a variable with minimal information populates the
            minimum fields required by the UMM-Var schema, and that any fields
            with None-type values are removed from the UMM-Var JSON.

            The full UMM-Var output isn't directly assessed as a single
            dictionary to avoid test brittleness with UMM-Var schema version
            numbers. Compulsory fields are Name, LongName, Definition and
            MetadataSpecification.

        """
        netcdf4_file = f'{self.tmp_dir}/input.nc4'
        with Dataset(netcdf4_file, 'w') as dataset:
            dataset.setncatts({'short_name': 'GPM_3IMERGHH-ish'})

            # Without a description, the full path of the variable will be used
            # as the UMM-Var Definition
            dataset.createVariable('precipitationUncal', float64)

        nc_varinfo = VarInfoFromNetCDF4(netcdf4_file)
        umm_var_record = get_umm_var(
            nc_varinfo, nc_varinfo.get_variable('/precipitationUncal')
        )

        # Ensure that the record adheres to the UMM-Var schema:
        self.assertTrue(self.is_valid_umm_var(umm_var_record))

        # Ensure that only the expected keys are present (and that None-type
        # values have been removed from the record):
        self.assertSetEqual(
            set(umm_var_record.keys()),
            {'Name', 'LongName', 'Definition', 'DataType',
             'MetadataSpecification'}
        )

        # Ensure that data fields have expected values:
        self.assertTrue(
            is_dictionary_subset(
                {
                    'Name': 'precipitationUncal',
                    'LongName': 'precipitationUncal',
                    'Definition': 'precipitationUncal',
                    'DataType': 'float64',
                },
                umm_var_record
            )
        )

        # Ensure the metadata specification has expected values, using a
        # regular expression for the schema version number:
        self.assertEqual(
            umm_var_record['MetadataSpecification']['Name'], 'UMM-Var'
        )
        self.assertRegex(
            umm_var_record['MetadataSpecification']['Version'],
            r'^\d+\.\d+\.\d+$'
        )
        self.assertRegex(
            umm_var_record['MetadataSpecification']['URL'],
            r'https://cdn.earthdata.nasa.gov/umm/variable/v\d+\.\d+\.\d+$'
        )

    def test_get_first_matched_attribute(self):
        """ Ensure the function returns the first matching attribute from the
            supplied list. Also ensure default values are returned when there
            is no matching attribute.

        """
        with self.subTest('No matching attribute returns default'):
            self.assertEqual(
                get_first_matched_attribute(
                    self.gpm_varinfo.get_variable('/Grid/lat'),
                    ['non-existent', 'attribute', 'list'], 'default value'
                ),
                'default value'
            )

        with self.subTest('No supplied default returns None as the default.'):
            self.assertIsNone(
                get_first_matched_attribute(
                    self.gpm_varinfo.get_variable('/Grid/lat'),
                    ['non-existent', 'attribute', 'list']
                )
            )

        with self.subTest('First matching attribute value returned.'):
            # This test establishes that a non-existent first attribute is
            # skipped and that, once the first matching attribute is found,
            # the second matching attribute is not returned.
            self.assertEqual(
                get_first_matched_attribute(
                    self.gpm_varinfo.get_variable('/Grid/lat'),
                    ['non-existent', 'units', 'standard_name']
                ),
                'degrees_north'
            )

    def test_get_dimensions(self):
        """ Ensure dimensions for a variable are identified and returned. """
        netcdf4_file = write_skeleton_netcdf4(self.tmp_dir)
        var_info = VarInfoFromNetCDF4(netcdf4_file)
        with self.subTest('Variable with dimensions returns all of them'):
            self.assertListEqual(
                get_dimensions(var_info, var_info.get_variable('/science1')),
                [{
                    'Name': 'time',
                    'Size': 1,
                    'Type': 'TIME_DIMENSION',
                }, {
                    'Name': 'lat',
                    'Size': 2,
                    'Type': 'LATITUDE_DIMENSION'
                }, {
                    'Name': 'lon',
                    'Size': 2,
                    'Type': 'LONGITUDE_DIMENSION'
                }]
            )

        with self.subTest('Variable with no dimensions returns None'):
            self.assertIsNone(
                get_dimensions(var_info, var_info.get_variable('/scalar1'))
            )

    def test_get_dimension_information(self):
        """ Ensure dimension information for the supported types can be
            extracted. Special handling is present for bounds dimensions that
            indicate the 2-element dimension for the bounds variable.

        """
        netcdf4_file = write_skeleton_netcdf4(self.tmp_dir)
        var_info = VarInfoFromNetCDF4(netcdf4_file)
        variable = var_info.get_variable('/science1')

        with self.subTest('Temporal dimension variable'):
            self.assertDictEqual(
                get_dimension_information(var_info, variable, '/time'),
                {
                    'Name': 'time',
                    'Size': 1,
                    'Type': 'TIME_DIMENSION'
                }
            )

        with self.subTest('Longitude dimension variable'):
            self.assertDictEqual(
                get_dimension_information(var_info, variable, '/lon'),
                {
                    'Name': 'lon',
                    'Size': 2,
                    'Type': 'LONGITUDE_DIMENSION'
                }
            )

        with self.subTest('Latitude dimension variable'):
            self.assertDictEqual(
                get_dimension_information(var_info, variable, '/lat'),
                {
                    'Name': 'lat',
                    'Size': 2,
                    'Type': 'LATITUDE_DIMENSION'
                }
            )

        with self.subTest('Other-type dimension variable'):
            # Uses M2I3NPASM from DMR, so lacks size information
            merra_variable = self.merra_varinfo.get_variable('/EPV')
            self.assertDictEqual(
                get_dimension_information(self.merra_varinfo, merra_variable,
                                          '/lev'),
                {
                    'Name': 'lev',
                    'Size': 'Varies',
                    'Type': 'OTHER'
                }
            )

        with self.subTest('Variable missing shape returns size "Varies"'):
            # Currently uses a VariableFromDmr because those do not yet have
            # shape information.
            atl03_variable = self.atl03_varinfo.get_variable(
                '/gt3r/bckgrd_atlas/bckgrd_counts'
            )
            self.assertDictEqual(
                get_dimension_information(self.atl03_varinfo, atl03_variable,
                                          '/gt3r/bckgrd_atlas/delta_time'),
                {
                    'Name': 'gt3r/bckgrd_atlas/delta_time',
                    'Size': 'Varies',
                    'Type': 'TIME_DIMENSION'
                }
            )

        with self.subTest('Bounds, 2-element dimension'):
            # Bounds variable dimensions, e.g., lat_bnds, have a non-variable
            # dimension, e.g., latv, which just indicates that the array has
            # 2-elements in that dimension.
            bounds_variable = self.gpm_varinfo.get_variable('/Grid/lat_bnds')
            self.assertDictEqual(
                get_dimension_information(self.gpm_varinfo, bounds_variable,
                                          '/Grid/latv'),
                {
                    'Name': 'Grid/latv',
                    'Size': 2,
                    'Type': 'OTHER'
                }
            )

        with self.subTest('Absent dimension'):
            # Typically a size-only dimension, without an accompanying variable
            # It is assumed that the list of dimensions associated with the
            # variable (as derived from the source granule) is correct, and
            # that the UMM-Var dimensions should track this dimension.
            # Note: This test uses a completely fictitious dimension to
            # replicate this condition due to a lack of a real-world example.
            gpm_variable = self.gpm_varinfo.get_variable('/Grid/precipitationCal')
            self.assertDictEqual(
                get_dimension_information(self.gpm_varinfo, gpm_variable,
                                          '/Grid/absent'),
                {
                    'Name': 'Grid/absent',
                    'Size': 'Varies',
                    'Type': 'OTHER'
                }
            )

    def test_get_dimension_size(self):
        """ Ensure the dimension size can be extracted from the locations that
            should be checked: the shape of the variable with the dimension,
            the shape of any 1-D dimension variable, or heuristic matching for
            bounds 2-element dimensions. The default value should be None.

        """
        netcdf4_file = write_skeleton_netcdf4(self.tmp_dir)
        var_info = VarInfoFromNetCDF4(netcdf4_file)

        # Overwrite the shape attribute of a variable to ensure tests with that
        # variable extract information from the dimension shape:
        shapeless_variable = var_info.get_variable('/group/science2')
        shapeless_variable.shape = None

        with self.subTest('Size obtained from the referring variable shape'):
            variable = var_info.get_variable('/science1')
            self.assertEqual(
                get_dimension_size(var_info, variable, '/time'), 1
            )

        with self.subTest('Size obtained from dimension variable shape, int'):
            lon_variable = var_info.get_variable('/lon')
            # Set shape property of 1-D dimension variable to be an integer:
            lon_variable.shape = 3

            self.assertEqual(
                get_dimension_size(var_info, shapeless_variable, '/lon'), 3
            )

        with self.subTest('Size obtained from dimension variable shape, tuple'):
            self.assertEqual(
                get_dimension_size(var_info, shapeless_variable, '/lat'), 2
            )

        with self.subTest('"Varies" obtained from bad type dimension variable shape'):
            lon_variable = var_info.get_variable('/lon')
            # Set shape property of 1-D dimension variable to something other
            # than a tuple or an integer:
            lon_variable.shape = 'This cannot be parsed'

            self.assertEqual(
                get_dimension_size(var_info, shapeless_variable, '/lon'),
                'Varies'
            )

        with self.subTest('Bounds 2-element size-only dimension return 2'):
            # This test currently uses input from a DMR file, as the
            # VariableFromDMR class does not derive shape information for any
            # variable - this guarantees skipping the first two conditions in
            # the function.
            bounds_variable = self.gpm_varinfo.get_variable('/Grid/lat_bnds')
            self.assertEqual(
                get_dimension_size(self.gpm_varinfo, bounds_variable,
                                   '/Grid/latv'),
                2
            )

        with self.subTest('Variable with no shape, no dimension shape returns "Varies"'):
            # This test currently uses input from a DMR file, as the
            # VariableFromDMR class does not derive shape information for any
            # variable - this guarantees skipping the first two conditions in
            # the function.
            gpm_variable = self.gpm_varinfo.get_variable('/Grid/precipitationCal')
            self.assertEqual(
                get_dimension_size(self.gpm_varinfo, gpm_variable, '/Grid/lon'),
                'Varies'
            )

    def test_get_valid_ranges(self):
        """ Ensure a ValidRangeType item can be constructed based on the
            metadata attributes of a variable. Only non-None values should be
            retained in the output dictionary, and if there are no metadata
            attributes indicating the valid range, there should be a return
            value of None.

        """
        with self.subTest('A valid_range returns ValidRangeType item'):
            valid_range_variable_tree = ET.fromstring(
                '<Float64 name="variable">'
                '  <Attribute name="valid_range" type="Float32">'
                '    <Value>-180</Value>'
                '    <Value>180</Value>'
                '  </Attribute>'
                '</Float64>'
            )
            variable = VariableFromDmr(valid_range_variable_tree,
                                       self.atl03_config, '', '/variable')

            self.assertListEqual(
                get_valid_ranges(variable),
                [{
                    'Min': -180,
                    'Max': 180
                }]
            )

        with self.subTest('valid_min and valid_max returns ValidRangeType item'):
            valid_min_max_variable_tree = ET.fromstring(
                '<Float64 name="variable_name">'
                '  <Attribute name="valid_max" type="Float32">'
                '    <Value>90</Value>'
                '  </Attribute>'
                '  <Attribute name="valid_min" type="Float32">'
                '    <Value>-90</Value>'
                '  </Attribute>'
                '</Float64>'
            )
            variable = VariableFromDmr(valid_min_max_variable_tree,
                                       self.atl03_config, '', '/variable')

            self.assertListEqual(
                get_valid_ranges(variable),
                [{
                    'Min': -90,
                    'Max': 90
                }]
            )

        with self.subTest('valid_min only returns ValidRangeType item'):
            valid_min_only_variable_tree = ET.fromstring(
                '<Float64 name="variable_name">'
                '  <Attribute name="valid_min" type="Float32">'
                '    <Value>-90</Value>'
                '  </Attribute>'
                '</Float64>'
            )
            variable = VariableFromDmr(valid_min_only_variable_tree,
                                       self.atl03_config, '', '/variable')

            self.assertListEqual(get_valid_ranges(variable), [{'Min': -90}])

        with self.subTest('valid_max only returns ValidRangeType item'):
            valid_max_only_variable_tree = ET.fromstring(
                '<Float64 name="variable_name">'
                '  <Attribute name="valid_max" type="Float32">'
                '    <Value>90</Value>'
                '  </Attribute>'
                '</Float64>'
            )
            variable = VariableFromDmr(valid_max_only_variable_tree,
                                       self.atl03_config, '', '/variable')

            self.assertListEqual(get_valid_ranges(variable), [{'Max': 90}])

        with self.subTest('Neither valid_min nor valid_max returns None'):
            no_range_variable_tree = ET.fromstring(
                '<Float64 name="variable_name">'
                '</Float64>'
            )
            variable = VariableFromDmr(no_range_variable_tree,
                                       self.atl03_config, '', '/variable')

            self.assertIsNone(get_valid_ranges(variable))

    def test_get_fill_values(self):
        """ Ensure that a variable with a _FillValue metadata attribute
            correctly returns a single element list of FillValueType elements.
            For a variable without a _FillValue attribute, None should be
            returned.

        """
        with self.subTest('Variable has _FillValue returns FillValueType item'):
            self.assertListEqual(
                get_fill_values(
                    self.atl03_varinfo.get_variable('/gt1r/geophys_corr/dem_flag')
                ),
                [{
                    'Value': 127,
                    'Type': 'SCIENCE_FILLVALUE',
                    'Description': 'Extracted from _FillValue metadata attribute'
                }]
            )

        with self.subTest('Variable with no _FillValue returns None'):
            self.assertIsNone(
                get_fill_values(
                    self.atl03_varinfo.get_variable('/ds_surf_type')
                )
            )

    def test_get_umm_var_dtype(self):
        """ Ensure that, for a UMM-Var compatible type, the input data type is
            returned. Otherwise the default is 'OTHER'.

        """
        with self.subTest('Variable type is compatible with UMM-Var options'):
            self.assertEqual(get_umm_var_dtype('int32'), 'int32')

        with self.subTest('Variable type is incompatible with UMM-Var options'):
            self.assertEqual(get_umm_var_dtype('non UMM-Var dtype'), 'OTHER')

    def test_get_metadata_specification(self):
        """ Ensure the expected MetadataSpecification object is returned.
            Version numbers are not explicitly hard-coded to avoid test
            brittleness.

        """
        metadata_specification = get_metadata_specification()
        self.assertSetEqual(set(metadata_specification.keys()),
                            {'URL', 'Name', 'Version'})

        self.assertEqual(metadata_specification['Name'], 'UMM-Var')
        self.assertRegex(metadata_specification['Version'], r'^\d+\.\d+\.\d+$')
        self.assertRegex(
            metadata_specification['URL'],
            r'https://cdn.earthdata.nasa.gov/umm/variable/v\d+\.\d+\.\d+$'
        )

    def test_get_json_serializable_value(self):
        """ Ensure that numpy floating and integer types are converted to
            native Python types that can be serialized as JSON. Non-numpy type
            inputs should be returned unchanged.

        """
        with self.subTest('Numpy integer'):
            serializable_value = get_json_serializable_value(int32(4321))
            self.assertEqual(serializable_value, 4321)
            self.assertIsInstance(serializable_value, int)

        with self.subTest('Numpy double'):
            serializable_value = get_json_serializable_value(float64(43.21))
            self.assertEqual(serializable_value, 43.21)
            self.assertIsInstance(serializable_value, float)

        with self.subTest('Non-numpy value passes through unchanged'):
            input_value = 'string value'
            self.assertEqual(get_json_serializable_value(input_value),
                             input_value)

    def test_export_umm_var_to_json(self):
        """ Ensure that a UMM-Var JSON object is correctly written out to a
            directory.

        """
        umm_var_record = {
            'Name': 'Grid/precipitationCal',
            'LongName': 'Grid/precipitationCal',
            'Definition': 'Grid/precipitationCal',
            'DataType': 'float32',
            'Dimensions': [
                {'Name': 'Grid/time', 'Size': 1, 'Type': 'TIME_DIMENSION'},
                {'Name': 'Grid/lon', 'Size': 3600, 'Type': 'LONGITUDE_DIMENSION'},
                {'Name': 'Grid/lat', 'Size': 1800, 'Type': 'LATITUDE_DIMENSION'}
            ],
            'Units': 'mm/hr',
            'FillValues': [{
                'Value': -9999.900390625,
                'Type': 'SCIENCE_FILLVALUE',
                'Description': 'Extracted from _FillValue metadata attribute'
            }],
            'MetadataSpecification': {
                'URL': 'https://cdn.earthdata.nasa.gov/umm/variable/v1.8.2',
                'Name': 'UMM-Var',
                'Version': '1.8.2'
            }
        }

        with self.subTest('Pre-existing directory contents are not clobbered.'):
            other_file_path = f'{self.tmp_dir}/other_file.txt'
            with open(other_file_path, 'w', encoding='utf-8') as file_handler:
                file_handler.write('test string')

            export_umm_var_to_json(umm_var_record, self.tmp_dir)

            # Ensure the record was written with all content:
            expected_output_path = f'{self.tmp_dir}/Grid_precipitationCal.json'
            self.assertTrue(exists(expected_output_path))

            with open(expected_output_path, 'r', encoding='utf-8') as file_handler:
                saved_output = json.load(file_handler)

            self.assertDictEqual(saved_output, umm_var_record)

            # Ensure the other directory contents remain:
            self.assertTrue(exists(other_file_path))

        with self.subTest('New directory is created.'):
            sub_directory = f'{self.tmp_dir}/umm_var_dir'
            export_umm_var_to_json(umm_var_record, sub_directory)

            # Ensure the record was written with all content:
            expected_output_path = f'{sub_directory}/Grid_precipitationCal.json'
            self.assertTrue(exists(expected_output_path))

            with open(expected_output_path, 'r', encoding='utf-8') as file_handler:
                saved_output = json.load(file_handler)

            self.assertDictEqual(saved_output, umm_var_record)

        with self.subTest('Specified directory is a file, raises exception.'):
            with self.assertRaises(InvalidExportDirectory):
                other_file_path = f'{self.tmp_dir}/other_file.txt'
                with open(other_file_path, 'w', encoding='utf-8') as file_handler:
                    file_handler.write('test string')

                export_umm_var_to_json(umm_var_record, other_file_path)

    def test_export_all_umm_var_to_json(self):
        """ Ensure all records in the list are written out to files. """
        umm_var_records = [{
            'Name': 'Grid/precipitationCal',
            'LongName': 'Grid/precipitationCal',
            'Definition': 'Grid/precipitationCal',
            'DataType': 'float32',
            'Dimensions': [
                {'Name': 'Grid/time', 'Size': 1, 'Type': 'TIME_DIMENSION'},
                {'Name': 'Grid/lon', 'Size': 3600, 'Type': 'LONGITUDE_DIMENSION'},
                {'Name': 'Grid/lat', 'Size': 1800, 'Type': 'LATITUDE_DIMENSION'}
            ],
            'Units': 'mm/hr',
            'FillValues': [{
                'Value': -9999.900390625,
                'Type': 'SCIENCE_FILLVALUE',
                'Description': 'Extracted from _FillValue metadata attribute'
            }],
            'MetadataSpecification': {
                'URL': 'https://cdn.earthdata.nasa.gov/umm/variable/v1.8.2',
                'Name': 'UMM-Var',
                'Version': '1.8.2'
            }
        }, {
            'Name': 'Grid/lon',
            'LongName': 'Grid/lon',
            'StandardName': 'longitude',
            'Definition': 'Grid/lon',
            'DataType': 'float32',
            'Dimensions': [
                {'Name': 'Grid/lon', 'Size': 3600, 'Type': 'LONGITUDE_DIMENSION'}
            ],
            'Units': 'degrees_east',
            'MetadataSpecification': {
                'URL': 'https://cdn.earthdata.nasa.gov/umm/variable/v1.8.2',
                'Name': 'UMM-Var',
                'Version': '1.8.2'
            }
        }]

        export_all_umm_var_to_json(umm_var_records, self.tmp_dir)

        expected_output_files = [
            f'{self.tmp_dir}/Grid_precipitationCal.json',
            f'{self.tmp_dir}/Grid_lon.json'
        ]

        for umm_var_index, expected_file in enumerate(expected_output_files):
            self.assertTrue(exists(expected_file))

            with open(expected_file, 'r', encoding='utf-8') as file_handler:
                saved_json = json.load(file_handler)

            self.assertDictEqual(saved_json, umm_var_records[umm_var_index])


    def _mock_requests(self, status=200, content='VFOO-EEDTEST'):
        '''
        Mock requests.put module and it's methods content and status.
        Return the mock object.
        '''
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = status
        mock_response.content = content
        return mock_response


    @patch('requests.put')
    def test_publish_umm_var(self, mock_requests_put):
        ''' Check if `publish_umm_var` returns the expected
            content for the mocked response.
        '''
        umm_var_dict = {'Name': 'Test', 
                        'MetadataSpecification':{
                            'URL': 'https://foo.gov/umm/variable/v1.8.2',
                            'Name': 'UMM-Var',
                            'Version': '1.8.2'}}
        
        # Set the mock_response with the `_mock_requests` object content method'
        mock_response = self._mock_requests('VFOO-EEDTEST')
        
        # Set the return_value of `mock_requests_put` to mock_response
        mock_requests_put.return_value = mock_response
        
        concept_id = 'C1256535511-EEDTEST'
        cmr_env = CMR_UAT
        token = 'foo'
        headers_umm_var = {
            'Content-type': 'application/vnd.nasa.cmr.umm+json;version='
            + f'{umm_var_dict["MetadataSpecification"]["Version"]}',
            'Authorization': f'Bearer {token}',
            'Accept': 'application/json'}
        url_endpoint = (cmr_env.replace('search', 'ingest') + 'collections/'
                    f'{concept_id}/variables/{umm_var_dict["Name"]}')
        
        response = publish_umm_var(concept_id, umm_var_dict, 'foo', cmr_env)
        
        # Check if `publish_umm_var` was called once with expected parameters
        mock_requests_put.assert_called_once_with(url_endpoint,
                                                  json=umm_var_dict,
                                                  headers=headers_umm_var,
                                                  timeout=10)
