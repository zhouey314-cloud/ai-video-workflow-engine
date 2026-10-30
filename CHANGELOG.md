# Changelog

This file records source changes; a passing test is not human video approval.

## Unreleased

- Synchronized the roadmap with the existing original 54-second animation, full decode, black/audio/caption checks and exact-file user approval. No media bytes were changed or re-rendered by this documentation update.
- The current source includes the original nine-scene procedural generator, SELF video/soundtrack inputs, 4.5-second CI integration fixtures and hash-bound portfolio approval recorded on 2026-10-21. Future renders still require fresh review; the six-second compatibility fixture remains available.
- Version policy: keep the historical `v1.0.0` tag and legacy `0.1.0` package metadata intact for this docs-only change. The next public release must have a unique version greater than `1.0.0`, matching package metadata and tested release artifacts.

### Earlier CLI and maintenance changes

- CLI workflow failures and material gaps now exit with status `1`; mechanical QA success awaiting `HUMAN_REVIEW` exits with status `0`. JSON reports are still written to the requested path and stdout before exit.
- Added process-level regressions for mock/FFmpeg success, unconfigured providers/tools, material gaps, render errors, QA failure, and the console-script callable.
- Added maintenance, contribution, issue/PR, and release-checklist documentation.
- CI installs FFmpeg and a supported font, then requires FFmpeg/ffprobe before the real-render test.
- No rendering behavior or public Release was changed.

## Historical public demo release

GitHub lists `v1.0.0` (2026-09-23) for the offline engineering demo. Current `pyproject.toml` source metadata is the legacy `0.1.0`; these describe different historical snapshots and are not interchangeable install targets. Follow the forward-only version policy above for the next release. The historical release is not evidence of production readiness or independent human acceptance.

## 2026-10-30 · Verifiable delivery bundles

Add fresh-directory job bundles with input/artifact hashes, complete QA, fail-closed verification and cleanup. Original CLI and artifact-specific human approval remain unchanged. 56 tests including a real encoded bundle.
