# AI Video Workflow Engine

**A reproducible video-workflow engine from asset checks to a real FFmpeg render and human QA gate.** It solves the handoff problem where a file exists but the inputs, failure state or approval are unclear.

**OFFLINE_ENGINEERING_DEMO / HUMAN_REVIEW** · [Watch synthetic MP4](examples/demo-output.mp4) · [Case study](docs/case-study.md) · [Resume bullets](docs/resume-bullets.md) · [Interview notes](docs/interview-notes.md)

[![CI](https://github.com/zhouey314-cloud/ai-video-workflow-engine/actions/workflows/ci.yml/badge.svg)](https://github.com/zhouey314-cloud/ai-video-workflow-engine/actions/workflows/ci.yml)

![Opening frame of the reproducible six-second synthetic FFmpeg sample](examples/demo-output.png)

Independent clean-room framework for synthetic video production. No company pipeline source, customer media, voice data, internal prompt or paid provider call is included.

![Workflow architecture](docs/images/architecture.svg)

## Demo and quick start

Python 3.10+: `python3 -m unittest discover -s tests -v`; `python3 -m video_workflow.cli`. The mock run writes `output/demo.json` and `output/report.json`. The real synthetic FFmpeg run:

```bash
python3 -m video_workflow.cli --provider ffmpeg --media-output examples/demo-output.mp4 --output examples/demo-qa.json
```

This walks synthetic input → storyboard → asset-tag retrieval → timeline → two distinct title-card shots → burned test subtitles + generated tone → render → ffprobe QA → human-review gate. [Watch the 6-second synthetic MP4](examples/demo-output.mp4) (72 KB). [Opening frame](examples/demo-output.png) · [closing frame](examples/demo-frame-2.png) · [captions](examples/demo-output.srt) · [timeline](examples/demo-output.timeline.json) · [QA report](examples/demo-qa.json). To reproduce the closing frame: `ffmpeg -ss 4 -i examples/demo-output.mp4 -frames:v 1 examples/demo-frame-2.png`. `--provider external` remains `NOT_CONFIGURED` and fails closed.

The CLI writes the workflow JSON report to `--output` and stdout before exiting. Exit code `0` means mechanical QA passed and the workflow reached `HUMAN_REVIEW` (or `APPROVED` if supplied by the workflow); pending human review is a successful CLI run, not human approval. Exit code `1` means the workflow failed or stopped with a material `GAP`. Use the JSON `state`, `failures`, and `events` to diagnose the result.

![Opening synthetic title card](examples/demo-output.png)

![Closing synthetic title card](examples/demo-frame-2.png)

## Problem, architecture and features

Input → Script → Persona/Grounding → Storyboard → licensed synthetic material retrieval → gap detection → optional generation request → timeline plan → render adapter → QA → human review. The implementation models each state, validates a storyboard, checks license and synthetic tags, records failures, enforces a zero dollar budget and requires a named human to approve. See [architecture](docs/architecture.md), [sample storyboard](examples/storyboard.json) and [sample report](examples/sample-report.json).

## Verification and boundaries

41 tests cover state, retrieval, missing material, real FFmpeg render, media stream/duration QA, provider configuration and review gates. The five delivery regressions add special-character output paths, explicit invalid-font failure without overwriting an existing artifact, recovery after a blocked destination, long Chinese captions and black/clipped media rejection. Existing CLI success/failure/GAP exit behavior is retained.

MP4 QA now decodes the complete file, checks black intervals of at least 0.30 seconds, measures sample audio peak (limit −0.5 dBFS), records mean volume and verifies expected resolution/duration/audio. Subtitles use a private fixed-name ASS/font workspace; user paths never enter FFmpeg filter syntax. A separate render of the identical subtitle layer measures actual libass glyph pixel bounds at 2 fps, including wrapping and missing-glyph diagnostics. This measures subtitle-layer geometry, not readability or full-frame visual quality. `--font /path/to/font.ttf` selects an available local font; `--storyboard` and `--assets` choose explicit input files. Missing/invalid input produces a nonzero JSON failure. Over-dense captions are rejected rather than truncated. FFmpeg failures preserve an existing MP4; generated sidecars are promoted only after FFmpeg completes.

`HUMAN_REVIEW` means mechanical QA passed, not video quality approval. The committed six-second MP4 was visually spot-checked at opening/closing frames; it has not been approved by an external reviewer. There is no AI model eval or paid video API. All examples are `synthetic_unverified`; real footage and publishing are outside scope. Font files are not bundled; preserve any selected font's license. See [resume bullets](docs/resume-bullets.md) and [interview notes](docs/interview-notes.md).

## Maintenance and release status

The current source metadata is `0.1.0` in `pyproject.toml`. A historical GitHub `v1.0.0` demo Release exists; it does not establish production maturity, and no new version is proposed until that numbering conflict is resolved. See the [capability roadmap](ROADMAP.md), [changelog](CHANGELOG.md), [contribution guide](CONTRIBUTING.md), and [release checklist](docs/releases/RELEASE_CHECKLIST.md). New Release publication requires a separate decision.

MIT. See [LICENSE](LICENSE).
