# 实际验收记录 — 2026-10-27

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
