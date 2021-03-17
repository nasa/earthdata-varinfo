# sds-varinfo

A Python package for parsing Earth Observiation science granule structure and
extracting relations between science variables and their associated metadata,
such as coordinates.

## Features:

### CFConfig

A class that takes a YAML file and retrieves all related configuration based on
the supplied mission name and collection shortname.

```
from varinfo import CFConfig

cf_config = CFConfig('ICESat2', 'ATL03', 'varinfo/sample_config.yml')
cf_attributes = cf_config.get_cf_attributes('/full/variable/path')
```

### VarInfo

A class that contains the relations between all variables within a single
granule. Currently this maps input from a `.dmr` file downloaded from Hyrax in
the cloud, using the `harmony-service-lib`.

```
from logging import getLogger
from harmony.util import config
from varinfo import VarInfo

logger = getLogger('dev')
harmony_config = config(False)
var_info = VarInfo('https://www.opendap.uat.nasa.gov/providers/<provider>/collections/<entry title>/granules/<granule UR>',
				   logger,
				   <temp_dir path>,
				   <access token>,
				   harmony_config,
				   'varinfo/sample_config.yml')
var_info.get_science_variables()
var_info.get_metadata_variables()
var_info.get_required_variables('/path/to/science/variable')
```

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
