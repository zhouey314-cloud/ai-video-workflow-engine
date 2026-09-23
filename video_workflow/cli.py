import json
from pathlib import Path
from .engine import Asset,Shot,Job,MockProvider,LocalFFmpegProvider,ExternalProviderInterface,run
def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--provider',choices=['mock','ffmpeg','external'],default='mock');p.add_argument('--output',default='output/report.json');p.add_argument('--media-output',default='output/demo.mp4');args=p.parse_args()
    data=json.loads(Path('examples/storyboard.json').read_text())
    job=Job(data['title'],data['script'],data['persona'],[Shot(**s) for s in data['shots']],data['budget_usd'])
    assets=[Asset(**{**a,'tags':tuple(a['tags'])}) for a in json.loads(Path('examples/assets.json').read_text())]
    provider={'mock':MockProvider(),'ffmpeg':LocalFFmpegProvider(),'external':ExternalProviderInterface()}[args.provider]
    output=Path(args.media_output if args.provider=='ffmpeg' else 'output/demo.json')
    result=run(job,assets,provider,output)
    Path(args.output).parent.mkdir(parents=True,exist_ok=True);Path(args.output).write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
if __name__=='__main__': main()
