from shutil import rmtree
from tempfile import mkdtemp
from unittest import TestCase
import re

from varinfo import VarInfoFromDmr, VarInfoFromNetCDF4
from varinfo.exceptions import (InvalidConfigFileFormatError,
                                MissingConfigurationFileError)
from tests.utilities import (netcdf4_global_attributes, write_dmr,
                             write_skeleton_netcdf4)


class TestVarInfoFromDmr(TestCase):
    """ A class for testing the `VarInfo` class with a `.dmr` URL. """

    @classmethod
    def setUpClass(cls):
        """ Set up properties of the class that do not need to be reset between
            tests.

        """
        cls.config_file = 'tests/unit/data/test_config.json'
        cls.namespace = 'namespace_string'
        cls.sample_config = 'config/0.0.1/sample_config_0.0.1.json'
        cls.mock_geographic_dmr = 'tests/unit/data/mock_geographic.dmr'
        cls.mock_dmr_two = 'tests/unit/data/mock_dataset_two.dmr'
        cls.mock_geo_and_projected_dmr = 'tests/unit/data/mock_geo_and_projected.dmr'
        cls.dimension_grouping_dmr = 'tests/unit/data/dimension_grouping.dmr'

    def setUp(self):
        self.output_dir = mkdtemp()

    def tearDown(self):
        rmtree(self.output_dir)

    def test_var_info_short_name(self):
        """ Ensure an instance of the VarInfo class correctly identifies a
            collection short name if it is stored as a metadata attribute in
            any of the prescribed locations.

            Alternatively, ensure that the optional `short_name` argument for
            the `VarInfo` classes will be used in the absence of metadata
            attributes. This supplied argument should also take precedence over
            metadata supplied values.

        """
        short_name = 'ATL03'

        hdf5_global = (
            '  <Group name="HDF5_GLOBAL">'
            '    <Attribute name="short_name">'
            f'      <Value>{short_name}</Value>'
            '    </Attribute>'
            '  </Group>'
        )

        nc_global = (
            '  <Group name="NC_GLOBAL">'
            '    <Attribute name="short_name">'
            f'      <Value>{short_name}</Value>'
            '    </Attribute>'
            '  </Group>'
        )

        metadata_dataset_lower_case = (
            '  <Group name="Metadata">'
            '    <Group name="DatasetIdentification">'
            '      <Attribute name="shortName">'
            f'        <Value>{short_name}</Value>'
            '      </Attribute>'
            '    </Group>'
            '  </Group>'
        )

        metadata_dataset_upper_case = (
            '  <Group name="METADATA">'
            '    <Group name="DatasetIdentification">'
            '      <Attribute name="shortName">'
            f'        <Value>{short_name}</Value>'
            '      </Attribute>'
            '    </Group>'
            '  </Group>'
        )

        metadata_series_lower_case = (
            '  <Group name="Metadata">'
            '    <Group name="SeriesIdentification">'
            '      <Attribute name="shortName">'
            f'        <Value>{short_name}</Value>'
            '      </Attribute>'
            '    </Group>'
            '  </Group>'
        )

        metadata_series_upper_case = (
            '  <Group name="METADATA">'
            '    <Group name="SeriesIdentification">'
            '      <Attribute name="shortName">'
            f'        <Value>{short_name}</Value>'
            '      </Attribute>'
            '    </Group>'
            '  </Group>'
        )

        root_group_short_name = (
            '  <Attribute name="short_name">'
            f'    <Value>{short_name}</Value>'
            '  </Attribute>'
        )

        test_attributes = [hdf5_global, nc_global, metadata_dataset_lower_case,
                           metadata_dataset_upper_case,
                           metadata_series_lower_case,
                           metadata_series_upper_case, root_group_short_name]

        for global_attributes in test_attributes:
            with self.subTest(global_attributes):
                mock_dmr = (f'<Dataset xmlns="{self.namespace}">'
                            f'{global_attributes}'
                            '</Dataset>')
                dmr_path = write_dmr(self.output_dir, mock_dmr)

                dataset = VarInfoFromDmr(dmr_path,
                                         config_file=self.sample_config)

                self.assertEqual(dataset.short_name, short_name)

        with self.subTest('No short name'):
            mock_dmr = (f'<Dataset xmlns="{self.namespace}"></Dataset>')
            dmr_path = write_dmr(self.output_dir, mock_dmr)

            dataset = VarInfoFromDmr(dmr_path,
                                     config_file=self.sample_config)

            self.assertEqual(dataset.short_name, None)

        with self.subTest('No short name in metadata, but given in call'):
            mock_dmr = (f'<Dataset xmlns="{self.namespace}"></Dataset>')
            dmr_path = write_dmr(self.output_dir, mock_dmr)

            dataset = VarInfoFromDmr(dmr_path, short_name='ATL03',
                                     config_file=self.sample_config)

            self.assertEqual(dataset.short_name, 'ATL03')

        with self.subTest('Short name given in call overrides metadata'):
            mock_dmr = (f'<Dataset xmlns="{self.namespace}">'
                        '  <Attribute name="short_name">'
                        f'    <Value>ATL03</Value>'
                        '  </Attribute>'
                        '</Dataset>')
            dmr_path = write_dmr(self.output_dir, mock_dmr)

            dataset = VarInfoFromDmr(dmr_path, short_name='ATL08',
                                     config_file=self.sample_config)
            self.assertEqual(dataset.short_name, 'ATL08')

    def test_var_info_mission(self):
        """ Ensure VarInfo can identify the correct mission given a collection
            short name, or absence of one.

        """
        test_args = [['ATL03', 'ICESat2'],
                     ['GEDI_L1A', 'GEDI'],
                     ['GEDI01_A', 'GEDI'],
                     ['SPL3FTP', 'SMAP'],
                     ['VIIRS_NPP-OSPO-L2P-V2.3', 'VIIRS_PO'],
                     ['RANDOMSN', None],
                     [None, None]]

        for short_name, expected_mission in test_args:
            with self.subTest(short_name):
                mock_dmr = (f'<Dataset xmlns="{self.namespace}">'
                            '  <Attribute name="short_name">'
                            f'    <Value>{short_name}</Value>'
                            '  </Attribute>'
                            '</Dataset>')
                dmr_path = write_dmr(self.output_dir, mock_dmr)

                dataset = VarInfoFromDmr(dmr_path,
                                         config_file=self.sample_config)

                self.assertEqual(dataset.mission, expected_mission)

    def test_var_info_instantiation_no_config_file(self):
        """ Ensure VarInfo can instantiate when no configuration file is given.
            This will mean the mission cannot be determined for the VarInfo
            class and that the associated CFConfig instance will be mostly a
            no-op.

        """
        dataset = VarInfoFromDmr(self.mock_geographic_dmr)

        self.assertIsNone(dataset.short_name)
        self.assertIsNone(dataset.mission)
        self.assertSetEqual(set(dataset.variables.keys()),
                            {'/ancillary_one', '/dimension_one', '/latitude',
                             '/longitude', '/metadata_variable',
                             '/science_variable', '/subset_one'})

    def test_var_info_missing_configuration_file(self):
        """ Ensure a MissingConfigurationFileError is raised when a path to a
            non-existent configuration file is specified.

        """
        with self.assertRaises(MissingConfigurationFileError):
            VarInfoFromDmr('tests/unit/data/ATL03_example.dmr',
                           short_name='ATL03',
                           config_file='bad_file_path.json')

    def test_var_info_invalid_configuration_file_format(self):
        """ Ensure an InvalidConfigFileFormatError is raised when the specified
            configuration file path is not a non-JSON file.

        """
        with self.assertRaises(InvalidConfigFileFormatError):
            VarInfoFromDmr('tests/unit/data/ATL03_example.dmr',
                           short_name='ATL03',
                           config_file='tests/unit/data/ATL03_example.dmr')

    def test_var_info_instantiation_no_augmentation(self):
        """ Ensure VarInfo instantiates correctly, creating records of all the
            variables in the granule, and correctly deciding if they are
            science variables, metadata or references. This test uses a mission
            and short name that do not have any CF overrides or supplements.

        """
        dataset = VarInfoFromDmr(self.mock_geographic_dmr,
                                 config_file=self.config_file)

        self.assertEqual(dataset.short_name, 'ATL03')
        self.assertEqual(dataset.mission, 'ICESat2')
        self.assertEqual(
            dataset.global_attributes,
            {'METADATA': {'DatasetIdentification': {'shortName': 'ATL03'}}}
        )

        self.assertEqual(set(dataset.variables.keys()),
                         {'/ancillary_one', '/dimension_one', '/latitude',
                          '/longitude', '/metadata_variable',
                          '/science_variable', '/subset_one'})
        self.assertEqual(dataset.references, {'/ancillary_one',
                                              '/dimension_one', '/latitude',
                                              '/longitude', '/subset_one'})

    def test_var_info_instantiation_cf_augmentation(self):
        """ Ensure VarInfo instantiates correcly, using a missions that has
            overrides and supplements in the CFConfig class.

        """
        dataset = VarInfoFromDmr(self.mock_dmr_two,
                                 config_file=self.config_file)

        expected_global_attributes = {
            'METADATA': {'DatasetIdentification': {'shortName': 'FAKE99'}},
            'global_override': 'GLOBAL',
            'fakesat_global_supplement': 'fakesat value'
        }
        self.assertEqual(dataset.global_attributes, expected_global_attributes)
        self.assertEqual(set(dataset.variables.keys()),
                         {'/science/latitude', '/science/longitude',
                          '/required_group/has_no_coordinates',
                          '/science/lat_bnds', '/science/interesting_thing',
                          '/exclude_one/has_coordinates'})
        self.assertEqual(set(dataset.references), {'/science/latitude',
                                                   '/science/longitude'})

    def test_var_info_from_dmr_instantiation_nested_attributes(self):
        """ Ensure VarInfoFromDmr can successfully extract global attributes
            from the `.dmr` if they are stored in an Attribute container with
            name "HDF5_GLOBALS".

        """
        history = '2021-06-24T01:02:03+00:00 Service v0.0.1'
        mock_dmr = (
            f'<Dataset xmlns="{self.namespace}">'
            '  <Attribute name="HDF5_GLOBAL" type="Container">'
            '    <Attribute name="short_name" type="String">'
            '      <Value>FAKESAT1</Value>'
            '    </Attribute>'
            '    <Attribute name="history" type="String">'
            f'      <Value>{history}</Value>'
            '    </Attribute>'
            '    <Attribute name="numeric_attribute" type="Float64">'
            '      <Value>-90.0</Value>'
            '    </Attribute>'
            '  </Attribute>'
            '</Dataset>'
        )
        dmr_path = write_dmr(self.output_dir, mock_dmr)
        dataset = VarInfoFromDmr(dmr_path, config_file=self.config_file)

        expected_globals = {'history': history,
                            'numeric_attribute': -90.0,
                            'short_name': 'FAKESAT1'}
        self.assertDictEqual(expected_globals, dataset.global_attributes)

    def test_var_info_get_all_variables(self):
        """ Ensure all variables from the input are returned, regardless of
            whether they are science variables or metadata variables. This will
            also include any variables that are considered excluded science
            variables.

        """
        dataset = VarInfoFromDmr(self.mock_dmr_two,
                                 config_file=self.config_file)

        expected_variables = {'/science/interesting_thing',
                              '/required_group/has_no_coordinates',
                              '/exclude_one/has_coordinates',
                              '/science/lat_bnds',
                              '/science/latitude',
                              '/science/longitude'}

        self.assertSetEqual(dataset.get_all_variables(),
                            expected_variables)

    def test_var_info_get_science_variables(self):
        """ Ensure the correct set of science variables is returned. This
            should account for excluded science variables defined in the
            associated instance of the `CFConfig` class.

        """
        dataset = VarInfoFromDmr(self.mock_dmr_two,
                                 config_file=self.config_file)

        science_variables = dataset.get_science_variables()
        self.assertEqual(science_variables, {'/science/interesting_thing'})

    def test_var_info_get_metadata_variables(self):
        """ Ensure the correct set of metadata variables (those without
            coordinate references) is returned. This should exclude variables
            that are also referred to by others via the metadata such as the
            coordinates attribute.

            This set should also include science variables that are explicitly
            excluded by the `CFConfig` instance.

        """
        dataset = VarInfoFromDmr(self.mock_dmr_two,
                                 config_file=self.config_file)

        metadata_variables = dataset.get_metadata_variables()
        self.assertEqual(metadata_variables,
                         {'/required_group/has_no_coordinates',
                          '/exclude_one/has_coordinates', '/science/lat_bnds'})

    def test_var_info_get_required_variables(self):
        """ Ensure a full list of variables is returned when the VarInfo
            class is asked for those variables required to make a viable output
            granule. This should recursively search the references of all
            requested variables, to also include supporting variables such as
            coordinates, dimensions, ancillary_variables and
            subset_control_variables.

        """
        dataset = VarInfoFromDmr(self.mock_dmr_two,
                                 config_file=self.config_file)

        with self.subTest('All references to other variables are retrieved'):
            required_variables = dataset.get_required_variables(
                {'/science/interesting_thing'}
            )
            self.assertSetEqual(
                required_variables,
                {'/required_group/has_no_coordinates',
                 '/science/interesting_thing',
                 '/science/latitude',
                 '/science/longitude'}
            )

        with self.subTest('Non-variable dimensions are not returned'):
            self.assertSetEqual(
                dataset.get_required_variables({'/science/lat_bnds'}),
                {'/science/lat_bnds', '/science/latitude',
                 '/required_group/has_no_coordinates'}
            )

    def test_var_info_variable_is_excluded(self):
        """ Ensure the a variable is correctly identified as being excluded or
            not, including when there are not exclusions for the collection.

        """
        variable = 'variable_name'
        test_args = [['No exclusions', '', variable, False],
                     ['Not excluded', 'not_var', variable, False],
                     ['Excluded', 'var', variable, True]]

        for description, pattern, variable_name, expected_result in test_args:
            with self.subTest(description):
                re_pattern = re.compile(pattern)
                result = VarInfoFromDmr.variable_is_excluded(variable_name,
                                                             re_pattern)

                self.assertEqual(result, expected_result)

    def test_exclude_fake_dimensions(self):
        """ Ensure a set of required variables will not include any dimension
            generated by OPeNDAP, that does not actually exist in a granule.
            Only variables with names like FakeDim0, FakeDim1, etc should be
            removed.

        """
        input_variables = {'/science_variable', '/FakeDim0', '/other_science',
                           '/FakeDim1234', '/nested/FakeDim0'}

        required_variables = VarInfoFromDmr.exclude_fake_dimensions(
            input_variables
        )

        self.assertEqual(required_variables,
                         {'/science_variable', '/other_science'})

    def test_get_variable(self):
        """ Ensure a variable, both with or without, coordinates can be
            retrieved. In the case that a non-existent variable is requested,
            ensure `None` is returned.

        """
        dataset = VarInfoFromDmr(self.mock_dmr_two,
                                 config_file=self.config_file)

        with self.subTest('A variable with coordinates'):
            science_variable = dataset.get_variable('/science/interesting_thing')
            self.assertIsNotNone(science_variable)
            self.assertEqual(science_variable,
                             dataset.variables['/science/interesting_thing'])

        with self.subTest('A metadata variable'):
            metadata_variable = dataset.get_variable('/required_group/has_no_coordinates')
            self.assertIsNotNone(metadata_variable)
            self.assertEqual(metadata_variable,
                             dataset.variables['/required_group/has_no_coordinates'])

        with self.subTest('A non existent variable returns `None`'):
            self.assertIsNone(dataset.get_variable('/non/existent/variable'))

    def test_get_required_dimensions(self):
        """ Ensure all dimensions, that are themselves variables, associated
            with the specified variables are returned. Dimensions that are
            only used to specify an array size in one dimension, and do not
            have an associated variable, will not be returned.

        """
        mock_dmr = (f'<Dataset xmlns="{self.namespace}">'
                    '  <Attribute name="short_name">'
                    '    <Value>FAKE123A</Value>'
                    '  </Attribute>'
                    '  <Dimension name="latitude" size="1800"/>'
                    '  <Dimension name="longitude" size="3600"/>'
                    '  <Float64 name="science_one">'
                    '    <Dim name="/latitude"/>'
                    '  </Float64>'
                    '  <Float64 name="science_two">'
                    '    <Dim name="/longitude"/>'
                    '  </Float64>'
                    '  <Float64 name="science_three">'
                    '  </Float64>'
                    '  <Float64 name="longitude">'
                    '  </Float64>'
                    '  <Float64 name="latitude">'
                    '  </Float64>'
                    '  <Float64 name="lat_bnds">'
                    '    <Dim name="latv" size="2"/>'
                    '    <Dim name="latitude" size="1800"/>'
                    '  </Float64>'
                    '</Dataset>')

        dmr_path = write_dmr(self.output_dir, mock_dmr)
        dataset = VarInfoFromDmr(dmr_path, config_file=self.config_file)

        with self.subTest('All dimensions are retrieved'):
            self.assertSetEqual(
                dataset.get_required_dimensions({'/science_one', '/science_two'}),
                {'/latitude', '/longitude'}
            )

        with self.subTest('A variable with no dimensions returns an empty set'):
            self.assertSetEqual(dataset.get_required_dimensions({'/science_three'}),
                                set())

        with self.subTest('A non-existent variable returns an empty set'):
            self.assertSetEqual(dataset.get_required_dimensions({'/science_four'}),
                                set())

        with self.subTest('Non-variable dimensions are not returned'):
            self.assertSetEqual(dataset.get_required_dimensions({'/lat_bnds'}),
                                {'/latitude'})

    def test_get_spatial_dimensions(self):
        """ Ensure all horizontal spatial dimensions are returned, both
            geographic and projected.

        """
        dataset = VarInfoFromDmr(self.mock_geo_and_projected_dmr,
                                 config_file=self.config_file)

        with self.subTest('All horizontal spatial variables are returned'):
            self.assertSetEqual(
                dataset.get_spatial_dimensions({'/science_one',
                                                '/science_two'}),
                {'/latitude', '/longitude', '/x', '/y'}
            )

        with self.subTest('A variable with no dimensions is handled'):
            self.assertSetEqual(
                dataset.get_spatial_dimensions({'/science_three'}),
                set()
            )

        with self.subTest('A misnamed variable is handled'):
            self.assertSetEqual(
                dataset.get_spatial_dimensions({'/science_one', '/science_five'}),
                {'/latitude', '/longitude'}
            )

        with self.subTest('A misnamed dimension is handled'):
            self.assertSetEqual(
                dataset.get_spatial_dimensions({'/science_two', '/science_four'}),
                {'/x', '/y'}
            )

    def test_get_geographic_spatial_dimensions(self):
        """ Ensure only geographic spatial dimensions are returned and, if a
            variable or dimension is misnamed, the method will not cause an
            error.

        """
        dataset = VarInfoFromDmr(self.mock_geo_and_projected_dmr,
                                 config_file=self.config_file)

        with self.subTest('All (and only) geographic variables are returned'):
            self.assertSetEqual(
                dataset.get_geographic_spatial_dimensions({'/science_one',
                                                           '/science_two'}),
                {'/latitude', '/longitude'}
            )

        with self.subTest('A variable with no dimensions is handled'):
            self.assertSetEqual(
                dataset.get_geographic_spatial_dimensions({'/science_three'}),
                set()
            )

        with self.subTest('A misnamed variable is handled'):
            self.assertSetEqual(
                dataset.get_geographic_spatial_dimensions({'/science_one',
                                                           '/science_five'}),
                {'/latitude', '/longitude'}
            )

        with self.subTest('A misnamed dimension is handled'):
            self.assertSetEqual(
                dataset.get_geographic_spatial_dimensions({'/science_one',
                                                           '/science_four'}),
                {'/latitude', '/longitude'}
            )

    def test_get_projected_spatial_dimensions(self):
        """ Ensure only projected geographic spatial dimensions are returned
            and, of a variable or dimension is misnamed, the method will not
            cause an error.

        """
        dataset = VarInfoFromDmr(self.mock_geo_and_projected_dmr,
                                 config_file=self.config_file)

        with self.subTest('All (and only) projected dimension variables are returned'):
            self.assertSetEqual(
                dataset.get_projected_spatial_dimensions({'/science_one',
                                                           '/science_two'}),
                {'/x', '/y'}
            )

        with self.subTest('A variable with no dimensions is handled'):
            self.assertSetEqual(
                dataset.get_projected_spatial_dimensions({'/science_three'}),
                set()
            )

        with self.subTest('A misnamed variable is handled'):
            self.assertSetEqual(
                dataset.get_projected_spatial_dimensions({'/science_two',
                                                          '/science_five'}),
                {'/x', '/y'}
            )

        with self.subTest('A misnamed dimension is handled'):
            self.assertSetEqual(
                dataset.get_projected_spatial_dimensions({'/science_two',
                                                          '/science_four'}),
                {'/x', '/y'}
            )

    def test_get_temporal_dimensions(self):
        """ Ensure only temporal dimensions are returned, and if a variable or
            dimension is misnamed, the method will not cause an error.

        """
        mock_dmr = (f'<Dataset xmlns="{self.namespace}">'
                    '  <Attribute name="short_name">'
                    '    <Value>FAKE123A</Value>'
                    '  </Attribute>'
                    '    <Float64 name="science_one">'
                    '      <Dim name="/latitude"/>'
                    '      <Dim name="/longitude"/>'
                    '      <Dim name="/time"/>'
                    '    </Float64>'
                    '    <Float64 name="science_two">'
                    '      <Dim name="x"/>'
                    '      <Dim name="y"/>'
                    '    </Float64>'
                    '    <Float64 name="science_three">'
                    '    </Float64>'
                    '    <Float64 name="science_four">'
                    '      <Dim name="non-existent"/>'
                    '    </Float64>'
                    '    <Int32 name="time">'
                    '      <Attribute name="units" type="String">'
                    '        <Value>minutes since 1980-01-02 00:30:00 </Value>'
                    '      </Attribute>'
                    '    </Int32>'
                    '    <Float64 name="latitude">'
                    '      <Attribute name="units" type="String">'
                    '        <Value>degrees_north</Value>'
                    '      </Attribute>'
                    '    </Float64>'
                    '    <Float64 name="longitude">'
                    '      <Attribute name="units" type="String">'
                    '        <Value>degrees_east</Value>'
                    '      </Attribute>'
                    '    </Float64>'
                    '    <Float64 name="x">'
                    '      <Attribute name="units" type="String">'
                    '        <Value>m</Value>'
                    '      </Attribute>'
                    '    </Float64>'
                    '    <Float64 name="y">'
                    '      <Attribute name="units" type="String">'
                    '        <Value>m</Value>'
                    '      </Attribute>'
                    '    </Float64>'
                    '</Dataset>')

        dmr_path = write_dmr(self.output_dir, mock_dmr)
        dataset = VarInfoFromDmr(dmr_path, config_file=self.config_file)

        with self.subTest('All (and only) temporal variables are returned'):
            self.assertSetEqual(
                dataset.get_temporal_dimensions({'/science_one', '/science_two'}),
                {'/time'}
            )

        with self.subTest('A variable with no dimensions is handled'):
            self.assertSetEqual(
                dataset.get_temporal_dimensions({'/science_three'}),
                set()
            )

        with self.subTest('A misnamed variable is handled'):
            self.assertSetEqual(
                dataset.get_temporal_dimensions({'/science_one', '/science_five'}),
                {'/time'}
            )

        with self.subTest('A misnamed dimension is handled'):
            self.assertSetEqual(
                dataset.get_temporal_dimensions({'/science_one', '/science_four'}),
                {'/time'}
            )

    def test_get_variables_with_dimensions(self):
        """ Ensure that all variables that use the listed dimensions are
            retrieved. This should include variables for which the listed
            dimensions are both the full set or just a subset of their total
            dimensions, e.g., a variable with dimensions (time, y, x) will be
            returned when a request names only `{'/y', '/x'}`, as will a
            variable with only those dimensions.

        """
        dataset = VarInfoFromDmr(self.mock_geo_and_projected_dmr,
                                 config_file=self.config_file)

        with self.subTest('Only geographically gridded variables are retrieved'):
            self.assertSetEqual(
                dataset.get_variables_with_dimensions({'/latitude', '/longitude'}),
                {'/science_one'}
            )

        with self.subTest('Only projection gridded variables are retrieved'):
            self.assertSetEqual(
                dataset.get_variables_with_dimensions({'/x', '/y'}),
                {'/science_two'}
            )

        with self.subTest('Subsets of dimensions are identified'):
            self.assertSetEqual(
                dataset.get_variables_with_dimensions({'/latitude'}),
                {'/science_one', '/latitude'}
            )

    def test_group_variables_by_dimensions(self):
        """ Ensure all variables are grouped according to their dimensions. """
        dataset = VarInfoFromDmr(self.dimension_grouping_dmr,
                                 config_file=self.config_file)

        expected_groups = {
            ('/time', '/latitude', '/longitude'): {'/science_one',
                                                   '/science_two'},
            ('/latitude', '/longitude'): {'/science_three', },
            ('/longitude', '/latitude'): {'/science_four', },
            ('/latitude', ): {'/latitude', },
            ('/longitude', ): {'/longitude', },
            ('/time', ): {'/time', }
        }

        self.assertDictEqual(dataset.group_variables_by_dimensions(),
                             expected_groups)

    def test_group_variables_by_horizontal_dimensions(self):
        """ Ensure all variables are grouped according to their horizontal
            spatial dimensions. Order should be considered, though, so the
            same dimensions in a different order are not grouped together.

        """
        dataset = VarInfoFromDmr(self.dimension_grouping_dmr,
                                 config_file=self.config_file)

        expected_groups = {
            ('/latitude', '/longitude'): {'/science_one', '/science_two',
                                          '/science_three'},
            ('/longitude', '/latitude'): {'/science_four', },
            ('/latitude', ): {'/latitude', },
            ('/longitude', ): {'/longitude', },
            tuple(): {'/time', }
        }

        self.assertDictEqual(
            dataset.group_variables_by_horizontal_dimensions(),
            expected_groups
        )

    def test_var_info_netcdf4(self):
        """ Ensure a NetCDF-4 file can be parsed by the `VarInfoFromNetCDF4`
            class, with the expected results.

        """
        netcdf4_path = write_skeleton_netcdf4(self.output_dir)
        dataset = VarInfoFromNetCDF4(netcdf4_path,
                                     config_file=self.config_file)

        self.assertSetEqual(dataset.get_science_variables(),
                            {'/science1', '/group/science2'})

        self.assertSetEqual(dataset.get_metadata_variables(),
                            {'/scalar1', '/group/scalar2'})

        self.assertDictEqual(dataset.global_attributes,
                             netcdf4_global_attributes)
