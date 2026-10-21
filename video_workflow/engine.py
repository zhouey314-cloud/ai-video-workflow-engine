from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import json
import hashlib
import math
import os
import sys
import unicodedata
from .media_qa import measure_media, measure_caption_pixels
import shutil
import subprocess
import tempfile

class State(str, Enum):
    INPUT="INPUT"; SCRIPT="SCRIPT"; GROUNDED="GROUNDED"; STORYBOARD="STORYBOARD"
    MATERIAL="MATERIAL"; GAP="GAP"; TIMELINE="TIMELINE"; RENDERED="RENDERED"
    QA="QA"; HUMAN_REVIEW="HUMAN_REVIEW"; APPROVED="APPROVED"; FAILED="FAILED"

@dataclass(frozen=True)
class Asset:
    id: str
    kind: str
    tags: tuple[str,...]
    license: str
    synthetic: bool=True
    path: str|None=None

@dataclass(frozen=True)
class Shot:
    id: str
    seconds: float
    requested_tag: str
    narration: str

@dataclass(frozen=True)
class RenderConfig:
    width: int = 640
    height: int = 360
    fps: int = 24
    font_path: str | None = None
    font_family: str | None = None
    caption_font_size: int | None = None
    music_path: str | None = None
    music_license: str | None = None

@dataclass
class Job:
    title: str
    script: str
    persona: str
    shots: list[Shot]
    budget_usd: float=0.0
    state: State=State.INPUT
    events: list[str]=field(default_factory=list)
    cost_usd: float=0.0
    retries: int=0
    output: str|None=None
    render: RenderConfig=field(default_factory=RenderConfig)
    media_qa: dict=field(default_factory=dict)

class Provider:
    def render(self, job:Job, assets:list[Asset], destination:Path)->str:
        raise NotImplementedError

class MockProvider(Provider):
    def render(self, job:Job, assets:list[Asset], destination:Path)->str:
        destination.parent.mkdir(parents=True,exist_ok=True)
        destination.write_text(json.dumps({"demo":True,"title":job.title,"shots":[s.id for s in job.shots],"assets":[a.id for a in assets]},indent=2))
        return str(destination)

class ExternalProviderInterface(Provider):
    def render(self, job:Job, assets:list[Asset], destination:Path)->str:
        raise RuntimeError("NOT_CONFIGURED")

def _timestamp(seconds: float, ass: bool = False) -> str:
    ms = round(seconds*1000)
    h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); sec, ms = divmod(ms, 1000)
    return f"{h}:{m:02d}:{sec:02d}.{ms//10:02d}" if ass else f"{h:02d}:{m:02d}:{sec:02d},{ms:03d}"


def _caption_lines(text: str, width: int, font_size: int) -> list[str]:
    limit = int(width * 0.84 / (font_size * 0.55))
    lines = []; line = ''; units = 0
    for char in text:
        size = 2 if unicodedata.east_asian_width(char) in {'W','F'} else 1
        if char == '\n' or (line and units+size > limit):
            lines.append(line); line = ''; units = 0
        if char != '\n': line += char; units += size
    if line: lines.append(line)
    if len(lines) > 3: raise ValueError('CAPTION_TOO_DENSE: split the shot text; maximum three lines')
    return lines


class LocalFFmpegProvider(Provider):
    def render(self, job:Job, assets:list[Asset], destination:Path)->str:
        for binary in ('ffmpeg','ffprobe'):
            if not shutil.which(binary): raise RuntimeError('NOT_CONFIGURED: '+binary)
        cfg = job.render
        if cfg.music_path and cfg.music_license not in {'SELF','CC0'}: raise ValueError('MUSIC_LICENSE_UNVERIFIED')
        if cfg.music_path and not Path(cfg.music_path).is_file(): raise ValueError('MUSIC_FILE_MISSING')
        candidates = ([cfg.font_path] if cfg.font_path else [
            '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
            '/System/Library/Fonts/STHeiti Medium.ttc',
            '/System/Library/Fonts/Supplemental/Verdana.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'])
        font = next((Path(p) for p in candidates if p and Path(p).is_file()), None)
        if not font: raise RuntimeError('NOT_CONFIGURED: font')
        family = cfg.font_family or ('Noto Sans CJK SC' if 'Noto' in font.name else
            'Heiti SC' if 'Heiti' in font.name else 'Verdana' if 'Verdana' in font.name else 'DejaVu Sans')
        destination = destination.resolve()
        if destination.suffix.lower() != '.mp4': raise ValueError('MP4_OUTPUT_REQUIRED')
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.is_dir(): raise IsADirectoryError(str(destination))
        timeline = []; elapsed = 0.0
        with tempfile.TemporaryDirectory(prefix='video-workflow-', dir=destination.parent) as scratch:
            tmp = Path(scratch); (tmp/'fonts').mkdir()
            copied_font = Path('fonts') / ('workflow'+font.suffix)
            shutil.copyfile(font, tmp/copied_font)
            palette=[('0x102c45','0x26c6b5'),('0x172b47','0xffb36a'),('0x25304e','0x91a7ff')]
            parts=[]; size=cfg.caption_font_size or round(cfg.height/15)
            ass = (f'[Script Info]\nScriptType: v4.00+\nPlayResX: {cfg.width}\nPlayResY: {cfg.height}\nWrapStyle: 0\n'
                '[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n'
                f'Style: Default,{family},{size},&H00F4F4EE,&H00F4F4EE,&H0021374A,&H80000000,0,0,0,0,100,100,0,0,1,2,0,2,{round(cfg.width*.07)},{round(cfg.width*.07)},{round(cfg.height*.08)},1\n'
                '[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n')
            srt = ''
            def execute(args):
                subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y',*args],cwd=tmp,check=True,timeout=180)
            for i,(shot,asset) in enumerate(zip(job.shots,assets)):
                background,accent=palette[i%len(palette)]
                (tmp/f'title-{i}.txt').write_text('SYNTHETIC WORKFLOW\n'+shot.requested_tag.upper(),encoding='utf-8')
                clip=f'shot-{i}.mp4'
                vf=(f'drawbox=x=36:y=32:w={cfg.width-72}:h={cfg.height-64}:color={accent}@0.12:t=fill,'
                    f'drawbox=x=38:y=56:w=9:h={cfg.height-122}:color={accent}:t=fill,'
                    f'drawtext=fontfile={copied_font}:textfile=title-{i}.txt:fontcolor=white:fontsize={round(cfg.height/11)}:x=72:y=94:line_spacing=15')
                if asset.path:
                    source = Path(asset.path).resolve()
                    if not source.is_file(): raise ValueError('MATERIAL_FILE_MISSING:'+asset.id)
                    if asset.kind != 'video': raise ValueError('UNSUPPORTED_MATERIAL_KIND:'+asset.kind)
                    execute(['-i',str(source),'-t',str(shot.seconds),'-an','-vf',
                        f'scale={cfg.width}:{cfg.height}:force_original_aspect_ratio=decrease,pad={cfg.width}:{cfg.height}:(ow-iw)/2:(oh-ih)/2',
                        '-r',str(cfg.fps),'-c:v','libx264','-crf','20','-pix_fmt','yuv420p',clip])
                else:
                    execute(['-f','lavfi','-i',f'color=c={background}:s={cfg.width}x{cfg.height}:r={cfg.fps}:d={shot.seconds}',
                        '-vf',vf,'-c:v','libx264','-pix_fmt','yuv420p',clip])
                parts.append(clip)
                timeline.append({'shot_id':shot.id,'asset_id':asset.id,'start_seconds':elapsed,
                    'duration_seconds':shot.seconds,'end_seconds':elapsed+shot.seconds,'synthetic':True})
                lines=_caption_lines(shot.narration,cfg.width,size)
                wrapped='\n'.join(lines)
                srt+=f'{i+1}\n{_timestamp(elapsed)} --> {_timestamp(elapsed+shot.seconds)}\n{wrapped}\n\n'
                escaped=wrapped.replace('\\','\\\\').replace('{','\\{').replace('}','\\}').replace('\n',r'\N')
                ass+=f'Dialogue: 0,{_timestamp(elapsed,True)},{_timestamp(elapsed+shot.seconds,True)},Default,,0,0,0,,{escaped}\n'
                elapsed+=shot.seconds
            (tmp/'captions.srt').write_text(srt,encoding='utf-8');(tmp/'captions.ass').write_text(ass,encoding='utf-8')
            (tmp/'concat.txt').write_text(''.join(f"file '{part}'\n" for part in parts),encoding='utf-8')
            caption_bounds=measure_caption_pixels(scratch=tmp,width=cfg.width,height=cfg.height,seconds=elapsed)
            if not caption_bounds['within_safe_area']: raise ValueError('CAPTIONS_OUT_OF_BOUNDS_OR_INVISIBLE')
            audio_input = ['-i',str(Path(cfg.music_path).resolve())] if cfg.music_path else ['-f','lavfi','-i',f'sine=frequency=330:sample_rate=48000:duration={elapsed}']
            audio_filter = f'afade=t=in:d=0.35,afade=t=out:st={max(0,elapsed-1)}:d=1' if cfg.music_path else 'volume=0.10'
            execute(['-f','concat','-safe','0','-i','concat.txt',*audio_input,
                '-vf','subtitles=filename=captions.ass:fontsdir=fonts','-af',audio_filter,
                '-c:v','libx264','-crf','22','-c:a','aac','-b:a','160k','-pix_fmt','yuv420p','-shortest','final.mp4'])
            execute(['-ss',str(min(1,elapsed/2)),'-i','final.mp4','-frames:v','1','preview.png'])
            (tmp/'timeline.json').write_text(json.dumps(timeline,indent=2),encoding='utf-8')
            # FFmpeg/filter paths use fixed relative names in a private scratch dir;
            # user paths never enter filter syntax or concat manifests.
            for name,suffix in [('captions.srt','.srt'),('captions.ass','.ass'),('timeline.json','.timeline.json'),('preview.png','.png')]:
                os.replace(tmp/name,destination.with_suffix(suffix))
            os.replace(tmp/'final.mp4',destination)
            job.media_qa={'font':{'available':True,'name':family,'sha256':hashlib.sha256(font.read_bytes()).hexdigest()},
                'caption_pixel_bounds':caption_bounds,'music':{'license':cfg.music_license if cfg.music_path else 'SELF','source':'operator-provided locally licensed soundtrack' if cfg.music_path else 'mathematical sine tone; compatibility demo, not a finished soundtrack','sha256':hashlib.sha256(Path(cfg.music_path).read_bytes()).hexdigest() if cfg.music_path else None}}
        return str(destination)

def probe_media(path:Path)->dict:
    result=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration,size:stream=codec_type,codec_name,width,height","-of","json",str(path)],check=True,capture_output=True,text=True)
    return json.loads(result.stdout)

def validate(job:Job)->None:
    if not job.title.strip() or not job.script.strip() or not job.persona.strip(): raise ValueError("missing input")
    if not job.shots or any(not math.isfinite(s.seconds) or s.seconds<=0 or not s.id for s in job.shots): raise ValueError("invalid storyboard")
    if len({s.id for s in job.shots})!=len(job.shots): raise ValueError("duplicate shot")
    if not math.isfinite(job.budget_usd) or job.budget_usd<0: raise ValueError("invalid budget")
    if job.render.width < 320 or job.render.height < 180 or job.render.width%2 or job.render.height%2 or not 1 <= job.render.fps <= 60: raise ValueError("invalid render dimensions/fps")

def retrieve(shots:list[Shot],assets:list[Asset])->tuple[list[Asset],list[str]]:
    found=[];gaps=[]
    for shot in shots:
        matches=[a for a in assets if a.synthetic and a.license in {"CC0","SELF"} and shot.requested_tag in a.tags]
        if matches: found.append(matches[0])
        else: gaps.append(shot.id)
    return found,gaps

def qa(job:Job)->list[str]:
    failures=[]
    if not job.output or not Path(job.output).exists(): failures.append("OUTPUT_MISSING")
    if sum(s.seconds for s in job.shots)>60: failures.append("DURATION_EXCEEDS_DEMO_LIMIT")
    if job.cost_usd>job.budget_usd: failures.append("BUDGET_EXCEEDED")
    if any(not s.narration.strip() for s in job.shots): failures.append("NARRATION_MISSING")
    if job.output and Path(job.output).suffix.lower()==".mp4" and Path(job.output).exists():
        try:
            measured=measure_media(Path(job.output))
            job.media_qa.update(measured)
            media=measured["probe"]
            if not measured["full_decode"]: failures.append("MEDIA_DECODE_FAILED")
            if measured["black_intervals"]: failures.append("BLACK_FRAMES")
            peak=measured["audio_sample_peak_dbfs"]
            if peak is None: failures.append("AUDIO_SILENT_OR_UNMEASURED")
            elif peak > measured["audio_peak_limit_dbfs"]: failures.append("AUDIO_PEAK_EXCEEDED")
            if not job.media_qa.get("caption_pixel_bounds",{}).get("within_safe_area"): failures.append("CAPTION_BOUNDS_NOT_VERIFIED")
            if not job.media_qa.get("font",{}).get("available"): failures.append("FONT_NOT_VERIFIED")
            if job.media_qa.get("music",{}).get("license") not in {"SELF","CC0"}: failures.append("MUSIC_LICENSE_UNVERIFIED")
            streams=media["streams"]
            video=next((s for s in streams if s["codec_type"]=="video"),None)
            if not video or video.get("width")!=job.render.width or video.get("height")!=job.render.height:failures.append("VIDEO_STREAM_INVALID")
            if not any(s["codec_type"]=="audio" for s in streams):failures.append("AUDIO_STREAM_MISSING")
            if abs(float(media["format"]["duration"])-sum(s.seconds for s in job.shots))>0.25:failures.append("DURATION_MISMATCH")
            if not Path(job.output).with_suffix(".srt").exists():failures.append("CAPTIONS_MISSING")
        except (OSError,KeyError,ValueError,subprocess.CalledProcessError,subprocess.TimeoutExpired):failures.append("MEDIA_PROBE_FAILED")
    return failures

def run(job:Job,assets:list[Asset],provider:Provider,destination:Path)->dict:
    validate(job)
    for state in (State.SCRIPT,State.GROUNDED,State.STORYBOARD,State.MATERIAL):
        job.state=state;job.events.append(state.value)
    selected,gaps=retrieve(job.shots,assets)
    if gaps:
        job.state=State.GAP;job.events.append("MATERIAL_GAP:"+",".join(gaps));job.events.append("OPTIONAL_GENERATION_NOT_CONFIGURED")
        return report(job,gaps,["MATERIAL_GAP"])
    job.state=State.TIMELINE;job.events.append("TIMELINE_PLANNED")
    try:
        job.output=provider.render(job,selected,destination)
        job.state=State.RENDERED;job.events.append("RENDERED")
    except Exception as exc:
        print("RENDER_FAILED:"+str(exc),file=sys.stderr)
        job.retries+=1;job.state=State.FAILED;job.events.append("RENDER_FAILED:"+str(exc))
        return report(job,[],["RENDER_FAILED"])
    failures=qa(job);job.state=State.QA;job.events.append("QA:"+("PASS" if not failures else "FAIL"))
    if failures:job.state=State.FAILED;return report(job,[],failures)
    job.state=State.HUMAN_REVIEW;job.events.append("AWAITING_HUMAN_REVIEW")
    return report(job,[],[])

def approve(job:Job,reviewer:str)->None:
    if job.state!=State.HUMAN_REVIEW or not reviewer.strip(): raise ValueError("human review required")
    job.state=State.APPROVED;job.events.append("APPROVED_BY:"+reviewer)

def report(job:Job,gaps:list[str],failures:list[str])->dict:
    return {"title":job.title,"state":job.state.value,"gaps":gaps,"failures":failures,"output":job.output,"cost_usd":job.cost_usd,"budget_usd":job.budget_usd,"retries":job.retries,"events":job.events,"synthetic_unverified":True,"media_qa":job.media_qa}
