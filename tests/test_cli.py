"""Exercise exit status and JSON reports through real Python processes."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]
FFMPEG = shutil.which('ffmpeg')
FFPROBE = shutil.which('ffprobe')


class CLITests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory(prefix='video-workflow-cli-')
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name)
        (self.root / 'examples').mkdir()
        for name in ('storyboard.json', 'assets.json'):
            shutil.copyfile(REPO / 'examples' / name, self.root / 'examples' / name)

    def invoke(self, *args, path=None, console_entry=False):
        env = {
            'PATH': os.environ.get('PATH', os.defpath) if path is None else str(path),
            'PYTHONPATH': str(REPO),
            'PYTHONDONTWRITEBYTECODE': '1',
            'TMPDIR': str(self.root),
            'XDG_CACHE_HOME': str(self.root / 'cache'),
        }
        # The configured console script also exits with the return value of main().
        entry = (['-c', 'from video_workflow.cli import main; raise SystemExit(main())']
                 if console_entry else ['-m', 'video_workflow.cli'])
        process = subprocess.run([sys.executable, '-B', *entry, *args], cwd=self.root,
                                 env=env, capture_output=True, text=True, timeout=45)
        report_path = self.root / 'output' / 'report.json'
        self.assertTrue(report_path.is_file(), process.stderr)
        report = json.loads(report_path.read_text())
        self.assertEqual(json.loads(process.stdout), report, process.stderr)
        self.assertTrue(report['synthetic_unverified'])
        return process, report

    def assert_review(self, process, report):
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(report['state'], 'HUMAN_REVIEW')
        self.assertEqual(report['failures'], [])
        self.assertEqual(report['gaps'], [])
        self.assertIn('QA:PASS', report['events'])
        self.assertIn('AWAITING_HUMAN_REVIEW', report['events'])
        self.assertFalse(any(event.startswith('APPROVED_BY:') for event in report['events']))

    def assert_render_failure(self, process, report):
        self.assertEqual(process.returncode, 1, process.stderr)
        self.assertEqual(report['state'], 'FAILED')
        self.assertEqual(report['failures'], ['RENDER_FAILED'])
        self.assertEqual(report['retries'], 1)
        self.assertIsNone(report['output'])

    def test_mock_success_awaits_human_review(self):
        process, report = self.invoke()
        self.assert_review(process, report)
        rendered = json.loads((self.root / report['output']).read_text())
        self.assertTrue(rendered['demo'])
        self.assertEqual(rendered['shots'], ['opening', 'closing'])

    def test_external_unconfigured_fails_with_json_report(self):
        process, report = self.invoke('--provider', 'external')
        self.assert_render_failure(process, report)
        self.assertIn('RENDER_FAILED:NOT_CONFIGURED', report['events'])

    def test_missing_material_fails_with_gap_report(self):
        (self.root / 'examples' / 'assets.json').write_text('[]')
        process, report = self.invoke('--provider', 'mock')
        self.assertEqual(process.returncode, 1, process.stderr)
        self.assertEqual(report['state'], 'GAP')
        self.assertEqual(report['gaps'], ['opening', 'closing'])
        self.assertEqual(report['failures'], ['MATERIAL_GAP'])
        self.assertEqual(report['retries'], 0)
        self.assertIsNone(report['output'])
        self.assertFalse((self.root / 'output' / 'demo.json').exists())

    def test_rejected_material_fails_with_gap_report(self):
        asset_path = self.root / 'examples' / 'assets.json'
        original = json.loads(asset_path.read_text())
        for property_name, value in (('license', 'UNKNOWN'), ('synthetic', False)):
            with self.subTest(property=property_name):
                assets = [dict(asset, **{property_name: value}) for asset in original]
                asset_path.write_text(json.dumps(assets))
                process, report = self.invoke('--provider', 'mock')
                self.assertEqual(process.returncode, 1, process.stderr)
                self.assertEqual(report['state'], 'GAP')
                self.assertEqual(report['failures'], ['MATERIAL_GAP'])

    def test_mock_render_error_fails_with_json_report(self):
        (self.root / 'output' / 'demo.json').mkdir(parents=True)
        self.assert_render_failure(*self.invoke('--provider', 'mock'))

    def test_mechanical_qa_failure_is_nonzero(self):
        storyboard = self.root / 'examples' / 'storyboard.json'
        data = json.loads(storyboard.read_text())
        data['shots'][0]['narration'] = ''
        storyboard.write_text(json.dumps(data))
        process, report = self.invoke('--provider', 'mock')
        self.assertEqual(process.returncode, 1, process.stderr)
        self.assertEqual(report['state'], 'FAILED')
        self.assertEqual(report['failures'], ['NARRATION_MISSING'])
        self.assertIn('QA:FAIL', report['events'])
        self.assertEqual(report['retries'], 0)
        self.assertTrue((self.root / report['output']).is_file())

    def test_missing_ffmpeg_fails_with_json_report(self):
        empty_bin = self.root / 'empty-bin'
        empty_bin.mkdir()
        process, report = self.invoke('--provider', 'ffmpeg', path=empty_bin)
        self.assert_render_failure(process, report)
        self.assertIn('RENDER_FAILED:NOT_CONFIGURED: ffmpeg', report['events'])

    @unittest.skipUnless(FFMPEG, 'FFmpeg required')
    def test_missing_ffprobe_fails_with_json_report(self):
        only_ffmpeg = self.root / 'only-ffmpeg'
        only_ffmpeg.mkdir()
        (only_ffmpeg / 'ffmpeg').symlink_to(FFMPEG)
        process, report = self.invoke('--provider', 'ffmpeg', path=only_ffmpeg)
        self.assert_render_failure(process, report)
        self.assertIn('RENDER_FAILED:NOT_CONFIGURED: ffprobe', report['events'])

    @unittest.skipUnless(FFMPEG and FFPROBE, 'FFmpeg/ffprobe required')
    def test_ffmpeg_success_awaits_human_review(self):
        process, report = self.invoke('--provider', 'ffmpeg')
        self.assert_review(process, report)
        media = self.root / report['output']
        for suffix in ('.mp4', '.srt', '.timeline.json', '.png'):
            self.assertTrue(media.with_suffix(suffix).is_file())
        probe = subprocess.run([FFPROBE, '-v', 'error', '-show_entries',
                                'format=duration:stream=codec_type', '-of', 'json', str(media)],
                               capture_output=True, text=True, check=True, timeout=15)
        result = json.loads(probe.stdout)
        self.assertEqual({stream['codec_type'] for stream in result['streams']}, {'video', 'audio'})
        self.assertAlmostEqual(float(result['format']['duration']), 6.0, delta=0.25)

    @unittest.skipUnless(FFMPEG and FFPROBE, 'FFmpeg/ffprobe required')
    def test_ffmpeg_render_error_fails_with_json_report(self):
        # An existing directory cannot serve as an MP4 destination; run real FFmpeg.
        destination = self.root / 'output' / 'blocked.mp4'
        destination.mkdir(parents=True)
        process, report = self.invoke('--provider', 'ffmpeg', '--media-output', str(destination))
        self.assert_render_failure(process, report)
        self.assertTrue(process.stderr, 'FFmpeg must report the real render error')

    def test_console_entry_callable_returns_status(self):
        for provider, expected in (('mock', 0), ('external', 1)):
            with self.subTest(provider=provider):
                process, report = self.invoke('--provider', provider, console_entry=True)
                self.assertEqual(process.returncode, expected, process.stderr)
                self.assertEqual(report['state'], 'HUMAN_REVIEW' if expected == 0 else 'FAILED')


if __name__ == '__main__':
    unittest.main()
