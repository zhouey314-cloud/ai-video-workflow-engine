# Release checklist

The historical `v1.0.0` demo Release and source `0.1.0` metadata conflict. **BLOCKED:** choose and document a version strategy before creating another tag or publishing a Release. This checklist does not authorize publication.

- [ ] Decide the next version and confirm its order relative to historical tags; update source metadata and changelog consistently.
- [ ] Run `python3 -m unittest discover -s tests -v` with FFmpeg/ffprobe present; confirm the real-render test is not skipped and CI passes.
- [ ] Reproduce the local CLI mock and FFmpeg paths; inspect MP4 video/audio streams, duration, SRT, timeline, QA report, and failure states.
- [ ] Have a named human view/listen to the candidate media and record acceptance or rejection separately from mechanical QA.
- [ ] Confirm fixture/media licenses, synthetic labels, no secrets or private data, and README links/install steps.
- [ ] Fill the [release note template](RELEASE_NOTES_TEMPLATE.md) with actual changes, verification, limits, and run instructions.
- [ ] Obtain a separate explicit publication decision; only then tag/publish. Do not mark this checklist complete from CI alone.
