# sds-varinfo

A Python package for parsing Earth Observation science granule structure and
extracting relations between science variables and their associated metadata,
such as coordinates.

## Features:

### CFConfig

A class that takes a YAML file and retrieves all related configuration based on
the supplied mission name and collection shortname. The YAML file is optional,
and if not supplied, a `CFConfig` class will be constructed with largely empty
attributes.

```
from varinfo import CFConfig

cf_config = CFConfig('ICESat2', 'ATL03', 'varinfo/sample_config.yml')
cf_attributes = cf_config.get_cf_attributes('/full/variable/path')
```

### VarInfo

A group of classes that contain the relations between all variables within a
single granule. Current classes include:

* VarInfoBase: An abstract base class that contains core logic and methods used
  by the child classes that parse different sources of granule information.
* VarInfoFromDmr: Child class that maps input from a `.dmr` file downloaded
  from Hyrax in the cloud. This inherits all the methods and logic of
  VarInfoBase.
* VarInfoFromNetCDF4: Child class that maps input directly from a NetCDF-4
  file. Thus inherits all the methods and logic of VarInfoBase.

```
from logging import getLogger
from varinfo import VarInfoFromDmr

logger = getLogger('dev')

var_info = VarInfoFromDmr('/path/to/local/file.dmr', logger,
                          config_file='varinfo/sample_config.yml')

# Retrieve a set of variables with coordinate metadata:
var_info.get_science_variables()

# Retrieve a set of variables without coordinate metadata:
var_info.get_metadata_variables()

# Augment a set of desired variables with all variables required to support
# the requested set. For example coordinate variables.
var_info.get_required_variables({'/path/to/science/variable'})

# Retrieve an ordered list of dimensions associated with all specified variables.
var_info.get_required_dimensions({'/path/to/science/variable'})

# Retrieve all spatial dimensions associated with the specified set of science
# variables.
var_info.get_spatial_dimensions({'/path/to/science/variable'})
```

The `VarInfoFromDmr` and `VarInfoFromNetCDF4` classes also have an optional
argument `short_name`, which can be used upon instantiation to specify the
short name of the collection to which the granule belongs. This option is to be
used when a granule does not contain the collection short name within its
metadata global attributes (e.g., ABoVE collections from ORNL).

```
var_info = VarInfoFromDmr('/path/to/local/file.dmr', logger,
                          short_name='ATL03')
```

Note: as there are now two optional parameters, `short_name` and `config_file`,
it is best to ensure that both are specified as named arguments upon
instantiation.


## Installing

### Using pip

Install the latest version of the package from Maven using pip:

```bash
$ pip install sds-varinfo --extra-index-url https://maven.earthdata.nasa.gov/repository/python-repo/simple
```

### Other methods:

If using a local source tree, run the following in the root directory:

```
$ pip install -e .
```

## Developing

Development on this repo should occur on a feature branch. PRs are created with
a target of the `dev` branch before being reviewed and merged.

Releases are created when the `dev` branch is merged to `master`. This happens
when the team decides to cut a release.

## Releasing:

Refer to the Data Services Wiki page on the CI/CD setup for this package.
Before triggering a release, ensure the `VERSION` and `CHANGELOG.md` files are
updated accordingly.

## Development Setup:

Prerequisites:

  - Python 3.7+, ideally installed in a virtual environment, such as `pyenv` or
    `conda`.
  - A local copy of this repository.

Install dependencies:

```bash
$ make develop
```

Run linter against package code (preferably do this prior to submitting code
for a Pull Request review):

```bash
$ make lint
```

Run `unittest` suite:

```bash
$ make test
```

Build and publish the package (note, this should only be used by Bamboo, as a
result of successful pull requests).

```bash
$ make publish
```
