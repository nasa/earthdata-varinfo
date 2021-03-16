from logging import Logger
from unittest import TestCase
from unittest.mock import patch
from urllib.error import HTTPError
import xml.etree.ElementTree as ET

import numpy as np

from harmony.util import config

from varinfo.exceptions import (DmrNamespaceError, UrlAccessFailed,
                                UrlAccessFailedWithRetries)
from varinfo.utilities import (download_url, get_xml_attribute,
                               get_xml_namespace, HTTP_REQUEST_ATTEMPTS,
                               recursive_get, split_attribute_path)


class TestUtilities(TestCase):
    """ A class for testing functions in the varinfo.utilities module. """

    @classmethod
    def setUpClass(cls):
        cls.namespace = 'namespace_string'

    def setUp(self):
        self.logger = Logger('tests')
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

    @patch('varinfo.utilities.util_download')
    def test_download_url(self, mock_util_download):
        """ Ensure that the `harmony.util.download` function is called. Also
            ensure that if a 500 error is returned, the request is retried. If
            a different HTTPError occurs, the caught HTTPError should be
            re-raised. Finally, check the maximum number of request attempts is
            not exceeded.

        """
        output_directory = 'output/dir'
        test_url = 'test.org'
        access_token = 'xyzzy'
        message_retry = 'Internal Server Error'
        message_other = 'Authentication Error'

        http_response = f'{output_directory}/output.nc'
        http_error_retry = HTTPError(test_url, 500, message_retry, {}, None)
        http_error_other = HTTPError(test_url, 403, message_other, {}, None)

        with self.subTest('Successful response, only make one request.'):
            mock_util_download.return_value = http_response
            response = download_url(test_url, output_directory, self.logger,
                                    access_token, self.config)

            self.assertEqual(response, http_response)
            mock_util_download.assert_called_once_with(
                test_url,
                output_directory,
                self.logger,
                access_token=access_token,
                data=None,
                cfg=self.config)

            mock_util_download.reset_mock()

        with self.subTest('500 error triggers a retry.'):
            mock_util_download.side_effect = [http_error_retry, http_response]

            response = download_url(test_url, output_directory, self.logger)

            self.assertEqual(response, http_response)
            self.assertEqual(mock_util_download.call_count, 2)

        with self.subTest('Non-500 error does not retry, and is re-raised.'):
            mock_util_download.side_effect = [http_error_other, http_response]

            with self.assertRaises(UrlAccessFailed):
                download_url(test_url, output_directory, self.logger)
                mock_util_download.assert_called_once_with(test_url,
                                                           output_directory,
                                                           self.logger)

        with self.subTest('Maximum number of attempts not exceeded.'):
            mock_util_download.side_effect = [http_error_retry] * (HTTP_REQUEST_ATTEMPTS + 1)
            with self.assertRaises(UrlAccessFailedWithRetries):
                download_url(test_url, output_directory, self.logger)
                self.assertEqual(mock_util_download.call_count,
                                 HTTP_REQUEST_ATTEMPTS)
