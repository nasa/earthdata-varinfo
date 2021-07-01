""" Utility classes used to extend the unittest capabilities """
from netCDF4 import Dataset
from numpy import float64


netcdf4_global_attributes = {'short_name': 'ATL03',
                             'history': '2021-07-02T14:18:00 Test data'}


def write_dmr(output_dir: str, content: str):
    """ A helper function to write out the content of a `.dmr`, which will be
        used as inputs to tests using `VarInfoFromDmr`. This will be called as
        a side-effect to the mock for that function.

    """
    dmr_name = f'{output_dir}/downloaded.dmr'

    with open(dmr_name, 'w') as file_handler:
        file_handler.write(content)

    return dmr_name


def write_skeleton_netcdf4(output_dir: str) -> str:
    """ A helper function to write a skeletal NetCDF-4 file that contains
        global attributes, variables (nested and in the root group) with
        minimal data arrays and their associated dimensions.

    """
    file_path = '/'.join([output_dir, 'test.nc4'])

    with Dataset(file_path, 'w') as dataset:
        dataset.setncatts(netcdf4_global_attributes)
        dataset.createDimension('lat', size=2)
        dataset.createDimension('lon', size=2)
        dataset.createVariable('lat', float64, dimensions=('lat', ))
        dataset.createVariable('lon', float64, dimensions=('lon', ))
        create_science_variable(dataset, 'science1')
        create_science_variable(dataset, '/group/science2')
        dataset.createVariable('scalar1', float64, dimensions=())
        dataset.createVariable('/group/scalar2', float64, dimensions=())

    return file_path


def create_science_variable(dataset: Dataset, variable_name: str):
    """ A utility function to create a science variable in a skeletal NetCDF-4
        test file.

    """
    variable = dataset.createVariable(variable_name, float64,
                                      dimensions=('lat', 'lon'))

    variable.setncatts({'coordinates': '/lat /lon',
                        'description': 'A science variable for testing'})
