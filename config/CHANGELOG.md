# earthdata-varinfo JSON configuration file.

This change log preserves the changes made between different schema versions of
the earthdata-varinfo configuration file.

## 1.0.0
### Unreleased

**TRT-552** Implementing a simpler `earthdata-varinfo` configuration file schema.

This version of the configuration file schema makes several significant changes
to simplify the schema for broader use.

### Changed:

* `CF_Overrides` has been renamed to `MetadataOverrides`.
* `CFOverridesOrSupplementsItemType` has been renamed to
  `MetadataOverridesItemType`.
* `Required_Fields` has been renamed to `RequiredVariables` to match the
  terminology used for other schema properties.
* The casing of all attributes in the configuration file schema has been
  updated to be `PascalCase` throughout. Affected schema attributes include:
  * `CollectionShortNamePath`.
  * `ExcludedScienceVariables`.

### Removed:

* The `CF_Supplements` property of the schema has been removed. All metadata
  changes must now be specified in a `MetadataOverrides` item (formerly
  `CF_Overrides`).
* The `Global_Attributes` property has been removed from `MetadataOverrides`.
  Global attribute overrides should now be specified in the same way as
  metadata attributes on any other variable or group. That is: specifying the
  path to the group in the `Applicability` part of the item, and including the
  updated attributes under the `Attributes` property of the item. This allows
  metadata overrides to all groups, not just the global attributes in an input
  file.
* The `Applicability_Group` property within `MetadataOverrides` (formerly
  `CF_Overrides`) has been removed. Now attributes should only be specified
  within the `Attributes` property at the root level of an override or
  supplement. The `Applicability` of a `MetadataOverrides` item must now
  include either a `Mission` or a `ShortNamePath`.
* The unused `ProductEpochs` section of the schema has been removed.
* The `Grid_Mapping_Data` section of the schema has been removed, in favour of
  specifying grid mapping attributes via `MetadataOverrides`.

## 0.0.1
### 2023-01-09

This version of the configuration file schema captures the schema as it
currently is in use for HOSS, the Swath Projector and the Trajectory Subsetter.
