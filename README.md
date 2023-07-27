# earthdata-varinfo

A Python package developed as part of the NASA Earth Observing System Data and
Information System (EOSDIS) for parsing Earth Observation science granule
structure and extracting relations between science variables and their
associated metadata, such as coordinates. This package also includes the
capability to generate variable (UMM-Var) metadata records that are compatible
with the NASA EOSDIS Common Metadata Repository
([CMR](https://www.earthdata.nasa.gov/eosdis/science-system-description/eosdis-components/cmr)).

For general usage of classes and functions in `earthdata-varinfo`, see:
<https://github.com/nasa/earthdata-varinfo/blob/main/docs/earthdata-varinfo.ipynb>.

## Features:

### CFConfig

A class that takes a JSON file and retrieves all related configuration based on
the supplied mission name and collection shortname. The JSON file is optional,
and if not supplied, a `CFConfig` class will be constructed with largely empty
attributes.

```
from varinfo import CFConfig

cf_config = CFConfig('ICESat2', 'ATL03', config_file='config/0.0.1/sample_config_0.0.1.json')
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
from varinfo import VarInfoFromDmr

var_info = VarInfoFromDmr('/path/to/local/file.dmr',
                          config_file='config/0.0.1/sample_config_0.0.1.json')

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
var_info = VarInfoFromDmr('/path/to/local/file.dmr', short_name='ATL03')
```

Note: as there are now two optional parameters, `short_name` and `config_file`,
it is best to ensure that both are specified as named arguments upon
instantiation.

### UMM-Var generation

`earthdata-varinfo` can generate variable metadata records compatible with the
CMR UMM-Var schema:

```
from varinfo import VarInfoFromNetCDF4
from varinfo.umm_var import export_all_umm_var_to_json, get_all_umm_var

# Instantiate a VarInfoFromNetCDF4 object for a local NetCDF-4 file.
var_info = VarInfoFromNetCDF4('/path/to/local/file.nc4', short_name='ATL03')

# Retrieve a dictionary of UMM-Var JSON records. Keys are the full variable
# paths, values are UMM-Var schema-compatible, JSON-serialisable dictionaries.
umm_var = get_all_umm_var(var_info)

# Write each UMM-Var dictionary to its own JSON file:
export_all_umm_var_to_json(list(umm_var.values()), output_dir='local_dir')
```

## Configuration file schema:

The configuration file schema is defined as a JSON schema file in the `config`
directory. Each new iteration to the schema should be placed in its own
semantically versioned subdirectory, and a sample configuration file should be
provided. Additionally, notes on the schema changes should be provided in
`config/CHANGELOG.md`.

## Installing

### Using pip

Install the latest version of the package from PyPI using pip:

```bash
$ pip install earthdata-varinfo
```

### Other methods:

For local development, it is possible to clone the repository and then install
the version being developed in editable mode:

```bash
$ git clone https://github.com/nasa/earthdata-varinfo
$ cd earthdata-varinfo
$ pip install -e .
```

## Contributing

Contributions are welcome! For more information see `CONTRIBUTING.md`.

## Developing

Development within this repository should occur on a feature branch. Pull
Requests (PRs) are created with a target of the `main` branch before being
reviewed and merged.

Releases are created when a feature branch is merged to `main` and that branch
also contains an update to the `VERSION` file.

### Development Setup:

Prerequisites:

  - Python 3.7+, ideally installed in a virtual environment, such as `pyenv` or
    `conda`.
  - A local copy of this repository.

Install dependencies:

```bash
$ make develop
```

Run a linter against package code (preferably do this prior to submitting code
for a PR review):

```bash
$ make lint
```

Run `unittest` suite:

```bash
$ make test
```

## Releasing:

All CI/CD for this repository is defined in the `.github/workflows` directory:

* run_tests.yml - A reusable workflow that runs the unit test suite under a
  matrix of Python versions.
* run_tests_on_pull_requests.yml - Triggered for all PRs against main. It runs
  the workflow in run_test.yml to ensure all tests pass on the new code.
* publish_to_pypi.yml - Triggered either manually or for commits to the main
  branch that contain changes to the `VERSION` file.

The `publish_to_pypi.yml` workflow will:

* Run the full unit test suite, to prevent publication of broken code.
* Extract the semantic version number from `VERSION`.
* Extract the release notes for the most recent version from `CHANGELOG.md`.
* Build the package to be published to PyPI.
* Publish the package to PyPI.
* Publish a GitHub release under the semantic version number, with associated
  git tag.

Before triggering a release, ensure the `VERSION` and `CHANGELOG.md`
files are updated accordingly.

## Get in touch:

You can reach out to the maintainers of this repository via email:

* david.p.auty@nasa.gov
* owen.m.littlejohns@nasa.gov
