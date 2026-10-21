# Cut / Set / Deliver — 54 seconds, pending human review

Nine original procedural-animation shots demonstrate planning, source provenance,
subtitle layout, music, transitions, output checks, recovery and full-film review.
This is **not human talking-head footage, a customer video or a production claim**.
No model, paid API, TTS, private voice, stock clip or downloaded recording is used.

The score is an original 120-BPM mathematical arpeggio/bass/percussion composition.
Drawings and score are SELF assets, redistributable under this repository's MIT
license. This grant does not apply to font files: none are bundled. Use a licensed
CJK font such as Noto Sans CJK and retain its SIL OFL notice. Debian/Ubuntu's
`fonts-noto-cjk` package supplies `/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc`.
The rendered sample used Noto Sans CJK SC Bold under SIL OFL; its hash is in the
asset manifest. Font glyph masks are checked before baking text into frames.

## Reproduce locally

Install FFmpeg/ffprobe and `python -m pip install -r examples/original_54s/requirements.txt`.
From the repository root, set `--font` to an available licensed CJK font:

```bash
python examples/original_54s/generate.py --output output/original54 --font /path/to/NotoSansCJK-Regular.ttc
python -m video_workflow.cli --provider ffmpeg --storyboard output/original54/storyboard.json --assets output/original54/assets.json --font /path/to/NotoSansCJK-Regular.ttc --media-output output/original54/film.mp4 --output output/original54/report.json
```

The generator streams frames directly to FFmpeg; it does not store 1,296 PNGs.
It writes nine independent 6-second/1280×720/24fps video assets, a 54-second stereo
WAV, storyboard, asset map and SHA256 provenance. Transitions are drawn into the
original source frames. The existing workflow selects SELF-tagged assets,
normalizes/concatenates them, burns real subtitles, adds the score and runs QA.
Relative paths are resolved against the explicit storyboard/asset files.

The generator's `--shot-seconds 0.5 --fps 2` mode is only a fast integration
fixture: all nine scenes pass through actual encoding, asset selection, subtitle
rendering, audio and QA in 4.5 seconds. CI uses this fixture; **CI does not render
or human-approve the complete 54-second film**. Full-duration local evidence and
the committed sample are separate. Default generation remains 54 seconds.

## Acceptance limits

`HUMAN_REVIEW` is a successful mechanical run and exit 0. `FAILED` and `GAP` are
nonzero. Unknown soundtrack licenses and missing video assets fail before output
publication; over-dense captions fail instead of being truncated. Font absence,
special paths, missing FFmpeg and render recovery have process regressions.

Black detection covers intervals at least 0.30 seconds. Audio peak is a sample
peak, not a true-peak/loudness certification. Caption-layer pixel bounds are
sampled at 2fps, not every full frame. Assistant frame spot-checks and mechanical
metrics do not establish human full-film approval. Readability, rhythm, musical
quality, complete viewing and final `APPROVED / REJECTED` remain the user's gate.
No reviewer name or approval may be invented. No automatic publishing is added.
