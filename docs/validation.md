# 实际验收记录 — 2026-10-27

## 指定 output/demo.mp4 实际生成

- CAD v8：`artifacts/models/c5c7cdfe005db2bb/assembly.json`，19个独立零件；新增输入/输出青铜滑动轴承。19件STEP实际回读，均有效、正体积且各含一个实体，证据为模型目录的 `solid-validation.json`。
- 新拆解镜头先打开壳体和紧固件，再逐个分离太阳轮与三颗行星轮，最后展开轴、轴承、销和行星架；150帧全部实际Eevee渲染。关键帧1/42/85/120已人工视觉检查，保存为 `output/demo.keyframes.jpg`。
- 成片 `output/demo.mp4`：503334字节，1280×720，30/1 fps，5.000秒，150帧，H.264；ffprobe检查与FFmpeg全帧解码通过。`output/demo.validation.json`记录场景与模型路径及队列done状态。
- Blender工程 `artifacts/videos/d2de4840dc9d7b5fd144/scene.blend`，独立场景审核19对象、取景边界及相对位移通过，排除了静态画面和整体平移。原始帧、脚本快照、STEP/STL和装配STEP全部保留。
- 本轮13项unittest通过，日志 `output/tests.log`。沙箱内Blender曾SIGSEGV；通过本机GPU访问重新渲染成功，未修改沙箱配置或安装环境。
- CAD Skill拓扑inspect因缺少GLB侧车未通过；实体有效性依据实际build123d STEP回读，不宣称Explorer验收。模型为教学推定结构，不代表制造认证或动力学仿真。

## Ethan音色版本

- 按用户要求实际调用 audiogen / qwen3-tts-flash / Ethan 重新生成11段中文语音，保留Roy成片，复用90秒镜头底片。
- 输出 `artifacts/机械拆解-90秒-中文-Ethan.mp4`，重新按Ethan片段实测时长生成中文字幕与句间停顿。90秒、720p H.264、AAC、中文字幕轨，全片解码通过；同名 `.zh.srt` 单独保留。镜头剪辑仍沿用原版节奏，未随新音色重新剪辑。

## 90秒中文男声实际成片

- 用户配置已在运行环境生效，实际通过 audiogen / qwen3-tts-flash / Roy 生成11段中文语音，共71.736秒；未自动重试提供商请求。
- 成片 `artifacts/机械拆解-90秒-中文.mp4`：90.000秒，1280×720、30fps、2700帧，H.264/yuv420p、AAC中文音轨、mov_text中文字幕轨；FFmpeg全片解码通过。音轨均值-20.4dB，峰值-2.0dB；未做人工听感验收或ASR逐字校验。
- 使用已验证CAD镜头按讲解编排11段，放慢画面、保持语音原速、句间补观察停顿；不是重新渲染2700个独立镜头帧。原90秒单模板待处理任务标为superseded并保留。
- 中文SRT位于成片同名 `.zh.srt`；原始音频、稿件、缓存和合成音频均保留。镜头计划及来源哈希见 `artifacts/videos/chinese-explainer-90s/timeline.json`；导演脚本归档为同目录 `director.py`。
- 重构配音准备阶段以允许配音与渲染并行准备，本轮13项测试通过。下方“未配置凭据/未生成成片”为前一阶段历史记录，当前在线配音已验证。

## audiogen 中文配音接入

- 用户指定的 audiogen Skill 原样复制到项目 `.agents/skills/audiogen`，未修改来源项目；项目 openai 依赖已安装并验证导入。
- 新增 `mechanical_video.voiceover` 和90秒中文示例稿，支持按行生成、语音缓存、实测音频时长字幕、句间停顿和 AAC/中文字幕合成，保留基础视频。
- 本轮13项 unittest 全通过；新增测试用本地合成音频代替提供商响应，实际执行 FFmpeg 音字幕合成、ffprobe 时长/流检查、全片解码和缓存复用验证。此测试不证明在线TTS支持，也不证明90秒成片已生成。
- 当前进程未配置 OPENAI_API_KEY，未提交在线配音请求；未生成90秒中文配音成片。中文字幕为软字幕，需播放器启用；现有讲解镜头仍为三阶段，未实现逐句智能镜头。

## 本轮恢复与启动验证

- 本轮12项 unittest 全部通过，包括新增的验收失败重试与归档脚本选择回归测试。
- 沙箱内 Blender 场景检查曾因 SIGSEGV 失败；允许本机 GPU 访问后，14条视频重新通过场景检查与 FFmpeg 全片解码，当前 acceptance.json 为14条通过、0条失败。
- 修复独立验收无法重试 `Acceptance:` 失败任务的问题；验收实际通过后才恢复 done 状态，并使用任务归档的 audit_scene.py。
- 本地工作台与单消费者 worker 已实际启动；HTTP状态接口可访问。视觉配置接口仍显示未配置外部服务，默认模型 gpt-6-luna，在线图片识别未验证。
- `.env` 及其本地变体加入 Git 忽略规则，避免意外提交服务凭据。

本记录基于本机实际执行结果。完整机器可读证据见 `artifacts/acceptance.json`、`environment.json`、`tests.log`、每条视频的 `scene.validation.json` 和 `video.verification.json`。

## 环境与项目级 Skills

macOS arm64 / Python 3.11.14（项目 .venv）/ build123d 0.13.0 / Blender 5.2.3 LTS / FFmpeg 9.0.1 / uv 0.9.16 / Node 26.11.1。系统 Python 3.9.6 未用于运行 CAD。工具已存在，未进行 Homebrew 系统安装。依赖与 Skills 均在项目内；uv 缓存使用 /private/tmp。

已评估两候选并安装 `.agents/skills/cad`，创建 `.agents/skills/mechanical-video/SKILL.md`，后者通过官方 quick_validate。未修改全局 Skill。CAD Skill 来源及 SHA256 见 skill-provenance.json。

## CAD、队列与恢复

- 最终模型版本7，`artifacts/models/dcf09ff6d55b11a9/assembly.json`；17个独立正体积零件，每件 STEP 回读为一个有效实体；另有装配 STEP 和每件 STL。
- 18/15/48齿教学行星传动，名义速比3.667；三组太阳轮/行星轮、三组内齿圈/行星轮静态相交检查通过。为教学展示放大了齿形间隙，不是制造认证或全周期干涉验证。
- 十一项 unittest 通过，覆盖 CAD 回读、静态齿轮间隙、缓存复用、队列十主题去重、竖屏尺寸、非法模数和视觉服务缺失/不支持产品的真实拒绝行为。外部视觉响应的单元测试使用 mock，未冒充在线推理。
- 实际启动第二 worker 被同一 render.lock 拒绝；早期 Blender 失败实际触发三次重试并记入队列。旧版本任务标为 superseded，保留历史文件。
- 实际重跑完整爆炸图，150张已有 PNG 的时间戳全部不变，重新编码和解码通过，见 resume-verification.json。
- 原图/分析、参数缓存、镜头和 .blend、逐帧、任务 JSON、SQLite历史均可保留复用。

## 实际视频

共14条真实视频：原有11条5秒视频、1条5秒1080p爆炸视频、1条1秒Cycles Metal特写、1条从网页提交的1秒Eevee特写。全部为30fps、H.264/yuv420p，ffprobe尺寸/时长检查和 FFmpeg 全片解码通过。另以 Blender 实际打开14个保存场景，验证17个独立对象、可见零件/标题取景边界；对360°相机和行星轮圆周轨迹做独立验收。所有视频附英文软字幕与SRT，无语音配音。

| 主题 | 分辨率 | 文件 | 场景与解码 |
|---|---|---|---|
| internals | 1280×720 | [MP4](../artifacts/videos/f0d46d1190e78f6a4246/video.mp4) | passed |
| transparent | 1280×720 | [MP4](../artifacts/videos/86ca459dc0f18e5cfc97/video.mp4) | passed |
| assembly | 1280×720 | [MP4](../artifacts/videos/2252aec71e5bc4b2c7e4/video.mp4) | passed |
| working | 1280×720 | [MP4](../artifacts/videos/3d2d54388d04dd774803/video.mp4) | passed |
| explanation | 1280×720 | [MP4](../artifacts/videos/927fbeb9905a1f356c7d/video.mp4) | passed |
| shell | 1280×720 | [MP4](../artifacts/videos/63187187e725d26bf3c4/video.mp4) | passed |
| overview | 1280×720 | [MP4](../artifacts/videos/1de3ee9b2ee856f321df/video.mp4) | passed |
| gears | 1280×720 | [MP4](../artifacts/videos/b3d4dd3173474e8fdc16/video.mp4) | passed |
| closeup | 1280×720 | [MP4](../artifacts/videos/f52f85be3d0ccf9de07f/video.mp4) | passed |
| explode | 720×1280 | [MP4](../artifacts/videos/1325bf45c951ff9626d6/video.mp4) | passed |
| explode | 1280×720 | [MP4](../artifacts/videos/be3c466beec8ba8cd5dd/video.mp4) | passed |
| explode / Eevee | 1920×1080 | [MP4](../artifacts/videos/d8914c6a27d223ae98af/video.mp4) | passed |
| closeup / Cycles Metal（1秒） | 1280×720 | [MP4](../artifacts/videos/9bc2480e5503779f09b1/video.mp4) | passed |
| 网页提交 closeup / Eevee（1秒） | 1280×720 | [MP4](../artifacts/videos/3cfa65d7e9cbad256037/video.mp4) | passed |

[本地播放目录](../artifacts/index.html) · [全部主题预览](../artifacts/contact-sheet.jpg)

## 生产与浏览器补充验收

- 在真实浏览器中实际播放1920×1080、5秒视频，无媒体错误；网页提交一秒特写后实际渲染完成并播放，同样无错误。重复点击显示新增0个、复用1个。证据：artifacts/browser-verification.json、workbench.png。
- 新任务归档renderer/三份脚本并保存指纹；源代码改变会创建新视频任务，CAD继续复用；旧任务使用自己的脚本快照。修改归档后明确拒绝渲染的测试通过。
- 持续监听使用worker.lock，渲染/验收使用render.lock；真实第二消费者被拒绝，空闲时render.lock可用，持续worker运行期间独立验收14条视频成功。证据：queue-verification.json。
- HTTP Range首段、尾段、不可满足范围均有自动测试；工作台支持分辨率、画幅、时长、主题、引擎和模型模数选择。
- 新worker生成的一秒任务耗时9.824秒，见对应metrics.json；不含首次Metal内核编译耗时。

## 当前外部依赖与未验证范围

- 图片上传工作台与兼容视觉服务接口已实现；HTTP页面/状态/视频200、非法上传415已实际检查。没有真实产品图和视觉服务凭据，尚未执行在线图片识别。
- 当前图片到CAD仅支持行星减速器家族的模数/整体尺度；不支持产品保存分析并拒绝替换成示例。单图不能证实内部结构，内部零件及估计尺寸全部标为推测。
- 1080p横屏已实际渲染和浏览器播放验证；Cycles实际使用Apple M3十核GPU、METAL、16 samples，完成30帧一秒实测，hardware.json有设备记录。1080p竖屏参数可用，本轮未实际渲染该尺寸。
- TripoSR运行兼容性未验证，禁用且不影响基础流水线；未下载权重或并行运行高内存重建模型。


## 图片识别模型配置

项目默认图片识别模型已设为 `gpt-6-luna`，CLI与工作台共用，`VISION_MODEL`环境变量可覆盖。十一项测试通过，新增测试验证默认名称和覆盖值都实际进入图片请求体（mock服务，不代表在线模型已验证）。工作台/config公开所选模型名称；尚未配置VISION_ENDPOINT，因此未进行该模型的在线图片识别。


## 2026-10-27 照片引导电钻概念装配

- 授权扩展 `cordless_drill` 家族；原照片 SHA256 `4e23a5ea935841900ad2cc228ec50e706eab5fea7e502bb3bd44662ed6dfa17c`。由助手直接视觉观察，无外部视觉服务调用。原“不支持”分析保留，新增 extension.json 记录扩展结果。
- 最终源 `mechanical_video/drill.py` VERSION=2，缓存 `artifacts/models/drill-4c0dddd1fb5480aa/`。56 个命名独立零件各自导出 STEP/STL，含装配 STEP、源快照及清单。每件重新导入：有效、单实体、正体积；装配 STEP 有效且含 56 实体；包围盒 189×61.2×214 mm（全部估算）。详见 geometry.verification.json。
- 外观包含分体青黑机壳、夹头、扭矩环、握柄、触发开关、顶部滑块、通风槽及电池。内部采用推测的通用电机、两级示意行星传动、离合盘、主轴/轴承、控制板与假设 5 节电池。不是实物拆机复原；简化齿形、尺寸、级数、电气配置均未验证；未做全装配干涉、强度、啮合或电气验算。
- 最终任务 `2de02c4b710953298f3b`：1280×720、30 fps、150 帧、5.000 秒、Eevee、H.264。ffprobe 核对尺寸/帧率/时长，FFmpeg 全片解码通过；scene.validation.json 检查独立对象数、各对象拆解位移及各采样时刻画面边界，全通过。手动查看首帧与末帧后保留 preview.png、assembled.png；scene.blend、150 帧、脚本归档、日志、job.json、验证报告及 queue.sqlite 均保留。
- `.venv/bin/python -m unittest discover -s tests`：16 项通过，包含实际 CAD 生成、STEP 重导入、缓存、禁用不支持的电钻传动仿真及正确字幕。`git diff --check` 与 `git diff --cached --check` 通过。
- 首版任务 `cacff09a1499eb7faf77` 在沙箱内 Blender GPU 初始化崩溃；获准沙箱外执行后成功。最终任务同样使用获准 GPU 访问，未改变沙箱设置。首版和改进版分别保留，未修改归档或混合帧。
- CAD Skill STEP/inspect 工具链遇到 OCP 缺少 TDF_LabelSequence；Explorer 启动缺少 vite，未安装依赖或改动 Skill 工具。改用 build123d 对实际 STEP 重新导入并记录独立几何验证；没有可用 Explorer 链接。

## 2026-10-27 电钻中文配音长片（94 秒）

- 用户要求约 90 秒带配音拆解视频，沿用已验收电钻缓存 `drill-4c0dddd1fb5480aa`，未重建 CAD、未改动旧渲染档案。输出 `artifacts/films/cordless-drill-90s/cordless-drill-94s-zh.mp4`，8.80 MB。
- 使用项目 audiogen runner，模型 `qwen3-tts-flash`、音色 `Ethan`；九段中文旁白成功生成。首次请求明确 HTTP 503 且未产生音频，记录失败后仅进行一次相同模型/音色重试，成功；未盲目重复不明状态请求，凭据未写入档案。原始 MP3、逐段文本、缓存与失败记录全部保留。
- 九段旁白 FFprobe 实测合计 90.264 秒，按每段约 0.415 秒短暂停顿编排 94 秒时间轴。SRT 时间与镜头来自实测音频，不按字数估计。`storyboard.json` 包含字幕文本、可见零件、每件位置轨迹和测量信息，参与渲染任务 ID；叙述始终明确内部结构及尺寸是推测。
- 任务 `b87d83ab5937e6b36b8b`：Eevee 实际渲染全部 2820 帧，1280×720、30fps、94.000 秒；渲染耗时 932.047 秒。分镜：外观、电池整体移出、分壳、夹头/主轴、齿轮、电机、控制部件、电池内部、完整爆炸图。各段先独立展开相关零件，并保留最终全装配爆炸态；未循环或拉长旧五秒视频。使用现有 macOS GPU 授权，遵守 worker.lock/render.lock。
- 渲染前预检与渲染后独立 Blender 审计均通过：56 个独立对象、独立拆解位移、九段各首/中/末帧以及标准采样帧边界通过。scene.blend、2820 张源帧、归档 renderer、job.json、日志、相机和时长报告及 queue.sqlite 均保留。
- 成片烧录中文旁白字幕及“内部结构与尺寸均为推测”提示，字幕每条单行且不超过 20 字符，使用实际字体预览检查中文显示；嵌入九个中文章节。音轨 AAC、48 kHz、94.000 秒；H.264 视频 2820 帧、30/1、1280×720、94.000 秒。FFprobe 核对视频、音频与九章；FFmpeg 对最终成片完整解码通过。响度实测 -16.2 LUFS、真峰值 -1.4 dBFS，见 loudness.log。未进行语音转写核对或听觉验收。
- 最终任务目录保留 narration.wav、逐段 MP3、narration.zh.txt/SRT、captions.zh.ass、chapters.ffmeta、中文分镜、合成命令、制作源码快照与 SHA256、delivery.json、ffprobe.json、verification.json、最终爆炸 PNG 与九宫格分镜预览。
- 测试：全套 18 项通过；随后新增音频合成模块的 2 项实际媒体/字幕测试通过，覆盖实测语音偏移、最终爆炸态、配音超时阻断、整包先移动后分芯、PCM 补静音、变更时长阻断及标点换行。成片合成及中文章节以实际 FFmpeg/FFprobe 验证。`git diff --check`、`git diff --cached --check` 通过。
- FFmpeg 扫描系统字体目录时提示未使用的 NISC18030.ttf 元数据不可读；实际使用 Arial Unicode MS，中文预览可见、无缺字。不宣称真实拆机、制造精度、仿真或内部结构验证。

## 2026-10-27 Ethan 配音替换准备

- 按用户要求以相同文案和 `qwen3-tts-flash` 模型生成 Ethan 配音，保留原 94 秒成片及其分镜、字幕和章节。
- 新目录 `artifacts/films/cordless-drill-90s-ethan/`；第 1、2、4、5、6、7、8、9 段已生成并通过实际音频解码。第 3 段读取响应失败，未保存音频且服务端完成状态不明；保留 `002.submitted`，未自动重发。
- 其余无争议段落已完成。`replace_voice.py` 可按实测时长将各段适配原字幕窗口、统一响度并复制原视频数据流；已生成前两段 Ethan 预览，最终九段合成等待第 3 段状态澄清或明确重发授权。没有将八段成功误报为整片替换完成。

### Ethan 完整版完成

- 用户明确授权“允许，只重新提交第 3 段”；仅重发该段，成功后复用其他八段。原不明提交标记及授权记录保留，未重新提交已成功段落。
- 完整版 `artifacts/films/cordless-drill-90s-ethan/cordless-drill-94s-ethan.mp4`：实际使用 `qwen3-tts-flash / Ethan` 九段音频；各段以保音高 tempo 适配原字幕讲解窗口，并补齐原章节间隔。保持原文案、烧录字幕、九章时间轴与 94 秒时长，原 Roy 版本保留。
- 实际验收：1280×720、30/1 fps、2820 帧、94.000 秒、H.264；AAC 中文音轨 94.000 秒。FFmpeg 完整解码通过，FFprobe 确认九章。视频直接复制原数据流，未重新渲染/编码；FFmpeg 视频包 SHA256 与原 Roy 成片完全一致，`7374d717c5d21d0b0be46c7f17725260681dc352de26ac347e4e21c7d3a62322`。
- 新目录包含原文案、逐段 Ethan MP3、实测时长、合成 WAV、制作脚本、命令和 verification.json。未进行听觉或 ASR 内容验收。


## 2026-10-27 原理讲解重制：Ethan／单行短字幕

- 根目录 `AGENTS.md` 新增“配音与字幕规范”：默认 qwen3-tts-flash / Ethan、每条单行且最多 20 字符、正式片至少 90 秒、普通观众因果讲解、实测音频编排和交付验收。项目 `voiceover.py` 默认值同时改为 Ethan；技能原有 Roy 默认值不改，实际调用显式传入 Ethan。
- 新版：[原理讲解 MP4](../artifacts/films/cordless-drill-principles-ethan-dba10f9fd66a281d/cordless-drill-principles-ethan.mp4)。旧 Roy、旧 Ethan 版本及其源帧、CAD、脚本档案全部保留。新任务由制作源指纹确定目录；保留 production 源快照、原 renderer 快照及 source-job.json、逐句 MP3、字幕、分镜、剪辑片段和验收脚本快照。
- 文案以“供电 → 控制 → 电机旋转 → 减速增扭 → 主轴与夹头输出”为主线，60 条短句分别使用项目 audiogen runner 在线生成 qwen3-tts-flash / Ethan。实测语音 130.728 秒；每句自然停顿 0.25 秒，时间轴 145.728 秒。没有变速、循环镜头或重复提交失败请求；本轮所有请求均成功保存音频。
- 复用已渲染任务 b87d83ab5937e6b36b8b 的九组无烧录旁白字幕画面，按主题重新排序；每个镜头只以原速播放一次，随后停留在结构图上继续讲解。没有新 Blender 渲染或修改 CAD。原有英文镜头标签/参考编号保留，中文旁白按新顺序播放；顶部持续显示内部结构与尺寸推测提示，旁白集中说明一次。九宫格抽查确认中文可见、单行、画面主题与旁白相符；不代表运动仿真或实物内部验证。
- 最终 FFprobe：H.264、1280×720、30/1 fps、4372 帧、145.733333 秒；AAC、48 kHz、145.728 秒。成片音视频全部完整解码通过。独立验收核对全部 60 条 SRT，最长 15 字符、全部单行、无重叠；每条字幕时间来自对应 MP3 实测时长，并与对应主题镜头时间窗一致。源快照 SHA256 校验通过。证据位于同目录 acceptance.json、ffprobe.json、delivery.json、storyboard-preview.png 与 review-00..08.png。未执行人工全片听觉或 ASR 转写验收。
- `.venv/bin/python -m unittest discover -s tests`：21 项通过（15.196 秒），包括实际 CAD 独立导出/STEP 重导入正体积验证、实测音频合成、默认 Ethan 调用参数、20 字符边界及换行拒绝、原理讲解顺序和逐句长度检查。独立媒体验收命令：`.venv/bin/python scripts/verify_drill_remake.py artifacts/films/cordless-drill-principles-ethan-dba10f9fd66a281d`，通过。
- FFmpeg 扫描未使用系统字体 NISC18030.ttf 时的元数据警告仍存在；实际字幕使用 Arial Unicode MS，抽帧中文可见。本轮 `git diff --check`、`git diff --cached --check` 通过；未暂存或提交现有改动。
