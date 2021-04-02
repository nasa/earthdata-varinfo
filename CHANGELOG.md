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
