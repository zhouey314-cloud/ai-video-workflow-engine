"""A small real encode of all nine original shots; not full-film human QA."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO=Path(__file__).resolve().parents[1]
FONTS=[Path('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'),Path('/System/Library/Fonts/STHeiti Medium.ttc')]

@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe') and importlib.util.find_spec('PIL'),'FFmpeg/ffprobe/Pillow required')
class OriginalDemoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.font=next((p for p in FONTS if p.is_file()),None)
        if not cls.font:raise unittest.SkipTest('A local CJK font is required')
        cls.temp=tempfile.TemporaryDirectory(prefix='original-demo-')
        cls.root=Path(cls.temp.name)
        cls.env={'PATH':os.environ.get('PATH',os.defpath),'PYTHONPATH':str(REPO),'PYTHONDONTWRITEBYTECODE':'1'}
        generated=subprocess.run([sys.executable,str(REPO/'examples/original_54s/generate.py'),'--output',str(cls.root/'assets'),
            '--font',str(cls.font),'--shot-seconds','0.5','--fps','2'],env=cls.env,capture_output=True,text=True,timeout=90)
        if generated.returncode:raise RuntimeError(generated.stderr)

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls,'temp'):cls.temp.cleanup()

    def invoke(self,*,config=None,assets=None):
        with tempfile.TemporaryDirectory(dir=self.root) as temporary:
            target=Path(temporary)
            data=json.loads((self.root/'assets/storyboard.json').read_text())
            records=json.loads((self.root/'assets/assets.json').read_text())
            data['render']['music_path']=str(self.root/'assets/original-score.wav')
            for record in records:record['path']=str(self.root/'assets'/record['path'])
            if config:config(data)
            if assets:assets(records)
            (target/'storyboard.json').write_text(json.dumps(data,ensure_ascii=False))
            (target/'assets.json').write_text(json.dumps(records))
            p=subprocess.run([sys.executable,'-m','video_workflow.cli','--provider','ffmpeg','--storyboard',str(target/'storyboard.json'),
                '--assets',str(target/'assets.json'),'--font',str(self.font),'--media-output',str(target/'result.mp4'),
                '--output',str(target/'report.json')],cwd=target,env=self.env,capture_output=True,text=True,timeout=90)
            self.assertTrue(p.stdout,p.stderr)
            report=json.loads(p.stdout)
            self.assertEqual(report,json.loads((target/'report.json').read_text()))
            return p,report

    def test_nine_original_assets_and_score_use_existing_engine(self):
        p,r=self.invoke()
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(r['state'],'HUMAN_REVIEW')
        self.assertEqual(r['failures'],[])
        self.assertEqual(r['media_qa']['music']['license'],'SELF')
        self.assertTrue(r['media_qa']['caption_pixel_bounds']['within_safe_area'])
        self.assertTrue(r['media_qa']['full_decode'])
        self.assertAlmostEqual(float(r['media_qa']['probe']['format']['duration']),4.5,delta=.25)

    def test_unknown_music_license_fails_before_render(self):
        p,r=self.invoke(config=lambda d:d['render'].update(music_license='UNKNOWN'))
        self.assertNotEqual(p.returncode,0)
        self.assertEqual(r['state'],'FAILED')
        self.assertIn('MUSIC_LICENSE_UNVERIFIED',' '.join(r['events']))

    def test_missing_video_asset_is_explicit(self):
        p,r=self.invoke(assets=lambda a:a[0].update(path=str(self.root/'missing.mp4')))
        self.assertNotEqual(p.returncode,0)
        self.assertEqual(r['state'],'FAILED')
        self.assertIn('MATERIAL_FILE_MISSING',' '.join(r['events']))

    def test_unreadably_dense_caption_is_rejected_without_truncation(self):
        p,r=self.invoke(config=lambda d:d['shots'][0].update(narration='中文长字幕。'*100))
        self.assertNotEqual(p.returncode,0)
        self.assertEqual(r['state'],'FAILED')
        self.assertIn('CAPTION_TOO_DENSE',' '.join(r['events']))

    def test_sample_generator_rejects_missing_glyph_instead_of_baking_a_box(self):
        from array import array
        from PIL import Image,ImageDraw
        spec=importlib.util.spec_from_file_location('original_sample',REPO/'examples/original_54s/generate.py')
        module=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        frames=module.Frames(self.font,array('f',[0]),.5)
        with self.assertRaisesRegex(ValueError,'FONT_GLYPH_UNAVAILABLE'):
            frames.text(ImageDraw.Draw(Image.new('RGB',(200,100))),(10,10),'\U0010ffff')
