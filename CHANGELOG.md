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
