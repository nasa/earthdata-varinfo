from shutil import rmtree
from tempfile import mkdtemp
from os.path import exists
from unittest import TestCase
from unittest.mock import patch, Mock

from cmr import (GranuleQuery, CMR_UAT)
import requests
from requests.exceptions import HTTPError

from varinfo.cmr_search import (get_granules, get_granule_link,
                                download_granule)
from varinfo.exceptions import (CMRQueryException,
                                MissingGranuleDownloadLinks,
                                MissingPositionalArguments,
                                GranuleDownloadException,
                                DirectoryCreationException)


class TestQuery(TestCase):
    ''' A class for testing functions in cmr_search. '''
    @classmethod
    def setUpClass(cls):
        ''' Set test fixtures that can be recycled between tests. '''
        cls.bearer_token_header = 'Bearer foo'
        cls.collection_concept_id = 'C1234567890-PROV'
        cls.collection_short_name = 'EXAMPLE_COLLECTION'
        cls.collection_version = '1.2.3'
        cls.granule_concept_id = 'G2345678901-PROV'
        cls.launchpad_token_header = 'launchpad-foo'
        cls.provider = 'PROV'

    def setUp(self):
        ''' Set test fixtures that must be unique to each test. '''
        self.output_dir = mkdtemp()

    def tearDown(self):
        if exists(self.output_dir):
            rmtree(self.output_dir)

    @patch('varinfo.cmr_search.GranuleQuery', spec=GranuleQuery)
    def test_with_concept_id(self, granule_query_mock):
        ''' Test when `get_granules` is called with, `concept_id`,
            the query made to CMR (with `GranuleQuery.get()`) uses the same
            `concept_id`. And `GranuleQuery.get()` is being returned
            from `get_granules` as expected.
        '''
        # Mock granule response
        granule_response = [
            {
                'links': [
                    {'rel': 'http://esipfed.org/ns/fedsearch/1.1/s3#'},
                    {'rel': 'http://esipfed.org/ns/fedsearch/1.1/data#'}
                ]
            }
        ]

        # Set return_value of `granule_query_mock` to `granule_response`
        granule_query_mock.return_value.get.return_value = granule_response
        query_response = get_granules(self.collection_concept_id,
                                      cmr_env=CMR_UAT,
                                      auth_header=self.bearer_token_header)
        # Check if `get_granules` returns the CMR GranuleQuery output
        self.assertListEqual(query_response, granule_response)

        # Check if the `GranuleQuery` object was instantiated with the correct
        # environment, Authorization header, and expected page size
        granule_query_mock.assert_called_once_with(mode=CMR_UAT)
        self.assertDictEqual(granule_query_mock.return_value.headers,
                             {'Authorization': self.bearer_token_header})
        granule_query_mock.return_value.get.assert_called_once_with(10)

    @patch('varinfo.cmr_search.GranuleQuery', spec=GranuleQuery)
    def test_with_shortname_version_provider(self, granule_query_mock):
        ''' Test when `get_granules` is called with parameters
            --shortname, collection_version, and provider--
            the query made to CMR (with `GranuleQuery.get()`) uses the same
            parameters. And `GranuleQuery.get()` is being returned
            from `get_granules` as expected.
        '''
        # Mock granule response
        granule_response = [
            {
                'links': [
                    {'rel': 'http://esipfed.org/ns/fedsearch/1.1/s3#'},
                    {'rel': 'http://esipfed.org/ns/fedsearch/1.1/data#'}
                ]
            }
        ]

        # Set return_value of `granule_query_mock` to `granule_response`
        granule_query_mock.return_value.get.return_value = granule_response
        query_response = get_granules(
            collection_shortname=self.collection_short_name,
            collection_version=self.collection_version,
            provider=self.provider,
            cmr_env=CMR_UAT,
            auth_header=self.bearer_token_header
        )

        # Check if `get_granules` returns the CMR GranuleQuery output
        self.assertListEqual(query_response, granule_response)

        # Check if the `GranuleQuery` object was instantiated with the correct
        # environment, Authorization header, and expected page size
        granule_query_mock.assert_called_once_with(mode=CMR_UAT)
        self.assertDictEqual(granule_query_mock.return_value.headers,
                             {'Authorization': self.bearer_token_header})
        granule_query_mock.return_value.get.assert_called_once_with(10)

    @patch('varinfo.cmr_search.GranuleQuery', spec=GranuleQuery)
    def test_with_launchpad_token(self, granule_query_mock):
        ''' Test when `get_granules` is called with an Authorization header
            that contains a LaunchPad token (e.g., no 'Bearer ' prefix), that
            header is propagated as expected to the `GranuleQuery` instance.

        '''
        granule_response = [
            {
                'links': [
                    {'rel': 'http://esipfed.org/ns/fedsearch/1.1/s3#'},
                    {'rel': 'http://esipfed.org/ns/fedsearch/1.1/data#'}
                ]
            }
        ]

        # Set return_value of `granule_query_mock` to `granule_response`
        granule_query_mock.return_value.get.return_value = granule_response
        query_response = get_granules(self.collection_concept_id,
                                      cmr_env=CMR_UAT,
                                      auth_header=self.launchpad_token_header)

        # Check if `get_granules` returns the CMR GranuleQuery output
        self.assertListEqual(query_response, granule_response)

        # Check if the `GranuleQuery` object was instantiated with the correct
        # environment, Authorization header, and expected page size
        granule_query_mock.assert_called_once_with(mode=CMR_UAT)
        self.assertDictEqual(granule_query_mock.return_value.headers,
                             {'Authorization': self.launchpad_token_header})
        granule_query_mock.return_value.get.assert_called_once_with(10)

    @patch('varinfo.cmr_search.GranuleQuery', spec=GranuleQuery)
    def test_runtime_error(self, granule_query_mock):
        ''' Test if CMR has a RuntimeError and if the CMRQueryException
            is invoked.
        '''
        # Mock CMR's RuntimeError
        granule_query_mock.return_value.get.side_effect = RuntimeError(
            'CMR timed out'
        )
        # Check if CMRQueryException is raised
        with self.assertRaises(CMRQueryException):
            get_granules(self.collection_concept_id, cmr_env=CMR_UAT,
                         auth_header=self.bearer_token_header)

    @patch('varinfo.cmr_search.GranuleQuery', spec=GranuleQuery)
    def test_exceptions_concept_id_with_mock(self, granule_query_mock):
        ''' Test if an IndexError is raised when `get_granules` is called
            for the 'G1245662789-EEDTEST' collection that is not in CMR_OPS.
        '''
        # Mock IndexError when no granules are returned
        granule_query_mock.return_value.get.return_value = []

        with self.assertRaises(IndexError) as context_manager:
            get_granules(self.collection_concept_id,
                         auth_header=self.bearer_token_header)

        self.assertEqual('No granules were found with selected '
                         'parameters and user permissions',
                         str(context_manager.exception))

    @patch('varinfo.cmr_search.GranuleQuery', spec=GranuleQuery)
    def test_exceptions_shortname_version_provider_mock(self,
                                                        granule_query_mock):
        ''' Test if an IndexError is raised when `get_granules` is called
            for the 'G1245662789-EEDTEST' collection that is not in CMR_OPS.
        '''
        # Mock IndexError when no granules are returned
        granule_query_mock.side_effect = IndexError('No granules were found '
                                                    'with selected parameters'
                                                    ' and user permissions')
        with self.assertRaises(IndexError) as context_manager:
            get_granules(collection_shortname=self.collection_short_name,
                         collection_version=self.collection_version,
                         provider=self.provider,
                         auth_header=self.bearer_token_header)

        self.assertEqual('No granules were found with selected '
                         'parameters and user permissions',
                         str(context_manager.exception))

    @patch('varinfo.cmr_search.GranuleQuery', spec=GranuleQuery)
    def test_granule_response_raises_cmr_exception(self, granule_query_mock):
        ''' Check if CMRQueryException is raised with a fake token. '''
        granule_query_mock.side_effect = CMRQueryException('No granules found')

        with self.subTest('Test CMRQueryException '
                          'with concept_id and fake token'):
            with self.assertRaises(CMRQueryException):
                get_granules(self.collection_concept_id,
                             auth_header=self.bearer_token_header)

        with self.subTest('Test CMRQueryException with '
                          'shortname, version, provider, and fake token'):
            with self.assertRaises(CMRQueryException):
                get_granules(collection_shortname=self.collection_short_name,
                             collection_version=self.collection_version,
                             provider=self.provider,
                             auth_header=self.bearer_token_header)

    def test_granule_response_raises_exception(self):
        ''' Check if get `get_granules` raises MissingPositionalArgument '''
        with self.subTest('No required positonal arguments'):
            with self.assertRaises(MissingPositionalArguments) as context_manager:
                get_granules()

            self.assertEqual('Missing positional argument: auth_header',
                             str(context_manager.exception))

        with self.subTest('Positional arguments entered: '
                          'shortname and collection_version'):
            with self.assertRaises(MissingPositionalArguments) as context_manager:
                get_granules(collection_shortname=self.collection_short_name,
                             collection_version=self.collection_version)

            self.assertEqual('Missing positional argument: auth_header',
                             str(context_manager.exception))

        with self.subTest('Positional arguments entered: collection_shortname,'
                          ' collection_version, and token'):
            with self.assertRaises(MissingPositionalArguments) as context_manager:
                get_granules(collection_shortname=self.collection_short_name,
                             collection_version=self.collection_version,
                             auth_header=self.bearer_token_header)

            expected_exception = ('Missing positional argument: '
                                  'concept_id or collection_shortname, '
                                  'collection_version, and provider')
            self.assertEqual(expected_exception,
                             str(context_manager.exception))

    def test_exceptions_granule_link(self):
        ''' Check if MissingGranuleDownloadLinks is raised. '''
        # Nested dict does not contain key `links`
        granule_response_no_links = [{
            'no_links': [{'rel': 'http://esipfed.org/ns/fedsearch/1.1/s3#'}]
        }]

        # Nested dict contains `links` but `rel` does not end in '/data#'
        granule_response_links_no_rel = [{
            'links': [{'rel': 'http://esipfed.org/ns/fedsearch/1.1/s3#'}]
        }]

        # Nested dict contains keys:
        # `links`, `inherited`, and `rel` ends in '/data#'
        granule_response_links_rel_inherit = [{
            'links': [{
                'rel': 'http://esipfed.org/ns/fedsearch/1.1/data#',
                'href': 'https://data.gesdisc.earthdata.nasa.gov/data/.nc4',
                'inherited': True
            }]
        }]

        granule_response_links_empty = [{
            'links': []
        }]

        granule_response_links_correct = [{
            'links': [{
                'rel': 'http://esipfed.org/ns/fedsearch/1.1/data#',
                'title': 'Download example.nc4',
                'hreflang': 'en-US',
                'href': 'https://data.gesdisc.earthdata.nasa.gov/example.nc4'
            }]
        }]

        with self.subTest('Granule has no `links` key'):
            with self.assertRaises(MissingGranuleDownloadLinks) as context_manager:
                get_granule_link(granule_response_no_links)
            self.assertEqual(
                f'No links for granule record: {str(granule_response_no_links)}',
                str(context_manager.exception)
            )

        with self.subTest('Granule has `links`'
                          'but `rel` does not end with `/data#`'):
            with self.assertRaises(MissingGranuleDownloadLinks):
                get_granule_link(granule_response_links_no_rel)

        with self.subTest('Granule has `links`, `inherited`, '
                          'and `rel` ends in `/data#`'):
            with self.assertRaises(MissingGranuleDownloadLinks):
                get_granule_link(granule_response_links_rel_inherit)

        with self.subTest('Granule has `links` but it is an empty list'):
            with self.assertRaises(MissingGranuleDownloadLinks):
                get_granule_link(granule_response_links_empty)

        with self.subTest('Granule has `links` and all correct attributes'):
            self.assertEqual(
                get_granule_link(granule_response_links_correct),
                'https://data.gesdisc.earthdata.nasa.gov/example.nc4'
            )

    def test_download_gran_exceptions(self):
        ''' Check if exceptions are raised for incorrect input parameters
        '''
        with self.assertRaises(DirectoryCreationException):
            # Input parameter, `out_directory` is a path that does not exist
            download_granule(granule_link='https://foo.gov/example.nc4',
                             auth_header=self.bearer_token_header,
                             out_directory='/Usr/foo/dir')

        with self.assertRaises(GranuleDownloadException):
            # Not a real https link
            download_granule('https://foo.gov/example.nc4',
                             auth_header=self.bearer_token_header)

    def _mock_requests(self, status=200, content="CONTENT"):
        '''
        Mock requests.get module and it's methods content and status.
        Return the mock object.
        '''
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = status
        mock_response.content = content
        return mock_response

    @patch('requests.get')
    def test_download_granule(self, mock_requests_get):
        ''' Check if `download_granules` returns the expected
            content for the mocked response.
        '''
        link = 'https://foo.gov/example.nc4'
        expected_file_contents = 'Fake NetCDF-4 content'

        # Set mock_content as bytes for writing
        mock_content = bytes(expected_file_contents, encoding='utf-8')
        # Set the mock_response with the `_mock_requests` object content method
        mock_response = self._mock_requests(content=mock_content)
        # Set the return_value of `mock_requests_get` to mock_response
        mock_requests_get.return_value = mock_response
        file_path = download_granule(link,
                                     auth_header=self.bearer_token_header,
                                     out_directory=self.output_dir)
        # Check if `download_granule` was called once with expected parameters
        mock_requests_get.assert_called_once_with(
            link,
            headers={'Authorization': self.bearer_token_header},
            timeout=10
        )
        # Check if download file contains expected content from `requests.get`
        with self.subTest('Test if downloaded file contains expected content'):
            with open(file_path, 'r', encoding='utf-8') as file:
                actual_file_contents = file.read()

            self.assertEqual(actual_file_contents, expected_file_contents)

    @patch('requests.get')
    def test_download_granule_with_launchpad_token(self, mock_requests_get):
        ''' Ensure an Authorization header containing a LaunchPad token is
            correctly used in the `requests.get` call. This header does not
            contain a 'Bearer ' prefix, and the HTTPS call made by `requests`
            should not have that prefix either.

        '''
        link = 'https://foo.gov/example.nc4'
        expected_file_contents = 'Fake NetCDF-4 content'

        # Set mock_content as bytes for writing
        mock_content = bytes(expected_file_contents, encoding='utf-8')
        # Set the mock_response with the `_mock_requests` object content method
        mock_response = self._mock_requests(content=mock_content)
        # Set the return_value of `mock_requests_get` to mock_response
        mock_requests_get.return_value = mock_response
        file_path = download_granule(link,
                                     auth_header=self.launchpad_token_header,
                                     out_directory=self.output_dir)
        # Check if `download_granule` was called once with expected parameters
        mock_requests_get.assert_called_once_with(
            link,
            headers={'Authorization': self.launchpad_token_header},
            timeout=10
        )
        # Check if download file contains expected content from `requests.get`
        with self.subTest('Test if downloaded file contains expected content'):
            with open(file_path, 'r', encoding='utf-8') as file:
                actual_file_contents = file.read()

            self.assertEqual(actual_file_contents, expected_file_contents)

    @patch('requests.get')
    def test_requests_error(self, mock_requests_get):
        ''' Check if the GranuleDownloadException is raised when
            the `side_effect` for the mock request is an HTTPError
        '''
        link = 'https://foo.gov/example.nc4'
        mock_requests_get.return_value.side_effect = HTTPError('Wrong HTTP')
        with self.assertRaises(GranuleDownloadException):
            download_granule(link, auth_header=self.bearer_token_header)
