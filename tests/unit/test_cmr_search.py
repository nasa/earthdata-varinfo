from shutil import rmtree
from tempfile import mkdtemp
from os.path import exists
from unittest import TestCase
from unittest.mock import patch, Mock

from cmr import GranuleQuery, CMR_UAT
import requests
from requests.exceptions import HTTPError, Timeout

from varinfo.cmr_search import (
    get_granules,
    get_granule_link,
    get_dmr_xml_url,
    download_granule,
    get_edl_token_from_launchpad,
    get_edl_token_header,
    urs_token_endpoints,
)

from varinfo.exceptions import (
    CMRQueryException,
    MissingGranuleDownloadLinks,
    MissingPositionalArguments,
    GranuleDownloadException,
    DirectoryCreationException,
    GetEdlTokenException,
)


class TestQuery(TestCase):
    """A class for testing functions in cmr_search."""

    @classmethod
    def setUpClass(cls):
        """Set test fixtures that can be recycled between tests."""
        cls.bearer_token_header = 'Bearer foo'
        cls.collection_concept_id = 'C1234567890-PROV'
        cls.collection_short_name = 'EXAMPLE_COLLECTION'
        cls.collection_version = '1.2.3'
        cls.granule_concept_id = 'G2345678901-PROV'
        cls.launchpad_token_header = 'launchpad-foo'
        cls.provider = 'PROV'

    def setUp(self):
        """Set test fixtures that must be unique to each test."""
        self.output_dir = mkdtemp()

    def tearDown(self):
        if exists(self.output_dir):
            rmtree(self.output_dir)

    @patch('varinfo.cmr_search.GranuleQuery', spec=GranuleQuery)
    def test_with_concept_id(self, granule_query_mock):
        """Test when `get_granules` is called with, `concept_id`,
        the query made to CMR (with `GranuleQuery.get()`) uses the same
        `concept_id`. And `GranuleQuery.get()` is being returned
        from `get_granules` as expected.
        """
        # Mock granule response
        granule_response = [
            {
                'links': [
                    {'rel': 'http://esipfed.org/ns/fedsearch/1.1/s3#'},
                    {'rel': 'http://esipfed.org/ns/fedsearch/1.1/data#'},
                ]
            }
        ]

        # Set return_value of `granule_query_mock` to `granule_response`
        granule_query_mock.return_value.get.return_value = granule_response
        query_response = get_granules(
            self.collection_concept_id,
            cmr_env=CMR_UAT,
            auth_header=self.bearer_token_header,
        )
        # Check if `get_granules` returns the CMR GranuleQuery output
        self.assertListEqual(query_response, granule_response)

        # Check if the `GranuleQuery` object was instantiated with the correct
        # environment, Authorization header, and expected page size
        granule_query_mock.assert_called_once_with(mode=CMR_UAT)
        self.assertDictEqual(
            granule_query_mock.return_value.headers,
            {'Authorization': self.bearer_token_header},
        )
        granule_query_mock.return_value.get.assert_called_once_with(10)

    @patch('varinfo.cmr_search.GranuleQuery', spec=GranuleQuery)
    def test_with_shortname_version_provider(self, granule_query_mock):
        """Test when `get_granules` is called with parameters
        --shortname, collection_version, and provider--
        the query made to CMR (with `GranuleQuery.get()`) uses the same
        parameters. And `GranuleQuery.get()` is being returned
        from `get_granules` as expected.
        """
        # Mock granule response
        granule_response = [
            {
                'links': [
                    {'rel': 'http://esipfed.org/ns/fedsearch/1.1/s3#'},
                    {'rel': 'http://esipfed.org/ns/fedsearch/1.1/data#'},
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
            auth_header=self.bearer_token_header,
        )

        # Check if `get_granules` returns the CMR GranuleQuery output
        self.assertListEqual(query_response, granule_response)

        # Check if the `GranuleQuery` object was instantiated with the correct
        # environment, Authorization header, and expected page size
        granule_query_mock.assert_called_once_with(mode=CMR_UAT)
        self.assertDictEqual(
            granule_query_mock.return_value.headers,
            {'Authorization': self.bearer_token_header},
        )
        granule_query_mock.return_value.get.assert_called_once_with(10)

    @patch('varinfo.cmr_search.GranuleQuery', spec=GranuleQuery)
    def test_with_launchpad_token(self, granule_query_mock):
        """Test when `get_granules` is called with an Authorization header
        that contains a LaunchPad token (e.g., no 'Bearer ' prefix), that
        header is propagated as expected to the `GranuleQuery` instance.

        """
        granule_response = [
            {
                'links': [
                    {'rel': 'http://esipfed.org/ns/fedsearch/1.1/s3#'},
                    {'rel': 'http://esipfed.org/ns/fedsearch/1.1/data#'},
                ]
            }
        ]

        # Set return_value of `granule_query_mock` to `granule_response`
        granule_query_mock.return_value.get.return_value = granule_response
        query_response = get_granules(
            self.collection_concept_id,
            cmr_env=CMR_UAT,
            auth_header=self.launchpad_token_header,
        )

        # Check if `get_granules` returns the CMR GranuleQuery output
        self.assertListEqual(query_response, granule_response)

        # Check if the `GranuleQuery` object was instantiated with the correct
        # environment, Authorization header, and expected page size
        granule_query_mock.assert_called_once_with(mode=CMR_UAT)
        self.assertDictEqual(
            granule_query_mock.return_value.headers,
            {'Authorization': self.launchpad_token_header},
        )
        granule_query_mock.return_value.get.assert_called_once_with(10)

    @patch('varinfo.cmr_search.GranuleQuery', spec=GranuleQuery)
    def test_runtime_error(self, granule_query_mock):
        """Test if CMR has a RuntimeError and if the CMRQueryException
        is invoked.
        """
        # Mock CMR's RuntimeError
        granule_query_mock.return_value.get.side_effect = RuntimeError('CMR timed out')
        # Check if CMRQueryException is raised
        with self.assertRaises(CMRQueryException):
            get_granules(
                self.collection_concept_id,
                cmr_env=CMR_UAT,
                auth_header=self.bearer_token_header,
            )

    @patch('varinfo.cmr_search.GranuleQuery', spec=GranuleQuery)
    def test_exceptions_concept_id_with_mock(self, granule_query_mock):
        """Test if an IndexError is raised when `get_granules` is called
        for the 'G1245662789-EEDTEST' collection that is not in CMR_OPS.
        """
        # Mock IndexError when no granules are returned
        granule_query_mock.return_value.get.return_value = []

        with self.assertRaises(IndexError) as context_manager:
            get_granules(
                self.collection_concept_id, auth_header=self.bearer_token_header
            )

        self.assertEqual(
            'No granules were found with selected ' 'parameters and user permissions',
            str(context_manager.exception),
        )

    @patch('varinfo.cmr_search.GranuleQuery', spec=GranuleQuery)
    def test_exceptions_shortname_version_provider_mock(self, granule_query_mock):
        """Test if an IndexError is raised when `get_granules` is called
        for the 'G1245662789-EEDTEST' collection that is not in CMR_OPS.
        """
        # Mock IndexError when no granules are returned
        granule_query_mock.side_effect = IndexError(
            'No granules were found ' 'with selected parameters' ' and user permissions'
        )
        with self.assertRaises(IndexError) as context_manager:
            get_granules(
                collection_shortname=self.collection_short_name,
                collection_version=self.collection_version,
                provider=self.provider,
                auth_header=self.bearer_token_header,
            )

        self.assertEqual(
            'No granules were found with selected ' 'parameters and user permissions',
            str(context_manager.exception),
        )

    @patch('varinfo.cmr_search.GranuleQuery', spec=GranuleQuery)
    def test_granule_response_raises_cmr_exception(self, granule_query_mock):
        """Check if CMRQueryException is raised with a fake token."""
        granule_query_mock.side_effect = CMRQueryException('No granules found')

        with self.subTest('Test CMRQueryException ' 'with concept_id and fake token'):
            with self.assertRaises(CMRQueryException):
                get_granules(
                    self.collection_concept_id, auth_header=self.bearer_token_header
                )

        with self.subTest(
            'Test CMRQueryException with '
            'shortname, version, provider, and fake token'
        ):
            with self.assertRaises(CMRQueryException):
                get_granules(
                    collection_shortname=self.collection_short_name,
                    collection_version=self.collection_version,
                    provider=self.provider,
                    auth_header=self.bearer_token_header,
                )

    def test_granule_response_raises_exception(self):
        """Check if get `get_granules` raises MissingPositionalArgument"""
        with self.subTest('No required positonal arguments'):
            with self.assertRaises(MissingPositionalArguments) as context_manager:
                get_granules()

            self.assertEqual(
                'Missing positional argument: auth_header',
                str(context_manager.exception),
            )

        with self.subTest(
            'Positional arguments entered: ' 'shortname and collection_version'
        ):
            with self.assertRaises(MissingPositionalArguments) as context_manager:
                get_granules(
                    collection_shortname=self.collection_short_name,
                    collection_version=self.collection_version,
                )

            self.assertEqual(
                'Missing positional argument: auth_header',
                str(context_manager.exception),
            )

        with self.subTest(
            'Positional arguments entered: collection_shortname,'
            ' collection_version, and token'
        ):
            with self.assertRaises(MissingPositionalArguments) as context_manager:
                get_granules(
                    collection_shortname=self.collection_short_name,
                    collection_version=self.collection_version,
                    auth_header=self.bearer_token_header,
                )

            expected_exception = (
                'Missing positional argument: '
                'concept_id or collection_shortname, '
                'collection_version, and provider'
            )
            self.assertEqual(expected_exception, str(context_manager.exception))

    def test_exceptions_granule_link(self):
        """Check if MissingGranuleDownloadLinks is raised."""
        # Nested dict does not contain key `links`
        granule_response_no_links = [
            {'no_links': [{'rel': 'http://esipfed.org/ns/fedsearch/1.1/s3#'}]}
        ]

        # Nested dict contains `links` but `rel` does not end in '/data#'
        granule_response_links_no_rel = [
            {'links': [{'rel': 'http://esipfed.org/ns/fedsearch/1.1/s3#'}]}
        ]

        # Nested dict contains keys:
        # `links`, `inherited`, and `rel` ends in '/data#'
        granule_response_links_rel_inherit = [
            {
                'links': [
                    {
                        'rel': 'http://esipfed.org/ns/fedsearch/1.1/data#',
                        'href': 'https://data.gesdisc.earthdata.nasa.gov/data/.nc4',
                        'inherited': True,
                    }
                ]
            }
        ]

        granule_response_links_empty = [{'links': []}]

        granule_response_links_correct = [
            {
                'links': [
                    {
                        'rel': 'http://esipfed.org/ns/fedsearch/1.1/data#',
                        'title': 'Download example.nc4',
                        'hreflang': 'en-US',
                        'href': 'https://data.gesdisc.earthdata.nasa.gov/example.nc4',
                    }
                ]
            }
        ]

        with self.subTest('Granule has no `links` key'):
            with self.assertRaises(MissingGranuleDownloadLinks) as context_manager:
                get_granule_link(granule_response_no_links)
            self.assertEqual(
                f'No links for granule record: {str(granule_response_no_links)}',
                str(context_manager.exception),
            )

        with self.subTest('Granule has `links`' 'but `rel` does not end with `/data#`'):
            with self.assertRaises(MissingGranuleDownloadLinks):
                get_granule_link(granule_response_links_no_rel)

        with self.subTest(
            'Granule has `links`, `inherited`, ' 'and `rel` ends in `/data#`'
        ):
            with self.assertRaises(MissingGranuleDownloadLinks):
                get_granule_link(granule_response_links_rel_inherit)

        with self.subTest('Granule has `links` but it is an empty list'):
            with self.assertRaises(MissingGranuleDownloadLinks):
                get_granule_link(granule_response_links_empty)

        with self.subTest('Granule has `links` and all correct attributes'):
            self.assertEqual(
                get_granule_link(granule_response_links_correct),
                'https://data.gesdisc.earthdata.nasa.gov/example.nc4',
            )

    def test_download_gran_exceptions(self):
        """Check if exceptions are raised for incorrect input parameters"""
        with self.assertRaises(DirectoryCreationException):
            # Input parameter, `out_directory` is a path that does not exist
            download_granule(
                granule_link='https://foo.gov/example.nc4',
                auth_header=self.bearer_token_header,
                out_directory='/Usr/foo/dir',
            )

        with self.assertRaises(GranuleDownloadException):
            # Not a real https link
            download_granule(
                'https://foo.gov/example.nc4', auth_header=self.bearer_token_header
            )

    def _mock_requests(self, status=200, content="CONTENT"):
        """
        Mock requests.get module and it's methods content and status.
        Return the mock object.
        """
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = status
        mock_response.content = content
        return mock_response

    @patch('requests.get')
    def test_download_granule(self, mock_requests_get):
        """Check if `download_granules` returns the expected
        content for the mocked response.
        """
        link = 'https://foo.gov/example.nc4'
        expected_file_contents = 'Fake NetCDF-4 content'

        # Set mock_content as bytes for writing
        mock_content = bytes(expected_file_contents, encoding='utf-8')
        # Set the mock_response with the `_mock_requests` object content method
        mock_response = self._mock_requests(content=mock_content)
        # Set the return_value of `mock_requests_get` to mock_response
        mock_requests_get.return_value = mock_response
        file_path = download_granule(
            link, auth_header=self.bearer_token_header, out_directory=self.output_dir
        )
        # Check if `download_granule` was called once with expected parameters
        mock_requests_get.assert_called_once_with(
            link, headers={'Authorization': self.bearer_token_header}, timeout=10
        )
        # Check if download file contains expected content from `requests.get`
        with self.subTest('Test if downloaded file contains expected content'):
            with open(file_path, 'r', encoding='utf-8') as file:
                actual_file_contents = file.read()

            self.assertEqual(actual_file_contents, expected_file_contents)

    @patch('requests.get')
    def test_download_granule_with_launchpad_token(self, mock_requests_get):
        """Ensure an Authorization header containing a LaunchPad token is
        correctly used in the `requests.get` call. This header does not
        contain a 'Bearer ' prefix, and the HTTPS call made by `requests`
        should not have that prefix either.

        """
        link = 'https://foo.gov/example.nc4'
        expected_file_contents = 'Fake NetCDF-4 content'

        # Set mock_content as bytes for writing
        mock_content = bytes(expected_file_contents, encoding='utf-8')
        # Set the mock_response with the `_mock_requests` object content method
        mock_response = self._mock_requests(content=mock_content)
        # Set the return_value of `mock_requests_get` to mock_response
        mock_requests_get.return_value = mock_response
        file_path = download_granule(
            link, auth_header=self.launchpad_token_header, out_directory=self.output_dir
        )
        # Check if `download_granule` was called once with expected parameters
        mock_requests_get.assert_called_once_with(
            link, headers={'Authorization': self.launchpad_token_header}, timeout=10
        )
        # Check if download file contains expected content from `requests.get`
        with self.subTest('Test if downloaded file contains expected content'):
            with open(file_path, 'r', encoding='utf-8') as file:
                actual_file_contents = file.read()

            self.assertEqual(actual_file_contents, expected_file_contents)

    @patch('requests.get')
    def test_requests_error(self, mock_requests_get):
        """Check if the GranuleDownloadException is raised when
        the `side_effect` for the mock request is an HTTPError
        """
        link = 'https://foo.gov/example.nc4'
        mock_requests_get.return_value.side_effect = HTTPError('Wrong HTTP')
        with self.assertRaises(GranuleDownloadException):
            download_granule(link, auth_header=self.bearer_token_header)

    @patch('requests.post')
    def test_get_edl_token_from_launchpad(self, mock_requests_post):
        """Check if `get_edl_token_from_launchpad` is called with
        expected parameters and if its response contains
        the expected content.
        """
        # Mock the `request.post` call
        mock_response = Mock(spec=requests.Response)
        mock_response.json.return_value = {'access_token': 'edl-token'}
        mock_requests_post.return_value = mock_response

        # Input parameters
        urs_uat_edl_token_endpoint = urs_token_endpoints.get(CMR_UAT)
        edl_token_from_launchpad_response = get_edl_token_from_launchpad(
            self.launchpad_token_header, CMR_UAT
        )

        self.assertEqual(edl_token_from_launchpad_response, 'edl-token')

        mock_requests_post.assert_called_once_with(
            url=urs_uat_edl_token_endpoint,
            data=f'token={self.launchpad_token_header}',
            timeout=10,
        )

    @patch('requests.post')
    def test_bad_edl_token_from_launchpad_response(self, mock_requests_post):
        """Check if the `get_edl_token_from_launchpad_response` contains
        the expected content for unsuccessful response.
        """
        # Create `mock_requests_post` for a unsuccessful request
        # and set its return_value
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 400
        mock_response.raise_for_status.side_effect = HTTPError()
        mock_requests_post.return_value = mock_response

        with self.assertRaises(GetEdlTokenException):
            get_edl_token_from_launchpad(self.launchpad_token_header, CMR_UAT)

    @patch('requests.post', side_effect=Timeout('Request timed out'))
    def test_request_exception(self, mock_requests_post):
        """Check if `GetEdlTokenException` is raised if `requests.post`
        fails.
        """
        with self.assertRaises(GetEdlTokenException) as context_manager:
            get_edl_token_from_launchpad(self.launchpad_token_header, CMR_UAT)

        self.assertEqual(
            str(context_manager.exception),
            str(GetEdlTokenException('Request timed out')),
        )

    @patch('requests.post')
    def test_get_edl_token_header_with_launchpad(self, mock_requests_post):
        """Test if an EDL token and its appropriate header is returned given
        a LaunchPad token.
        """
        # Create successful mock response
        mock_response = Mock(spec=requests.Response)
        mock_response.ok = True
        mock_response.json.return_value = {'access_token': 'edl-token'}
        mock_requests_post.return_value = mock_response

        test_bearer_token = get_edl_token_header(self.launchpad_token_header, CMR_UAT)
        self.assertEqual(test_bearer_token, 'Bearer edl-token')

    def test_get_edl_token_header_with_edl_token(self):
        """Test if an EDL token is entered with its "Bearer" header prefix.
        If it is the same EDL token is returned.
        """
        test_bearer_token = get_edl_token_header(self.bearer_token_header, CMR_UAT)
        self.assertEqual(test_bearer_token, self.bearer_token_header)

    def test_get_dmr_xml_url_raises(self):
        """Check if MissingGranuleDownloadLinks is raised with get_dmr_xml_url,
        when the "links" attribute in the "RelatedUrls" of a granule response don't contain
        the correct fields for an OPeNDAP service url.
        """

        # Nested dict does not contain key `links`
        granule_response_no_links = [
            {'no_links': [{'rel': 'http://esipfed.org/ns/fedsearch/1.1/s3#'}]}
        ]

        # Nested dict contains `links` but `rel` does not end in '/service#'
        granule_response_links_no_rel = [
            {'links': [{'rel': 'http://cool-science-data.#'}]}
        ]

        # Nested dict contains "inherited" key
        granule_response_links_rel_inherit = [
            {
                'links': [
                    {
                        'rel': 'http://cool-science-data/1.1/service#',
                        'href': 'http://cool-science-data/data/.nc4',
                        'inherited': True,
                    }
                ]
            }
        ]

        granule_response_links_empty = [{'links': []}]

        granule_response_links_no_opendap = [
            {
                'links': [
                    {
                        'rel': 'http://cool-science-data/1.1/service#',
                        'title': 'OPeNDAP request URL (GET DATA : OPENDAP DATA)',
                        'hreflang': 'en-US',
                        'href': 'https://fake.earthdata.nasa.gov/example.nc4',
                    }
                ]
            }
        ]

        with self.subTest('Granule has no `links` key'):
            with self.assertRaises(MissingGranuleDownloadLinks) as context_manager:
                get_dmr_xml_url(granule_response_no_links)
            self.assertEqual(
                f'No links for granule record: {str(granule_response_no_links)}',
                str(context_manager.exception),
            )

        with self.subTest(
            'Granule has `links`' 'but `rel` does not end with `/service#`'
        ):
            with self.assertRaises(MissingGranuleDownloadLinks):
                get_dmr_xml_url(granule_response_links_no_rel)

        with self.subTest(
            'Granule has `links` and `rel` ends in `/service#`, but contains `inherited` field.'
        ):
            with self.assertRaises(MissingGranuleDownloadLinks):
                get_dmr_xml_url(granule_response_links_rel_inherit)

        with self.subTest('Granule has `links` but it is an empty list'):
            with self.assertRaises(MissingGranuleDownloadLinks):
                get_dmr_xml_url(granule_response_links_empty)

        with self.subTest(
            'Granule has `links` and `rel` ends in `/service#`, but opendap is NOT in url.'
        ):
            with self.assertRaises(MissingGranuleDownloadLinks):
                get_dmr_xml_url(granule_response_links_no_opendap)

    def test_get_dmr_xml_url(self):
        """Assert the correct OPeNDAP url is returned for a good granule response
        (i.e. when the "links" attribute in the "RelatedUrls" of a granule response has
        the correct fields for an OPeNDAP service url).
        """
        granule_response_links_correct_cloud_opendap = [
            {
                'links': [
                    {
                        'rel': 'http://cool-science-data/1.1/service#',
                        'title': 'OPeNDAP request URL (GET DATA : OPENDAP DATA)',
                        'hreflang': 'en-US',
                        'href': 'https://fake.opendap.earthdata.nasa.gov/example.hdf',
                    }
                ]
            }
        ]

        granule_response_links_correct_onprem_opendap = [
            {
                'links': [
                    {
                        'rel': 'http://cool-science-data/1.1/service#',
                        'type': 'application/x-hdf',
                        'title': 'OPeNDAP request URL (GET DATA : OPENDAP DATA)',
                        'hreflang': 'en-US',
                        'href': 'https://some.fake.server.onprem.opendap.nasa.gov/example.hdf',
                    }
                ]
            }
        ]
        with self.subTest('Cloud OPeNDAP Related Urls response'):
            self.assertEqual(
                get_dmr_xml_url(granule_response_links_correct_cloud_opendap),
                'https://fake.opendap.earthdata.nasa.gov/example.hdf.dmr.xml',
            )

        with self.subTest('Onprem OPeNDAP Related Urls response'):
            with self.assertRaises(MissingGranuleDownloadLinks):
                get_dmr_xml_url(granule_response_links_correct_onprem_opendap),
                'https://some.fake.server.onprem.opendap.nasa.gov/example.hdf.dmr.xml',
