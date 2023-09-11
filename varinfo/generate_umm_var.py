''' This module generates and publishes a UMM-Var entry, by performing a
    CMR granule search and then downloading the granule locally,
    reading the variable metadata from the granule,
    formatting the variable metadata into a UMM-Var entry, and 
    (optional) publishing the UMM-Var entry to the selected CMR environment.

'''
from shutil import rmtree
from tempfile import mkdtemp
from typing import Dict
import json

from cmr import CMR_UAT

from varinfo import VarInfoFromNetCDF4
from varinfo.cmr_search import get_granules, download_granule, get_granule_link
from varinfo.umm_var import get_all_umm_var, publish_all_umm_var


def handler(collection_id: str,
            auth_header: str,
            cmr_env: CMR_UAT = CMR_UAT) -> Dict:
    ''' Run all the of the functions for downloading and publishing
        a UMM-Var entry to CMR given:
        * collection_id: a collection's concept_id
        * all_umm_var_dict: a nested dictionary containing
            dictionaries of all UMM-Var entries for a collection
        * auth_header: Earthdata Login (EDL) bearer_token or LaunchPad token
            with their respective headers
        * cmr_env: CMR environments (OPS, UAT, and SIT)
    '''
    granule_response = get_granules(collection_id, CMR_UAT, auth_header)

    # Get the data download URL for the most recent granule (NetCDF-4 file)
    granule_link = get_granule_link(granule_response)

    # Make a temporary directory
    temp_dir = mkdtemp()

    # Download file to lambda runtime environment
    local_granule = download_granule(granule_link,
                                     auth_header,
                                     out_directory=temp_dir)

    # Parse the granule with VarInfo:
    var_info = VarInfoFromNetCDF4(local_granule)

    # Generate all the UMM-Var records:
    all_umm_var_dict = get_all_umm_var(var_info)

    # Probably need to perform clean-up of temp_dir at this point:
    rmtree(temp_dir)

    # Also will need optional thing to publish UMM-Var to CMR
    # Then return either UMM-Var as JSON or the concept IDs for new records.

    # END OF FUNCTIONALITY TO COMBINE

    # Return a successful response (may not be correct,
    # given this might not be invoked similarly to API Gateway)
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps(list(all_umm_var_dict.values()))
    } 