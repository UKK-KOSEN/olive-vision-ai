# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2026-08-21

### Added
- Soil moisture integration with UKK-KOSEN monitoring system
- CLI `soil` subcommand (latest/history/stats/status)
- `--no-soil-moisture` flag for analyze/capture commands
- GUI Soil Moisture tab with on/off toggle
- Time-based soil moisture queries (`get_moisture_at_time()`)
- Health assessment combining visual + moisture scores
- `integrate_soil_moisture()` for analysis results
- `assess_moisture_health()` with risk levels
- Japanese documentation for evaluation criteria
- VERSION file for semantic versioning
- Release automation workflow
- SECURITY.md
- Enhanced CI with SARIF security scanning
- Dependency review on PRs
- Auto-labeling for PRs

### Changed
- API URL updated to `soil-moisture-pages-ddl.pages.dev`
- Default kit_id: `shodoshima-field-01`
- User-Agent header added for Cloudflare Pages compatibility

### Fixed
- 403 Forbidden error when accessing soil moisture API
- Cloudflare Pages blocking default Python User-Agent

## [0.2.0] - 2026-08-20

### Added
- GitHub repository setup with CI/CD
- Bandit security scanning
- Dependabot dependency updates
- Release Drafter
- Issue/PR templates
- CODEOWNERS
- Stale issue management

### Changed
- Full README rewrite with badges and documentation
- Comprehensive documentation (QUICKSTART, API_REFERENCE, etc.)

## [0.1.0] - 2026-08-19

### Added
- Initial release
- Image analysis pipeline
- Video analysis support
- QR code tree ID detection
- CLI and GUI interfaces
- Health trend analysis
