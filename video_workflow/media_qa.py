"""Deterministic FFmpeg measurements. Passing these is never human approval."""
from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess


def command(args: list[str], *, cwd: Path | None = None, timeout: int = 180) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True, timeout=timeout)


def measure_media(path: Path) -> dict:
    path = path.resolve()
    probe = command(['ffprobe', '-v', 'error', '-show_entries',
        'format=duration,size:stream=codec_type,codec_name,width,height,avg_frame_rate', '-of', 'json', str(path)])
    result = {'probe': json.loads(probe.stdout)}
    # Full decode, rather than trusting container headers alone.
    decoded = command(['ffmpeg', '-v', 'error', '-i', str(path), '-f', 'null', '-'])
    result['full_decode'] = not decoded.stderr.strip()
    analysis = command(['ffmpeg', '-hide_banner', '-nostats', '-i', str(path),
        '-vf', 'blackdetect=d=0.30:pic_th=0.98:pix_th=0.05', '-af', 'volumedetect', '-f', 'null', '-'])
    black = [{'start': float(a), 'end': float(b), 'duration': float(c)} for a,b,c in
        re.findall(r'black_start:([\d.]+) black_end:([\d.]+) black_duration:([\d.]+)', analysis.stderr)]
    peaks = re.findall(r'max_volume:\s*(-?[\d.]+|-inf) dB', analysis.stderr)
    peak = float(peaks[-1]) if peaks and peaks[-1] != '-inf' else None
    means = re.findall(r'mean_volume:\s*(-?[\d.]+|-inf) dB', analysis.stderr)
    result.update({'black_intervals': black, 'black_detection': {'minimum_seconds': 0.30,
        'frame_black_fraction': 0.98, 'pixel_luma_threshold': 0.05},
        'audio_sample_peak_dbfs': peak, 'audio_peak_limit_dbfs': -0.5,
        'audio_mean_volume_dbfs': float(means[-1]) if means and means[-1] != '-inf' else None})
    return result


def measure_caption_pixels(*, scratch: Path, width: int, height: int, seconds: float) -> dict:
    # Render the exact same ASS/font layer on black. bbox measures actual glyph
    # pixels after libass layout, including wrapping/fallback, not source coordinates.
    result = command(['ffmpeg', '-hide_banner', '-nostats', '-f', 'lavfi', '-i',
        f'color=c=black:s={width}x{height}:r=2:d={seconds}', '-vf',
        'subtitles=filename=captions.ass:fontsdir=fonts,bbox=min_val=40', '-an', '-f', 'null', '-'], cwd=scratch)
    boxes = [tuple(map(int, values)) for values in re.findall(
        r'x1:(\d+) x2:(\d+) y1:(\d+) y2:(\d+) w:(\d+) h:(\d+)', result.stderr)]
    visible = [box for box in boxes if box[4] > 0 and box[5] > 0]
    margin_x, margin_y = round(width * 0.04), round(height * 0.035)
    missing = sorted(set(re.findall(r'Glyph (0x[0-9A-Fa-f]+).*not found', result.stderr)))
    within = bool(visible) and not missing and all(x1 >= margin_x and x2 < width-margin_x
        and y1 >= margin_y and y2 < height-margin_y for x1,x2,y1,y2,_,_ in visible)
    return {'method': 'libass caption-only rendered pixels + FFmpeg bbox, 2 frames/second',
        'measured_frames': len(boxes), 'visible_frames': len(visible),
        'safe_area': [margin_x, margin_y, width-margin_x, height-margin_y],
        'union': [min(x[0] for x in visible), min(x[2] for x in visible),
                  max(x[1] for x in visible), max(x[3] for x in visible)] if visible else None,
        'within_safe_area': within, 'missing_glyphs': missing,
        'limits': 'Caption-layer pixel bounds only; does not establish readability, semantic timing or full visual/human acceptance.'}
