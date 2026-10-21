# Changelog

This file records source changes; a passing test is not human video approval.

## Unreleased

- CLI workflow failures and material gaps now exit with status `1`; mechanical QA success awaiting `HUMAN_REVIEW` exits with status `0`. JSON reports are still written to the requested path and stdout before exit.
- Added process-level regressions for mock/FFmpeg success, unconfigured providers/tools, material gaps, render errors, QA failure, and the console-script callable.
- Added maintenance, contribution, issue/PR, and release-checklist documentation.
- CI installs FFmpeg and a supported font, then requires FFmpeg/ffprobe before the real-render test.
- No rendering behavior or public Release was changed.

## Historical public demo release

GitHub lists `v1.0.0` (2026-09-23) for the offline engineering demo. Current `pyproject.toml` source metadata is `0.1.0`; this mismatch needs an explicit maintainer version decision before any new tag. The historical release is not evidence of production readiness or independent human acceptance.
