# AI Video Workflow Engine — case study

## Problem
A workflow diagram and JSON report do not show whether a video pipeline can actually render an inspectable artifact.

## Context
This clean-room engine uses only self-generated cards, text, subtitles and tone. The example is six seconds, not a customer production or paid-model run.

## Constraints
No copyrighted footage, private voice, internal company pipeline or paid provider. The artifact must be small enough to keep in the public repository.

## My Role
I implemented the state machine, synthetic asset gate, local FFmpeg provider, timeline/caption outputs, media QA and reproducible demo render.

## Architecture
Synthetic input → storyboard → licensed synthetic asset-tag retrieval → timeline → two generated card shots → subtitle/tone composition → MP4 → ffprobe QA → human-review state.

## Key Decisions
The external provider fails closed as `NOT_CONFIGURED`; only `SELF`/CC0 synthetic assets are selected. QA checks streams, duration and captions but does not claim aesthetic approval.

## Hardest Problem
Making the FFmpeg path produce visible per-shot changes instead of a single-color placeholder while preserving the existing workflow gates. The renderer generates distinct title cards, a caption file, audio and a timeline from the selected shots.

## Failure/Tradeoff
The output is a synthetic proof of pipeline mechanics, not a polished commissioned video. The voice is a generated tone, not speech; captions carry the shot narration.

## Testing
25 deterministic tests, including a real FFmpeg render test, pass. The committed MP4 is 6 seconds at 640×360 with H.264 video and AAC audio; opening/closing frames were visually spot-checked and QA returned `HUMAN_REVIEW` with no mechanical failures.

## Eval
No probabilistic provider runs, so model quality is `NOT_RUN`. Mechanical QA checks cannot substitute for human creative review.

## Current Evidence
[Synthetic MP4](../examples/demo-output.mp4) · [opening frame](../examples/demo-output.png) · [closing frame](../examples/demo-frame-2.png) · [timeline](../examples/demo-output.timeline.json) · [QA report](../examples/demo-qa.json).

## Limitations
No licensed customer media pipeline, speech generation, creative-quality scoring, provider cost receipt or external approval.

## What I Would Do in Production
Add provenance manifests for media, deterministic render containers, frame/audio quality thresholds, caption review and signed human approval before publication.

## What I Learned
An inspectable artifact and stream-level QA reveal integration gaps that a JSON-only mock cannot.
