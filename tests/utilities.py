""" Utility classes used to extend the unittest capabilities """

from typing import Dict

from netCDF4 import Dataset
from numpy import float64


netcdf4_global_attributes = {
    'short_name': 'ATL03',
    'history': '2021-07-02T14:18:00 Test data',
}


def is_dictionary_subset(subset_dict: Dict, container_dict: Dict) -> bool:
    """Check that one dictionary is a subset of another, ensuring all keys
    are present with the expected values.

    """
    return all(
        subset_key in container_dict and subset_value == container_dict[subset_key]
        for subset_key, subset_value in subset_dict.items()
    )


def write_dmr(output_dir: str, content: str):
    """A helper function to write out the content of a `.dmr`, which will be
    used as inputs to tests using `VarInfoFromDmr`. This will be called as
    a side-effect to the mock for that function.

    """
    dmr_name = f'{output_dir}/downloaded.dmr'

    with open(dmr_name, 'w', encoding='utf-8') as file_handler:
        file_handler.write(content)

    return dmr_name


def write_skeleton_netcdf4(output_dir: str) -> str:
    """A helper function to write a skeletal NetCDF-4 file that contains
    global attributes, variables (nested and in the root group) with
    minimal data arrays and their associated dimensions.

    """
    file_path = '/'.join([output_dir, 'test.nc4'])

    with Dataset(file_path, 'w') as dataset:
        dataset.setncatts(netcdf4_global_attributes)
        dataset.createDimension('lat', size=2)
        dataset.createDimension('lon', size=2)
        dataset.createDimension('time', size=1)
        lat = dataset.createVariable('lat', float64, dimensions=('lat',))
        lat.setncatts(
            {
                'long_name': 'latitude',
                'standard_name': 'latitude',
                'units': 'degrees_north',
            }
        )
        lon = dataset.createVariable('lon', float64, dimensions=('lon',))
        lon.setncatts(
            {
                'long_name': 'longitude',
                'standard_name': 'longitude',
                'units': 'degrees_east',
            }
        )
        time = dataset.createVariable('time', float64, dimensions=('time',))
        time.setncatts(
            {'long_name': 'time', 'units': 'seconds since 1970-01-01T00:00:00'}
        )
        create_science_variable(dataset, 'science1')
        create_science_variable(dataset, '/group/science2')
        dataset.createVariable('scalar1', float64, dimensions=())
        dataset.createVariable('/group/scalar2', float64, dimensions=())

    return file_path


def create_science_variable(dataset: Dataset, variable_name: str):
    """A utility function to create a science variable in a skeletal NetCDF-4
    test file.

    """
    variable = dataset.createVariable(
        variable_name, float64, dimensions=('time', 'lat', 'lon')
    )

    variable.setncatts(
        {'coordinates': '/lat /lon', 'description': 'A science variable for testing'}
    )
