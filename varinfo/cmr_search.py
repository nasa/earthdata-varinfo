''' This script leverages the `python-cmr` library to conduct a CMR search
    and get a granule download URL. With the granule download URL and the
    `requests` library a granule is downloaded via https and saved locally.
'''
import os.path

# Import CMR query and environment types
from cmr import GranuleQuery, CMR_OPS
import requests

from varinfo.exceptions import (CMRQueryException,
                                MissingGranuleDownloadLinks,
                                MissingPositionalArguments,
                                GranuleDownloadException,
                                DirectoryCreationException)


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
        raise CMRQueryException(str(cmr_exception)) from cmr_exception

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


def download_granule(granule_link: str,
                     token: str,
                     out_directory: str = os.getcwd()) -> str:
    ''' Use the requests module to download data via https.
        * granule_link: granule download URL.
        * token: Earthdata Login (EDL) bearer_token
        * out_directory: path to save downloaded granule
            (the default is the current directory).
    '''
    # Create `out_directory` if it does not exist and create out_filename
    if not os.path.isdir(out_directory):
        try:
            os.mkdir(out_directory)
        except Exception as os_exception:
            raise DirectoryCreationException(
                str(os_exception)) from os_exception
    out_filename = os.path.join(out_directory, os.path.basename(granule_link))

    try:  # Write content of data to out_filename and return response
        response = requests.get(granule_link,
                                headers={'Authorization': f'Bearer {token}'},
                                timeout=10)
        with open(out_filename, 'wb') as file_download:
            file_download.write(response.content)
        return out_filename
    except Exception as requests_exception:
        # Custom exception for error from `requests.get`
        raise GranuleDownloadException(
            str(requests_exception)) from requests_exception
