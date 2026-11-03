# 共享确定性技术证据

```sh
.venv/bin/python -m mechanical_video.technical_evidence /path/to/new.mp4 \
  --output /path/to/new-evidence --producer visual-agent-id \
  --script /path/to/narration.txt --subtitles /path/to/captions.json
.venv/bin/python -m mechanical_video.video_qa /path/to/new.mp4 \
  --output /path/to/new-video-qa --technical-evidence /path/to/new-evidence/technical-evidence.json
.venv/bin/python -m mechanical_video.audio_qa /path/to/new.mp4 /path/to/narration.txt \
  --output /path/to/new-audio-qa --technical-evidence /path/to/new-evidence/technical-evidence.json
```

默认 QA 调用保持兼容。证据采集只运行本地 FFmpeg/ffprobe，不请求 ASR/TTS/视觉供应商。输出生产者身份、内容指纹、依赖指纹、工具版本、命令、参数、覆盖和逐项结果摘要哈希；QA 报告明确记录引用及生产来源。退出码 0=所有已请求确定性项成功，1=存在失败项，2=输入错误；不是媒体验收。

Video QA 新增 `--profile formal|local-silent|local-av`，默认 formal。local-silent 仅豁免正式90秒片长与必需音轨；local-av 仅豁免正式片长，仍要求音轨。已有音轨仍检查 AAC，画面仍要求 H.264/原规格并完整解码；局部报告明确 `formal_acceptance: false`，不升级为正式验收。已确认 P0/P1 保持 FAIL/REWORK，即使感官分数缺失，也不能只标 NEEDS_REVIEW。

每项缓存依媒体内容、该项所用依赖、工具版本、检查代码版本及检查参数识别；媒体/工具变化失效全部，字幕变化仅失效字幕，抽帧参数变化仅失效抽帧。失败、损坏和缺失结果不复用，缺失/变化的抽帧重建。依赖路径必须仍可读取，QA 加载时重新验证所有指纹、必需检查和结果完整性，音频 QA 另核对实际稿件哈希；失效即拒绝而非假装通过。未提供的字幕/时间线不会伪报通过。

Video QA 按项校验缓存：只重新执行失效/命令不匹配的项，报告 `technical_cache_mismatches` 的字段路径及实际 `technical_reused_checks`。未传 parameters 时沿用包内参数，再校验逐项键；包内自带参数不再因默认空参数被整包误拒。无关依赖缺失不影响媒体本身的 decode，但依赖它的检查不得复用。媒体/工具/实现版本变化仍使相关全部失效。严格 `load`（含 Audio QA 默认调用）仍拒绝不完整包；需要独立执行的检查继续省略 `--technical-evidence`，不由生产缓存替代。

采集项目：probe 原始流信息（编码分辨率/帧率；原生设置仍须由制作记录提供）、完整音视频解码、独立音轨解码、静音/音量测量、黑屏/冻结/静音候选、抽帧清单和适当分辨率联系表。先看联系表，再打开疑点原图；字幕、引线及细小几何保留原生细节。技术扫描候选仍需结合意图判断，不由结果自动生成感官分。

字幕输入为 JSON 数组 `[{"start":0,"end":1,"text":"短字幕"}]`，逐行检查单行、≤20字、一次一条、无重叠、有效且在媒体内的区间。可选 `--timeline` 是带 `media_sha256`、`dependencies`（除时间线本身外所有依赖名称→哈希）的 JSON；只检查关联，不宣称逐词/镜头语义同步。未请求项保持未测。

独立 QA 必须核验来源、配置、范围和实际媒体并形成自己的结论；要求独立执行的检查应省略 `--technical-evidence` 按原命令执行。共享包不继承生产自评、用户批准、音频/观众分数或新版本 QA 结论；哈希是关联和损坏检测，不是防篡改签名。不得以缓存或更换模型补足缺失的实时播放、听审和对齐能力。
