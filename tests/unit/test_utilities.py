from unittest import TestCase
import xml.etree.ElementTree as ET

import numpy as np

from harmony.util import config

from varinfo.exceptions import DmrNamespaceError
from varinfo.utilities import (get_xml_attribute, get_xml_namespace,
                               recursive_get, split_attribute_path)


class TestUtilities(TestCase):
    """ A class for testing functions in the varinfo.utilities module. """

    @classmethod
    def setUpClass(cls):
        cls.namespace = 'namespace_string'

    def setUp(self):
        self.config = config(validate=False)

    def test_recursive_get(self):
        """ Can retrieve a nested dictionary value, or account for missing
            data.

        """
        test_args = [
            ['Top level', {'a': 'b'}, ['a'], 'b'],
            ['Nested', {'a': {'b': 'c'}}, ['a', 'b'], 'c'],
            ['Missing nested data', {'a': {'c': 'd'}}, ['a', 'b'], None],
            ['Missing top level', {'b': {'c': 'd'}}, ['a', 'c'], None]
        ]

        for description, test_dictionary, keys, expected_output in test_args:
            with self.subTest(description):
                self.assertEqual(recursive_get(test_dictionary, keys),
                                 expected_output)

    def test_split_attribute_path(self):
        """ Check that a fully qualified path to a metadata attribute is
            correctly converted to a combination of two keys, to locate the
            attribute in the global attributes for the granule.

            For example: /Metadata/SeriesIdentification/shortName will be
            located at: dataset.attributes['Metadata_SeriesIdentification']['shortName']

        """
        test_args = [['Not nested', '/short_name', ['short_name']],
                     ['Singly nested', '/Metadata/short_name',
                      ['Metadata', 'short_name']],
                     ['Doubly nested', '/Metadata/Series/short_name',
                      ['Metadata', 'Series', 'short_name']]]

        for description, full_path, expected_key_list in test_args:
            with self.subTest(description):
                self.assertEqual(split_attribute_path(full_path),
                                 expected_key_list)

    def test_get_xml_namespace(self):
        """ Check that an XML namespace can be retrieved, or if one is absent,
            that a `DmrNamespaceError` is raised.

        """
        with self.subTest('Valid Element'):
            element = ET.fromstring(f'<{self.namespace}Dataset>'
                                    f'</{self.namespace}Dataset>')
            self.assertEqual(get_xml_namespace(element), self.namespace)

        with self.subTest('Non-Dataset Element'):
            element = ET.fromstring(f'<{self.namespace}OtherTag>'
                                    f'</{self.namespace}OtherTag>')
            with self.assertRaises(DmrNamespaceError):
                get_xml_namespace(element)

    def test_get_xml_attribute(self):
        """ Ensure the value of an XML attribute is correctly retrieved, or
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
            f'</{self.namespace}Int64>'
        )

        test_args = [['Element with Float64 attribute', 'valid_attr', value, np.float64],
                     ['Absent Attribute uses default', 'missing_attr', default, type(default)],
                     ['Attribute omitting type property', 'no_type', '12.0', str],
                     ['Absent Value tag uses default', 'no_value', default, type(default)],
                     ['Unexpected type property', 'bad_type', '12.0', str]]

        for description, attr_name, expected_value, expected_type in test_args:
            with self.subTest(description):
                attribute_value = get_xml_attribute(variable, attr_name,
                                                    self.namespace, default)

                self.assertIsInstance(attribute_value, expected_type)
                self.assertEqual(attribute_value, expected_value)
