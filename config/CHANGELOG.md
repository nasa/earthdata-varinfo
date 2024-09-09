# earthdata-varinfo JSON configuration file.

This change log preserves the changes made between different schema versions of
the earthdata-varinfo configuration file.

## 1.0.0
### Unreleased

**TRT-552** Implementing a simpler `earthdata-varinfo` configuration file schema.

This version of the configuration file schema makes several significant changes
to simplify the schema for broader use.

### Removed:
* The `Global_Attributes` property has been removed from the `CF_Overrides` and
  `CF_Supplements` items, in favour of specifying group metadata attribute
  overrides in the same way as variables. That is: specifying the group in the
  `Applicability` part of the item, and including the updated attributes under
  the `Attributes` property of the item. This allows metadata overrides to all
  groups, not just the global attributes in an input file.
* The `Applicability_Group` property within `CF_Overrides` and `CF_Supplements`
  has been removed. Now attributes should only be specified within the
  `Attributes` property at the root level of an override or supplement. The
  `Applicability` of a `CF_Override` or `CF_Supplement` must now include either
  a `Mission` or a `ShortNamePath`.
* The `CF_Supplements` section of the `CFOverridesOrSupplementItemType` has
  been removed, and the item type renamed to `CFOverridesItemType`. All changes
  to in-file metadata attributes should now be specified in `CF_Overrides`.

## 0.0.1
### 2023-01-09

This version of the configuration file schema captures the schema as it
currently is in use for HOSS, the Swath Projector and the Trajectory Subsetter.
