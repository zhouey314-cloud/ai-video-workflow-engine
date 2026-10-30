# 一次任务，一份可检查的交付包

适合素材、字幕与导出容易在交接中失去对应关系的流程。引擎读取明确的素材清单和分镜，检查许可，执行 FFmpeg、完整解码和机械 QA，最后等待人工审片。调用者可以用退出码和报告接入自己的任务系统。

```sh
mkdir -p output
python -m video_workflow.cli --provider ffmpeg --bundle-dir output/job-001 --output output/job-001.receipt.json
python -m video_workflow.cli --verify-bundle output/job-001
```

目标目录必须全新。先在同目录下的私有临时目录渲染、检查，再发布完成的任务目录；失败不发布半套包，原有目标不会覆盖。每个并发任务使用不同目标目录；它不是跨进程的任务队列。原 `--media-output` 兼容路径继续可用。

包中有 MP4、SRT、ASS、时间轴 JSON、真实预览图、QA 报告和 manifest。manifest 保存输入清单、使用的素材/音轨哈希和每个交付文件的大小/SHA256。校验器拒绝缺文件、篡改、重复路径、越界路径、符号链接及未列入清单的文件；只接受等待人工审片的状态。校验结果是文件完整性，不是来源签名、剪辑质量或人工批准。

`--verify-bundle` 只做本地校验，不重渲染、不付费。失败返回非零。所有正式业务素材仍应由操作员确认权利；当前示例是原创/合成素材。原有 54 秒样片的批准只绑定其历史文件哈希，不扩展到新任务。

本轮 55 条测试含真实 FFmpeg 交付包、篡改、路径和失败回收，保留全部原测试与样片批准记录。CLI 返回 HUMAN_REVIEW 并不授予 APPROVED。
