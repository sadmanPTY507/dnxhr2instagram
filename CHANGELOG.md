# Changelog

All notable changes to this project will be documented in this file.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.2.0] - 2026-10-06

### Added
- Output file browser tab with individual download buttons
- Download link in the success banner after conversion completes
- `/api/outputs` endpoint to list converted files
- `/api/download/<filename>` endpoint to download output files

## [1.1.0] - 2026-10-06

### Added
- ntfy test notification buttons (success and failure)
- `/api/test-notification` endpoint reusing the transcoder's `_notify` method

## [1.0.0] - 2026-10-06

### Added
- Web UI with drag-and-drop file upload and real-time upload progress
- File list from shared input directory (`/inputs`)
- Manual conversion trigger via "CONVERTIR" button
- FFmpeg transcoding: DNxHR → H.264/AAC MP4 (Instagram/WhatsApp compatible)
- Real-time conversion progress bar with ETA via Server-Sent Events
- Configurable FFmpeg parameters via environment variables (CRF, preset, CPU cores)
- Post-processing option to delete source file on success
- ntfy notifications on conversion success or failure
- Dockerized setup targeting Raspberry Pi 4 (ARM64)
- CPU core limiting (3 of 4 cores) for system stability
- Path traversal protection on all file operations
