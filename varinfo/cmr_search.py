''' This script leverages the `python-cmr` library to conduct a CMR search
    and get a granule download URL. With the granule download URL and the
    `requests` library a granule is downloaded via https and saved locally.
'''
import os.path

# Import CMR query and environment types
from cmr import GranuleQuery, CMR_OPS
import requests

from varinfo.exceptions import (CMRQueryException, MissingGranuleDownloadLinks,
                                MissingPositionalArguments, GranuleDownloadException)


def get_granules(concept_id: str = None,
                 shortname: str = None,
                 collection_version: str = None,
                 provider: str = None,
                 cmr_env: CMR_OPS = CMR_OPS,
                 token: str = None) -> list:
    ''' Search CMR given:
        * concept_id: a collection or granule's IDs
        * shortname/short_name: 'SNDRSNIML2CCPRET' or 'M2T1NXSLV'
        * collection_version/version: a collection version: '2' or 5.12.4'
        * provider: data center ID (e.g. GES_DISC, PODAAC, POCLOUD, EEDTEST)
        * cmr_env/mode: CMR environments (OPS, UAT, and SIT)
        * token: Earthdata Login (EDL) bearer_token
    For a successful search response concept_id
    or short_name, version and provider have must be entered
    along with a bearer_token.
    '''
    granule_query = GranuleQuery(mode=cmr_env)

    # Check if bearer_token was entered
    if token is not None:
        granule_query.bearer_token(token)
    else:
        raise MissingPositionalArguments('token')

    if concept_id is not None:  # Check for concept_id
        # Set `sort_key` = `-start_date` to get most recent granules first
        query_parameters = {'concept_id': concept_id}

    # Check for short_name, version, and provider
    elif shortname and collection_version and provider is not None:
        query_parameters = {'short_name': shortname,
                            'version': collection_version,
                            'provider': provider}
    else:
        # If no short_name, version and provider raise MissingPositionalArguments
        raise MissingPositionalArguments('concept_id '
                                         'or shortname, collection_version, and provider')
    # Assign parameters to GranuleQuery
    granule_query.parameters(downloadable=True,
                             sort_key='-start_date',
                             **query_parameters)
    try:
        # .get() is the number of links to return (e.g. page_size)
        granule_response = granule_query.get(10)

    except Exception as cmr_exception:
        # Use custom exception, CMRQueryException, if CMR fails
        raise CMRQueryException(str(cmr_exception))

    # Check if granule_response is an empty list
    if len(granule_response) == 0:
        raise IndexError('No granules were found with selected '
                         'parameters and user permissions')
    return granule_response


def get_granule_link(granule_response: list) -> str:
    ''' Get the granule download link from CMR
    '''
    granule_link = next((link['href']
                         for link in granule_response[0].get('links', [])
                         if link['rel'].endswith('/data#') and 'inherited' not in link), None)

    if granule_link is None:
        raise MissingGranuleDownloadLinks(granule_response)
    return granule_link


def download_granule(granule_link: str = None,
                     out_directory: str = os.getcwd(),
                     token: str = None) -> str:
    ''' Use the requests module to download data via https.
        * granule_link: granule download URL.
        * out_directory: path to save downloaded granule
            (the default is the current directory).
        * token: Earthdata Login (EDL) bearer_token
    '''
    if granule_link is not None:  # Check if input parameter was entered
        if isinstance(granule_link, str):  # Check if granule link is a string
            # Check if `out_directory` is a directory and create out_filename
            if os.path.isdir(out_directory):
                out_filename = out_directory + '/' + os.path.basename(granule_link)
            else:
                raise NotADirectoryError('Input directory '
                                         '"out_directory" is not a directory')
        else:
            raise ValueError('Not a string')
    else:
        raise MissingPositionalArguments('granule_link')

    if token is not None:
        try:  # Write content of data to out_filename and return response
            response = requests.get(granule_link,
                                    headers={'Authorization': f'Bearer {token}'},
                                    timeout=10)
            with open(out_filename, 'wb') as file_download:
                file_download.write(response.content)
            return out_filename
        except Exception as requests_exception:
            # Custom exception for error from `requests.get`
            raise GranuleDownloadException(str(requests_exception))
    else:
        raise MissingPositionalArguments('token')
