# Roadmap

Status labels describe the current source, not promises of production use.

| Area | Status | Current boundary |
|---|---|---|
| Input/storyboard checks, tag-gap detection, error states | IMPLEMENTED | CLI reads bundled synthetic fixtures. |
| FFmpeg render and render evidence | IMPLEMENTED | Original 54-second procedural animation with a mathematical score; six-second title cards/tone remain a compatibility fixture. MP4/SRT/timeline/report are committed. |
| Asset validation | PARTIAL | License/synthetic tags, existing media inputs and explicit SELF provenance are checked; no independent third-party rights verification. |
| Timeline and subtitles | PARTIAL | Sequential shot timing, generated SRT and burn-in; no general editing/transcription. |
| Mechanical QA and human gate | IMPLEMENTED_WITH_LIMITS | Full decode, streams/duration/resolution, black intervals >=0.30s, sample audio peak and sampled caption bounds. User approval is bound to the exact committed 54-second file, not future renders. |
| Soundtrack input and reusable templates | PARTIAL | Licensed audio input and the original mathematical score work; a general BGM library and reusable template system are not implemented. |
| External provider, real footage, publishing | NOT_IMPLEMENTED | External adapter fails `NOT_CONFIGURED`. |

## Current

Keep both synthetic local runs reproducible and preserve failure and `HUMAN_REVIEW` boundaries. The [54-second sample](examples/original_54s/README.md) has hash-bound user approval for portfolio display; machine QA remains `HUMAN_REVIEW`. CI exercises a 4.5-second integration fixture, not full-film human acceptance. Source `0.1.0` is legacy package metadata and GitHub `v1.0.0` is a historical demo snapshot. This documentation maintenance does not issue a Release; the next public release must use a new version greater than `1.0.0` and align source metadata, tag and tested artifacts.

## Next

- Extend current media-input/provenance checks only when a new asset type needs independent failure coverage.
- Obtain a fresh human review for any changed render; expand QA beyond sampled caption geometry and sample-peak audio only against a defined need.
- Decide whether subtitle input, BGM policy, or template configuration is the first tested extension.

## Later

Planned only: reusable timeline/template schema, licensed BGM handling, preview UI, packaged runner, and provider cost receipts. None is currently implemented or required to run the synthetic demo.
