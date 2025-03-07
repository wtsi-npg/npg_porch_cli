<!-- markdownlint-disable MD024 -->
# Change Log for npg_porch_cli Project

The format is based on [Keep a Changelog](http://keepachangelog.com/).
This project adheres to [Semantic Versioning](http://semver.org/).

## [0.3.0] - 2025-03-06

### Added

* CLI now supports the `--task_file` option so that JSON Porch task definitions
  can be loaded from file instead of inline with `--task_json`.

## [0.2.0] - 2024-12-18

### Added

* Added .github/dependabot.yml file to auto-update GitHub actions
* Implemented the `create_token` action. Provided the caller has an admin token,
  this action generates and returns a new pipeline-specific token.
* Used npg-python-lib to read Porch config

## [0.1.0] - 2024-07-23

### Added

* Initial project scaffold, code and tests
