from unittest import TestCase
import xml.etree.ElementTree as ET

from varinfo import CFConfig
from varinfo import Variable


class TestVariable(TestCase):
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
            f'  <{cls.namespace}Dim name="dimension" />'
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

    def test_variable_instantiation(self):
        """ Ensure a `Variable` instance can be created from an input `.dmr`
            XML element instance.

        """
        variable = Variable(self.dmr_variable, self.fakesat_config,
                            self.namespace, self.dmr_variable_path)

        self.assertEqual(variable.full_name_path, '/group/variable')
        self.assertEqual(variable.group_path, '/group')
        self.assertEqual(variable.name, 'variable')
        self.assertEqual(variable.attributes.get('units'), 'm')
        self.assertEqual(variable.ancillary_variables, {'/ancillary_data/epoch'})
        self.assertEqual(variable.coordinates, {'/group/latitude',
                                                '/group/longitude'})
        self.assertEqual(variable.dimensions, {'/group/dimension'})
        self.assertEqual(variable.subset_control_variables,
                         {'/group/begin', '/group/count'})

    def test_variable_cf_override(self):
        """ Ensure a CF attribute is overridden by the `CFConfig` value. """
        dmr_variable = ET.fromstring(
            f'<{self.namespace}Float64 name="science">'
            f'  <{self.namespace}Attribute name="coordinates" type="String">'
            f'    <{self.namespace}Value>latitude, longitude</{self.namespace}Value>'
            f'  </{self.namespace}Attribute>'
            f'</{self.namespace}Float64>'
        )

        variable = Variable(dmr_variable, self.fakesat_config, self.namespace,
                            '/coordinates_group/science')

        self.assertEqual(variable.coordinates, {'/coordinates_group/lat',
                                                '/coordinates_group/lon'})

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
                variable = Variable(dmr_variable, self.fakesat_config,
                                    self.namespace, variable_name)
                self.assertEqual(variable.coordinates, {qualified_reference})

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

                variable = Variable(dmr_variable, self.fakesat_config,
                                    self.namespace, root_var_name)
                self.assertEqual(variable.coordinates, {qualified_reference})

    def test_variable_get_references(self):
        """ Ensure that a set of absolute paths to all variables referred to
            in the ancillary_variables, coordinates, dimensions and
            subset_control_variables is returned.

        """
        variable = Variable(self.dmr_variable, self.fakesat_config,
                            self.namespace, self.dmr_variable_path)

        references = variable.get_references()

        self.assertEqual(references, {'/ancillary_data/epoch',
                                      '/group/latitude',
                                      '/group/longitude',
                                      '/group/dimension',
                                      '/group/begin',
                                      '/group/count'})

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
        variable = Variable(dmr_variable, self.fakesat_config, self.namespace,
                            variable_name)

        self.assertEqual(variable.dimensions, {'/group_one/delta_time'})
