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
