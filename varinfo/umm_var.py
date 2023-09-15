""" Functionality to convert a Variable instance, from either a DMR or NetCDF-4
    input, to a UMM-Var record.

    To use:

    ```
    from varinfo import VarInfoFromNetCDF4
    from varinfo.umm_var import export_all_umm_var, get_all_umm_var

    varinfo_gpm = VarInfoFromNetCDF4('/path/to/GPM_3IMERGHH/granule.nc4',
                                     short_name='GPM_3IMERGHH')

    umm_var_records = get_all_umm_var(varinfo_gpm)

    # To export to disk:
    export_all_umm_var(umm_var_records.values(), output_dir='path/to/directory')
    ```

    To validate generated records:

    ```
    import json
    from jsonschema import validate

    with open('tests/unit/data/umm_var_json_schema_1.8.2.json') as file_handler:
        umm_var_schema = json.load(file_handler)

    for record in umm_var_records:
        validate(schema=umm_var_schema, instance=umm_var_schema)
    ```

"""
from os import makedirs
from os.path import isfile, join as join_path
from typing import Any, Dict, List, Optional, Union
import json
import requests

from cmr import CMR_UAT
from numpy import floating as np_floating, integer as np_integer

from varinfo.cmr_search import CmrEnvType
from varinfo.exceptions import InvalidExportDirectory
from varinfo.var_info import VarInfoBase
from varinfo.variable import VariableBase


UMM_URL = 'https://cdn.earthdata.nasa.gov/umm'
UMM_VAR_VERSION = '1.8.2'

UMM_VAR_DTYPES = ['byte', 'float', 'float32', 'float64', 'double', 'ubyte',
                  'ushort', 'uint', 'uchar', 'string', 'char8', 'uchar8',
                  'short', 'long', 'int', 'int8', 'int16', 'int32', 'int64',
                  'uint8', 'uint16', 'uint32', 'uint64', 'OTHER']


def get_all_umm_var(var_info: VarInfoBase) -> Dict[str, Dict]:
    """ Iterate through all variables detected from the source granule and
        return a list of UMM-Var records for those variables.

    """
    return {variable_name: get_umm_var(var_info, variable)
            for variable_name, variable in var_info.variables.items()}


def get_umm_var(var_info: VarInfoBase, variable: VariableBase) -> Dict:
    """ Map the contents of a Variable instance to a UMM-Var record.
        Initial attempts will be made to extract all possibly information,
        with the return value being scrubbed of all UMM-Var attributes with
        None values.

    """
    variable_name = variable.full_name_path.lstrip('/')
    umm_var_record = {
        'Name': variable_name,
        'LongName': variable_name,
        'StandardName': get_first_matched_attribute(variable,
                                                    ['standard_name']),
        'Definition': get_first_matched_attribute(
            variable,
            ['description', 'Description', 'definition', 'Definition',
             'title', 'Title'],
            variable_name
        ),
        'DataType': get_umm_var_dtype(variable.data_type),
        'Dimensions': get_dimensions(var_info, variable),
        'Units': get_first_matched_attribute(variable, ['units', 'Units']),
        'FillValues': get_fill_values(variable),
        'Scale': get_first_matched_attribute(
            variable, ['scale_factor', 'scale', 'Scale']
        ),
        'Offset': get_first_matched_attribute(
            variable, ['add_offset', 'offset', 'Offset']
        ),
        'ValidRanges': get_valid_ranges(variable),
        'MetadataSpecification': get_metadata_specification()
    }

    return {umm_var_attribute: umm_var_value
            for umm_var_attribute, umm_var_value
            in umm_var_record.items()
            if umm_var_value is not None}


def export_all_umm_var_to_json(umm_var_records: List, output_dir: str = '.'):
    """ Iterate through a list of UMM-Var JSON records and save them all to
        files (one file per record).

        The output file name will be the full path of each variable will be the
        full path of the variable, with any slashes replaced with underscores.

    """
    for umm_var_record in umm_var_records:
        export_umm_var_to_json(umm_var_record, output_dir)


def export_umm_var_to_json(umm_var_record: Dict, output_dir: str = '.'):
    """ Export a single UMM-Var JSON object to a JSON output file in a
        specified directory (the default is the directory in which the function
        is called). If the specified directory does not exist, it will be
        created.

        The output file name will be the full path of the variable, with any
        slashes replaced with underscores.

    """
    if isfile(output_dir):
        raise InvalidExportDirectory(output_dir)
    else:
        # `exists_ok=True` makes this a no-op for existing directories:
        makedirs(output_dir, exist_ok=True)

    output_file_path = join_path(
        output_dir,
        f'{umm_var_record["Name"].replace("/", "_")}.json'
    )

    with open(output_file_path, 'w', encoding='utf-8') as file_handler:
        json.dump(umm_var_record, file_handler, indent=2)


def get_first_matched_attribute(variable: VariableBase,
                                attribute_names: List[str],
                                default_value: Any = None) -> Any:
    """ Check a list of metadata attributes and return the value of the first
        one that is present in the Variable. If none of the attributes are
        in the variable metadata, return the supplied default value.

    """
    return next(
        (get_json_serializable_value(variable.attributes.get(attribute_name))
         for attribute_name in attribute_names
         if attribute_name in variable.attributes),
        default_value
    )


def get_dimensions(var_info: VarInfoBase,
                   variable: VariableBase) -> Optional[List]:
    """ Return a list of all dimensions for the variable, """
    dimensions = [get_dimension_information(var_info, variable, dimension_name)
                  for dimension_name in variable.dimensions]

    if len(dimensions) == 0:
        dimensions = None

    return dimensions


def get_dimension_information(var_info: VarInfoBase, variable: VariableBase,
                              dimension_name: str) -> Dict:
    """ Retrieve a DimensionType object for the given Variable dimension. This
        function is only called for named dimensions listed in the `dimensions`
        attribute of another variable, and so should exist as at least a
        dimension within the source file.

        The dimension types in earthdata-varinfo are currently limited to
        horizontal spatial dimensions (e.g., lat, lon, projected x or projected
        y), or temporal dimensions based on the available heuristics in the
        VariableBase class.

        The dimension Name property is the full path to the variable, omitting
        any leading slashes. (E.g., a variable located at "/group/variable"
        within a file will extract a name of "group/variable")

        Currently unsupported dimension types (will have type: 'OTHER'):

        * Vertical dimensions (pressure, height, depth).
        * Projected horizontal spatial dimension (no UMM-Var type for this).
        * Swath dimensions (along or across track).

        Also note: VariableFromDmr instances do not currently extract variable
        shapes.

    """
    dimension_variable = var_info.get_variable(dimension_name)

    if dimension_variable is not None:
        dimension_name = dimension_variable.full_name_path
        if dimension_variable.is_latitude():
            dimension_type = 'LATITUDE_DIMENSION'
        elif dimension_variable.is_longitude():
            dimension_type = 'LONGITUDE_DIMENSION'
        elif dimension_variable.is_temporal():
            dimension_type = 'TIME_DIMENSION'
        else:
            dimension_type = 'OTHER'

    else:
        # Dimension without variable, potentially used only to denote array
        # size in a specific, non-physical dimension (e.g., nv, latv, lonv).
        dimension_type = 'OTHER'

    return {'Name': dimension_name.lstrip('/'),
            'Size': get_dimension_size(var_info, variable, dimension_name),
            'Type': dimension_type}


def get_dimension_size(var_info: VarInfoBase, variable_with_dim: VariableBase,
                       dimension_name: str) -> Union[str, int]:
    """ Extract the size of a specific dimension for a variable. This
        function will attempt to retrieve the dimension size from the following
        locations (in the order given):

        * The shape of the variable with the dimension itself, if present.
        * The shape of the 1-D dimension variable corresponding to the
          dimension for which the size is requested.
        * The variable will be checked for known names, as described in the
          CF-Conventions, to assign a length (relating to bounds variables).
        * If no other condition is met, the size of 'Varies' is returned.

        Note, this function is only called via an iteration through the
        `variable_with_dim.dimensions` list, and so `dimension_name` should
        always be present in that list.

    """
    dimension_variable = var_info.get_variable(dimension_name)

    if variable_with_dim.shape is not None:
        dimension_index = variable_with_dim.dimensions.index(dimension_name)
        dimension_size = variable_with_dim.shape[dimension_index]
    elif dimension_variable is not None:
        if isinstance(dimension_variable.shape, int):
            dimension_size = dimension_variable.shape
        elif (
            isinstance(dimension_variable.shape, tuple)
            and len(dimension_variable.shape) > 0
        ):
            dimension_size = dimension_variable.shape[0]
        else:
            # UMM-Var requires a size for each dimension, which must be either
            # an integer or 'Varies':
            dimension_size = 'Varies'
    elif dimension_name.endswith(('latv', 'lonv', 'nv')):
        # Bound variable dimensions (2-elements, minimum and maximum):
        dimension_size = 2
    else:
        # Other dimension without variable, potentially used only to denote
        # array size in a specific, non-physical dimension
        dimension_size = 'Varies'

    return dimension_size


def get_valid_ranges(variable: VariableBase) -> Optional[List[Dict]]:
    """ Return a dictionary containing the valid minimum and/or valid maximum
        values from the variable metadata. If valid_min, valid_max or
        valid_range are not set, None is returned.

    """
    valid_range = {
        'Min': get_json_serializable_value(variable.get_valid_min()),
        'Max': get_json_serializable_value(variable.get_valid_max())
    }

    # Remove keys with None values:
    valid_range = {range_key: range_value
                   for range_key, range_value in valid_range.items()
                   if range_value is not None}

    if len(list(valid_range.keys())) > 0:
        valid_range = [valid_range]
    else:
        valid_range = None

    return valid_range


def get_fill_values(variable: VariableBase) -> Optional[List]:
    """ Return a List containing elements of the UMM-Var FillValueType, if
        there is a fill value contained in the variable metadata. Otherwise
        return None.

        An initial simplification is that all fill values are of type
        `SCIENCE_FILLVALUE`.

    """
    fill_value = get_first_matched_attribute(variable, ['_FillValue'])
    if fill_value is not None:
        fill_values = [{
            'Value': get_json_serializable_value(fill_value),
            'Type': 'SCIENCE_FILLVALUE',
            'Description': 'Extracted from _FillValue metadata attribute'
        }]
    else:
        fill_values = None

    return fill_values


def get_umm_var_dtype(variable_data_type: str) -> str:
    """ Map the variable data type to a string in the UMM-Var DataTypeEnum. """
    if variable_data_type in UMM_VAR_DTYPES:
        umm_var_type = variable_data_type
    else:
        umm_var_type = 'OTHER'

    return umm_var_type


def get_metadata_specification() -> Dict:
    """ Return standard object for the UMM-Var specification, including the
        URL, Name and Version.

    """
    return {'URL': f'{UMM_URL}/variable/v{UMM_VAR_VERSION}',
            'Name': 'UMM-Var',
            'Version': UMM_VAR_VERSION}


def get_json_serializable_value(input_value: Any) -> Any:
    """ Ensure the value is JSON serializable, as some numpy float and integer
        types are not.

    """
    if isinstance(input_value, np_integer):
        output_value = int(input_value)
    elif isinstance(input_value, np_floating):
        output_value = float(input_value)
    else:
        output_value = input_value

    return output_value


def generate_variable_native_id(collection_concept_id: str,
                                umm_var_record: Dict) -> str:
    """ A helper function to create a CMR native ID given the collection
        concept ID and the variable UMM-Var JSON. This native ID must be unique
        within the entire provider. The initial implementation will be to
        concatenate the collection concept ID and the long name of the variable
        while removing slashes that CMR will interpret as part of the URL path.

    """
    return '-'.join([collection_concept_id,
                     umm_var_record['LongName'].replace('/', '_').lstrip('_')])


def publish_umm_var(collection_id: str,
                    umm_var_dict: Dict,
                    auth_header: str,
                    cmr_env: CmrEnvType = CMR_UAT) -> str:
    """" Publish a single UMM-Var entry to CMR given:
        * collection_id: a collection's concept_id
        * umm_var_dict: a dictionary of a single UMM-Var entry for a collection
        * auth_header: Authorization HTTP header, containing a LaunchPad
          token: 'Authorization: <token>'
        * cmr_env: CMR environments (OPS, UAT, and SIT) default is CMR_UAT

        For a successful requests all of these fields must be entered

    """
    # Required UMM-Var headers for ingesting variable entries
    headers_umm_var = {
        'Content-type': 'application/vnd.nasa.cmr.umm+json;version='
        + f'{umm_var_dict["MetadataSpecification"]["Version"]}',
        'Authorization': auth_header,
        'Accept': 'application/json'
    }
    variable_native_id = generate_variable_native_id(collection_id,
                                                     umm_var_dict)

    url_endpoint = (cmr_env.replace('search', 'ingest') + 'collections/'
                    f'{collection_id}/variables/{variable_native_id}')

    response = requests.put(url_endpoint,
                            json=umm_var_dict,
                            headers=headers_umm_var,
                            timeout=10)

    if response.ok:
        # A successful request returns the variable concept-id
        # e.g., 'V1259791517-EEDTEST'
        return response.json()['concept-id']
    else:
        # A failed request returns the response containing a list of error
        # message, e.g., {'errors': ['#: required key [LongName] not found']}.
        # This will be converted into a single string that can be returned to
        # the end-user. Multiple errors will be combined into a single string,
        # e.g.: '#: CMR error 1\n  #: CMR error 2'
        return '\n  '.join(response.json()['errors'])


def publish_all_umm_var(collection_id: str,
                        all_umm_var_dict: Dict,
                        auth_header: str,
                        cmr_env: CmrEnvType = CMR_UAT) -> Dict[str, str]:
    """ Publish all UMM-Var entries associated with a collection to CMR given:
        * collection_id: a collection's concept_id
        * all_umm_var_dict: a nested dictionary containing
            dictionaries of all UMM-Var entries for a collection
        * auth_header: Authorization HTTP header, containing a LaunchPad
          token: 'Authorization: <token>'
        * cmr_env: CMR environments (OPS, UAT, and SIT)
    For a successful requests all of these fields must be entered
    """
    return {
        var_name: publish_umm_var(collection_id, umm_var, auth_header, cmr_env)
        for var_name, umm_var in all_umm_var_dict.items()
    }
