from cmr import (GranuleQuery, CMR_OPS, CMR_UAT, CMR_SIT)
import requests
from unittest import TestCase
from unittest.mock import patch, Mock
from varinfo.cmr_search import (query_cmr, get_granule_link)

class TestQuery(TestCase):
    ''' A class for testing functions in cmr_search 
    '''
    @patch('cmr_search.GranuleQuery', spec=GranuleQuery)
    def test_with_concept_id(self, granule_query_mock):
            ''' Check if `query_cmr` was called with parameter: `concept_id`
                and if the expected values are returned
            '''
            granule_response = [    # Mock granule response
                {
                    'links': [
                        {'rel': 'http://esipfed.org/ns/fedsearch/1.1/s3#'},
                        {'rel': 'http://esipfed.org/ns/fedsearch/1.1/data#'}
                        ]
                    }
                ]
            
            concept_id = 'G1245662789-EEDTEST'  # EEDTEST granule in UAT
            
            # Set return_value of `granule_query_mock` to `granule_response`
            granule_query_mock.return_value.get.return_value = granule_response
            query_response = query_cmr(concept_id, env=CMR_UAT)
            
            # Check the `query_response` against the mock response
            self.assertListEqual(query_response, granule_response)
            
            # Check if `query_cmr` was called with env=CMR_UAT
            granule_query_mock.assert_called_once_with(mode=CMR_UAT)
            
            # Check if `query_cmr` was called with page_size=10
            granule_query_mock.return_value.get.assert_called_once_with(10)
    
    
    @patch('cmr_search.GranuleQuery', spec=GranuleQuery)
    def test_with_sn_ver_provider(self, granule_query_mock):
            ''' Check if `query_cmr` was called with parameters: 
                `short_name`, 'version` and `provider` were called
                and if the expected values are returned
            '''
            granule_response = [    # Mock granule response
                {
                    'links': [
                        {'rel': 'http://esipfed.org/ns/fedsearch/1.1/s3#'},
                        {'rel': 'http://esipfed.org/ns/fedsearch/1.1/data#'}
                        ]
                    }
                ]
            
            sn = 'M2T1NXSLV'
            ver = '5.12.4'
            provider = 'EEDTEST'
            
            # Set return_value of `granule_query_mock` to `granule_response`
            granule_query_mock.return_value.get.return_value = granule_response
            
            query_response = query_cmr(sn=sn, 
                                       ver=ver, 
                                       provider=provider, 
                                       env=CMR_UAT)
            
            # Check the `query_response` against the mock response
            self.assertListEqual(query_response, granule_response)
            
            # Check if `query_cmr` was called with env=CMR_UAT
            granule_query_mock.assert_called_once_with(mode=CMR_UAT)
            
            # Check if `query_cmr` was called with page_size=10
            granule_query_mock.return_value.get.assert_called_once_with(10)
    
    
    def test_granule_response_raises_exception(self):
        ''' Check if IndexError and TypeError is raised
        '''
        with self.assertRaises(IndexError):
            # `G1245662789-EEDTEST` is not in CMR_OPS so IndexError is raised
            query_cmr('G1245662789-EEDTEST')
        
        with self.assertRaises(TypeError):
            # No required positional arguments so TypeError is raised
            query_cmr()
        
        
    
    def test_exceptions_granule_link(self):
        ''' Check if IndexError, KeyError and TypeError is raised
        '''
        # Nested dict does not contain key `links`
        granule_response_no_links = [{
            'no_links': [{'rel': 'http://esipfed.org/ns/fedsearch/1.1/s3#'}]
            }]
        
        # Nested dict contains `links` but `rel` does not end in '/data#'
        granule_response_links_no_rel = [{
            'links': [{'rel': 'http://esipfed.org/ns/fedsearch/1.1/s3#'}]
            }]
        
        ''' Nested dict contains keys:
                `links`, `inherited`, and `rel` ends in '/data#' '''
        granule_response_links_rel_inherit = [{
            'links': [{
                'rel': 'http://esipfed.org/ns/fedsearch/1.1/data#',
                'href': 'https://data.gesdisc.earthdata.nasa.gov/data/.nc4',
                'inherited': True
                }]
            }]
        
        with self.assertRaises(IndexError):
            get_granule_link(granule_response_no_links)
        
        with self.assertRaises(KeyError):
            get_granule_link(granule_response_links_no_rel)
        
        with self.assertRaises(KeyError):
            get_granule_link(granule_response_links_rel_inherit)
        
        with self.assertRaises(TypeError):
            # No required positional arguments so TypeError is raised
            get_granule_link()
