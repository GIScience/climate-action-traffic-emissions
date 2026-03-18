# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project mostly adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased](https://gitlab.heigit.org/climate-action/plugins/traffic-emissions/-/compare/0.1.0...main)

### Added

- Added chart artifacts with mean emissions per area ([#28](https://gitlab.heigit.org/climate-action/plugins/traffic-emissions/-/issues/28))

### Changed
- Added limitations to methodology ([#27](https://gitlab.heigit.org/climate-action/plugins/traffic-emissions/-/issues/27))
- Normalize legend colors logarithmically so the different values are better recognisable in the map ([#29](https://gitlab.heigit.org/climate-action/plugins/traffic-emissions/-/issues/29))
- Make plugin usable Germany-wide by integrating raster data download from Google Earth Engine ([#24](https://gitlab.heigit.org/climate-action/plugins/traffic-emissions/-/issues/24))
- Update Climatoology to version 7.0.3
- Switched to a gradient boosting regression model to estimate traffic volume. Minor roads not included. ([#23](https://gitlab.heigit.org/climate-action/plugins/traffic-emissions/-/issues/23))
- Updated methodology description with new traffic volume estimation method ([#36](https://gitlab.heigit.org/climate-action/plugins/traffic-emissions/-/issues/36))

### Fixed
- Make sure computation does not fail if fields are missing in the gdf, raise error if gdf is empty ([#33](https://gitlab.heigit.org/climate-action/plugins/traffic-emissions/-/issues/33))

### Removed
- all the shenanigans around accessing a private climatoology repository because that is now public

## [0.1.0](https://gitlab.heigit.org/climate-action/plugins/traffic-emissions/-/releases/0.1.0) - 2024-06-25

### Added

- Traffic volume estimation [#18](https://gitlab.heigit.org/climate-action/plugins/traffic-emissions/-/issues/18)
- Traffic emission estimation [#21](https://gitlab.heigit.org/climate-action/plugins/traffic-emissions/-/issues/21)
- Emission summary charts with mean emissions per road-km for city districts [#19](https://gitlab.heigit.org/climate-action/plugins/traffic-emissions/-/issues/19)