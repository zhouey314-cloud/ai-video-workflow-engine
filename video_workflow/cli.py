import json
from pathlib import Path
from .engine import Asset,Shot,Job,State,RenderConfig,MockProvider,LocalFFmpegProvider,ExternalProviderInterface,run
def main() -> int:
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--provider',choices=['mock','ffmpeg','external'],default='mock');p.add_argument('--output',default='output/report.json');p.add_argument('--media-output',default='output/demo.mp4');p.add_argument('--font');p.add_argument('--storyboard',default='examples/storyboard.json');p.add_argument('--assets',default='examples/assets.json');args=p.parse_args()
    try:
        data=json.loads(Path(args.storyboard).read_text())
        config=dict(data.get('render',{}))
        if args.font:config['font_path']=args.font
        elif config.get('font_path'):config['font_path']=str((Path(args.storyboard).resolve().parent / config['font_path']).resolve())
        if config.get('music_path'):config['music_path']=str((Path(args.storyboard).resolve().parent / config['music_path']).resolve())
        job=Job(data['title'],data['script'],data['persona'],[Shot(**s) for s in data['shots']],data['budget_usd'],render=RenderConfig(**config))
        asset_records=json.loads(Path(args.assets).read_text())
        for asset in asset_records:
            if asset.get('path'):asset['path']=str((Path(args.assets).resolve().parent / asset['path']).resolve())
        assets=[Asset(**{**a,'tags':tuple(a['tags'])}) for a in asset_records]
        provider={'mock':MockProvider(),'ffmpeg':LocalFFmpegProvider(),'external':ExternalProviderInterface()}[args.provider]
        output=Path(args.media_output if args.provider=='ffmpeg' else 'output/demo.json')
        result=run(job,assets,provider,output)
    except (OSError,ValueError,KeyError,TypeError) as exc:
        result={'state':'FAILED','failures':['INPUT_INVALID'],'events':['INPUT_INVALID:'+str(exc)],
                'output':None,'gaps':[],'synthetic_unverified':True}
    Path(args.output).parent.mkdir(parents=True,exist_ok=True);Path(args.output).write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
    return 0 if result['state'] in (State.HUMAN_REVIEW.value,State.APPROVED.value) else 1
if __name__=='__main__': raise SystemExit(main())
