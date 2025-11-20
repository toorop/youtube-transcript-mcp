# Changelog

## [Unreleased] - 2025-11-20

### Added
- **Multi-language fallback strategy**: Automatically tries alternative languages if requested language is unavailable
  - English request: tries en → fr → es → de → pt → ja → ko
  - French request: tries fr → fr-orig → en → es → de
  - Other languages: tries requested → en → fr → es
- **Language metadata in responses**: All endpoints now return `language` (actual language obtained) and `requested_language` fields
- **Enhanced error reporting**: Error responses include `details` and `attempted_languages` fields for better debugging

### Changed
- **Improved error handling**: No longer relies on yt-dlp returncode (which can be non-zero even on success)
- **Success detection**: Now checks for actual `.vtt` file creation instead of subprocess return code
- **Timeout protection**: Added 30-second timeout to yt-dlp subprocess calls

### Fixed
- **Videos in non-English languages**: Fixed issue where videos with non-English primary language (e.g., French) would fail when requesting English subtitles
- **Partial failures**: Fixed cases where yt-dlp returns error code but successfully downloads subtitles
- **Better cleanup**: Properly removes existing VTT files before each download attempt

## Previous Versions

See git history for earlier changes.
