## v2.0.0
### 2023-09-15

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

## v1.0.1
### 2023-08-28

This version of `earthdata-varinfo` includes preliminary functionality to
streamline the process of creating UMM-Var records given information about a
collection in CMR:
* Added `cmr_search.py` to search CMR for granule URLs given collection
  information.
* Added function `download_granule` to `cmr_search.py`, to download a granule
  from a specified URL.

## v1.0.0
### 2023-06-16

This version of `earthdata-varinfo` contains all functionality previous
released as `sds-varinfo==4.1.1`, but resets the version number to begin
semantic version numbers for `earthdata-varinfo` at 1.0.0. Additional contents
to the repository include updated documentation and files outlined by the
[NASA open-source guidelines](https://code.nasa.gov/#/guide).

For more information on internal releases prior to NASA open-source approval,
see `legacy-CHANGELOG.md`.
