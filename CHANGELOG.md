# Changelog

earthdata-varinfo follows semantic versioning. All notable changes to this
project will be documented in this file. The format is based on
[Keep a Changelog](http://keepachangelog.com/en/1.0.0/).

## [v3.3.1] - 2025-12-08

### Changed:

* Release notes for `earthdata-varinfo` will now include the commit history for
  that release.

* `urllib3` dependency is pinned to ~2.6.1 to handle vulnerabilies CVE-2025-66471 and CVE-2025-66418.

## [v3.3.0] - 2025-09-11

### Changed:

* DAS-2373 - Updated the retrieval of data type from `netCDF4.Variable` objects
  to first consider the `netCDF4.Variable.datatype.name` and then fall back to
  `netCDF4.Variable.datatype.dtype`.

## [v3.2.0] - 2025-07-25

### Changed:

* DAS-2339 - Clarified documentation regarding `RequiredVariables` in the
  configuration file schema, `CFConfig` class and
  `VarInfoBase.get_required_variables`. Variables specified in
  `RequiredVariables` will be included as required variables for all variables
  variable subsets of the relevant collection defined in the configuration file
  rule. There is no filtering based on the variable path of the requested
  variables in the input set to `VarInfoBase.get_required_variables`.

### Added:

* Support for getting an OPeNDAP url with `cmr_search.get_dmr_xml_url` and
  a `use_dmr=True` flag to `varinfo/generate_umm_var.generate_collection_umm_var`

## [v3.1.0] - 2025-03-25

### Added:

* `VariableBase::is_projection_x` and `VariableBase::is_projection_y` added to
  determine a variable's exact projected coordinate.

### Changed:

* earthdata-varinfo's numpy requirements relaxed to allow numpy v2.

## [v3.0.3] - 2025-03-21

### Changed:

* Updated to `netCDF4~=1.7.2` to enable `mypy` type hints for the package.

## [v3.0.2] - 2025-02-07

This version of `earthdata-varinfo` enables support for `VariableFromDmr`
variable dimension shape data in NetCDF-4 files with named dimensions
and HDF-5 files with anonymous size-only dimensions.

### Added:
* `VariableFromDmr::_get_shape()` returns dimension shape data for NetCDF-4
files with named dimensions and HDF-5 files with anonymous size-only dimensions.

### Changed:

* Update DMR `unittest` to validate variable dimension shape data.

## [v3.0.1] - 2024-10-18

### Changed:

* CMR native IDs generated from variable names with spaces in them will replace
  those space characters with underscores to avoid errors when trying to ingest
  such variables.
* The `python-cmr` requirement is updated to v0.12.0, which adds type hints for
  that package. A couple of type hints in `earthdata-varinfo` have been updated
  accordingly.
* The `numpy` requirement has been relaxed to allow broader compatibility with
  client software. Note: This enables Python 3.12 compatibility.
* To ensure compatibility with Python 3.12, the tests are now run using
  `pytest`. This allows JUnit style output to be produced, as the previously
  used `unittets-xml-runner` package was not compatible with Python 3.12. The
  tests themselves are still written using classes and syntax from `unittest`.
  The CI/CD for running the tests has been updated to also run the tests under
  Python 3.12.

## [v3.0.0] - 2024-09-11

The configuration file schema for `earthdata-varinfo` is significantly updated
in this release. For more information, see the release notes for schema v1.0.0
in `config/CHANGELOG.md`.

### Added:

* Groups within a NetCDF-4 or DMR file are now assigned to the `VarInfo*.groups`
dictionary, allowing for their metadata attributes to be accessed after parsing
an input file.

### Changed:

* `CFConfig.get_cf_attributes` has been renamed `CFConfig.get_metadata_overrides`,
  as there are now only overrides to be returned from this method. Calls to
  `CFConfig.get_metadata_overrides` now _must_ specify a variable path. All
  overrides from a configuration file for a given collection are now retrievable
  from the newly public `CFConfig.metadata_overrides` class attribute.
* Metadata overrides retrieved for a matching file path are ordered such that
  the most specific applicable override to the variable takes precedence. For
  example, when requesting the value of the "units" metadata attribute for
  variable "/nested/variable", an applicability rule that exactly matches this
  variable path will take precedence over rules matching to either the group,
  or all variables in the file.
* Handling of nested `Applicability_Groups` has been removed from the `CFConfig`
  class, as the configuration file no longer nests these items in overrides.

### Removed:

* `CFConfig._cf_supplements` has been deprecated in favour of specifying all
  in-file metadata changes via a `MetadataOverrides` item (formerly
  `CFOverrides`) instead.

## [v2.3.0] - 2024-08-26

The `VarInfoBase.get_missing_variable_attributes` method has been added to allow
someone to get metadata attributes from the configuration file for variables
that are absent from a file. An example usage is when a CF Convention grid
mapping variable is missing from a source file.
The `VarInfoBase.get_references_for_attribute` method has been added to retrieve
all unique variable references contained in a single metadata attribute for a
list of variables. For example, retrieving all references listed under the
coordinates metadata attribute.

## [v2.2.2] - 2024-07-16

The `generate_collection_umm_var` function in earthdata-varinfo updated to
support an optional kwarg `config_file` for a configuration file, to be able to
override known metadata errors.


## [v2.2.1] - 2024-04-06

The `requests` package has been added as an explicit dependency of the package.
Additionally, black code formatting has been applied to the entire repository.

## [v2.2.0] - 2023-11-30

This version of `earthdata-varinfo` updates `varinfo.cmr_search` to include
functionality to get a users EDL token given a LaunchPad token with
`get_edl_token_from_launchpad` and `get_edl_token_header`.
`get_edl_token_from_launchpad` returns a users EDL token given a LaunchPad
token and CMR environment and `get_edl_token_header` returns the appropriate header
prefix for each respective token.

## [v2.1.2] - 2023-11-14

This version of `earthdata-varinfo` updates the value of the `LongName`
attribute in generated UMM-Var records to use the value of the CF-Convention
`long_name` attribute for a variable, if it is present in the file. If this
attribute is not present in the in-file metadata, then the full path to the
variable (without the leading `/`) is used as before.

## [v2.1.1] - 2023-10-24

Fixed deployment issues

## [v2.1.0] - 2023-10-20

This version of `earthdata-varinfo` improves the functionality of the
`varinfo.get_science_variables` function with `varinfo.is_science_variable()` method.
This method returns true if a variable is a science variable by checking if
a variable contains dimension scale variables or if it contains coordinate references
or grid mapping attribute variables. This version also updates `umm_var.get_umm_var`
with `get_umm_var_type`. This function adds the UMM-Var field "VariableType"
to a UMM-Var record if a variable is a science variable.

## [v2.0.0] - 2023-09-15

This version of `earthdata-varinfo` adds functionality to publish records to
CMR, along with a single overarching function that wraps the search, download
and publication functionality into a single function for the convenience of the
end-user. Additionally, the function signatures for `cmr_search.get_granules`
and `cmr_search.download_granule` have been updated to accept the full
`Authorization` header, instead of a bearer token, so that they are also
compatible with LaunchPad tokens.

* `generate_umm_var.generate_collection_umm_var` is designed to be a single
  call for local workflows to find appropriate granules for a collection,
  download them, parse them and generate UMM-Var JSON, which can be optionally
  published to CMR.
* `umm_var.publish_umm_var` ingests a single UMM-Var entry to CMR
* `umm_var.publish_all_umm_var` ingests all of the UMM-Var entries from a given
  collection to CMR

## [v1.0.1] - 2023-08-28

This version of `earthdata-varinfo` includes preliminary functionality to
streamline the process of creating UMM-Var records given information about a
collection in CMR:
* Added `cmr_search.py` to search CMR for granule URLs given collection
  information.
* Added function `download_granule` to `cmr_search.py`, to download a granule
  from a specified URL.

## [v1.0.0] - 2023-06-16

This version of `earthdata-varinfo` contains all functionality previous
released as `sds-varinfo==4.1.1`, but resets the version number to begin
semantic version numbers for `earthdata-varinfo` at 1.0.0. Additional contents
to the repository include updated documentation and files outlined by the
[NASA open-source guidelines](https://code.nasa.gov/#/guide).

For more information on internal releases prior to NASA open-source approval,
see `legacy-CHANGELOG.md`.

[v3.3.1]: https://github.com/nasa/earthdata-varinfo/releases/tag/3.3.1
[v3.3.0]: https://github.com/nasa/earthdata-varinfo/releases/tag/3.3.0
[v3.2.0]: https://github.com/nasa/earthdata-varinfo/releases/tag/3.2.0
[v3.1.0]: https://github.com/nasa/earthdata-varinfo/releases/tag/3.1.0
[v3.0.3]: https://github.com/nasa/earthdata-varinfo/releases/tag/3.0.3
[v3.0.2]: https://github.com/nasa/earthdata-varinfo/releases/tag/3.0.2
[v3.0.1]: https://github.com/nasa/earthdata-varinfo/releases/tag/3.0.1
[v3.0.0]: https://github.com/nasa/earthdata-varinfo/releases/tag/3.0.0
[v2.3.0]: https://github.com/nasa/earthdata-varinfo/releases/tag/2.3.0
[v2.2.2]: https://github.com/nasa/earthdata-varinfo/releases/tag/2.2.2
[v2.2.1]: https://github.com/nasa/earthdata-varinfo/releases/tag/2.2.1
[v2.2.0]: https://github.com/nasa/earthdata-varinfo/releases/tag/2.2.0
[v2.1.2]: https://github.com/nasa/earthdata-varinfo/releases/tag/2.1.2
[v2.1.1]: https://github.com/nasa/earthdata-varinfo/releases/tag/2.1.1
[v2.1.0]: https://github.com/nasa/earthdata-varinfo/releases/tag/2.1.0
[v2.0.0]: https://github.com/nasa/earthdata-varinfo/releases/tag/2.0.0
[v1.0.1]: https://github.com/nasa/earthdata-varinfo/releases/tag/1.0.1
[v1.0.0]: https://github.com/nasa/earthdata-varinfo/releases/tag/1.0.0
