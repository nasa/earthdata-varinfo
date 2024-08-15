from shutil import rmtree
from tempfile import mkdtemp
from typing import List
from unittest import TestCase
import xml.etree.ElementTree as ET

from netCDF4 import Dataset
import numpy as np

from varinfo.exceptions import DmrNamespaceError
from varinfo.utilities import (
    get_full_path_netcdf4_attribute,
    get_full_path_xml_attribute,
    get_xml_attribute,
    get_xml_attribute_value,
    get_xml_container_attribute,
    get_xml_namespace,
    recursive_get,
    split_attribute_path,
)

from tests.utilities import write_skeleton_netcdf4


class TestUtilities(TestCase):
    """A class for testing functions in the varinfo.utilities module."""

    @classmethod
    def setUpClass(cls):
        cls.namespace = 'namespace_string'

    def setUp(self):
        self.output_dir = mkdtemp()

    def tearDown(self):
        rmtree(self.output_dir)

    def test_recursive_get(self):
        """Can retrieve a nested dictionary value, or account for missing
        data.

        """
        test_args = [
            ['Top level', {'a': 'b'}, ['a'], 'b'],
            ['Nested', {'a': {'b': 'c'}}, ['a', 'b'], 'c'],
            ['Missing nested data', {'a': {'c': 'd'}}, ['a', 'b'], None],
            ['Missing top level', {'b': {'c': 'd'}}, ['a', 'c'], None],
        ]

        for description, test_dictionary, keys, expected_output in test_args:
            with self.subTest(description):
                self.assertEqual(recursive_get(test_dictionary, keys), expected_output)

    def test_split_attribute_path(self):
        """Check that a fully qualified path to a metadata attribute is
        correctly converted to a combination of two keys, to locate the
        attribute in the global attributes for the granule.

        For example: /Metadata/SeriesIdentification/shortName will be
        located at: dataset.attributes['Metadata_SeriesIdentification']['shortName']

        """
        test_args = [
            ['Not nested', '/short_name', ['short_name']],
            ['Singly nested', '/Metadata/short_name', ['Metadata', 'short_name']],
            [
                'Doubly nested',
                '/Metadata/Series/short_name',
                ['Metadata', 'Series', 'short_name'],
            ],
            ['Without leading slash', 'Metadata/Series', ['Metadata', 'Series']],
        ]

        for description, full_path, expected_key_list in test_args:
            with self.subTest(description):
                self.assertEqual(split_attribute_path(full_path), expected_key_list)

    def test_get_xml_namespace(self):
        """Check that an XML namespace can be retrieved, or if one is absent,
        that a `DmrNamespaceError` is raised.

        """
        with self.subTest('Valid Element'):
            element = ET.fromstring(
                f'<{self.namespace}Dataset>' f'</{self.namespace}Dataset>'
            )
            self.assertEqual(get_xml_namespace(element), self.namespace)

        with self.subTest('Non-Dataset Element'):
            element = ET.fromstring(
                f'<{self.namespace}OtherTag>' f'</{self.namespace}OtherTag>'
            )
            with self.assertRaises(DmrNamespaceError):
                get_xml_namespace(element)

    def test_get_xml_attribute(self):
        """Ensure the value of an XML attribute is correctly retrieved, or
        that the default value is returned, where given. This function
        should also cope with non-DAP4 types, by defaulting to a string
        type, before casting the result correctly.

        """
        value = 12.0
        default = 10.0
        variable = ET.fromstring(
            f'<{self.namespace}Int64 name="test_variable">'
            f'  <{self.namespace}Attribute name="valid_attr" type="Float64">'
            f'    <{self.namespace}Value>{value}</{self.namespace}Value>'
            f'  </{self.namespace}Attribute>'
            f'  <{self.namespace}Attribute name="no_type">'
            f'    <{self.namespace}Value>{value}</{self.namespace}Value>'
            f'  </{self.namespace}Attribute>'
            f'  <{self.namespace}Attribute name="no_value" type="String">'
            f'  </{self.namespace}Attribute>'
            f'  <{self.namespace}Attribute name="bad_type" type="Random64">'
            f'    <{self.namespace}Value>{value}</{self.namespace}Value>'
            f'  </{self.namespace}Attribute>'
            f'  <{self.namespace}Attribute name="multi" type="Float64">'
            f'    <{self.namespace}Value>-90.0</{self.namespace}Value>'
            f'    <{self.namespace}Value>90.0</{self.namespace}Value>'
            f'  </{self.namespace}Attribute>'
            f'  <{self.namespace}Attribute name="named_container" type="Container">'
            f'    <{self.namespace}Attribute name="nested_one" type="Float64">'
            f'      <{self.namespace}Value>{value}</{self.namespace}Value>'
            f'    </{self.namespace}Attribute>'
            f'    <{self.namespace}Attribute name="nested_two" type="Float64">'
            f'      <{self.namespace}Value>{value}</{self.namespace}Value>'
            f'    </{self.namespace}Attribute>'
            f'  </{self.namespace}Attribute>'
            f'</{self.namespace}Int64>'
        )

        expected_container_outputs = {
            'nested_one': 12.0,
            'nested_two': 12.0,
        }
        test_args = [
            ['Element with Float64 attribute', 'valid_attr', value, np.float64],
            ['Absent Attribute uses default', 'missing_attr', default, type(default)],
            ['Attribute omitting type property', 'no_type', '12.0', str],
            ['Absent Value tag uses default', 'no_value', default, type(default)],
            ['Unexpected type property', 'bad_type', '12.0', str],
            [
                'Container attribute',
                'named_container',
                expected_container_outputs,
                dict,
            ],
        ]

        for description, attr_name, expected_value, expected_type in test_args:
            with self.subTest(description):
                attribute_value = get_xml_attribute(
                    variable, attr_name, self.namespace, default
                )

                self.assertIsInstance(attribute_value, expected_type)
                self.assertEqual(attribute_value, expected_value)

        with self.subTest('Multiple values are retrieved'):
            attribute_value = get_xml_attribute(variable, 'multi', self.namespace)

            self.assertIsInstance(attribute_value, List)
            self.assertEqual(len(attribute_value), 2)
            self.assertListEqual(attribute_value, [-90.0, 90.0])

            for value in attribute_value:
                self.assertIsInstance(value, np.float64)

    def test_get_xml_attribute_value(self):
        """Ensure a single or list value can be extracted from a given XML
        Attribute tag. If there are no child Value tags, the default value
        should be returned.

        """
        with self.subTest('Single value is retrieved.'):
            value = 'value_123'
            attribute = ET.fromstring(
                f'  <{self.namespace}Attribute name="no_type">'
                f'    <{self.namespace}Value>{value}</{self.namespace}Value>'
                f'  </{self.namespace}Attribute>'
            )
            self.assertEqual(
                get_xml_attribute_value(attribute, self.namespace, 'String', 'default'),
                value,
            )

        with self.subTest('List of values are retrieved.'):
            value_one = 'value_1'
            value_two = 'value_2'
            value_three = 'value_3'
            attribute = ET.fromstring(
                f'  <{self.namespace}Attribute name="no_type">'
                f'    <{self.namespace}Value>{value_one}</{self.namespace}Value>'
                f'    <{self.namespace}Value>{value_two}</{self.namespace}Value>'
                f'    <{self.namespace}Value>{value_three}</{self.namespace}Value>'
                f'  </{self.namespace}Attribute>'
            )
            self.assertListEqual(
                get_xml_attribute_value(attribute, self.namespace, 'String', 'default'),
                [value_one, value_two, value_three],
            )

        with self.subTest('No values returns default.'):
            default = 'default value'
            attribute = ET.fromstring(
                f'  <{self.namespace}Attribute name="no_type">'
                f'  </{self.namespace}Attribute>'
            )
            self.assertEqual(
                get_xml_attribute_value(attribute, self.namespace, 'String', default),
                default,
            )

    def test_get_xml_container_attribute(self):
        """Ensure a dictionary of attributes is retrieved for a container."""

        with self.subTest('Flat dictionary.'):
            flat_container = ET.fromstring(
                f'<{self.namespace}Attribute name="container" type="Container">'
                f'  <{self.namespace}Attribute name="attribute_one" type="Float64">'
                f'    <{self.namespace}Value>1.0</{self.namespace}Value>'
                f'  </{self.namespace}Attribute>'
                f'  <{self.namespace}Attribute name="attribute_two" type="Float64">'
                f'    <{self.namespace}Value>2.0</{self.namespace}Value>'
                f'  </{self.namespace}Attribute>'
                f'</{self.namespace}Attribute>'
            )

            expected_attribute_container = {
                'attribute_one': 1.0,
                'attribute_two': 2.0,
            }

            self.assertDictEqual(
                get_xml_container_attribute(flat_container, self.namespace),
                expected_attribute_container,
            )

        with self.subTest('Nested dictionary.'):
            nested_container = ET.fromstring(
                f'<{self.namespace}Attribute name="named_container" type="Container">'
                f'  <{self.namespace}Attribute name="attribute_one" type="Float64">'
                f'    <{self.namespace}Value>1.0</{self.namespace}Value>'
                f'  </{self.namespace}Attribute>'
                f'  <{self.namespace}Attribute name="group_one" type="Container">'
                f'    <{self.namespace}Attribute name="attribute_two" type="Float64">'
                f'      <{self.namespace}Value>2.0</{self.namespace}Value>'
                f'    </{self.namespace}Attribute>'
                f'    <{self.namespace}Attribute name="group_two" type="Container">'
                f'      <{self.namespace}Attribute name="attribute_three" type="Float64">'
                f'        <{self.namespace}Value>3.0</{self.namespace}Value>'
                f'      </{self.namespace}Attribute>'
                f'    </{self.namespace}Attribute>'
                f'  </{self.namespace}Attribute>'
                f'</{self.namespace}Attribute>'
            )

            expected_attribute_container = {
                'attribute_one': 1.0,
                'group_one': {
                    'attribute_two': 2.0,
                    'group_two': {
                        'attribute_three': 3.0,
                    },
                },
            }

            self.assertDictEqual(
                get_xml_container_attribute(nested_container, self.namespace),
                expected_attribute_container,
            )

    def test_get_full_path_xml_attribute(self):
        """Ensure an XML attribute nested to an arbitrary amount can have its
        value retrieved from the element tree.

        """
        with open(
            'tests/unit/data/ATL03_example.dmr', 'r', encoding='utf-8'
        ) as file_handler:
            atl03_dmr = ET.fromstring(file_handler.read())

        atl03_namespace = '{http://xml.opendap.org/ns/DAP/4.0#}'

        with self.subTest('Non nested attribute.'):
            self.assertEqual(
                get_full_path_xml_attribute(
                    atl03_dmr,
                    '/Conventions',
                    atl03_namespace,
                ),
                'CF-1.6',
            )

        with self.subTest('No leading slash.'):
            self.assertEqual(
                get_full_path_xml_attribute(
                    atl03_dmr,
                    'Conventions',
                    atl03_namespace,
                ),
                'CF-1.6',
            )

        with self.subTest('Singly nested attribute.'):
            self.assertEqual(
                get_full_path_xml_attribute(
                    atl03_dmr,
                    '/gt1l/atlas_pce',
                    atl03_namespace,
                ),
                'pce1',
            )

        with self.subTest('Deeply nested attribute.'):
            self.assertEqual(
                get_full_path_xml_attribute(
                    atl03_dmr,
                    '/gt1l/bckgrd_atlas/tlm_height_band1/coordinates',
                    atl03_namespace,
                ),
                'delta_time',
            )

        with self.subTest('Attribute that does not exist returns None.'):
            self.assertIsNone(
                get_full_path_xml_attribute(
                    atl03_dmr,
                    '/NONEXISTENT',
                    atl03_namespace,
                )
            )

        with self.subTest('Non-existent variable or group returns None.'):
            self.assertIsNone(
                get_full_path_xml_attribute(
                    atl03_dmr,
                    '/absent_attribute_container/units',
                    atl03_namespace,
                )
            )

    def test_get_full_path_netcdf4_attribute(self):
        """Ensure a NetCDF-4 metadata attribute can be retrieved from anywhere
        in the file. This includes the root group, nested groups, variables in
        the root group and variables within groups.

        """
        netcdf_file_path = write_skeleton_netcdf4(self.output_dir)

        with self.subTest('Root group attribute.'):
            with Dataset(netcdf_file_path) as dataset:
                self.assertEqual(
                    get_full_path_netcdf4_attribute(dataset, '/short_name'), 'ATL03'
                )

        with self.subTest('Root group attribute without a leading slash.'):
            with Dataset(netcdf_file_path) as dataset:
                self.assertEqual(
                    get_full_path_netcdf4_attribute(dataset, 'short_name'), 'ATL03'
                )

        with self.subTest('Absent root group attribute returns None.'):
            with Dataset(netcdf_file_path) as dataset:
                self.assertIsNone(
                    get_full_path_netcdf4_attribute(dataset, 'missing_attribute'),
                )

        with self.subTest('Root-level variable.'):
            with Dataset(netcdf_file_path) as dataset:
                self.assertEqual(
                    get_full_path_netcdf4_attribute(dataset, '/science1/coordinates'),
                    '/lat /lon',
                )

        with self.subTest('Absent variable attribute returns None.'):
            with Dataset(netcdf_file_path) as dataset:
                self.assertIsNone(
                    get_full_path_netcdf4_attribute(dataset, '/science1/missing'),
                )

        with self.subTest('Attribute on non-existent variable returns None.'):
            with Dataset(netcdf_file_path) as dataset:
                self.assertIsNone(
                    get_full_path_netcdf4_attribute(dataset, '/science3/coordinates'),
                )

        with self.subTest('Variable in nested group.'):
            with Dataset(netcdf_file_path) as dataset:
                self.assertEqual(
                    get_full_path_netcdf4_attribute(
                        dataset, '/group/science2/coordinates'
                    ),
                    '/lat /lon',
                )
