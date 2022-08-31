## v2.1.0
### 2022-08-31

This minor version updates the `VarInfoFromDmr` and `VarInfoFromNetCDF4`
classes to optionally accept a collection short name via the new `short_name`
keyword argument. If this is supplied, it will be used as the identifier for
the collection associated with the granule metadata being parsed. If
`short_name` is not supplied, the `VarInfo` classes will scan the granule for
known metadata attributes that contain the collection short name, as before.
This new `short_name` argument allows for clients to specify the collection
short name in cases where it is not listed in the metadata of a granule, which
is particularly useful if there are metadata overrides or supplements required
for granules within that collection.

## v2.0.0
### 2022-08-04

This major version updates both the `VariableBase` and `VarInfoBase` classes
to allow the retrieval of projected horizontal spatial dimensions. The
`VarInfoBase.get_spatial_dimensions` method now retrieves both geographic and
projected horizontal spatial dimensions, instead of just geographic dimensions.
Two new methods have been added to the class:
`VarInfoBase.get_geographic_spatial_dimensions`, which replaces the old
functionality of `VarInfoBase.get_spatial_dimensions` to retrieve only
geographic dimensions. `VarInfoBase.get_projected_spatial_dimensions` will
retrieve only projected horizontal spatial dimensions.

The `VariableBase.is_projected_x_or_y` method has been added in support of this
functionality.

## v1.2.5
### 2022-05-19

This patch version updates the `Variable.is_temporal` method such that it can
handle variables without a `units` metadata attribute. In these instances, the
variable will be determined to not be temporal.

## v1.2.4
### 2022-04-05

This patch version updates the `ipython` development dependency to mitigate
a security vulnerability identified with `ipython~=7.21.0`.

## v1.2.3
### 2022-02-07

This patch version updates the `numpy` dependency within `sds-varinfo` to help
mitigate security vulnerabilities from `numpy` versions in downstream services.

## v1.2.2
### 2021-12-10

The `VariableBase` and child classes have been updated such that all metadata
attributes can be augmented by overrides and supplements, not just those that
contain CF-Convention references. In addition the configuration file can now be
used to set values for metadata attributes not present in the original granule
metadata.

## v1.2.1
### 2021-12-01

The `VarInfoFromDmr._set_global_attributes` class method has been updated to
correctly handle `Attribute` XML elements with a DAP4 type: `Container`.

## v1.2.0
### 2021-11-18

The `VariableBase` class has been updated to include an `is_temporal` method.
This will  return a boolean value indicating whether the variable has a `units`
metadata attribute conforming to the format outlined in the CF-Conventions
(section 4.4). A convenience method `Variable.get_attribute_value` has been
added This will allow an end-user to retrieve the value of a metadata
attribute, while specifying a default value. Lastly, the
`VarInfoBase.get_temporal_dimensions` method has been added, which retrieves a
set of required `Variables` for which `Variable.is_temporal()` is true, based
on a set of requested variables.

## v1.1.0
### 2021-09-03

The `VariableBase` class has been updated to retrieve all metadata attributes,
rather than only named attributes. In addition the retrieval of CF-Convention
references from metadata attributes has been consolidated into a `references`
class attribute. This causes a minor change to clients attempting to access
coordinate variable references: `variable.reference.get('coordinates')`. The
`VariableBase.dimensions` attribute remains in place, and will still be
combined with other variable references when using the `get_references` class
method.

## v1.0.1
### 2021-08-20

The `VarInfoBase.get_required_variables` and
`VarInfoBase.get_required_dimensions` methods have been updated to filter out
any variable references that point to non-existent variables. This might occur
when a variable has a dimension only present to denote array size. For example,
a CF-Convention `bounds` reference variable, such as `lat_bnds`. In these
cases, the variable will have an additional dimension without a corresponding
variable. The amended class methods continue to return references to all
variables that are both listed via variable metadata and present in the
granule.

## v1.0.0
### 2021-07-07

New `VarInfoFromNetCDF4` and `VariableFromNetCDF4` classes have been added to
`sds-varinfo` so that a raw NetCDF-4 file can be parsed to provide the same
level of granule information as from a `.dmr` file.

Additionally, the `CFConfig` class has been updated to not require a
configuration file, resulting in an instance of the class with no CF-Convention
overrides or supplements.

## v0.2.1
### 2021-06-18

The `VarInfoFromDmr` class has been updated to make it compatible with `.dmr`
files that place global variables in a container `Attribute` element with a
name of "HDF5_GLOBAL". This is preferentially selected as the root element for
global attribute extraction, falling back on the main `Dataset` element if it
is not present.

## v0.2.0
### 2021-06-15

The `VariableBase` class now has additional methods: `get_range`,
`get_valid_min` and `get_valid_max` that will try to retrieve range-based
metadata based on the `valid_range`, `valid_min` and `valid_max` attributes.
The `VariableBase` class also has heuristic based methods to determine if the
variable is latitudinal or longitudinal, based on the value of the `units`
metadata attribute.

Metadata attributes within a `.dmr` with multiple values will now return a list
of values of all child element.

Finally, the `VarInfoBase` class has two new utility methods:
`get_required_dimensions` and `get_spatial_dimensions`, which retrieve sets of
dimensions for an input set of variables within a granule.

## v0.1.1
### 2021-05-13

The `VariableBase.dimensions` class attribute is now a list, rather than a set,
to enable retrieval of dimensions in the order they are stored in sources such
as a `.dmr` file. The `VarInfoBase.get_variable` utility method has been added
to enable retrieval of any variable using a fully qualified path. Finally, the
`CFConfig` class has been updated to avoid the requirement of several
fields within the configuration file schema. This ensures that if these options
are not relevant for a service, they do not have to be included in that version
of the configuration file.

## v0.1.0
### 2021-04-02

The `VarInfo` and `Variable` classes have been reimplemented as abstract base
classes. This will allow for common functionality to be inherited by child
classes, while those child classes can parse information from different input
representations of a granule. `sds-varinfo` currently only supports `.dmr`
file representations, as retrieved from OPeNDAP. The `VarInfo` class is now
imported as `VarInfoFromDmr` and the `Variable` class is imported as
`VariableFromDmr`. In addition the `VarInfoFromDmr` will now only parse a local
`.dmr` file, assuming it to have already been retrieved from OPeNDAP.

## v0.0.1
### 2021-03-11

This version of the `sds-varinfo` package captures the initial functionality
already present in the Variable Subsetter Harmony service.
