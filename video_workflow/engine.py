from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import json
import shutil
import subprocess

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
        destination.parent.mkdir(parents=True,exist_ok=True)
        duration=sum(s.seconds for s in job.shots)
        subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y","-f","lavfi","-i",f"color=c=#192f46:s=640x360:r=24:d={duration}","-pix_fmt","yuv420p",str(destination)],check=True)
        return str(destination)

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
