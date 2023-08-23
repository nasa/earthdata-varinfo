from shutil import rmtree
from tempfile import mkdtemp
from unittest import TestCase
from unittest.mock import patch, Mock

from cmr import (GranuleQuery, CMR_UAT)
import requests
from requests.exceptions import HTTPError

from varinfo.cmr_search import (get_granules, get_granule_link,
                                download_granule)
from varinfo.exceptions import (CMRQueryException, MissingGranuleDownloadLinks,
                                MissingPositionalArguments, GranuleDownloadException)


class TestQuery(TestCase):
    ''' A class for testing functions in cmr_search.
    '''
    @classmethod
    def setUp(self):
        self.output_dir = mkdtemp()

    def tearDown(self):
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
            {'links': [
                {'rel': 'http://esipfed.org/ns/fedsearch/1.1/s3#'},
                {'rel': 'http://esipfed.org/ns/fedsearch/1.1/data#'}
            ]
            }
        ]
        concept_id = 'G1245662789-EEDTEST'  # EEDTEST granule in UAT

        # Set return_value of `granule_query_mock` to `granule_response`
        granule_query_mock.return_value.get.return_value = granule_response
        query_response = get_granules(concept_id,
                                      cmr_env=CMR_UAT,
                                      token='foo')
        # Check if `get_granules` returns the CMR GranuleQuery output
        self.assertListEqual(query_response, granule_response)

        # Check if the `GranuleQuery` object was
        # instantiated with the correct environment, token, and
        # expected page size
        granule_query_mock.assert_called_once_with(mode=CMR_UAT)
        granule_query_mock.return_value.bearer_token.assert_called_once_with
        ('foo')
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
            {'links': [
                {'rel': 'http://esipfed.org/ns/fedsearch/1.1/s3#'},
                {'rel': 'http://esipfed.org/ns/fedsearch/1.1/data#'}
            ]
            }
        ]
        shortname = 'M2T1NXSLV'
        collection_version = '5.12.4'
        provider = 'EEDTEST'

        # Set return_value of `granule_query_mock` to `granule_response`
        granule_query_mock.return_value.get.return_value = granule_response
        query_response = get_granules(shortname=shortname,
                                      collection_version=collection_version,
                                      provider=provider,
                                      cmr_env=CMR_UAT,
                                      token='foo')

        # Check if `get_granules` returns the CMR GranuleQuery output
        self.assertListEqual(query_response, granule_response)

        # Check if the `GranuleQuery` object was
        # instantiated with the correct environment, token, and
        # expected page size
        granule_query_mock.assert_called_once_with(mode=CMR_UAT)
        granule_query_mock.return_value.bearer_token.assert_called_once_with
        ('foo')
        granule_query_mock.return_value.get.assert_called_once_with(10)


    @patch('varinfo.cmr_search.GranuleQuery', spec=GranuleQuery)
    def test_runtime_error(self, granule_query_mock):
        ''' Test if CMR has a RuntimeError and if the CMRQueryException
            is invoked.
        '''
        concept_id = 'G1245662789-EEDTEST'  # EEDTEST granule in UAT
        # Mock CMR's RuntimeError
        granule_query_mock.return_value.get.side_effect = RuntimeError('CMR timed out')
        # Check if CMRQueryException is raised
        with self.assertRaises(CMRQueryException):
            get_granules(concept_id, cmr_env=CMR_UAT, token='foo')


    @patch('varinfo.cmr_search.GranuleQuery', spec=GranuleQuery)
    def test_exceptions_concept_id_with_mock(self, granule_query_mock):
        ''' Test if an IndexError is raised when `get_granules` is called 
            for the 'G1245662789-EEDTEST' collection that is not in CMR_OPS.
        '''
        concept_id = 'G1245662789-EEDTEST'  # EEDTEST granule in UAT
        # Mock IndexError when no granules are returned
        granule_query_mock.return_value.get.return_value = []
        
        with self.assertRaises(IndexError) as cm:
            get_granules(concept_id, token='foo')
        self.assertEqual('No granules were found with selected '
                         'parameters and user permissions', str(cm.exception))


    @patch('varinfo.cmr_search.GranuleQuery', spec=GranuleQuery)
    def test_exceptions_shortname_version_provider_mock(self,
                                                        granule_query_mock):
        ''' Test if an IndexError is raised when `get_granules` is called
            for the 'G1245662789-EEDTEST' collection that is not in CMR_OPS.
        '''
        shortname = 'M2T1NXSLV'
        collection_version = '5.12.4'
        provider = 'EEDTEST'  # EEDTEST granule in UAT

        # Mock IndexError when no granules are returned
        granule_query_mock.side_effect = IndexError('No granules were found '
                                                    'with selected parameters'
                                                    ' and user permissions')
        with self.assertRaises(IndexError) as cm:
            get_granules(shortname=shortname,
                         collection_version=collection_version,
                         provider=provider,
                         token='foo')
        self.assertEqual('No granules were found with selected '
                         'parameters and user permissions', str(cm.exception))


    @patch('varinfo.cmr_search.GranuleQuery', spec=GranuleQuery)
    def test_granule_response_raises_cmr_exception(self, granule_query_mock):
        ''' Check if CMRQueryException is raised with a fake token.
        '''
        concept_id = 'G1245662789-EEDTEST'  # EEDTEST granule in UAT
        granule_query_mock.side_effect = CMRQueryException('No granules found')

        with self.subTest('Test CMRQueryException '
                          'with concept_id and fake token'):
            with self.assertRaises(CMRQueryException):
                get_granules(concept_id, token='foo')

        with self.subTest('Test CMRQueryException with '
                          'shortname, version, provider, and fake token'):
            with self.assertRaises(CMRQueryException):
                get_granules(shortname='M2T1NXSLV',
                             collection_version='5.12.4',
                             provider='EEDTEST',
                             token='foo')


    def test_granule_response_raises_exception(self):
        ''' Check if get `get_granules` raises MissingPositionalArgument
        '''
        with self.subTest('No required positonal arguments'):
            with self.assertRaises(MissingPositionalArguments) as cm:
                get_granules()
            self.assertEqual('Missing positional argument: token', 
                             str(cm.exception))

        with self.subTest('Positional arguments entered: '
                          'shortname and collection_version'):
            with self.assertRaises(MissingPositionalArguments) as cm:
                get_granules(shortname='M2T1NXSLV',
                             collection_version='5.12.4')
            self.assertEqual('Missing positional argument: token', 
                             str(cm.exception))

        with self.subTest('Positional arguments entered: '
                          'shortname, collection_version, and token'):
            with self.assertRaises(MissingPositionalArguments) as cm:
                get_granules(shortname='M2T1NXSLV',
                             collection_version='5.12.4',
                             token='foo')
            self.assertEqual('Missing positional argument: concept_id ' 
                             'or shortname, collection_version, and provider',
                              str(cm.exception))


    def test_exceptions_granule_link(self):
        ''' Check if MissingGranuleDownloadLinks is raised.
        '''
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
                'title': 'Download MERRA2_400.tavg1_2d_slv_Nx.20230701.nc4',
                'hreflang': 'en-US',
                'href': 'https://data.gesdisc.earthdata.nasa.gov/.nc4'
            }]
        }]

        with self.subTest('Granule has no `links` key'):
            with self.assertRaises(MissingGranuleDownloadLinks) as cm:
                get_granule_link(granule_response_no_links)
            self.assertEqual('No links for granule record: ' + 
                             str(granule_response_no_links), str(cm.exception))

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
            self.assertEqual(get_granule_link(granule_response_links_correct),
                             'https://data.gesdisc.earthdata.nasa.gov/.nc4')
    
    
    def test_download_gran_exceptions(self):
        ''' Check if exceptions are raised for incorrect input parameters
        '''
    
        with self.assertRaises(MissingPositionalArguments):
            # Input parameter, token, is missing
            download_granule(granule_link='https://foo.gov/example.nc4')
            
        with self.assertRaises(NotADirectoryError):
            # Input parameter, `out_directory` should be a real directory
            download_granule('https://foo.gov/example.nc4', 
                             '/Usr/foo/dir',
                             'foo')
        
        with self.assertRaises(MissingPositionalArguments):
            # Missing argument, `granule_link`
            download_granule(token='foo')
        
        with self.assertRaises(ValueError):
            # `granule_link` should be str or bytes like not int
            download_granule(granule_link=0, token='foo')
        
        with self.assertRaises(GranuleDownloadException):
            # Not a real https link
            download_granule('https://foo.gov/example.nc4', token='foo')
    
    
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
        # Set mock_content as bytes for writing
        mock_content = bytes(link, encoding='utf-8')
        # Set the mock_response with the `_mock_requests` object content method
        mock_response = self._mock_requests(content=mock_content)
        # Set the return_value of `mock_requests_get` to mock_response
        mock_requests_get.return_value = mock_response
        file_path = download_granule(link, self.output_dir, token='foo')
        # Check if `download_granule` was called once with expected parameters
        mock_requests_get.assert_called_once_with(link, headers=
                                                  {'Authorization':
                                                      f'Bearer {"foo"}'},
                                                  timeout=10)
        # Check if download file contains expected content from `requests.get`
        with self.subTest('Test if the downloaded file contains '
                          'expected content'):
            with open(file_path) as file:
                data = file.read()
            self.assertEqual(data, link)
    
    
    @patch('requests.get')
    def test_requests_error(self, mock_requests_get):
        ''' Check if the GranuleDownloadException is raised when
            the `side_effect` for the mock request is an HTTPError
        '''
        link = 'https://foo.gov/example.nc4'
        mock_requests_get.return_value.side_effect = HTTPError('Wrong HTTP')
        with self.assertRaises(GranuleDownloadException):
            download_granule(link, token='foo')
