# Contributing

This repository accepts small, reproducible fixes to the offline synthetic workflow. Open an Issue first for behavior or scope changes; PRs should state what is implemented versus planned.

1. Use Python 3.10+, FFmpeg, and ffprobe. Run `python3 -m unittest discover -s tests -v` from the repository root. The FFmpeg test must run, not skip.
2. For a render change, run `python3 -m video_workflow.cli --provider ffmpeg --media-output /tmp/video-workflow-review.mp4 --output /tmp/video-workflow-review.json` and inspect its report and media streams. A mechanical pass does not replace human viewing/listening.
3. Describe reproduction steps, expected/actual behavior, tests, and any output artifacts in the PR. Keep samples synthetic or clearly licensed; do not add private footage, voices, client data, credentials, or unreviewed third-party media.
4. Update `CHANGELOG.md` for user-visible behavior. Keep planned features in `ROADMAP.md` until implemented and tested.

See the [release checklist](docs/releases/RELEASE_CHECKLIST.md) before proposing a tag. Release publication and the current version-number conflict require a maintainer decision.
