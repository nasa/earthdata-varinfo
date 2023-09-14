''' This module generates UMM-Var records for a specified collection, and
    optionally will publish those records to CMR.
    `generation_collection_umm_var` will:

    * Performing a CMR granule search with collection-based query parameters.
    * Downloading the granule locally.
    * Parse the variable metadata from the granule using VarInfoFromNetCDF4.
    * Generate UMM-Var JSON as a dictionary for each identified variable.
    * (Optional) Publish each UMM-Var entry to the selected CMR environment.

'''
from tempfile import TemporaryDirectory
from typing import Dict, List, Union

from cmr import CMR_UAT

from varinfo import VarInfoFromNetCDF4
from varinfo.cmr_search import (CmrEnvType, download_granule, get_granule_link,
                                get_granules)
from varinfo.umm_var import get_all_umm_var, publish_all_umm_var


# Custom return type: either a list of UMM-Var JSON (a list of dictionaries),
# or a list of strings (either concept IDs or error strings).
UmmVarReturnType = List[Union[Dict, str]]


def generate_collection_umm_var(collection_concept_id: str,
                                auth_header: str,
                                cmr_env: CmrEnvType = CMR_UAT,
                                publish: bool = False) -> UmmVarReturnType:
    ''' Run all the of the functions for downloading and publishing
        a UMM-Var entry to CMR given:

        * collection_concept_id: Concept ID for collection that variables have
          been generated for.
        * cmr_env: URLs for CMR environments (OPS, UAT, and SIT)
        * auth_header: Authorization HTTP header, containing either:
          - A LaunchPad token: 'Authorization: <token>'
          - An EDL bearer token: 'Authorization: Bearer <token>'
        * publish: Optional argument determining whether to publish the
          generated UMM-Var records to the indicated CMR instance. Defaults to
          False.

    '''
    granule_response = get_granules(collection_concept_id, cmr_env,
                                    auth_header)

    # Get the data download URL for the most recent granule (NetCDF-4 file)
    granule_link = get_granule_link(granule_response)

    with TemporaryDirectory() as temp_dir:
        # Download file to runtime environment
        local_granule = download_granule(granule_link,
                                         auth_header,
                                         out_directory=temp_dir)

        # Parse the granule with VarInfo to map all variables and relations:
        var_info = VarInfoFromNetCDF4(local_granule)

        # Generate all the UMM-Var records:
        all_umm_var_records = get_all_umm_var(var_info)

    if publish:
        # Publish to CMR and construct an output object that is a list of
        # strings. These strings will be either variable concept IDs or
        # error messages returned from CMR.
        publication_response = publish_all_umm_var(collection_concept_id,
                                                   all_umm_var_records,
                                                   auth_header, cmr_env)

        return_value = [variable_response
                        if variable_response.startswith('V')
                        else ': '.join([variable_name, variable_response])
                        for variable_name, variable_response
                        in publication_response.items()]
    else:
        # If not publishing, return the full UMM-Var JSON records
        return_value = list(all_umm_var_records.values())

    return return_value
