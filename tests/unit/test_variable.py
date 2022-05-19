from unittest import TestCase
import xml.etree.ElementTree as ET

from netCDF4 import Dataset
from numpy import float64

from varinfo import CFConfig
from varinfo import VariableFromDmr, VariableFromNetCDF4


class TestVariableFromDmr(TestCase):
    """ Tests for the `Variable` class using `xml.etree.ElementTree` input. """

    @classmethod
    def setUpClass(cls):
        """ Set up properties of the class that do not need to be reset between
            tests.

        """
        cls.config_file = 'tests/unit/data/test_config.yml'
        cls.fakesat_config = CFConfig('FakeSat', 'FAKE99',
                                      config_file=cls.config_file)
        cls.namespace = 'namespace_string'
        cls.dmr_variable = ET.fromstring(
            f'<{cls.namespace}Float64 name="variable">'
            f'  <{cls.namespace}Dim name="first_dimension" />'
            f'  <{cls.namespace}Dim name="second_dimension" />'
            f'  <{cls.namespace}Attribute name="ancillary_variables" type="String">'
            f'    <{cls.namespace}Value>/ancillary_data/epoch</{cls.namespace}Value>'
            f'  </{cls.namespace}Attribute>'
            f'  <{cls.namespace}Attribute name="coordinates" type="String">'
            f'    <{cls.namespace}Value>latitude, longitude</{cls.namespace}Value>'
            f'  </{cls.namespace}Attribute>'
            f'  <{cls.namespace}Attribute name="subset_control_variables" type="String">'
            f'    <{cls.namespace}Value>begin count</{cls.namespace}Value>'
            f'  </{cls.namespace}Attribute>'
            f'  <{cls.namespace}Attribute name="units" type="String">'
            f'    <{cls.namespace}Value>m</{cls.namespace}Value>'
            f'  </{cls.namespace}Attribute>'
            f'</{cls.namespace}Float64>'
        )
        cls.dmr_variable_path = '/group/variable'
        cls.longitude_variable_string = (
            f'<{cls.namespace}Float64 name="variable_name">'
            f'  <{cls.namespace}Attribute name="units" type="String">'
            f'    <{cls.namespace}Value>degrees_east</{cls.namespace}Value>'
            f'  </{cls.namespace}Attribute>'
            f'</{cls.namespace}Float64>'
        )
        cls.latitude_variable_string = (
            f'<{cls.namespace}Float64 name="variable_name">'
            f'  <{cls.namespace}Attribute name="units" type="String">'
            f'    <{cls.namespace}Value>degrees_north</{cls.namespace}Value>'
            f'  </{cls.namespace}Attribute>'
            f'</{cls.namespace}Float64>'
        )
        cls.non_geo_variable_string = (
            f'<{cls.namespace}Float64 name="variable_name">'
            f'  <{cls.namespace}Attribute name="units" type="String">'
            f'    <{cls.namespace}Value>m</{cls.namespace}Value>'
            f'  </{cls.namespace}Attribute>'
            f'</{cls.namespace}Float64>'
        )
        cls.no_units_variable_string = (
            f'<{cls.namespace}Float64 name="variable_name">'
            f'</{cls.namespace}Float64>'
        )
        cls.valid_range_string = (
            f'<{cls.namespace}Float64 name="variable_name">'
            f'  <{cls.namespace}Attribute name="valid_range" type="Float32">'
            f'    <{cls.namespace}Value>-180</{cls.namespace}Value>'
            f'    <{cls.namespace}Value>180</{cls.namespace}Value>'
            f'  </{cls.namespace}Attribute>'
            f'</{cls.namespace}Float64>'
        )
        cls.valid_min_max_string = (
            f'<{cls.namespace}Float64 name="variable_name">'
            f'  <{cls.namespace}Attribute name="valid_max" type="Float32">'
            f'    <{cls.namespace}Value>90</{cls.namespace}Value>'
            f'  </{cls.namespace}Attribute>'
            f'  <{cls.namespace}Attribute name="valid_min" type="Float32">'
            f'    <{cls.namespace}Value>-90</{cls.namespace}Value>'
            f'  </{cls.namespace}Attribute>'
            f'</{cls.namespace}Float64>'
        )
        cls.valid_min_only_string = (
            f'<{cls.namespace}Float64 name="variable_name">'
            f'  <{cls.namespace}Attribute name="valid_min" type="Float32">'
            f'    <{cls.namespace}Value>-90</{cls.namespace}Value>'
            f'  </{cls.namespace}Attribute>'
            f'</{cls.namespace}Float64>'
        )
        cls.valid_max_only_string = (
            f'<{cls.namespace}Float64 name="variable_name">'
            f'  <{cls.namespace}Attribute name="valid_max" type="Float32">'
            f'    <{cls.namespace}Value>90</{cls.namespace}Value>'
            f'  </{cls.namespace}Attribute>'
            f'</{cls.namespace}Float64>'
        )
        cls.no_range_string = (
            f'<{cls.namespace}Float64 name="variable_name">'
            f'</{cls.namespace}Float64>'
        )

    def test_variable_instantiation(self):
        """ Ensure a `Variable` instance can be created from an input `.dmr`
            XML element instance.

            This variable should contain the correct metadata, including
            full path, coordinates, dimensions and subset control variables.
            The dimensions retrieved from the variable should be in the order
            they are contained in the variable XML, to ensure data requests
            can be made against the variable with index ranges specified.

            Any applicable attribute override or supplement for an absent
            metadata attribute should also be adopted as the value for that
            attribute, with overrides taking precedence over supplements.

        """
        variable = VariableFromDmr(self.dmr_variable, self.fakesat_config,
                                   self.namespace, self.dmr_variable_path)

        self.assertEqual(variable.full_name_path, '/group/variable')
        self.assertEqual(variable.group_path, '/group')
        self.assertEqual(variable.name, 'variable')
        self.assertSetEqual(set(variable.attributes.keys()),
                            {'ancillary_variables', 'coordinates',
                             'subset_control_variables', 'units',
                             'collection_override', 'collection_supplement',
                             'group_override', 'variable_override'})
        self.assertEqual(variable.attributes.get('units'), 'm')
        self.assertEqual(variable.dimensions, ['/group/first_dimension',
                                               '/group/second_dimension'])
        self.assertSetEqual(set(variable.references.keys()),
                            {'ancillary_variables', 'coordinates',
                             'subset_control_variables'})
        self.assertSetEqual(variable.references.get('ancillary_variables'),
                            {'/ancillary_data/epoch'})
        self.assertSetEqual(variable.references.get('coordinates'),
                            {'/group/latitude', '/group/longitude'})
        self.assertSetEqual(variable.references.get('subset_control_variables'),
                            {'/group/begin', '/group/count'})

    def test_variable_cf_override_reference(self):
        """ Ensure a CF-Convention attribute that contains references to other
            variables is overridden by the `CFConfig` value.

        """
        dmr_variable = ET.fromstring(
            f'<{self.namespace}Float64 name="science">'
            f'  <{self.namespace}Attribute name="coordinates" type="String">'
            f'    <{self.namespace}Value>latitude, longitude</{self.namespace}Value>'
            f'  </{self.namespace}Attribute>'
            f'</{self.namespace}Float64>'
        )

        variable = VariableFromDmr(dmr_variable, self.fakesat_config,
                                   self.namespace, '/coordinates_group/science')

        self.assertSetEqual(variable.references.get('coordinates'),
                            {'/coordinates_group/lat', '/coordinates_group/lon'})

    def test_variable_cf_override_non_reference(self):
        """ Ensure a metadata attribute that is not a reference to other
            variables is overridden by the `CFConfig` value.

        """
        dmr_variable = ET.fromstring(
            f'<{self.namespace}Float64 name="random">'
            f'  <{self.namespace}Attribute name="collection_override" type="String">'
            f'    <{self.namespace}Value>original value</{self.namespace}Value>'
            f'  </{self.namespace}Attribute>'
            f'</{self.namespace}Float64>'
        )

        variable = VariableFromDmr(dmr_variable, self.fakesat_config,
                                   self.namespace, '/random')

        self.assertEqual(variable.attributes.get('collection_override'),
                         'collection value')

    def test_variable_cf_supplement_non_reference(self):
        """ Ensure a metadata attribute is supplemented by the `CFConfig`. """
        dmr_variable = ET.fromstring(
            f'<{self.namespace}Float64 name="science">'
            f'  <{self.namespace}Attribute name="group_supplement" type="String">'
            f'    <{self.namespace}Value>initial_value</{self.namespace}Value>'
            f'  </{self.namespace}Attribute>'
            f'</{self.namespace}Float64>'
        )

        variable = VariableFromDmr(dmr_variable, self.fakesat_config,
                                   self.namespace, '/group4/science')

        self.assertEqual(variable.attributes.get('group_supplement'),
                         'initial_value, FAKE99 group4')

    def test_variable_cf_override_absent(self):
        """ Ensure a metadata attribute adopts the override value, even if the
            granule metadata originally omitted that attribute. The overriding
            value should be used, and any supplemental value should be ignored.

        """
        dmr_variable = ET.fromstring(
            f'<{self.namespace}Float64 name="absent_override">'
            f'</{self.namespace}Float64>'
        )

        variable = VariableFromDmr(dmr_variable, self.fakesat_config,
                                   self.namespace, '/absent_override')

        self.assertEqual(variable.attributes.get('extra_override'),
                         'overriding value')

    def test_variable_cf_supplement_absent(self):
        """ Ensure a metadata attribute adopts the override value, even if the
            granule metadata originally omitted that attribute.

        """
        dmr_variable = ET.fromstring(
            f'<{self.namespace}Float64 name="absent_supplement">'
            f'</{self.namespace}Float64>'
        )

        variable = VariableFromDmr(dmr_variable, self.fakesat_config,
                                   self.namespace, '/absent_supplement')

        self.assertEqual(variable.attributes.get('extra_supplement'),
                         'supplemental value')

    def test_variable_reference_qualification(self):
        """ Ensure different reference types (relative, absolute) are correctly
            qualified.

        """
        variable_name = '/gt1r/heights/bckgrd_mean'
        test_args = [['In parent group', '../latitude', '/gt1r/latitude'],
                     ['In granule root', '/latitude', '/latitude'],
                     ['Relative in same', './latitude', '/gt1r/heights/latitude'],
                     ['Basename only', 'latitude', '/gt1r/heights/latitude']]

        for description, coordinates, qualified_reference in test_args:
            with self.subTest(description):
                dmr_variable = ET.fromstring(
                    f'<{self.namespace}Float64 name="/gt1r_heights_bckgrd_mean">'
                    f'  <{self.namespace}Attribute name="coordinates" type="String">'
                    f'    <{self.namespace}Value>{coordinates}</{self.namespace}Value>'
                    f'  </{self.namespace}Attribute>'
                    f'</{self.namespace}Float64>'
                )
                variable = VariableFromDmr(dmr_variable, self.fakesat_config,
                                           self.namespace, variable_name)
                self.assertSetEqual(variable.references.get('coordinates'),
                                    {qualified_reference})

        root_var_name = '/global_aerosol_frac'
        test_args = [
            ['Root, relative with leading slash', '/global_lat', '/global_lat'],
            ['Root, relative needs leading slash', 'global_lat', '/global_lat']
        ]

        for description, coordinates, qualified_reference in test_args:
            with self.subTest(description):
                dmr_variable = ET.fromstring(
                    f'<{self.namespace}Float64 name="/global_aerosol_frac">'
                    f'  <{self.namespace}Attribute name="coordinates" type="String">'
                    f'    <{self.namespace}Value>{coordinates}</{self.namespace}Value>'
                    f'  </{self.namespace}Attribute>'
                    f'</{self.namespace}Float64>'
                )

                variable = VariableFromDmr(dmr_variable, self.fakesat_config,
                                           self.namespace, root_var_name)
                self.assertSetEqual(variable.references.get('coordinates'),
                                    {qualified_reference})

    def test_variable_get_references(self):
        """ Ensure that a set of absolute paths to all variables referred to
            in the ancillary_variables, coordinates, dimensions and
            subset_control_variables is returned.

        """
        with self.subTest('References include anc, coords, dims and subset'):
            variable = VariableFromDmr(self.dmr_variable, self.fakesat_config,
                                       self.namespace, self.dmr_variable_path)

            references = variable.get_references()

            self.assertSetEqual(references, {'/ancillary_data/epoch',
                                             '/group/latitude',
                                             '/group/longitude',
                                             '/group/first_dimension',
                                             '/group/second_dimension',
                                             '/group/begin',
                                             '/group/count'})

        with self.subTest('References include bounds and grid_mapping'):
            dmr_variable = ET.fromstring(
                f'<{self.namespace}Float64 name="/lat">'
                f'  <{self.namespace}Attribute name="bounds" type="String">'
                f'    <{self.namespace}Value>lat_bnds</{self.namespace}Value>'
                f'  </{self.namespace}Attribute>'
                f'  <{self.namespace}Attribute name="grid_mapping" type="String">'
                f'    <{self.namespace}Value>longitude_latitude</{self.namespace}Value>'
                f'  </{self.namespace}Attribute>'
                f'</{self.namespace}Float64>'
            )

            variable = VariableFromDmr(dmr_variable, self.fakesat_config,
                                       self.namespace, '/lat')

            self.assertSetEqual(variable.get_references(),
                                {'/lat_bnds', '/longitude_latitude'})

    def test_get_attribute_value(self):
        """ Ensure that a metadata attribute value is retrieved or, if that
            metadata attribute is not included in the variable, the default
            value is returned.

        """
        variable = VariableFromDmr(self.dmr_variable, self.fakesat_config,
                                   self.namespace, self.dmr_variable_path)

        default_value = 'default'

        with self.subTest('Present attribute returns expected value'):
            self.assertEqual(variable.get_attribute_value('units'), 'm')

        with self.subTest('Present attribute ignores default value'):
            self.assertEqual(
                variable.get_attribute_value('units', default_value), 'm'
            )

        with self.subTest('Absent attribute uses supplied default'):
            self.assertEqual(
                variable.get_attribute_value('missing', default_value),
                default_value
            )

        with self.subTest('Absent attribute with no default returns `None`'):
            self.assertIsNone(variable.get_attribute_value('missing'))

    def test_dmr_dimension_conversion(self):
        """ Ensure that if a dimension has a `.dmr` style name it is converted
            to the full path, for example:

            /group_one_group_two_variable

            becomes:

            /group_one/group_two/variable

        """
        variable_name = '/group_one/variable'

        dmr_variable = ET.fromstring(
            f'<{self.namespace}Float64 name="{variable_name}">'
            f'  <{self.namespace}Dim name="/group_one/delta_time" />'
            f'</{self.namespace}Float64>'
        )
        variable = VariableFromDmr(dmr_variable, self.fakesat_config,
                                   self.namespace, variable_name)

        self.assertEqual(variable.dimensions, ['/group_one/delta_time'])

    def test_is_temporal(self):
        """ Ensure that a dimension is correctly recognised as temporal. If
            there is not `units` metadata attribute, the variable is not
            identified as temporal (and also doesn't raise an exception).

        """
        with self.subTest('Temporal variable'):
            temporal_variable_xml = ET.fromstring(
                f'<{self.namespace}Float64 name="/group_one/time">'
                f'  <{self.namespace}Dim name="/group_one/time" />'
                f'  <{self.namespace}Attribute name="units" type="String">'
                f'    <{self.namespace}Value>'
                '        seconds since 1980-01-01T00:00:00'
                f'    </{self.namespace}Value>'
                f'  </{self.namespace}Attribute>'
                f'</{self.namespace}Float64>'
            )
            temporal_variable = VariableFromDmr(temporal_variable_xml,
                                                self.fakesat_config,
                                                self.namespace,
                                                '/group_one/time')

            self.assertTrue(temporal_variable.is_temporal())

        with self.subTest('Non-temporal variable'):
            non_temporal_variable_xml = ET.fromstring(
                f'<{self.namespace}Float64 name="/group_one/longitude">'
                f'  <{self.namespace}Dim name="/group_one/longitude" />'
                f'  <{self.namespace}Attribute name="units" type="String">'
                f'    <{self.namespace}Value>'
                '        degrees_east'
                f'    </{self.namespace}Value>'
                f'  </{self.namespace}Attribute>'
                f'</{self.namespace}Float64>'
            )
            non_temporal_variable = VariableFromDmr(non_temporal_variable_xml,
                                                    self.fakesat_config,
                                                    self.namespace,
                                                    '/group_one/longitude')

            self.assertFalse(non_temporal_variable.is_temporal())

        with self.subTest('Variable with no "units" metadata attribute'):
            unitless_variable_xml = ET.fromstring(
                f'<{self.namespace}Float64 name="/group_one/unitless">'
                f'  <{self.namespace}Dim name="/group_one/unitless" />'
                f'</{self.namespace}Float64>'
            )
            unitless_variable = VariableFromDmr(unitless_variable_xml,
                                                self.fakesat_config,
                                                self.namespace,
                                                '/group_one/unitless')

            self.assertFalse(unitless_variable.is_temporal())

    def test_is_geographic(self):
        """ Ensure that a dimension is correctly recognised as geographic, and
            that if there is no `units` metadata attribute, the variable is not
            identified as geographic.

        """

        test_args = [['Longitudinal variable', self.longitude_variable_string],
                     ['Latitudinal variable', self.latitude_variable_string]]

        for description, variable_string in test_args:
            with self.subTest(description):
                variable_tree = ET.fromstring(variable_string)
                variable = VariableFromDmr(variable_tree, self.fakesat_config,
                                           self.namespace, '/variable')

                self.assertTrue(variable.is_geographic())

        test_args = [['Non geographic variable', self.non_geo_variable_string],
                     ['No units in variable', self.no_units_variable_string]]

        for description, variable_string in test_args:
            with self.subTest(description):
                variable_tree = ET.fromstring(variable_string)
                variable = VariableFromDmr(variable_tree, self.fakesat_config,
                                           self.namespace, '/variable')

                self.assertFalse(variable.is_geographic())

    def test_is_latitude(self):
        """ Ensure that a varaible is correctly identified a latitudinal based
            on its `units` metadata attribute.

        """
        with self.subTest('Latitude variable'):
            variable_tree = ET.fromstring(self.latitude_variable_string)
            variable = VariableFromDmr(variable_tree, self.fakesat_config,
                                       self.namespace, '/variable')

            self.assertTrue(variable.is_latitude())

        test_args = [['Longitude variable', self.longitude_variable_string],
                     ['Non geographic variable', self.non_geo_variable_string],
                     ['No units variable', self.no_units_variable_string]]

        for description, variable_string in test_args:
            with self.subTest(description):
                variable_tree = ET.fromstring(variable_string)
                variable = VariableFromDmr(variable_tree, self.fakesat_config,
                                           self.namespace, '/variable')

                self.assertFalse(variable.is_latitude())

    def test_is_longitude(self):
        """ Ensure that a variable is correctly identified as longitudinal
            based on its `units` metadata attribute.

        """
        with self.subTest('Longitude variable'):
            variable_tree = ET.fromstring(self.longitude_variable_string)
            variable = VariableFromDmr(variable_tree, self.fakesat_config,
                                       self.namespace, '/variable')

            self.assertTrue(variable.is_longitude())

        test_args = [['Latitude variable', self.latitude_variable_string],
                     ['Non geographic variable', self.non_geo_variable_string],
                     ['No units variable', self.no_units_variable_string]]

        for description, variable_string in test_args:
            with self.subTest(description):
                variable_tree = ET.fromstring(variable_string)
                variable = VariableFromDmr(variable_tree, self.fakesat_config,
                                           self.namespace, '/variable')

                self.assertFalse(variable.is_longitude())

    def test_get_range(self):
        """ Ensure the correct valid range is returned based either on the
            `valid_range` metadata attribute or both the `valid_min` and
            `valid_max` metadata attributes. If insufficient metadata exists to
            define the range, then the method should return `None`.

        """
        test_args = [
            ['Variable with valid_range', self.valid_range_string, [-180.0, 180.0]],
            ['Variable with valid_min and valid_max', self.valid_min_max_string, [-90, 90]],
            ['Variable with only valid_min', self.valid_min_only_string, None],
            ['Variable with only valid_max', self.valid_max_only_string, None],
            ['Variable with no range metadata', self.no_range_string, None]
        ]

        for description, variable_string, expected_range in test_args:
            with self.subTest(description):
                variable_tree = ET.fromstring(variable_string)
                variable = VariableFromDmr(variable_tree, self.fakesat_config,
                                           self.namespace, '/variable')

                self.assertEqual(variable.get_range(), expected_range)

    def test_get_valid_min(self):
        """ Ensure the correct valid minimum of the variable range is extracted
            from a variable based on the `valid_min` metadata attribute, or if
            that is missing the first element of the `valid_range` metadata
            attribute. If neither are present, then `None` should be returned.

        """
        test_args = [
            ['Variable with valid_min and valid_max', self.valid_min_max_string, -90],
            ['Variable with valid_range', self.valid_range_string, -180.0],
            ['Variable with only valid_min', self.valid_min_only_string, -90],
            ['Variable with only valid_max', self.valid_max_only_string, None],
            ['Variable with no range metadata', self.no_range_string, None]
        ]

        for description, variable_string, expected_valid_min in test_args:
            with self.subTest(description):
                variable_tree = ET.fromstring(variable_string)
                variable = VariableFromDmr(variable_tree, self.fakesat_config,
                                           self.namespace, '/variable')

                self.assertEqual(variable.get_valid_min(), expected_valid_min)

    def test_get_valid_max(self):
        """ Ensure the correct valid maximum of the variable range is extracted
            from a variable based on the `valid_max` metadata attribute, or if
            that is missing the second element of the `valid_range` metadata
            attribute. If neither are present, then `None` should be returned.

        """
        test_args = [
            ['Variable with valid_min and valid_max', self.valid_min_max_string, 90],
            ['Variable with valid_range', self.valid_range_string, 180.0],
            ['Variable with only valid_min', self.valid_min_only_string, None],
            ['Variable with only valid_max', self.valid_max_only_string, 90],
            ['Variable with no range metadata', self.no_range_string, None]
        ]

        for description, variable_string, expected_valid_max in test_args:
            with self.subTest(description):
                variable_tree = ET.fromstring(variable_string)
                variable = VariableFromDmr(variable_tree, self.fakesat_config,
                                           self.namespace, '/variable')

                self.assertEqual(variable.get_valid_max(), expected_valid_max)

    def test_variable_from_netcdf4(self):
        """ Ensure that a `netCDF4.Variable` instance can be correctly parsed
            by the `VariableFromNetCDF4` child class.

        """
        with Dataset('test.nc4', 'w', diskless=True) as dataset:
            dataset.createDimension('lat', size=2)
            dataset.createDimension('lon', size=2)
            nc4_variable = dataset.createVariable('science', float64,
                                                  dimensions=('lat', 'lon'))
            nc4_variable.setncatts({'coordinates': '/lat /lon',
                                    'units': 'metres',
                                    'valid_min': -10,
                                    'valid_max': 10})

            variable = VariableFromNetCDF4(nc4_variable, self.fakesat_config,
                                           self.namespace, '/science')

        self.assertEqual(variable.full_name_path, '/science')
        self.assertEqual(variable.data_type, 'float64')
        self.assertSetEqual(set(variable.attributes.keys()),
                            {'coordinates', 'units', 'valid_min', 'valid_max',
                             'collection_override', 'collection_supplement'})
        self.assertEqual(variable.attributes['units'], 'metres')
        self.assertListEqual(variable.get_range(), [-10, 10])
        self.assertEqual(variable.get_valid_min(), -10)
        self.assertEqual(variable.get_valid_max(), 10)
        self.assertSetEqual(variable.get_references(), {'/lat', '/lon'})
