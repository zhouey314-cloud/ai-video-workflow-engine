# Roadmap

Status labels describe the current source, not promises of production use.

| Area | Status | Current boundary |
|---|---|---|
| Input/storyboard checks, tag-gap detection, error states | IMPLEMENTED | CLI reads bundled synthetic fixtures. |
| FFmpeg render and render evidence | IMPLEMENTED | Synthetic title cards, generated tone, MP4/SRT/timeline/report. |
| Asset validation | PARTIAL | License/synthetic tags only; no media file or rights verification. |
| Timeline and subtitles | PARTIAL | Sequential shot timing, generated SRT and burn-in; no general editing/transcription. |
| Mechanical QA and human gate | PARTIAL | Streams/duration/budget checks and explicit approval state; no independent quality acceptance. |
| BGM and template system | NOT_IMPLEMENTED | Tone is test audio; card palette/layout are hard-coded. |
| External provider, real footage, publishing | NOT_IMPLEMENTED | External adapter fails `NOT_CONFIGURED`. |

## Current

Keep the synthetic local run reproducible and preserve the failure and `HUMAN_REVIEW` boundaries. Resolve the historical `v1.0.0` Release versus source `0.1.0` numbering before selecting another tag.

## Next

- Validate actual input media and provenance with fixtures that can fail independently of metadata tags.
- Add frame/audio QA and a recorded human review outcome for a bounded real-user task.
- Decide whether subtitle input, BGM policy, or template configuration is the first tested extension.

## Later

Planned only: reusable timeline/template schema, licensed BGM handling, preview UI, packaged runner, and provider cost receipts. None is currently implemented or required to run the synthetic demo.
