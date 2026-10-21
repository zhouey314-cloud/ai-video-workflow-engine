"""Real process/media regression cases; all fixtures are synthetic."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from video_workflow.engine import Job, Shot, qa

REPO = Path(__file__).resolve().parents[1]
FFMPEG = shutil.which('ffmpeg')
FFPROBE = shutil.which('ffprobe')

@unittest.skipUnless(FFMPEG and FFPROBE, 'FFmpeg/ffprobe required')
class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory(prefix='video-delivery-')
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name)
        shutil.copytree(REPO / 'examples', self.root / 'examples')

    def invoke(self, *args):
        process = subprocess.run([sys.executable, '-m', 'video_workflow.cli', '--provider', 'ffmpeg', *args],
            cwd=self.root, env={'PATH': os.environ.get('PATH', os.defpath), 'PYTHONPATH': str(REPO), 'PYTHONDONTWRITEBYTECODE': '1'},
            capture_output=True, text=True, timeout=90)
        self.assertTrue(process.stdout, process.stderr)
        report = json.loads(process.stdout)
        self.assertEqual(json.loads((self.root / 'output/report.json').read_text()), report)
        return process, report

    def test_special_character_output_path(self):
        output = self.root / "作品 O'Brien [v1]: review" / '字幕 demo.mp4'
        process, report = self.invoke('--media-output', str(output))
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(report['state'], 'HUMAN_REVIEW')
        self.assertTrue(output.is_file())

    def test_invalid_font_returns_failure_json_and_preserves_existing_output(self):
        output = self.root / 'previous.mp4'
        output.write_bytes(b'previous synthetic artifact')
        process, report = self.invoke('--font', str(self.root / 'missing.ttf'), '--media-output', str(output))
        self.assertNotEqual(process.returncode, 0)
        self.assertEqual(report['state'], 'FAILED')
        self.assertIn('font', ' '.join(report['events']).lower())
        self.assertEqual(output.read_bytes(), b'previous synthetic artifact')

    def test_recovery_after_blocked_destination(self):
        output = self.root / 'blocked.mp4'
        output.mkdir()
        failed, failure = self.invoke('--media-output', str(output))
        self.assertNotEqual(failed.returncode, 0)
        self.assertEqual(failure['state'], 'FAILED')
        output.rmdir()
        process, report = self.invoke('--media-output', str(output))
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(report['state'], 'HUMAN_REVIEW')
        self.assertFalse(any(x.startswith('APPROVED_BY:') for x in report['events']))

    def test_long_chinese_caption_is_measured_from_rendered_pixels(self):
        storyboard = self.root / 'examples/storyboard.json'
        data = json.loads(storyboard.read_text())
        data['shots'][0]['narration'] = '字幕需要真实检查边界，中文标点、长句和特殊路径都不能让画面越界。'
        storyboard.write_text(json.dumps(data, ensure_ascii=False))
        process, report = self.invoke()
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(report['state'], 'HUMAN_REVIEW')
        metrics = report['media_qa']
        self.assertTrue(metrics['caption_pixel_bounds']['within_safe_area'])
        self.assertGreater(metrics['caption_pixel_bounds']['measured_frames'], 0)
        self.assertTrue(metrics['font']['available'])

    def test_black_and_clipped_media_cannot_pass_qa(self):
        output = self.root / 'unsafe.mp4'
        subprocess.run([FFMPEG, '-v', 'error', '-y', '-f', 'lavfi', '-i', 'color=c=black:s=640x360:r=24:d=2',
            '-f', 'lavfi', '-i', 'sine=frequency=440:duration=2', '-af', 'volume=30', '-c:v', 'libx264',
            '-c:a', 'aac', '-pix_fmt', 'yuv420p', '-shortest', str(output)], check=True, capture_output=True)
        output.with_suffix('.srt').write_text('1\n00:00:00,000 --> 00:00:02,000\nSynthetic caption\n')
        job = Job('QA fixture', 'synthetic', 'fixture', [Shot('a', 2, 'a', 'Synthetic caption')])
        job.output = str(output)
        failures = qa(job)
        self.assertIn('BLACK_FRAMES', failures)
        self.assertIn('AUDIO_PEAK_EXCEEDED', failures)
