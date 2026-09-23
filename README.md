# AI Video Workflow Engine

Independent clean-room framework for synthetic video production. No company pipeline source, customer media, voice data, internal prompt or paid provider call is included.

![Workflow architecture](docs/images/architecture.svg)

## Demo and quick start

Python 3.10+: `python3 -m unittest discover -s tests -v`; `python3 -m video_workflow.cli`. The mock run writes `output/demo.json` and `output/report.json`. `--provider ffmpeg` renders a plain color placeholder if local FFmpeg is installed. `--provider external` reports `NOT_CONFIGURED` and fails closed.

## Problem, architecture and features

Input → Script → Persona/Grounding → Storyboard → licensed synthetic material retrieval → gap detection → optional generation request → timeline plan → render adapter → QA → human review. The implementation models each state, validates a storyboard, checks license and synthetic tags, records failures, enforces a zero dollar budget and requires a named human to approve. See [architecture](docs/architecture.md), [sample storyboard](examples/storyboard.json) and [sample report](examples/sample-report.json).

## Verification and boundaries

24 deterministic tests cover state, retrieval, missing material, QA, provider configuration and review gates. `HUMAN_REVIEW` means a mechanical QA pass, not video quality approval. There is no AI model eval or paid video API. All examples are `synthetic_unverified`; real footage and publishing are outside scope. See [resume bullets](docs/resume-bullets.md) and [interview notes](docs/interview-notes.md).

## Roadmap and license

Add real storyboard visual validation, frame/audio QA and provider cost receipts before production integration. MIT.
