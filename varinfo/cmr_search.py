''' This script leverages the python-cmr library to conduct a CMR search
'''
# Import CMR query and environment types
from cmr import GranuleQuery, CMR_OPS, CMR_UAT, CMR_SIT

def query_cmr(concept_id: str = None, sn: str = None, 
             ver: str = None, provider: str = None,
             page_size: int = 10, env: CMR_OPS = CMR_OPS) -> list:
    ''' 
    Search CMR given:
        * concept_id: a collection or granule's IDs
        * sn/short_name: 'SNDRSNIML2CCPRET' or 'M2T1NXSLV'
        * ver/version: a collection version (e.g. '2' or 5.12.4')
        * provider: data center ID (e.g. GES_DISC, PODAAC, POCLOUD, EEDTEST)
        * page_size: number of links to return, the default is 10
        * env/environment: CMR environments (OPS, UAT, and SIT)
    '''
    granule_query = GranuleQuery(mode=env)
    
    if concept_id: # Check for concept_id
        # Set `sort_key` = `-start_date` to get most recent granules first
        query_parameters = {'concept_id': concept_id,
                            'sort_key': '-start_date'}
    
    elif sn and ver and provider: 
        # Check for short_name, version, and provider
        query_parameters = {'short_name': sn, 
                            'version': ver, 
                            'provider': provider,
                            'sort_key': '-start_date'}
    else:
        # If no short_name, version and provider raise TypeErorr
        raise TypeError(
            'Missing required positional argument: \
                concept_id or sn, ver, and provider')
    
    # Assign parameters to GranuleQuery:
    granule_query.parameters(downloadable=True,
                             **query_parameters)
    
    try:
        granule_response = granule_query.get(page_size)
        
        # Check if granule_response is an empty list
        if len(granule_response) == 0:
            raise IndexError('No granules were found with selected \
                parameters and user permissions')
        
        return granule_response

    # Generic Exception for python-cmr
    except Exception as err:
        raise err


def get_granule_link(query_response: list) -> str:
    ''' Get the granule download link from CMR
    '''
    for link in query_response[0].get('links', [[]]):
        if len(link) == 0: # Check if the granule record contains `links`
            raise IndexError('Granule record does not contain links')
            
        # Check if the links are download links
        if link['rel'].endswith('/data#') and 'inherited' not in link:
                return link['href']
        raise KeyError('Links are not downloadable')