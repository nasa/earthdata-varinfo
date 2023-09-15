''' This script leverages the `python-cmr` library to conduct a CMR search
    and get a granule download URL. With the granule download URL and the
    `requests` library a granule is downloaded via https and saved locally.
'''
from typing import Literal
import os.path

from cmr import GranuleQuery, CMR_OPS, CMR_SIT, CMR_UAT
import requests

from varinfo.exceptions import (CMRQueryException,
                                MissingGranuleDownloadLinks,
                                MissingPositionalArguments,
                                GranuleDownloadException,
                                DirectoryCreationException)


CmrEnvType = Literal[CMR_OPS, CMR_UAT, CMR_SIT]


def get_granules(concept_id: str = None,
                 collection_shortname: str = None,
                 collection_version: str = None,
                 provider: str = None,
                 cmr_env: CmrEnvType = CMR_OPS,
                 auth_header: str = None) -> list:
    ''' Search CMR to retrieve granules for a specific collection given:

        * concept_id: a CMR collection or granule concept ID. For most
          workflows, including the generateVariableDrafts within the CMR
          GraphQL interface, this is anticipated to be a collection concept ID,
          but the `GranuleQuery` object can also make queries with a granule
          concept IDs.
        * shortname/short_name: e.g., 'SNDRSNIML2CCPRET' or 'M2T1NXSLV'
        * collection_version/version: a collection version: '2' or 5.12.4'
        * provider: data center ID (e.g. GES_DISC, PODAAC, POCLOUD, EEDTEST)
        * cmr_env/mode: CMR environments (OPS, UAT, and SIT)
        * auth_header: Authorization HTTP header, either:
          - A header with a LaunchPad token: 'Authorization: <token>'
          - An header with an EDL bearer token: 'Authorization: Bearer <token>'

        For a successful search response concept_id or short_name, version and
        provider must be entered along with a bearer_token.

    '''
    granule_query = GranuleQuery(mode=cmr_env)

    # Ensure the Authorization header was provided for CMR authentication
    if auth_header is not None:
        granule_query.headers = {'Authorization': auth_header}
    else:
        raise MissingPositionalArguments('auth_header')

    if concept_id is not None:
        # If a collection or granule concept ID is specified, can query CMR
        # just using that parameter.
        query_parameters = {'concept_id': concept_id}
    elif collection_shortname and collection_version and provider is not None:
        # Otherwise use the combination of short_name, version, and provider
        query_parameters = {'short_name': collection_shortname,
                            'version': collection_version,
                            'provider': provider}
    else:
        # If neither condition is met, there aren't enough CMR query parameters
        # to identify the collection.
        raise MissingPositionalArguments('concept_id or collection_shortname, '
                                         'collection_version, and provider')

    # Assign parameters to GranuleQuery
    granule_query.parameters(downloadable=True,
                             sort_key='-start_date',
                             **query_parameters)
    try:
        # .get() is the number of links to return (e.g. page_size)
        granule_response = granule_query.get(10)

    except Exception as cmr_exception:
        # Capture exception raised due to CMR failure and return an exception
        # with a more user-friendly message.
        raise CMRQueryException(str(cmr_exception)) from cmr_exception

    if len(granule_response) == 0:
        # No granules were identified, so no files can be downloaded and parsed
        raise IndexError('No granules were found with selected '
                         'parameters and user permissions')

    return granule_response


def get_granule_link(granule_response: list) -> str:
    ''' Get the granule download link from CMR. '''
    granule_link = next((link['href']
                         for link in granule_response[0].get('links', [])
                         if link['rel'].endswith('/data#') and 'inherited' not in link), None)

    if granule_link is None:
        raise MissingGranuleDownloadLinks(granule_response)

    return granule_link


def download_granule(granule_link: str,
                     auth_header: str,
                     out_directory: str = os.getcwd()) -> str:
    ''' Use the requests module to download data via https.
        * granule_link: granule download URL.
        * auth_header: Authorization HTTP header, either:
          - A header with a LaunchPad token: 'Authorization: <token>'
          - An header with an EDL bearer token: 'Authorization: Bearer <token>'
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

    try:
        # Write content of data to out_filename and return response
        response = requests.get(granule_link,
                                headers={'Authorization': auth_header},
                                timeout=10)

        with open(out_filename, 'wb') as file_download:
            file_download.write(response.content)

        return out_filename
    except Exception as requests_exception:
        # Custom exception for error from `requests.get`
        raise GranuleDownloadException(
            str(requests_exception)) from requests_exception
