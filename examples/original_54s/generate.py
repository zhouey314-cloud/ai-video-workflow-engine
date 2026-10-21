"""Original procedural animation and score. No stock, voices, models or downloads.

Outputs are local video assets for the existing video_workflow FFmpeg provider.
Pillow is used only by this optional sample generator. Font files are not bundled.
"""
from __future__ import annotations

import argparse
from array import array
import hashlib
import json
import math
from pathlib import Path
import random
import shutil
import subprocess
import wave

from PIL import Image, ImageDraw, ImageFont

W, H = 1280, 720
INK = (25, 30, 38)
PAPER = (241, 234, 218)
GOLD = (240, 173, 84)
MUTED = (141, 151, 158)
CHAPTERS = [
    ('OPEN THE FRAME', '交付，不止导出', '从一个想法开始，让每个镜头都有清楚的去处。'),
    ('PLAN THE SHOTS', '先看见，再剪辑', '把起承转合放进分镜，给节奏留出呼吸。'),
    ('KNOW THE SOURCE', '每个画面，都有来源', '这里的山、水和光，都是程序原创绘制，没有使用客户素材。'),
    ('MAKE WORDS READABLE', '信息，要看得清', '中文、标点和换行，都需要在真实画面里检查。'),
    ('LET SOUND BREATHE', '让声音成为节奏', '配乐由数学合成器原创生成，没有采样，也没有真人声音。'),
    ('CONNECT THE MOMENTS', '转场，是一口呼吸', '用光、方向和运动连接画面，让变化服务于叙事。'),
    ('MEASURE THE OUTPUT', '导出后，再检查', '时长、解码、黑帧、声音峰值和字幕边界，都要留下证据。'),
    ('MAKE FAILURE VISIBLE', '失败，也能重来', '失败要明确返回，已有文件要保护，修好之后再重试。'),
    ('REVIEW THE WHOLE FILM', '最后，交给人来看', '机器检查通过，仍然等待你完整观看，再决定是否批准。'),
]


def mix(a, b, t):
    return tuple(round(x+(y-x)*t) for x, y in zip(a, b))


def ease(t):
    t = max(0, min(1, t))
    return 1-(1-t)**3


def original_score(destination: Path, seconds: float) -> array:
    """A new 120-BPM pentatonic arpeggio/bass/percussion score, not a cover."""
    rate = 48000
    count = round(rate*seconds)
    mono = array('f', [0.0])*count
    rng = random.Random(20261021)
    # This algorithmic note sequence was authored for this sample. No recording,
    # reference melody, sample pack, TTS, performer or existing song is used.
    roots = [48, 45, 41, 43]
    pattern = [0, 7, 12, 16, 7, 19, 12, 7, 0, 12, 7, 16]
    def tone(start, duration, midi, level, bass=False):
        offset = round(start*rate)
        size = min(round(duration*rate), count-offset)
        frequency = 440*2**((midi-69)/12)
        for n in range(max(0,size)):
            t = n/rate
            envelope = min(1,t/.012)*math.exp(-t*(3.6 if bass else 6.5))
            value = math.sin(math.tau*frequency*t)+.17*math.sin(math.tau*frequency*2*t)
            mono[offset+n] += level*envelope*value
    for step in range(math.ceil(seconds/.25)):
        start = step*.25
        root = roots[(step//24)%len(roots)]
        tone(start,.55,root+12+pattern[step%len(pattern)],.11)
        if step%4 == 0:
            tone(start,.7,root-12,.18,True)
        if step%2 == 0:
            offset=round(start*rate)
            for n in range(min(round(rate*.16),count-offset)):
                t=n/rate
                kick=math.sin(math.tau*(52*t+12*(1-math.exp(-t*32))))*math.exp(-t*30)
                mono[offset+n]+=.18*kick
        offset=round(start*rate)
        for n in range(min(round(rate*.035),count-offset)):
            mono[offset+n]+=.025*(rng.random()*2-1)*math.exp(-n/(rate*.007))
    peak=max(abs(x) for x in mono) or 1
    scale=.38/peak
    pcm=array('h')
    for i,value in enumerate(mono):
        fade=min(1,i/(rate*.4),(count-i)/(rate*1.1))
        sample=value*scale*fade
        mono[i]=sample
        pan=.075*math.sin(math.tau*i/(rate*8))
        pcm.extend((round(sample*(1-pan)*32767),round(sample*(1+pan)*32767)))
    with wave.open(str(destination),'wb') as output:
        output.setnchannels(2);output.setsampwidth(2);output.setframerate(rate)
        output.writeframes(pcm.tobytes())
    return mono


class Frames:
    def __init__(self, font: Path, audio: array, seconds: float):
        self.font_path=font
        self.fonts={}
        self.audio=audio
        self.checked_glyphs=set()
        self.total=seconds*9
        self.seconds=seconds
        rng=random.Random(314)
        base=Image.new('RGB',(320,180))
        pixels=base.load()
        for y in range(180):
            for x in range(320):
                glow=max(0,1-math.hypot((x-235)/200,(y-45)/150))
                noise=rng.randrange(-2,3)
                pixels[x,y]=(round(25+glow*9)+noise,round(30+glow*7)+noise,round(38+glow*2)+noise)
        self.background=base.resize((W,H),Image.Resampling.BICUBIC)

    def font(self,size):
        if size not in self.fonts:self.fonts[size]=ImageFont.truetype(str(self.font_path),size)
        return self.fonts[size]

    def text(self,draw,xy,text,size=26,fill=PAPER,anchor=None):
        # Fail instead of silently baking a missing-glyph box into a video asset.
        font=self.font(24)
        missing=font.getmask('\U0010ffff')
        for char in set(text)-self.checked_glyphs:
            if not char.isspace():
                glyph=font.getmask(char)
                if glyph.size==missing.size and bytes(glyph)==bytes(missing):
                    raise ValueError(f'FONT_GLYPH_UNAVAILABLE: U+{ord(char):04X}')
            self.checked_glyphs.add(char)
        draw.text(xy,text,font=self.font(size),fill=fill,anchor=anchor)

    def landscape(self, image, rect, t, variant=0):
        x,y,w,h=rect
        d=ImageDraw.Draw(image,'RGBA')
        skies=[(211,181,143),(154,183,184),(49,67,83)]
        sky=skies[variant%3]
        d.rectangle((x,y,x+w,y+h),fill=sky)
        sunx=x+w*(.72+.04*math.sin(t*.3));suny=y+h*(.29+.03*math.cos(t*.2))
        suncolor=(248,222,153) if variant!=2 else (227,230,215)
        r=w*.065;d.ellipse((sunx-r,suny-r,sunx+r,suny+r),fill=suncolor)
        for layer in range(4):
            points=[(x,y+h)]
            for i in range(19):
                xx=x+i*w/18
                yy=y+h*(.45+layer*.135)+math.sin(i*1.3+layer*2.4+t*(.09+layer*.035))*h*(.1-layer*.013)
                points.append((xx,yy))
            points.append((x+w,y+h))
            color=mix((115,130,126),(28,62,70),layer/3) if variant!=2 else mix((79,98,112),(21,39,54),layer/3)
            d.polygon(points,fill=color)
        d.polygon([(x,y+h*.80),(x+w,y+h*.76),(x+w,y+h),(x,y+h)],fill=(71,102,108))
        for k in range(9):
            yy=y+h*(.82+k*.018)
            xx=x+w*(.20+.15*math.sin(k*2+t*.2))
            d.line((xx,yy,xx+w*(.18+.03*k),yy),fill=(*PAPER,55),width=max(1,round(h/180)))
        # Original geometric birds and a foreground reed move with the camera.
        for k in range(3):
            bx=x+w*((.15+k*.11+t*.012)%1);by=y+h*(.19+k*.055)
            d.line((bx-6,by+2,bx,by,bx+6,by+2),fill=(*INK,130),width=2)
        for k in range(8):
            px=x+w*(.88+k*.018);py=y+h
            d.line((px,py,px+w*.012*math.sin(t+k),py-h*(.13+(k%3)*.025)),fill=(*INK,180),width=2)

    def paper(self,image,xy,number,t,angle):
        card=Image.new('RGBA',(330,245),(0,0,0,0));d=ImageDraw.Draw(card,'RGBA')
        d.rounded_rectangle((3,3,326,241),radius=9,fill=PAPER)
        self.landscape(card,(16,16,298,165),t,number%3)
        self.text(d,(18,197),f'{number+1:02d} / SHOT',22,INK)
        d.line((185,212,307,212),fill=(*INK,110),width=2)
        rotated=card.rotate(angle,resample=Image.Resampling.BICUBIC,expand=True)
        image.paste(rotated,(round(xy[0]),round(xy[1])),rotated)

    def scene(self,index,t,global_time):
        im=self.background.copy();d=ImageDraw.Draw(im,'RGBA')
        phase=t/max(.001,self.seconds)
        # Shared registration marks and drifting editorial geometry.
        for k in range(7):
            xx=(k*235+global_time*7)%1500-100
            d.line((xx,135,xx+150,565),fill=(*PAPER,12),width=1)
        d.line((64,118,1216,118),fill=(*PAPER,55),width=1)
        self.text(d,(64,42),'CUT / SET / DELIVER',24,GOLD)
        self.text(d,(1216,43),f'{index+1:02d} / 09',24,PAPER,'ra')
        self.text(d,(64,82),'原创程序动画  ·  自制配乐  ·  非真人口播',20,MUTED)
        self.text(d,(1216,83),CHAPTERS[index][0],20,MUTED,'ra')

        if index==0:
            self.text(d,(80,200),'交付，',96)
            self.text(d,(80,310),'不止导出',96)
            self.text(d,(84,440),'A FILM ABOUT THE LAST MILE',23,GOLD)
            cx,cy=940,345
            for ring in range(3):
                r=155+ring*23+3*math.sin(t+ring)
                d.ellipse((cx-r,cy-r,cx+r,cy+r),outline=(*GOLD,160-ring*35),width=2)
            for k in range(12):
                a=math.tau*k/12+t*.19
                points=[(cx+math.cos(a)*165,cy+math.sin(a)*165),
                    (cx+math.cos(a+.43)*165,cy+math.sin(a+.43)*165),
                    (cx+math.cos(a+.9)*68,cy+math.sin(a+.9)*68),
                    (cx+math.cos(a+.48)*68,cy+math.sin(a+.48)*68)]
                d.polygon(points,fill=(*mix(INK,GOLD,.26+(k%3)*.15),255),outline=(*GOLD,180))
            self.text(d,(cx,cy-12),f'{self.total:g}',66,PAPER,'mm');self.text(d,(cx,cy+45),'SECONDS',18,GOLD,'mm')
        elif index==1:
            self.text(d,(80,185),'先看见，',78);self.text(d,(80,277),'再剪辑',78)
            self.text(d,(85,393),'结构 / 节奏 / 留白',28,GOLD)
            self.paper(im,(690+12*math.sin(t*.5),175),0,t,-9)
            self.paper(im,(860,290+10*math.sin(t*.6)),1,t,8)
            self.paper(im,(560,357),2,t,-4)
        elif index==2:
            self.landscape(im,(64,142,1152,440),t+20,0);d=ImageDraw.Draw(im,'RGBA')
            d.rectangle((64,142,1216,231),fill=(*INK,170))
            self.text(d,(92,162),'每个画面，都有来源',52)
            self.text(d,(1165,535),'ORIGINAL / NO STOCK',22,PAPER,'ra')
            d.line((90,545,370,545),fill=GOLD,width=3)
        elif index==3:
            self.landscape(im,(160,168,960,382),t+8,2);d=ImageDraw.Draw(im,'RGBA')
            d.rectangle((190,194,1090,520),fill=(*INK,115))
            for x,y,sx,sy in [(142,150,1,1),(1138,150,-1,1),(142,566,1,-1),(1138,566,-1,-1)]:
                d.line((x+sx*50,y,x,y,x,y+sy*40),fill=GOLD,width=4)
            self.text(d,(640,260),'信息，要看得清',68,PAPER,'mm')
            visible='中文、标点、换行，都值得认真对待。'[:max(1,round(19*min(1,phase*1.8)))]
            self.text(d,(640,361),visible,36,PAPER,'mm')
            d.line((300,407,300+680*ease(phase*1.6),407),fill=GOLD,width=3)
            self.text(d,(640,470),'CAPTION LAYOUT / GLYPH PIXELS',23,GOLD,'mm')
        elif index==4:
            cx,cy=350,356
            for r in range(34,204,8):d.ellipse((cx-r,cy-r,cx+r,cy+r),outline=(*PAPER,35 if r%16 else 70),width=2)
            d.ellipse((cx-72,cy-72,cx+72,cy+72),fill=GOLD)
            a=global_time*.9;d.line((cx,cy,cx+58*math.cos(a),cy+58*math.sin(a)),fill=INK,width=5)
            self.text(d,(665,185),'让声音',66);self.text(d,(665,264),'成为节奏',66)
            start=round(global_time*48000)
            points=[]
            for k in range(240):
                n=min(len(self.audio)-1,max(0,start+k*20))
                points.append((640+k*2.23,430+self.audio[n]*210))
            d.line(points,fill=GOLD,width=3)
            self.text(d,(650,505),'120 BPM  /  SELF-COMPOSED  /  NO VOICE',21,MUTED)
            beat=(global_time*2)%1
            for k in range(8):
                x=650+k*64;r=6+(1-beat)*8 if int(global_time*2)%8==k else 5
                d.ellipse((x-r,556-r,x+r,556+r),fill=GOLD if r>6 else (*MUTED,130))
        elif index==5:
            for k in range(3):
                x=64+k*384
                self.landscape(im,(x,143,382,435),t+k*13,k)
            d=ImageDraw.Draw(im,'RGBA');slide=math.sin(phase*math.pi)*110
            for k in range(2):
                x=446+k*384+slide*(1 if k==0 else -1)
                d.polygon([(x-65,143),(x+18,143),(x+118,578),(x+35,578)],fill=(*INK,235))
            d.rectangle((64,143,1216,240),fill=(*INK,180))
            self.text(d,(90,164),'转场，是一口呼吸',56)
            self.text(d,(1186,539),'DIRECTION / LIGHT / CONTINUITY',21,PAPER,'ra')
        elif index==6:
            self.landscape(im,(80,170,655,367),t+30,1);d=ImageDraw.Draw(im,'RGBA')
            scan=80+(phase%1)*655
            d.rectangle((scan-18,170,scan+18,537),fill=(*GOLD,80));d.line((scan,170,scan,537),fill=GOLD,width=3)
            self.text(d,(800,170),'导出后，',64);self.text(d,(800,247),'再检查',64)
            for k,label in enumerate(['DURATION / DECODE','BLACK / AUDIO PEAK','FONT / CAPTION BOUNDS','SOURCE / LICENSE']):
                yy=350+k*49;d.ellipse((800,yy+5,810,yy+15),outline=GOLD,width=2)
                self.text(d,(828,yy),label,21,PAPER)
            self.text(d,(82,554),'MEASURE THE FILE, NOT JUST ITS NAME',20,GOLD)
        elif index==7:
            self.text(d,(80,182),'失败，',78);self.text(d,(80,278),'也能重来',78)
            self.text(d,(83,401),'FAIL CLEARLY / KEEP THE PREVIOUS FILE',21,GOLD)
            nodes=[(650,340),(825,340),(1000,340),(1160,340)]
            d.line([p for p in nodes],fill=(*MUTED,110),width=4)
            for k,(x,y) in enumerate(nodes):
                r=38+3*math.sin(t+k)
                color=(218,114,96) if k==1 and phase<.42 else GOLD
                d.ellipse((x-r,y-r,x+r,y+r),fill=(*INK,255),outline=color,width=4)
                if k==1 and phase>=.42:
                    d.arc((x-15,y-15,x+15,y+15),35,315,fill=color,width=3)
                    d.polygon([(x+14,y-13),(x+17,y-2),(x+5,y-6)],fill=color)
                else:
                    self.text(d,(x,y),['IN','!','QA','OUT'][k],25,color,'mm')
            progress=ease(max(0,(phase-.38)/.62));x=650+510*progress
            d.ellipse((x-9,331,x+9,349),fill=PAPER)
            self.text(d,(910,440),'RETRY' if phase>=.42 else 'FAILURE IS A STATE',25,GOLD,'mm')
            for k in range(8):
                xx=650+k*65;d.line((xx,510,xx+35,510),fill=(*GOLD,80+int(progress*150)),width=3)
        else:
            for k in range(5):
                x=720+k*88;y=170+25*math.sin(t*.45+k*.5)
                self.landscape(im,(x,y,74,310),t+k*11,k%3)
            d=ImageDraw.Draw(im,'RGBA')
            self.text(d,(80,178),'最后，',78);self.text(d,(80,273),'交给人来看',78)
            self.text(d,(85,409),'HUMAN_REVIEW',40,GOLD)
            self.text(d,(85,477),'完整观看，再决定 APPROVED / REJECTED',25)
            d.line((82,546,580,546),fill=(*GOLD,160),width=2)
            self.text(d,(82,562),'NO AUTO-APPROVAL  /  NO PUBLISH',20,MUTED)
        d=ImageDraw.Draw(im,'RGBA')
        # Caption area below content remains clear for the real engine burn-in.
        d.rectangle((0,601,W,H),fill=(*INK,235))
        d.line((64,699,1216,699),fill=(*MUTED,75),width=2)
        progress=min(1,global_time/max(.001,self.total))
        d.line((64,699,64+1152*progress,699),fill=GOLD,width=3)
        return im

    def frame(self,index,t):
        global_time=index*self.seconds+t
        current=self.scene(index,t,global_time)
        transition=min(.32,self.seconds*.25)
        if index and t<transition:
            previous=self.scene(index-1,self.seconds-.001,global_time)
            alpha=ease(t/transition)
            if index%3==0:
                split=round(W*alpha);previous.paste(current.crop((0,0,split,H)),(0,0));return previous
            return Image.blend(previous,current,alpha)
        return current


def build(output: Path, font: Path, seconds: float=6, fps: int=24):
    if not shutil.which('ffmpeg'):raise RuntimeError('ffmpeg is required')
    if not font.is_file():raise ValueError('An available, licensed CJK font is required')
    if not .5<=seconds<=6 or not 1<=fps<=30 or seconds*fps%1:raise ValueError('Use 0.5..6 seconds and an integral frame count')
    output.mkdir(parents=True,exist_ok=True)
    audio=original_score(output/'original-score.wav',seconds*9)
    frames=Frames(font,audio,seconds)
    assets=[];shots=[]
    for index,(_,title,narration) in enumerate(CHAPTERS):
        path=output/f'shot-{index+1:02d}.mp4'
        process=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}',
            '-r',str(fps),'-i','-','-an','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p',str(path)],stdin=subprocess.PIPE)
        try:
            for frame in range(round(seconds*fps)):
                process.stdin.write(frames.frame(index,frame/fps).tobytes())
            process.stdin.close()
            if process.wait(timeout=120):raise RuntimeError('FFmpeg asset encoding failed')
        except BaseException:
            process.kill();process.wait();raise
        tag=f'original-{index+1:02d}'
        assets.append({'id':tag,'kind':'video','tags':[tag],'license':'SELF','synthetic':True,'path':path.name})
        shots.append({'id':tag,'seconds':seconds,'requested_tag':tag,'narration':narration})
        print(json.dumps({'shot':index+1,'title':title,'seconds':seconds,'file':path.name},ensure_ascii=False),flush=True)
    storyboard={'title':'交付，不止导出 / Cut, Set, Deliver','script':'Original procedural-film demonstration of a responsible video handoff.',
        'persona':'A viewer reviewing an offline engineering film; no client or human-speaker claim','budget_usd':0,
        'render':{'width':W,'height':H,'fps':fps,'caption_font_size':36,'music_path':'original-score.wav','music_license':'SELF'},'shots':shots}
    (output/'storyboard.json').write_text(json.dumps(storyboard,ensure_ascii=False,indent=2)+'\n')
    (output/'assets.json').write_text(json.dumps(assets,ensure_ascii=False,indent=2)+'\n')
    files=[output/'original-score.wav',*[output/a['path'] for a in assets]]
    manifest={'origin':'New original procedural drawing, animation and mathematical music authored for this sample; not real footage or speech',
        'license':'SELF; code is covered by repository MIT, generated original media may be redistributed under the repository MIT license; font rights remain separate',
        'third_party_media':False,'voices_or_models':False,'music':{'bpm':120,'rate':48000,'channels':2,'composition':'original arpeggio/bass/synthetic percussion; no melody reference or recording'},
        'font':{'name':font.name,'sha256':hashlib.sha256(font.read_bytes()).hexdigest(),'bundled':False,
            'operator_must_preserve_license':True,'glyph_mask_checked_codepoints':len(frames.checked_glyphs)},
        'human_review':'PENDING; machine checks cannot approve this film',
        'files':[{'file':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size} for p in files]}
    (output/'ASSET_MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    return storyboard


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--font',type=Path,required=True)
    parser.add_argument('--shot-seconds',type=float,default=6);parser.add_argument('--fps',type=int,default=24)
    args=parser.parse_args()
    build(args.output,args.font,args.shot_seconds,args.fps)
