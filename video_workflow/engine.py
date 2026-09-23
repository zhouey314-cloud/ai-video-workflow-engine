from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import json
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

@dataclass(frozen=True)
class Shot:
    id: str
    seconds: float
    requested_tag: str
    narration: str

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

class LocalFFmpegProvider(Provider):
    def render(self, job:Job, assets:list[Asset], destination:Path)->str:
        if not shutil.which("ffmpeg"): raise RuntimeError("NOT_CONFIGURED: ffmpeg")
        if not shutil.which("ffprobe"): raise RuntimeError("NOT_CONFIGURED: ffprobe")
        destination.parent.mkdir(parents=True,exist_ok=True)
        font=next((p for p in ("/System/Library/Fonts/Supplemental/Verdana.ttf","/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf") if Path(p).exists()),None)
        if not font:raise RuntimeError("NOT_CONFIGURED: font")
        palette=[("0x102c45","0x26c6b5"),("0x172b47","0xffb36a"),("0x25304e","0x91a7ff")]
        timeline=[];elapsed=0.0
        with tempfile.TemporaryDirectory(prefix="video-workflow-") as scratch:
            tmp=Path(scratch);parts=[]
            for i,(shot,asset) in enumerate(zip(job.shots,assets)):
                background,accent=palette[i%len(palette)]
                title_file=tmp/f"title-{i}.txt"
                title_file.write_text("SYNTHETIC WORKFLOW\n"+shot.requested_tag.upper(),encoding="utf-8")
                clip=tmp/f"shot-{i}.mp4"
                vf=(f"drawbox=x=36:y=32:w=568:h=296:color={accent}@0.12:t=fill,"
                    f"drawbox=x=38:y=56:w=9:h=238:color={accent}:t=fill,"
                    f"drawbox=x=70:y=265:w=490:h=2:color={accent}@0.8:t=fill,"
                    f"drawtext=fontfile={font}:textfile={title_file}:fontcolor=white:fontsize=32:x=72:y=94:line_spacing=15,"
                    f"drawtext=fontfile={font}:text=SCENE_{i+1:02d}:fontcolor={accent}:fontsize=16:x=72:y=55")
                subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y","-f","lavfi","-i",f"color=c={background}:s=640x360:r=24:d={shot.seconds}","-vf",vf,"-c:v","libx264","-pix_fmt","yuv420p",str(clip)],check=True)
                parts.append(clip)
                timeline.append({"shot_id":shot.id,"asset_id":asset.id,"start_seconds":elapsed,"duration_seconds":shot.seconds,"end_seconds":elapsed+shot.seconds,"synthetic":True})
                elapsed+=shot.seconds
            concat_file=tmp/"concat.txt"
            concat_file.write_text("".join(f"file '{p}'\n" for p in parts),encoding="utf-8")
            captions=destination.with_suffix(".srt")
            def timestamp(seconds:float)->str:
                ms=round(seconds*1000);h,ms=divmod(ms,3600000);m,ms=divmod(ms,60000);s,ms=divmod(ms,1000)
                return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
            captions.write_text("".join(f"{i+1}\n{timestamp(item['start_seconds'])} --> {timestamp(item['end_seconds'])}\n{shot.narration}\n\n" for i,(item,shot) in enumerate(zip(timeline,job.shots))),encoding="utf-8")
            subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y","-f","concat","-safe","0","-i",str(concat_file),"-f","lavfi","-i",f"sine=frequency=330:sample_rate=48000:duration={elapsed}","-vf",f"subtitles={captions}:force_style='FontSize=19,PrimaryColour=&H00FFFFFF,OutlineColour=&H0021374A,Outline=2,MarginV=25'","-af","volume=0.10","-c:v","libx264","-crf","25","-c:a","aac","-b:a","64k","-pix_fmt","yuv420p","-shortest",str(destination)],check=True)
        destination.with_suffix(".timeline.json").write_text(json.dumps(timeline,indent=2),encoding="utf-8")
        subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y","-ss","1","-i",str(destination),"-frames:v","1",str(destination.with_suffix(".png"))],check=True)
        return str(destination)

def probe_media(path:Path)->dict:
    result=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration,size:stream=codec_type,codec_name,width,height","-of","json",str(path)],check=True,capture_output=True,text=True)
    return json.loads(result.stdout)

def validate(job:Job)->None:
    if not job.title.strip() or not job.script.strip() or not job.persona.strip(): raise ValueError("missing input")
    if not job.shots or any(s.seconds<=0 or not s.id for s in job.shots): raise ValueError("invalid storyboard")
    if len({s.id for s in job.shots})!=len(job.shots): raise ValueError("duplicate shot")
    if job.budget_usd<0: raise ValueError("invalid budget")

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
    if job.output and Path(job.output).suffix==".mp4" and Path(job.output).exists():
        try:
            media=probe_media(Path(job.output))
            streams=media["streams"]
            video=next((s for s in streams if s["codec_type"]=="video"),None)
            if not video or video.get("width")!=640 or video.get("height")!=360:failures.append("VIDEO_STREAM_INVALID")
            if not any(s["codec_type"]=="audio" for s in streams):failures.append("AUDIO_STREAM_MISSING")
            if abs(float(media["format"]["duration"])-sum(s.seconds for s in job.shots))>0.25:failures.append("DURATION_MISMATCH")
            if not Path(job.output).with_suffix(".srt").exists():failures.append("CAPTIONS_MISSING")
        except (OSError,KeyError,ValueError,subprocess.CalledProcessError):failures.append("MEDIA_PROBE_FAILED")
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
    return {"title":job.title,"state":job.state.value,"gaps":gaps,"failures":failures,"output":job.output,"cost_usd":job.cost_usd,"budget_usd":job.budget_usd,"retries":job.retries,"events":job.events,"synthetic_unverified":True}
