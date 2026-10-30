## 3D 打印机系列最终交付（2026-10-27）

本轮实际完成 EP01、EP02、EP03，统一使用锁定官方 Voron 2.4r2 源 CAD（commit `7b32e405f0719881cca782500c822e01e3b16bf2`）、Ethan 中文普通话、单行中文字幕、原创低音量氛围音乐及独立零件机械关键帧。

| 成片 | 时长 | 字幕数 / 最大字数 | 实际移动零件 | FFprobe / 全片解码 |
|---|---:|---:|---:|---|
| `series/3d-printer/output/EP01.mp4` | 128.533333 秒 | 47 / 16 | 842 | 通过 |
| `series/3d-printer/output/EP02.mp4` | 133.266667 秒 | 47 / 16 | 532 | 通过 |
| `series/3d-printer/output/EP03.mp4` | 131.500000 秒 | 48 / 17 | 829 | 通过 |

三集均为 1080×1920、30fps、H.264 + AAC。每集 final.mp4 与 output/EPxx.mp4 的实际 SHA256 相同。字幕文件逐条匹配实测音频时间轴，单行、不重叠、最多 20 字。第三集音轨响度约 −16.65 LUFS，峰值 −1.42 dBTP。已抽查成片 EP01 30秒、EP02 52秒、EP03 84秒；这不是全片人工听审或制造仿真认证。

共同显示装配 SHA256：`a2800a3520163bccc145ab1517bc553475a11357334ee9bda68ea2f65397343e`；共同几何清单 SHA256：`b6568ef619914fae6237062d1549acb86a30957c9871af66452ea382c8d37d0b`。三集原生 Blender 场景均独立回开审核 1,428 个源实例、初始源坐标、非零运动、终点复位及全部采样 CAD 边界入画。真实 Eevee 帧和逐任务脚本快照保留；相同静止场景姿态通过硬链接复用，机械运动帧实际渲染。

**CAD 补充验收已通过**：原 STEP 兼容导出中三个零件的回读缺陷没有被隐去；生成了两个原边界平面修复 BRep 和一个源封闭网格派生的 Molex 分面 BRep。`cad_assembly.json` 保持源 ID/坐标/层级，映射独立原生几何。`cad-roundtrip-validation.json` 记录 1,414 个文件、1,428 个实例全部独立磁盘回读有效、正体积、实体数匹配。87 个文件的质量积分漂移仍有警告记录。三件原 STEP 和失败报告均保留，原显示模型没有更换。

显示限制：右 X 小车旧 STL 不是水密网格，不能用于制造；有效的原生 BRep 不会自动修正已渲染显示网格。源 CAD 近似与示意轨迹在画面持续标注。若今后修正显示网格，必须建立新的模型/渲染版本，保留当前验收成片。

实际运行 `series model` 验证原生 CAD 清单和所有几何文件哈希；`series status` 报告 EP01–03 complete、EP04–12 planned、下一集4。`series render` 对完成成片按 SHA256 跳过并保护；`continue --count 3` 可继续4–6，但本轮没有启动它。12集已有脚本和后续动画入口，EP04–12 尚无配音/成片验收。

最新 unittest discovery：**33 项通过，8.408 秒**，日志 `series/3d-printer/tests.log`；新增原生 CAD 侧车篡改检测。一次测试缩进错误已修正，失败日志保留。`git diff --check` 通过。汇总证据：`series/3d-printer/delivery-validation.json`，每集完整文件及独立 validation.json 保留。未修改全局 Skill，未提交 Git。

以下为此前阶段的恢复与历史记录，不代表最终状态。

## 3D 打印机系列恢复记录（2026-10-27，中间状态存档）

此前记录的 CW2 Main_Body 源曲面网格阻塞已解决：在原解析曲面和原 UV 范围重建两张锥面，保持法向与面积，缝合后清除旧三角缓存。修复证据保留于装配清单；没有替换为减速器示例模型。原始源文件与旧失败记录均保留。

EP01 已实际交付 128.533333 秒，EP02 已交付 133.266667 秒；两者 1080×1920、30fps、H.264/AAC、全片 FFmpeg 解码通过，47 条单行字幕，最大 16 字。两者原生 Blender 场景独立回开审核：1,428 个零件初始坐标匹配源装配、终点复位、采样边界均在画面内；移动零件分别 842/532。EP03 仍在渲染，不能据此宣称第三集完成。

共同显示装配 SHA256：`a2800a3520163bccc145ab1517bc553475a11357334ee9bda68ea2f65397343e`；几何资产清单 SHA256：`b6568ef619914fae6237062d1549acb86a30957c9871af66452ea382c8d37d0b`。Ethan 配音按原速短句实测编排，保留音频、源脚本、镜头、场景与帧序列。EP02 52 秒成片截图已人工检查，字幕与独立拆件画面清晰。

额外的完整 STEP 磁盘回读审计发现：1,414 个独立文件均有正体积，但 m00078、m00079、m00784 有回读拓扑缺陷，且部分有效螺纹件的质量积分存在约 0.281% 的数值差异。`roundtrip-validation.json` 的失败结果原样保留。显示模型不等于制造可用 CAD；`canonical_parts/` 中的修复试验没有通过，不能用于宣称修正版成功。原显示资产和已交付视频没有改写。

本次运行 `.venv/bin/python -m unittest discover -s tests`：32 项通过，9.486 秒，日志 `series/3d-printer/tests.log`。EP04–12 已有脚本与动画代码，但未运行配音、成片渲染和验收。

以下是先前各阶段的历史记录，状态以本节及最新 episode/validation.json 为准。

# 实际验收记录 — 2026-10-27

## 3D 打印机系列：已执行，CAD 阻塞，未生成成片

- 实际入口：`.venv/bin/python -m mechanical_video.cli series`，包含 init、plan、render（单集、范围）、continue、status，以及 assets/model/audio。已执行 init/plan/assets/audio 和 `series render --episode 1`；失败阶段已落盘，完成列表为空。EP04–12 仅有主题、知识点和镜头规划，尚无正式解说及专用动画；请求这些集数会明确报错，不输出占位影片。
- 官方 VoronDesign/Voron-2 提交 `7b32e405f0719881cca782500c822e01e3b16bf2`；保留 41,533,391 字节 STEP ZIP、241,522,213 字节原始 STEP、74,568,690 字节/263 页装配手册、GPL-3.0 LICENSE、上游树和提交元数据。ZIP 与 PDF 实际校验上游 Git blob SHA1，通过；asset_manifest.json 记录 SHA256。另下载官网 BOM 和 configurator JS，并解析 base/upgrade BOM 表，注明这是 2026-10-27 官网快照，不能冒充锁定 STEP 的精确采购清单。
- 实际使用项目 audiogen runner、`qwen3-tts-flash / Ethan`，生成 142 条独立配音：EP01 47 条/128.533333 秒，EP02 47 条/133.266667 秒，EP03 48 条/131.500000 秒。按实际音频时长编排，无语音减速；三个 narration.wav 均完整解码通过。全部字幕单行、无重叠，最大字符数分别为 16/16/17。各集 audio-validation.json 记录结果；这不是成片验收或人工听觉验收。
- EP02 第 26 句明确收到 HTTP 503，失败标记归档为 `.rejected-http503` 后仅重试该句，成功，其他成功片段复用；没有重发不明状态请求。
- 官方 STEP 存在无效源面。已实际测试常规 ShapeFix、基于原三维边界重建平面、源 CAD 网格的封闭性与分面实体转换；某些零件能得到有效正体积实体，修复或近似参数保留。完整装配仍未通过校验，不能宣称 master assembly 完成。
- 明确阻塞件：`/_Unsaved_/Gantry/X_Axis/X_Carriage/CW2_Assembly/CW2_Printed/Main_Body`。其部分面缺少可用三角网格，`tessellate` 抛出 `AttributeError: 'NoneType' object has no attribute 'NbNodes'`。OpenCascade 8.0.1.1 与隔离的 7.8.1.1 都复现；未覆盖项目现有环境。master_assembly/invalid-source.step、invalid-source.json、validation.json 和两种内核日志保留；原始 STEP 未改写，没有换用示例模型。
- Blender 安装版本为 5.2.3 LTS；最小测试发现 Eevee 枚举为 `BLENDER_EEVEE`，已加入兼容回退。沙箱内最小启动崩溃，独立 GPU 执行测试可启动；这不代表正式场景或影片已渲染。系列场景、机械关键帧、预览、1080p 帧序列、最终视频 FFprobe 和全片解码均未验收。
- 实际运行 `.venv/bin/python -m unittest discover -s tests`：29 项通过，8.211 秒。新增测试覆盖计划幂等、保留已完成输出、配音源变更拒绝、字幕限制、未编写集数拒绝、CAD 失败状态与不伪造完成，以及分面实体有效性。`git diff --check` 通过。
- **没有** `series/3d-printer/output/EP01.mp4`；EP02/03 没有成片。EP01 为 failed/model，EP02/03 为 waiting_for_ep01；不得把已成功配音或单零件修复当成用户要求的三集视频交付。

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

## EP04 opening editorial experiment (2026-10-28)

`series/3d-printer/experiments/EP04-hook-v1/EP04-hook-v1.mp4` is a 21.9-second
opening sample, exempt from the full-episode 90-second minimum. It reuses the
unchanged EP04 official Voron CAD frames and adds explicitly labelled 2D layer
shift and commanded/actual-position diagrams. It is an editorial recut, not a
new CAD render or a verified fault simulation. Narration uses qwen3-tts-flash /
Ethan. All eight subtitle utterances are single-line and at most 20 characters.
The 1080x1920, 30fps H.264/AAC output passed ffprobe and full FFmpeg decode;
evidence is in the experiment's validation.json. A diagram frame was visually
inspected; complete subjective audio/video review remains for the viewer.
The sample renderer and fingerprint are retained under renderer/. Existing
accepted episodes and the EP05-08 production queue were not replaced.

## Silent CW2 visual study (2026-10-28)

`series/3d-printer/experiments/visual-CW2-05d8d4ab426fa822/visual-test.mp4`
is a 10-second silent visual test: closed CW2 assembly, separation of source
housing pieces, illustrative gear rotation, and reassembly. It uses 56 source
CAD occurrences from the unchanged shared master hash
`a2800a3520163bccc145ab1517bc553475a11357334ee9bda68ea2f65397343e`.
Display colors, separation distances and rotation are illustrative; gear axes
and pivots are estimated from source placement and bounds, not independently
accepted meshing kinematics. It makes no filament-feed or motor-internal claim.
No new CAD solids were generated. Original STEP and display meshes are preserved.

Five 35-percent preview frames and a contact sheet were inspected. First task
`bd2a328f1abf0adf` was rejected for overexposure and framing; it is preserved.
The corrected task has new archived renderer fingerprints and separate frames.
All 300 production frames rendered with Eevee under the shared render lock.
FFprobe checked 1080x1920, 30fps, H.264 and 10 seconds; full FFmpeg decode passed.
No narration or audio track is present. Current unittest discovery passed 33
tests (`/tmp/mechanical-visual-tests.log`). Independent production CAD generation
was not repeated because no geometry changed. The EP05 worker was interrupted
with existing frames preserved, then EP05-08 automatically resumed (PID 33308).
See per-task job.json, scene.blend, blender.log, production-audit.json and
validation.json for evidence. This short test is exempt from the 90-second
full-episode minimum; audience engagement remains a subjective review.

## Visual-first CW2 narrated extension (2026-10-28)

`series/3d-printer/experiments/story-CW2-36b995412224ebaa/story-test.mp4`
extends the approved silent direction into a 31.7-second short study, not a
completed 90-second episode. The same pinned master display hash is retained.
59 original CAD occurrences cover CW2 and the Revo hotend; no source geometry
was edited or regenerated. New filament and moving bands are explicitly
schematic: assumed 1.75mm diameter, estimated Z-directed centerline between the
source gear bounds, illustrative 6mm/s feed, and an exaggerated loose-idler
separation. Gear rotation is illustrative, not accepted meshing/contact physics.
The bands stop during the loose-idler section while gear rotation continues.

Six Ethan/qwen3-tts-flash utterances were measured before scheduling. All
single-line subtitles have <=20 characters and non-overlapping speech intervals.
Five preview poses and two full-resolution macro frames were visually inspected
before/while production; review evidence, archived narration/renderer hashes,
source matrices and sampled poses remain under the experiment directory.
951 new 1080x1920 frames rendered under the existing GPU render lock. FFprobe
checked 30fps H.264/AAC and duration; full FFmpeg decode passed. The final has
no music. A remuxed silent comparison retains the same image/subtitle track
and also passed full decode. Subjective full audio/video viewing is not claimed.
33 unittest checks passed in the current run (experiment tests.log).
EP05-08 was resumed after the serialized test, PID 34311. Existing frames and
accepted episodes remain preserved. This short study is exempt from the
90-second production-episode minimum.

## Full-series visual-first remake start (2026-10-28)

User requested EP01-EP12 remade from the start and explicitly requested a new
male voice using the supplied Qwen voice catalog. The active edition now uses
qwen3-tts-flash / Andre; the prior Ethan default remains historical for earlier
outputs. `series/3d-printer-v2/voice-selection.json` records read-only catalog
provenance and the selected male entry. A real 11.904-second Andre opening
audition passed ffprobe and full FFmpeg audio decode.

All twelve second-edition scripts and eight-shot plans were authored and queued
in an independent SQLite queue. Each visual plan allocates >=96 seconds;
measured speech may extend shots. No earlier completed output was replaced.
The old EP05-08 worker was stopped; its frames and incomplete encoding remain.

New EP01 measured timeline is 96.000 seconds, with 58.224 seconds of Andre
speech in 23 short utterances. Caption limits and ordered timing are enforced.
The shared manifest hash is unchanged at
`a2800a3520163bccc145ab1517bc553475a11357334ee9bda68ea2f65397343e`;
all existing source STEP/STL bytes were rehashed and matched the retained
geometry inventory hash. Cached native CAD acceptance was reused; no new CAD
was generated. Source STEP and display-approximation limitations remain intact.
The renderer chooses one Octopus controller option, preserving other variants
on disk. Schematic filament/feed/layer paths do not establish real print physics.

Final EP01 task `96e124f78024655bfe71` produced sixteen native preview frames
(two per shot), an archived renderer, preview.blend, preview-audit.json and a
contact sheet inspected in this run. Electronics and bed views were adjusted
to oblique top views; superseded preview tasks remain separate and preserved.
38 unittest checks passed (series/3d-printer-v2/tests.log); Python compilation
and git diff --check passed. The detached sequential worker started as PID
37555, uses the shared render lock, and EP01 entered production. EP02-EP12
remain queued. No new full episode has passed final media acceptance yet;
this entry does not claim completed EP01-EP12 video output. Per-episode final
acceptance will require source/shot checks, expected media properties and full
decode. See docs/series-remake.md and the production log for current state.

## EP01 editorial rejection and mechanical hook test (2026-10-28)

The user rejected EP01 attraction and narration, then chose mechanical macro,
cutaway, transmission and sound rhythm. The full-series worker PID 37555 and
its active EP03 Blender child were stopped. EP01/EP02 remain technically
validated but are not claimed as editorially accepted; EP03 frames and later
plans are retained. An editorial hold now blocks accidental old-worker restart.

Actual EP01 samples confirmed an opaque enclosure through the early opening
while the voice referred to invisible bed/nozzle actions, and the first feed
macro arriving only around 35-40 seconds. 23 separately synthesized utterances
occupied 58.224 of 96 seconds. Structural timing was inspected; subjective
full audio listening is not claimed. Audit stills/findings are retained under
`series/3d-printer-v2/episodes/EP01/editorial-audit/`.

New experiment `mechanical-hook-ec95c9755b771260` contains eight macro/cutaway/
explosion/feed/reassembly framings in 15 seconds. It starts with source gears,
not an enclosure. 59 original source occurrences and the unchanged master hash
are reused. Only original housing is clipped by a display Boolean; no invented
motor internals were added. Assumed filament and rotation remain schematic.
The first failed task, using an obsolete Blender FAST enum, is preserved;
current Blender FLOAT compatibility uses a new archived task identity.

Eight preview images and a full-resolution cutaway frame were inspected.
450 new 1080x1920 frames rendered under the shared lock. The final H.264/AAC,
30fps, 15-second video passed ffprobe and full decode. Original procedural
foley aligns transients to the seven edit times; this is not recorded machine
sound. There is no spoken narration in this video. A separate 9.816-second
Moon/qwen3-tts-flash continuous paragraph audition passed audio probe/decode;
Moon remains a candidate, not an accepted whole-series replacement.

38 discovery tests passed before the added hold regression; the subsequent
six-test remake suite, including that regression, also passed. Evidence is
retained in experiment tests.log and hold-tests.log. No fresh manufacturing
CAD generation was needed because the source cache was unchanged. The sample
is exempt from the 90-second full-episode minimum. Neither this short test nor
technical decoding establishes audience engagement or full-episode acceptance.

## Continuous opening revision after jump-cut feedback (2026-10-28)

The user found the eight-cut mechanical hook jumpy. New task
`series/3d-printer-v2/experiments/mechanical-hook-6e21ea58c8729117`
uses one continuous 15-second shot: the same CW2 housing opens, the camera
pushes toward its gears, follows the same schematic filament downward to the
Revo hotend, then pulls back as the housing closes. Camera orientation is
constant. All 59 source CAD occurrences remain present throughout; no source
part visibility cuts or Boolean clipping occur. Quintic motion envelopes give
continuous camera position, scale and housing motion. Earlier task archives
and frames were preserved; all 450 frames of this revision were newly rendered.

Eight preview stills were inspected. Native production checked all 449 adjacent
frame pairs: source visibility IDs remained identical, camera translation per
frame <0.003m, and orthographic scale change per frame <0.005m. Exact maxima
are retained in production-audit.json and validation.json. These are continuity
checks, not physical simulation or subjective audience approval. Synthetic
foley is continuous, with soft housing slides and no edit-impact transients.
There is no narration in this visual-continuity test.

1080x1920, 30fps H.264/AAC, 15 seconds and full FFmpeg decode passed. Python
compilation passed. No CAD regeneration or provider call was necessary; the
shared source geometry and earlier Moon audition remain unchanged. The rejected
full-series queue remains on editorial hold. The short test is exempt from the
90-second formal-episode minimum and is not a completed optimized full EP01.

## EP01 continuous revision, 2026-10-28

Correction on later review: task `70063523807a5525b2ac` retained an enabled
Boolean modifier on CW2 housing parts. Its earlier audit text claiming the
cutaway was disabled was incorrect; visibility and transform continuity checks
did not test rendered geometry clipping. The user rejected that episode, and
the later `13ba4d94cd26498d5a97` revision removes the added Boolean modifiers.
Do not interpret the earlier audit as evidence of intact housing geometry.

Task `70063523807a5525b2ac` is an independent EP01 revision under
`series/3d-printer-v2/revisions/EP01/70063523807a5525b2ac/`. Its complete
100-second preview and 1080x1920, 30fps H.264/AAC production both passed full
FFmpeg decoding; the production stream contains 3000 frames. The production
video SHA-256 is
`61d4c0c8f49a46be197998550cb547f1d5d25935518c86065e2a9a29e6589866`.

The 750 preview samples were inspected in sequence on contact sheets. The
source scene and motion fingerprints match the production frame cache; the
audio timing revision was encoded separately. All 2999 production adjacent
frame pairs passed camera position, scale, source-part translation and source
visibility checks. Maximum camera and part translation steps are 0.00453m and
0.00625m respectively. Rotation continuity was reviewed from the archived
director's constant-speed gear formula, rather than measured from per-frame
rotation matrices; the feed markers wrap outside the central gear close-up.
These checks do not establish physical meshing or user acceptance.

The explicit `qwen3-tts-flash / Moon` configuration produced eight speech
clips totalling 26.04 seconds. Eight single-line captions have a maximum of
16 characters; the longest caption was checked on the encoded portrait video.
Audio and captions use measured clip durations without speech retiming. Foley
is synthesized and ducked during speech; there is no music. Full-size output
and the preview are preserved with their audio, subtitles, archived scripts,
fingerprints, frame provenance, and verification reports. Schematic motion,
filament and deposition are labeled on screen.

The original model manifest hash remained
`a2800a3520163bccc145ab1517bc553475a11357334ee9bda68ea2f65397343e`.
All 1428 source occurrences retain positive-volume valid records and their
display meshes; this revision reused previous CAD validation and did not
regenerate CAD. The prior outputs, approved reference and entire queue matched
their pre-render baseline. The test discovery run completed 39 tests. Visual
acceptance of this full episode is still pending and the season was not resumed.

## EP01 Engagement Revision, 2026-10-28

Correction: `a7fccaff52b0f5e17187` has incorrect feed kinematics. Its two
pinch-gear contact surfaces move upward while the filament marker moves down;
the large coaxial gear also turns opposite the drive gear. The checks below
established continuity and media properties, not correct gear direction.
The first direction fix `5b846984fff7e103f047` was stopped after a sampling
review showed its 50-tooth pattern could alias even at 30fps. The replacement
`b82decd2da0c6a1cb585` passed the checks recorded below.

Task `a7fccaff52b0f5e17187` reframes EP01 around why filament must stay
rigid above the hotend while softening below. A labeled hypothetical shows the
filament bending and recovering continuously; the heat cue and deposition path
are illustrative. Earlier EP01 outputs and the approved 15-second reference
remain preserved, and the season queue matched its pre-render baseline.

Production `EP01.mp4` is 100 seconds, 1080x1920, 30fps, H.264/AAC, and
contains 3000 rendered frames. Full FFmpeg audio/video decoding passed. SHA-256:
`bce97ce87372c677585e18972ef3b5eba966423a95f0301f6323b93eb0e3fcf8`.
The source task `f3fbfba91881025d5de8` rendered the images; the final narration
revision reused them only after scene, motion, source-scene and master-model
fingerprints matched. Archived scripts and frame-cache provenance are retained.

All 750 preview frames were inspected in sequence. The encoded preview and
production frames were checked for the hypothetical label and its matching
caption; the longest subtitle was checked on the encoded preview. Numerical
checks covered all 2999 adjacent production frames for camera movement, zoom,
source-part translation and visibility. A separate Blender inspection of the
saved production scene found 1428 source parts, none hidden and no active
Boolean modifiers. Per-frame rotations and deformation were not independently
measured; the bending demonstration was visually reviewed in the preview.

The explicit `qwen3-tts-flash / Moon` voice produced eight measured clips
totalling 37.824 seconds, above the original approximate 25-35 second target.
Captions are single-line and at most 20 characters, each timed to a whole clip.
Foley is synthesized and ducked during speech; no music or voice retiming was
added. The provider interface used here exposes no separate emotion control.
Subjective listening, user acceptance and actual viewer retention remain
unverified. The original CAD was reused without regeneration; source records
and meshes were checked, and the prior CAD validation remains the evidence
for the independent positive-volume solids. Unittest discovery passed 39 tests.

## EP01 Feed-Gear Direction Correction, 2026-10-29

Task `b82decd2da0c6a1cb585` corrects the feed direction and regenerates EP01.
The two pinch-gear contact velocities and the filament marker now point down at
approximately 0.0025 m/s. The large and small drive gears have the same world
angular velocity. Contact assumes a 1.75 mm filament and no slip; it is an
illustrative kinematic model, not a physical contact simulation.

The 50-tooth pattern frequency is approximately 5.865 Hz, below 80 percent of
the 15fps preview sample rate's Nyquist limit. FFmpeg image-sequence tests
verified that each 15fps preview image is encoded twice at 30fps and each
30fps production frame is encoded once. Image correlation on decoded preview
and production close-ups at 8-9.34 seconds measured counterclockwise screen
motion, approximately 3 degrees per 15fps sample, matching the expected 2.815
degrees. This is a localized visual check, not a full perceptual review.

All 3000 production poses were checked in an independent, non-rendering
preflight. The 2999 pairs of actually rendered frames were also checked for
gear contact velocity, marker speed and shared-shaft angular velocity. Maximum
errors were 0.000000786 m/s, 0.000000616 m/s and 0.000121 rad/s respectively.
The saved production scene contains 1428 source parts, none hidden, with no
active Boolean clipping. Prior CAD validation was reused without regeneration.

The regenerated `EP01.mp4` is 100 seconds, 1080x1920, 30fps, H.264/AAC and
3000 frames; FFmpeg decoded the full audio and video. SHA-256:
`bc1f8bf39a8e82e6f22bf4bb8327c23e9273213e4ef005dcd32aa9f083e19f91`.
Moon narration, mixed audio and subtitles match the prior episode by SHA-256.
Forty-five unittest cases passed. Prior outputs and the queue matched their
preservation baseline. Subjective visual and auditory acceptance remains pending.
# EP01 新旁白预览检查（2026-10-29）

- 独立任务 `ec83b8833597d8424197` 使用 `qwen3-tts-flash / Moon` 生成八段完整句子，语音实测共 60.984 秒；字幕按句分段，每条不超过 20 字。场景和齿轮动作复用已验证修正版，CAD 未重新生成，整季暂停标记保留。
- `preview.mp4` 为 100 秒、1080×1920、30fps、H.264/AAC，完整解码通过，SHA-256 为 `b3f4885d976c4a73a82c85ea279bb372cf6a8cc8728be345ecdd44fd94d2ef97`。底层预览帧是 15fps、25% 分辨率后放大，不能视为正式画质。
- 画面与文案的预览检查未通过：旁白在 43 秒讲挤出、54 秒讲床面路径，但现有场景的沉积路径直到 73 秒才开始生成；76 秒的逐层旁白也早于第一层路径完成。仍需重新编排沉积、工具头运动和龙门升高，重新渲染完整预览并检查音画对应，才能进入正式版。该任务没有 `preview-reviewed.json`，未生成正式成片；观感认可待用户审阅。

# EP01 打印示意优化预览（2026-10-29）

- 任务 `d5ce7c04cb16858e806f` 保留齿轮修正，第一层采用闭合轮廓和连续往复填充，第二层在龙门升高后采用交错填充；两层的喷头沿相同沉积轨迹运动，打印材料改为与线材同色的非金属材质。路径和运动均为示意，当前仅显示两层薄片，并非完整立体物件的打印过程。
- `preview.mp4` 为 100 秒、1080×1920、30fps、H.264/AAC，底层帧以 25% 分辨率、15fps 渲染；完整解码通过，SHA-256 为 `a9ce3d2abfcfa620a307cea17cdbfabb5cd8fd86218fe4e3267bc2c1c8d3818b`。Moon 配音 60.984 秒，24 条单行字幕最长 14 字。47 项单元测试通过。
- 场景审计包括 1499 对相邻帧，1428 个源零件保持可见，无硬切或可见性突变；齿轮接触速度最大误差 0.000000382 m/s、线材标记速度最大误差 0.000000266 m/s，同轴角速度最大误差 0.0000615 rad/s。按每秒抽取的 100 帧检查显示床面路径、层间抬升和退镜持续存在；这不是完整播放的动态或听感验收。
- 正式成片 `EP01.mp4` 已生成，100 秒、1080×1920、30fps、H.264/AAC、3000 帧，全片解码通过；SHA-256 为 `bdcc93f3522d66eb2ff267d15de88c2cfac1689f2d2360843fe94f2d2737555c`。`production-independent-verification.json` 记录 2999 对帧的连续性和方向检查、字幕、源哈希及帧文件完整性。接触速度最大误差 0.000000786 m/s，线材标记速度最大误差 0.000000616 m/s，同轴角速度最大误差 0.000121 rad/s。
- `preview-reviewed.json` 的通过范围仅限全片解码、帧对运动审计、逐秒抽帧和时间轴核对；字幕片段按整句实测时长和字数比例分配，未经逐词听辨。完整动态播放、声音听感和用户观感验收仍待完成，正式帧抽查可见床面阴影有颗粒。画面仅展示两层薄片，不是完整立体成品的打印过程。主模型未重新生成，EP02 至 EP12 保持暂停。

# 物件诞生短样片（2026-10-29）

- 独立实验 `print-birth-89e9680a886f175d103c`：16 秒连续镜头，从线材、喷嘴和螺旋杯底过渡到逐渐长出的杯壁。画面使用加速示意，线材、几何和送料均非物理仿真；机械声音为合成拟音。继续使用既有官方 CAD 和齿轮方向修正，原成片与整季暂停标记保留。
- 无旁白 `print-birth.mp4` 的 SHA-256 是 `901961678e466e50de1244e537fad387c85ed6034436ec8f3041753c40b0058c`；Moon 试听版 `print-birth-moon.mp4` 为 `5de8825f76351317fe832d6d7385b5d70e913be4a73889a26ba6b96334a54307`。两者均为 16 秒、720×1280、30fps、H.264/AAC，完整解码通过。无旁白版本的 479 对相邻帧通过场景及齿轮运动审计。47 项单元测试通过。
- 试听使用 `qwen3-tts-flash / Moon`，整句实测 5.496 秒；字幕两条、单行且每条不超过 20 字，按预计句段时间分配，尚未经逐词听辨。画面和声线的情绪、自然度及音画关系仍待连续播放和用户观感确认，不能由技术检查推断；杯底是疏间螺旋示意，并非完整实体打印过程。

# 机械拆解与送料讲解短样片（2026-10-29）

- 用户纠正创作方向：主体是机器拆解及原理讲解；上一个以小杯成型为主体的短样片不符合要求，保留作为未认可的实验，不作为后续方向。
- `disassembly-feed-b8123c42979603dc3bb4` 从已验证的 EP01 齿轮修正版连续帧截取前 18 秒，重新合成单句 Moon 原理讲解和原合成拟音；这是新剪辑，不是重新制作的拆解动画。画面先展示机构展开及齿轮运动，再解释旋转如何产生向下推力。
- 视频 SHA-256 `b0ef24fdf574b19f8959a686a622e4ec98990f1c8c17ee06a8bff85bc5a2152d`；18 秒、720×1280、30fps、H.264/AAC，完整音视频解码通过。`qwen3-tts-flash / Moon` 配音实测 5.424 秒；字幕单行且不超过 20 字，片段时间按字数比例估算，尚未经逐词听辨。原视频及 540 个源帧的哈希记录于任务归档，47 项单元测试通过。
- 齿轮接触是示意性无滑移近似，拟音非实录。连续播放听感和用户观感尚待确认；EP01 正式重制与 EP02 至 EP12 均未重新启动。

# 齿轮讲解 Ryan 音色试听（2026-10-29）

- 用户反馈 Moon 音色不合适，单独生成 `qwen3-tts-flash / Ryan` 试听任务 `disassembly-feed-7d5a7c519db44f454c70`；原 Moon 样片保留。两版复用相同的齿轮修正版画面、旁白文案和合成拟音，语音的实际时长及相应字幕时间不同。
- Ryan 配音实测 6.048 秒；成片 18 秒、720×1280、30fps、H.264/AAC，完整解码通过，SHA-256 `41cbdebfda17cea95bcda5ac65973af44b1290f6dfac561454b3f52375b5d688`。字幕单行、不超过 20 字，段内时间按字数比例估算，未逐词听辨。声音的自然度、情绪和用户认可尚待试听，不视为正式集音色批准。

# 齿轮讲解 Kai 音色试听（2026-10-29）

- 用户认为 Ryan 听起来不合适，生成 `qwen3-tts-flash / Kai` 试听任务 `disassembly-feed-772a1055858f7f87296f`。复用同一拆解画面、旁白文案和合成拟音，保留 Moon 和 Ryan 版本。
- Kai 配音实测 6.864 秒；成片为 18 秒、720×1280、30fps、H.264/AAC，完整解码通过，SHA-256 `8c0828bddd00370b4824b141e1cf9df9ab318dfd4dfcc2453122939e9bb34009`。字幕单行且不超过 20 字，片段时间按字数比例估算，未经逐词听辨；声音观感待用户试听。

# EP01 Kai 重制预览（2026-10-29）

- 独立任务 `dd5c18eec572c11be76e` 使用指定八段文案及 `qwen3-tts-flash / Kai`，语音实测共 73.104 秒，各段无重叠。脚本、语音、场景、1500 张预览帧和审计保存在任务目录；原模型和旧成片未覆盖，整季暂停。
- `preview.mp4` 为 100 秒、1080×1920、30fps、H.264/AAC，底层画面为 25% 尺寸、15fps，完整解码通过；SHA-256 为 `73c9b09b6935c6516217de9324aebc5c9ff9bc2f4c8e66cda097c8f0dc43189d`。1499 对相邻帧通过场景和齿轮运动断言，记录无硬切或源零件可见性变化。齿轮接触和打印运动为示意，拟音为合成声音。
- 抽查显示齿轮、热端及两层路径，但约 34 秒讲述喷嘴挤出时，画面未清晰展示挤出过程。字幕按整句时长和字数比例估算，未进行逐词听辨；完整连续播放、听感和用户观感均未验收。预览未通过内容检查，未生成正式版。需修正挤出动作并完成动态和音画同步检查后才可正式渲染。
- 沙箱内 Blender 在 Metal 初始化时 SIGSEGV；获得本机 GPU 访问后预览渲染成功。当前运行 unittest discovery，47 项通过。

# EP01 循环预览（2026-10-29）

- 在 Kai 预览基础上制作独立循环试版 `series/3d-printer-v2/experiments/ep01-kai-loop-preview/preview-loop.mp4`，末尾 96 秒起用约四秒叠化回首帧，原预览保留。播放时需在播放器启用循环；MP4 文件本身不控制播放器重复播放。
- 试版 100 秒、1080×1920、30fps、H.264/AAC，音视频全片解码通过；首末帧 PSNR 48.69 dB，SHA-256 `5b2e76e9f6dc0589e2ae8c1384f3ba828eb56cb3395364f6932f85c8dc5bc171`。接点为叠化而非连续三维动作，尚未进行连续播放及听感验收；原预览的挤出画面和字幕同步问题仍待解决，正式版未渲染。

- 用户反馈切换不自然后，修订任务 `6a19b7e7b0d0ecea1898` 将结尾重新编排为真实回镜：整机退回喷头近景、外壳复位并与首帧保持同一装配状态，取消叠化。修订预览已完成，100 秒、1080×1920、30fps、H.264/AAC，完整解码通过；交付副本为 `series/3d-printer-v2/experiments/ep01-kai-loop-preview/preview-loop-v2.mp4`，SHA-256 `af844a2432e4d20cd7974cdd6d8635520b13d1bab2ffb14fc1b463bc9638c51d`。正式版仍未渲染，连续播放和听感验收待进行。

- 用户指出打印阶段引导管与打印线分离。修订任务 `d72ba9556ab6492c9e32` 增加连续挤出桥曲线，明确连接导料线末端、喷嘴和当前沉积点；非打印阶段隐藏该桥。预览已完成并通过 FFmpeg 全片解码，抽查打印阶段确认导料线与喷嘴、打印 bead 位于同一连续路径。该修订仍是示意性挤出，不代表真实流体仿真或制造精度。

- 更正：上述检查没有解决截图中的灰色引导管与青色线分离，之前的结论有误。任务 `be3c9d196fc32ebef8f5` 误认了喷头内管件，画面仍有断开。新任务 `286fbb6553fde95a5e0d` 将源模型的 `4x3mm_PTFE_Guide_Tube` 纳入工具头位移；打印阶段两处抽帧显示灰色管下端接到青色线。完整预览解码通过。引导管整体平移是示意运动，上端并非固定支架下的真实柔性变形；连续播放及用户观感尚未验收。

### EP01 Kai 正式版（2026-10-29）

- 用户提供的正式制作计划确认预览任务 `286fbb6553fde95a5e0d` 审核通过，实测预览 SHA-256 为 `68e5b594e84893a4a0f023c407db6e02501366b3c1b3ce9f74f8539c580b3689`；绑定记录见该任务的 `preview-reviewed.json`。此批准不包含正式成片观感、发布或其他集数。
- 正式版 `EP01.mp4` SHA-256：`ee0664aae24fbc8e771b3883104b49f093cd33f4921de3129e05f75dff324dc3`。ffprobe：H.264 1080×1920、30fps、3000 帧、100 秒；AAC 音轨 100 秒。脚本完成 FFmpeg 全片音视频解码。保留 3000 张正式帧、`scene.blend`、日志、音频与归档脚本；未重建 CAD 或恢复整季队列。沙箱内 Blender 初始化 SIGSEGV，本机 GPU 访问后渲染完成。
- `production-audit.json` 记录 1428 个源零件、2999 对连续帧、0 个硬切和可见集合变化；齿轮接触速度最大误差 0.000000786 m/s，线材标记速度最大误差 0.000000575 m/s，轴角速度最大误差 0.000121 rad/s。编码画面 8–9.34 秒齿轮方向相关性检查通过（`production-visual-direction.json`）。这些为场景和局部画面检查，不构成物理仿真。
- 配音配置为 `qwen3-tts-flash / Kai`，实测配音总长 73.104 秒；29 条字幕均为单行，最长 16 字。字幕分句时间按字数比例估算，未逐句听辨确认。正式帧约 56.6 秒和 66.6 秒抽查到引导管与线材相接；首末原始帧构图一致。引导管整体跟随是示意运动，不是柔性管物理仿真。
- 实际连续播放、打印阶段全程连接、循环接点的动态观感、旁白画面对应及逐句听感和字幕同步尚未完成验收；不能从解码、数值审计或抽帧推断通过。正式版观感待用户审看。单元测试发现 47 项通过。

- 后续用户确认 EP01 正式版效果满足要求。按用户要求清理生产数据时，逐文件比较确认旧任务 `a7fccaff52b0f5e17187/frames` 与 `f3fbfba91881025d5de8/frames` 相同，`70063523807a5525b2ac/frames` 与 `bfc576bd5152b51686f3/frames` 相同，删除前者两份复制帧。源帧、复制来源记录和旧成片保留；如需对被清理的旧任务重新执行要求完整帧目录的验证，可按各自 `production-frame-cache-provenance.json` 从对应源目录恢复。已认可任务 `286fbb6553fde95a5e0d` 的正式帧未删除。

- 用户随后要求只保留最后认可的 EP01 版本，已删除其他 EP01 修订目录、原系列与重制系列的旧 EP01 输出、循环预览，以及最终任务的预览 MP4。上文关于旧版本和旧源帧保留、可恢复的描述仅是清理前的历史记录，不再适用；预览审核记录及哈希仍在。最终正式版、正式帧、音频和场景保留。独立的已确认风格参考和其他集数保留。

- 用户进一步要求移除其他未认可集数：原系列 EP02–EP05 和重制系列 EP02–EP03 的旧渲染目录或帧，以及原系列 EP02–EP04、重制系列 EP02 的输出 MP4 已删除。历史验证和队列记录仍是当时状态，不表示这些输出仍存在；系列暂停标记保留。EP04 的 `04fdabd9902948771c7e/scene.blend` 是 EP01 和渲染脚本的共享源场景，仍保留。

- 后续深度清理移除了原系列 `episodes` 中遗漏的 EP01–EP04 成片副本、原系列实验、重制系列未采用的实验、旧 EP01 指针和 `artifacts/review_rejected`。系列目录仅保留获认可的 EP01 正式视频与已确认的 15 秒风格参考；原系列集数脚本和计划保留。上文历史记录中指向已删除实验或成片的链接不再可用。
# EP02 优化预览（2026-10-29）

任务 `5074c6b9b285b9e532f0` 使用现有 Kai 音频及官方模型，保留归档脚本、场景和预览帧。预览 98 秒，H.264 1080×1920、30 fps，AAC，FFmpeg 全片解码通过；源画面为 10 fps 预览采样。Blender 沙箱内 Metal 初始化 SIGSEGV，本机 GPU 执行后完成。关键帧抽查发现开场主体偏小及示意标签对比度不足；字幕逐句听审、平台遮挡、拟音听审和首尾接点尚未验收。预览未通过，未进行正式渲染。

# EP02 口语化动态预览（2026-10-29）

任务 `18546db8c0d105706209` 使用新文案、qwen3-tts-flash / Kai 逐句音频及官方模型。预览 114 秒，H.264 1080×1920、30 fps，AAC，FFmpeg 全片解码通过；源画面为 10 fps 预览采样。保留帧、场景、归档脚本、音频与时间线。抽查发现旁白说移开外板时外板已经移到画外，画面与旁白不一致；逐句听审、拟音平衡、字幕平台遮挡、首尾接点及吸引力仍待审核。未通过正式版验收，旧批量队列保持暂停。

- 开场内部测试 `fbed098f65c7a3b25121`、`2825f22839ca45f38e7d` 各为 18 秒，源画面 270×480、10 fps 采样，编码为 1080×1920、30 fps H.264/AAC，FFmpeg 全片解码通过。后者调整转向时间，但连续采样显示构图重复，未通过内容审核。导管主体在画外，近端仍为示意变形；不能据此声称导管长度或连接已验证。听审、完整故事和正式版仍未完成。详见 `series/3d-printer-v2/ep02-internal-review.md`。
- 后续内部测试 `c21addb073f9699b410c` 以相同采样和编码规格渲染 18 秒并完成全片解码；每秒抽帧仍发现前半段内容重复，未通过内部内容审核。导管拟合审计表明按 Y 轴分段不适合源网格，不能据此宣称柔性件建模通过。
- 36 秒测试 `7069510aa3bdd8dbedd6` 和 `35c528db04f645e74cd8` 全片解码通过，源画面为 10 fps；抽帧显示外板在对应旁白期间移开。后者使用修整后的 Kai 音频，完整听审仍未进行。全片关键帧与后续工作版仅供内部审查，不构成内容通过或正式版验收。
- 全片内部工作版 `efdfa7fab770ad1d5426` 为 107 秒、1080×1920、30 fps H.264/AAC，源画面 10 fps，完整解码通过；中后段静止、字幕时间估算及听审缺失使其未通过。专用 Qwen ASR 对全段识别得到五处文案差异，两个对应片段复核一致，一处“对/堆”仍待听辨；同音字及 ASR 误识不能当作真实语音错误。
- 修订内部工作版 `7aafb6a340b38c4611e1` 为 107 秒、1080×1920、30 fps H.264/AAC，源画面为 10 fps 采样，FFmpeg 全片解码通过，SHA-256 `b6860f8200b691190bc267f1b0d4155c1b2298fe40a17570704be627741e5443`。52 条字幕均为单行、最长 17 字，时间与各音频片段边界一致且无重叠。逐三秒抽帧看到机架强调和外板逐渐回位；连续动态观感、旁白自然度、拟音听感、音画同步及“对/堆”读音未完成验收。47 项项目测试及 7 项导管/拖链相关测试通过；不得将此工作版标记为内容通过。
- 按用户反馈，预览 `9ade5cb9a08e02bc6322` 增强了动作同步的合成电机、导轨、转向、机架振动及外板拟音，并将字幕左右居中。107 秒，1080×1920、30 fps H.264/AAC，源画面为 10 fps 采样；FFmpeg 全片解码通过，SHA-256 `8fc04ce452907b3f39a1ae68177434a95b335412976aeeea869d51d4b7164c11`。成片最长字幕抽帧确认单行居中；独立混音测试峰值约 -0.8 dBFS。拟音为合成声音，不是机器实录；实际听感及用户观感待审核，正式版未渲染。
- 循环预览 `570d3f83d48ee5774656` 参照 EP01 的平滑回镜，将镜头从整机连续移回喷头，外板逐渐复位。107 秒、1080×1920、30 fps H.264/AAC，源画面 10 fps 采样；FFmpeg 全片解码通过。首末关键帧逐像素一致，编码后首末帧 PSNR 44.39 dB；解码音轨首尾采样差约 0.000036。`loop.html` 使用浏览器循环播放，实测从末尾回到 0.02 秒后继续播放；有声自动播放可能需要用户先点击播放。回镜动态和声音的实际观感仍待用户审核，正式版未渲染。
# Video QA foundation (2026-10-30)

## Multi-agent dispatch smoke test (2026-10-30)

- Codex CLI 0.166.0 reports `multi_agent` enabled. A fresh read-only `codex exec --strict-config --json -s read-only` session, asked to perform a delegation smoke test without naming a role, spawned `video_qa` child `/root/qa_docs_check`; the child returned a review of `docs/video-qa.md`. Parent thread `01a18a6a-cfe3-7f92-bbef-e6ec17b44e76`, child thread `01a18a6a-e1cb-7b40-96b4-3c384184c6af`. The persisted parent record contains `collaboration.spawn_agent`, and the child record contains the project `video_qa` developer instructions and result. No video or project file was modified by the test.
- A preceding read-only `--ephemeral` session reported `no rollout found` while spawning a child. Its output did not establish successful delegation; do not use it as evidence. The persisted test required host execution because the sandboxed CLI failed to initialize with `Operation not permitted`.
- The smoke-test prompt explicitly requested delegation. A separate generic readiness request completed without delegation, consistent with the small-task rule. Fully automatic delegation for every future production request, repair, rerender and scoring remain unverified; the current QA foundation cannot certify those production gates.

## Audio QA initial test (2026-10-30)

- EP02 revision `863a5dc2c1a995e72d6c`, `trimmed-clips/000.wav`, was inspected as actual audio and sent through the existing Qwen ASR adapter. ASR returned `喷头跑到一半，突然掉头。`, matching its script. Original timeline placement is 00:00.500–00:02.657; this is clip placement, not forced alignment.
- Full audio decode succeeded, measured mean/peak were -21.2/-1.2 dBFS, and no one-second silence interval was detected. Report: `artifacts/qa/audio-ep02-000-20261030/audio-qa-report.json`. Result NEEDS_REVIEW, all six scores null; ASR comparison does not establish audio naturalness, timing, final mix or mechanical/visual correspondence.
- Forced alignment, calibrated scoring, automatic repair, final-mix comparison, and blind multi-defect regression are not implemented. Synthetic silence test only is not a regression benchmark.

## Audience QA initial test (2026-10-30)

- Reviewed accepted EP01 `286fbb6553fde95a5e0d/EP01.mp4` using actual sampled frames and the configured `gpt-6-luna` vision endpoint. The full 100-second file decoded; independent technical and audience scores remain null and the combined result is NEEDS_REVIEW. The still-frame review cannot establish audio, caption timing, motion or audience response. The older episode timeline differs from this remake, so no shot IDs were inferred.
- The model reported possible opening context and visible speckling at 00:00, with evidence under `artifacts/qa/audience-ep01-v2-20261030/`. The wide-shot suggestion conflicts with the approved continuous close-up style and is not an established defect. Three future opening proposals are in `docs/ep01-opening-candidates.md`.
- One separate preview `artifacts/qa/ep01-opening-denoise-v1/EP01-preview.mp4` applies FFmpeg `hqdn3d=3:2:3:2` only before 5 seconds, re-encodes video and copies audio. The original remains intact. Full decode passed and a second still-frame vision review completed. The model did not repeat its speckling finding, but visual comparison still shows grain in the first frame; improvement is unconfirmed and no numerical score difference is available. The preview is not approved or delivered.
- Creative repair orchestration, complete audience/audio review, calibrated dimension scores and actual platform feedback are not implemented. No audience retention or engagement metrics were inferred.

## Audio direction and appeal check (2026-10-30)

- EP02 `863a5dc2c1a995e72d6c` is an unapproved preview. Full `narration.wav` was decoded and submitted to existing `qwen3-asr-flash`: seven text differences, including homophones, require listening. One sentence at timeline 00:06.969–00:08.800 was recognized as “堆” rather than scripted “对”; the timestamp is the existing clip placement, not forced alignment. Full report `artifacts/qa/ep02-narration-full-20261030/audio-qa-report.json`.
- A single independent replacement was generated via project audiogen, `qwen3-tts-flash / Kai`. Original clip ASR returned “堆”; replacement ASR returned “对”. Their decoded audio was measured: original WAV duration 1.830875 seconds, mean -26.9 and peak -7.1 dBFS; replacement MP3 duration 2.136 seconds, mean -29.9 and peak -11.0 dBFS. The MP3 duration includes container/encoder padding and is not a forced alignment measurement. Both comparison reports and the unmodified candidate are in `artifacts/qa/ep02-sentence-003-original/` and `artifacts/qa/ep02-sentence-003-candidate/`. ASR agreement is not listening approval; the candidate was not inserted into the film.
- Actual preview MP4 audio fully decoded; its mean and peak were -22.9 and -0.6 dBFS. Separate technical and appeal checks are in `artifacts/qa/ep02-final-mix-audio-20261030/` and `artifacts/qa/ep02-final-mix-appeal-20261030/`. All technical and appeal scores remain unverified and both gates return NEEDS_REVIEW. Full mix ASR, subjective listening, emotion understanding, subtitle alignment, source-to-picture review, splice, timing update and final reassembly were not performed.
- A 52-segment draft direction based on the existing Kai timeline is stored at `artifacts/qa/ep02-audio-direction-20261030.json`; emphasis and picture sync are not asserted, and it is not a provider instruction or production approval.

- `.venv/bin/python -m unittest discover -s tests`: 51 tests passed.
- `mechanical_video.video_qa` checked the actual EP02 `fcc2f1e2a2cbba47f85f` 36-second preview: full decode and scan succeeded; its duration is below the formal 90-second gate. Five actual frames were sent to the configured vision endpoint and the provider returned a description. The report remains NEEDS_REVIEW, with all scores unverified.
- A separate three-second synthetic black video was detected from 0.0 to 2.9 seconds. This is a smoke test, not a blind regression benchmark. The command returned exit code 3 for NEEDS_REVIEW.
- Current limitations: no shot-level evidence matching, audio/subtitle semantic assessment, calibrated scoring, repair orchestration, blind regression suite, or automated production integration. The model response does not establish mechanical accuracy or video motion.

# EP02 Continuous Motion (2026-10-30)

- Preview `863a5dc2c1a995e72d6c` keeps the toolhead moving throughout the 107-second loop using a 15 mm illustrative stroke; position and velocity match across the loop boundary. Centred subtitles and synthetic mechanical audio are retained. The 1080x1920 H.264/AAC file is encoded at 30 fps from 10 fps source frames and passed full FFmpeg decode; SHA-256 `53e9001fd0b58dbecfdc4dda7b26980b235076c02b589c5450fbe9bf0a76a513`. Browser playback resumed at 0.023 seconds after the end. The former 70–73 second static region and the loop boundary were inspected in source frames; motion is subtle in the wide view.
- The tube centreline is sampled from the official STEP cross sections. In 31 sampled displacements between -15 and 0 mm, the maximum mesh-edge length change was about 1.54%, and the maximum mean absolute change was about 0.018%. Across 16 poses, surface-crossing results with 59 nearby stationary candidates and 47 moving carriage/chain candidates matched source-pose crossings. These discrete surface checks do not establish continuous sweep, solid containment, physical dynamics, or manufacturing accuracy; source contacts already exist.
- `python -m unittest discover -s tests` passed 51 tests, including two guide/loop checks. The audio is synthesized, not recorded from the machine. Continuous playback and the sound's subjective quality still need user review; formal production has not been rendered.

## EP02 continuation: local quality inspection (2026-10-30)

- Independent visual, video QA, audio QA and editor work is recorded in `series/3d-printer-v2/ep02-production-20261030.md`. A 00:19–00:22 local excerpt from the existing scene is 540x960, native 30 fps, H.264/AAC; ffprobe and full FFmpeg decode passed. SHA-256 `911507f1dc79ea9e8f3dff773d9f9d8213dd0d69efcda36debf9bedc5fc8111b`. It has no subtitles and does not cover the subsequent beam and frame narration.
- Actual frame inspection identifies unclear rail-to-frame visual explanation and possible panel occlusion, while actual audio decoding cannot establish listening quality or sync. The local render did not repair these issues. Mechanical connection evidence, continuous visual inspection, independent listening, audio appeal and audience acceptance remain unverified; EP02 stays NEEDS_REVIEW and no formal production was rendered.

## EP02 fan animation (2026-10-30)

- Preview `b0d7b1803fe781968c2e` adds an illustrative rotating 4010 fan rotor separated from the single source mesh, while its frame follows the toolhead. The 107-second 1080x1920 H.264/AAC file is encoded at 30 fps from 10 fps source frames; ffprobe and full audio/video decode passed. SHA-256 `5c5feeb0e876dfdcddeef1782d6193fb757aa483c2868a7d06ecdcd6d335d295`.
- Independent frame review found rotation without obvious frame motion or tearing in the opening 0.9 seconds. A separate native-30fps two-second slow-speed excerpt showed coherent motion; an earlier faster excerpt showed aliasing. The split and speed are illustrative, not physical verification. Full-film visual, audio and audience acceptance remain unverified; no formal production or preview approval is claimed.

## EP02 print realism experiment (2026-10-30)

- Independent inspection found that the existing 00:55–01:00 illustrative lines are separated from the nozzle. A new four-second local experiment with an inferred printed object and growing line decoded, but actual-frame QA could not see the nozzle contact or line growth. Two subsequent camera-angle experiments did not resolve occlusion. The strategy stopped without a pass and was not integrated into the full preview; see `series/3d-printer-v2/ep02-production-20261030.md` for the evidence and remaining work.

- Following user rejection, three further local visual experiments did not expose a legible deposition point: the source object containing the nozzle candidate still occludes it even after the front cover moves. None was incorporated into the full preview. A validated cutaway or explicitly illustrative independent nozzle remains necessary; audience and technical acceptance are unverified.

- Subsequent STEP investigation found ten solids in the source object; the lowest has a tapered section and approximately 0.388 mm central hole. A closed positive-volume mesh was exported from this candidate. Two local separation renders still failed to show the tip and deposited line, and the last showed overlap with the illustrative workpiece. Source-CAD evidence and failed frames are recorded in `series/3d-printer-v2/ep02-production-20261030.md`; coordinate and intersection verification remains required. No full preview was modified.

- A subsequent repair traced invisible deposition to the evaluated curve transform placing the bead below the workpiece. A local correction exposed the line; independent review of 40 source frames saw continuous growth and a corner. Later transition tests removed an obvious camera-through-housing artifact, but the returning housing obscured the workpiece and two return strategies failed to improve visibility. These are silent 10 fps experiments, not an accepted EP02 preview; see the production record for paths and limitations.
### 2026-10-30 Metal startup diagnosis

- In the Codex sandbox, `MTLCreateSystemDefaultDevice()` returned null and Blender 5.2.3 exited 139 before executing Python. Its generated `/var/folders/t0/z5fmfnjn5xv1884nc6h2bsyw0000gn/T/blender.crash.txt` shows `_platform_strstr`, `supports_barycentric_whitelist`, and `metal_is_supported`. The null device is consistent with the crash; the exact Blender pointer has not been independently inspected.
- With GPU execution permission, the same Metal API returned a device named Apple M3. Blender opened `artifacts/videos/d2de4840dc9d7b5fd144/scene.blend` and rendered Eevee frames 1, 75 and 150 at its saved settings, exit 0. The 1280x720 PNGs at `/private/tmp/mechanical-gpu-check-0001.png`, `-0075.png`, and `-0150.png` were visually inspected: assembled, intermediate and exploded geometry respectively. This isolated diagnostic render did not acquire `artifacts/render.lock`; future renders must acquire it.
- The Python pipeline checks Metal availability before launching Blender. A missing device stops the worker without consuming an attempt; a subprocess signal stops automatic queue retries. The runtime cannot grant itself sandbox exceptions: invoke the existing pipeline from a terminal with GPU access, or have the Codex execution environment explicitly authorize the GPU-capable process. No global sandbox setting is changed. Archived one-off scripts are unchanged.


## EP02 continuation audit — 2026-10-30

Current remake remains NEEDS_REVIEW; older original-series EP02 completion above does not approve the Kai remake. Baseline is b0d7b1803fe781968c2e (107 seconds, 1080×1920 H.264/AAC; 10 fps source encoded at 30 fps). This turn ran unittest discovery: 65 tests passed in 10.763 seconds; the simulated Blender SIGSEGV output is an expected failure-path test, not a live render crash. Seven EP02 geometry helper tests passed in 0.084 seconds; neither test suite establishes mechanical motion or video acceptance.

Director checked all 52 baseline SRT entries: single line, maximum 17 characters, positive durations, no overlaps. Speech alignment and actual listening remain unverified. Baseline gate evidence: `series/3d-printer-v2/revisions/EP02/continuation-director-20261030/baseline-audit.json`. Independent audio technical/appeal reviews are under `audio-review-20261030-continuation`; no exposed actual audio-understanding capability is available, so no listening score may be assigned. New local print repair and independent video review are in progress; no formal approval or batch release is implied.

### Confirmed source-cache mapping repair

Research independently reread the original official STEP and checked all 14 shared-asset groups. Eight occurrences (n00356, n00487, n01246, n01267, n01288, n01309, n01517, n01643) were confirmed mapped to the wrong geometry. A two-box reproduction demonstrated that hashing temporary TShape Python wrappers can reuse integer identities for distinct solids. `series.py` now independently exports each occurrence; new builds use display3/geometry_version 3, and existing caches remain immutable. The regression exports two distinct same-label solids under a forced hash collision and rereads their STEP volumes. All 66 project tests passed in 10.153 seconds; `git diff --check` passed.

`source-repair-280890c41faa1c14` is a separate EP02 model cache. Eight source-corrected STEP exports independently reread valid, single-solid and positive-volume; corresponding STL meshes are watertight/positive-volume. The integration verified all 2,844 geometry file hashes, retained 1,428 occurrences, and verified the legacy master hash unchanged. New model SHA256: `0544e56b71fa3484d85fd96be6eb625d3dadff9f29c13687a43f5484bcef60ba`. Evidence is under `revisions/EP02/connection-research-20261030` and `models/source-repair-280890c41faa1c14/integration-validation.json`. Six other shared-asset groups matched source volumes but topology equivalence was not established; do not claim a complete source equivalence audit. Correct source bounds likewise do not prove load transfer, fastening, contact or simulation.

The 16-second native-30fps transparent-print diagnostic `print-ghost-motion-20261030/excerpt.mp4` fully decodes but is not a production candidate: it includes isolated bed and Y movements that must not be incorporated into the fixed-bed machine. Independent QA reviewed its 480 source frames and recorded visibility improvements and exit/appearance limitations. Fixed-bed integration keyframes remain unapproved, including the tall-workpiece visual risk. Corrected source geometry must be used for subsequent renders.

### Corrected-source native-motion excerpts

`corrected-panel-motion-20261030/connection.mp4` covers original19–30s (11s/330 frames), and `print.mp4` covers49–69s (20s/600 frames). Both use corrected model SHA0544e56b71fa3484d85fd96be6eb625d3dadff9f29c13687a43f5484bcef60ba, original Kai mix at matching offset, original timed subtitles and illustrative labels. Source is native30fps540×960, encoded1080×1920 H.264/AAC; do not call it native1080p. Both ffprobe and full audio/video decode passed; Director independently verified actual output hashes against verification.json. Connection SHA0ad14c5ffbf5e5054f62e793535c4542b821c12a487835c407a28d979b89d04e; print SHA75d2a0d01ceb7e7acc17200ae2fc352cd0285c1c74058ade505c91515a41ec55.

Independent Audience QA inspected all930 decoded frames in order plus encoded caption keyframes. Beam/frame correspondence and visible persistent straight deposition improved; no new audience-only P1 was established. Remaining P2 observations: brief panel occlusion21.57–21.73, small supports24.3–26.5, early workpiece appearance49–51, thin-line/large-cylinder readability57–65, transparency ghosting65.2–65.7. Real-time audience perception, actual listening and full-film opening/ending remain unverified; audience score null. Audio QA independently decoded both actual local mixes and compared corresponding PCM lengths/source offsets; correlation supports correct source association but is not listening/alignment evidence. Technical and appeal audio scores remain null. All evidence is under continuation-video-qa-20261030, continuation-audience-qa-20261030 and audio-review-20261030-continuation.

No full repaired episode exists yet. `corrected-full-prepared-90d7695b1599bcb663a6` preserves a hash-checked prepared scene/job and recovery command but has no full frames/film or pass. render.lock released; original model/films and batch editorial hold preserved. Overall NEEDS_REVIEW: actual audio understanding/listening unavailable, preview approval and global mechanical/audience evidence not complete.


## EP02 user-approved preview continuation — full video generated (2026-10-30)

The user reviewed the two corrected-source excerpts and stated 我看，视频可以，继续. Their exact approval and both clip hashes are saved in `corrected-panel-motion-20261030/user-preview-accepted.json`; this authorizes EP02 full rendering only, preserving Kai and the other-episode batch hold. No human acceptance of the newly generated entire film is inferred.

New immutable full revision: `series/3d-printer-v2/revisions/EP02/approved-full-90d7695b1599bcb663a6/EP02.mp4`. Actual SHA256 `8e5848a06e8a4db9dbb72303af36e90044e2c5fed9f7756ecad4d5dd43d859b2`,107seconds,3210frames,H.2641080×1920@30/AACmono48kHz; native source540×960@30 is upscaled, not native1080p. All3210 frames newly rendered from one frozen corrected model/renderer, numbered continuously, independently decoded and sized. Original caches, approved local clips and previous films retained. `source-frame-verification.json`, `encoded-frame-inventory.json`, `encode-plan.json`, `encoding-verification.json` and `editor-report.json` preserve provenance. Full video and audio decode passed; Director independently checked final hash and encoded frames0/23/57/106s. render.lock released.

52subtitles are single-line, max17characters, no overlaps; all match renderer events, measured-clip boundary rounding <=0.0005s. Actual encoded subtitle and persistent schematic labels reviewed by Editor and independent QA. No forced alignment/listening claim.66project tests passed in10.207seconds; `git diff --check` passed.

Full Audio QA independently decoded actual final mix:107s/5,136,000PCM samples,mean-22.9dBFS,peak-0.6dBFS,no>=1s below-50dB silence. Baseline Kai mix sample counts match; whole-film correlation0.997319 and five segment checks support source association only, not perceptual sync. Audio Appeal QA independently verified actual final file identity and capabilities. No new provider requests or voice changes. Actual listening unavailable, audio scores remain null.

Independent Audience QA inspected all3210 source frames and actual final52caption midpoint frames (two at full1080p); no new audienceP0/P1 established. P2: panel sweep21.3–21.9s, ambiguous connection referent38.943–41.322s, thin-line/space-reference/ghost transparency around61–65.63s, and closing narration93.716–96.401s ahead of visible completed closure. Real-time perception/listening unavailable, audience score null; no unsupported >=85/90pass assigned. Final independent reports are `full-video-qa-20261030`, `full-audience-qa-20261030` and `full-audio-qa-20261030`. Full video generation is complete, formal whole-film quality status remains NEEDS_REVIEW. Full playback page is `watch.html` in the new revision; user-owned publication and other episodes remain untouched.

Final Video QA independently confirmed actual full-file hash and visually inspected all3210native source frames plus all52actual encoded caption midpoints. Final reports `full-video-qa-20261030/final-report.json` and `final-review.md` record no new definiteP0/P1, the same fourP2 and null audio/alignment/combined scores. Director state is FULL_VIDEO_GENERATED_NEEDS_REVIEW: complete watchable film, no unsupported formal quality pass.


## EP02 audience-focused local optimization — 2026-10-30

New immutable A/B candidates are under `revisions/EP02/ep02-optimization-20261030`. The24s opening `visual/hook-discovery-e6775ef41acdfa8b/hook.mp4` exposes the rail cue around3.4s and earlier support relations. All720 native source frames were independently inspected. The29s ending `visual/tail-frame-memory-eb9a031250d32fa5/tail-synced.mp4` restores panels before93.716s narration, then uses explicitly labelled front-door schematic transparency and an orange complete support outline. All870 source frames and10 actual encoded samples were independently inspected. Both are540×960 native30fps upscaled1080×1920 H.264/AAC, full AV decode passed. Tail SHA256 c6f59ba8069827549571d59a1816ce1286d8e8468bfa3bd941936281ab2021e8 independently confirmed by Director. Comparison page is `comparison/index.html`; baseline full107s film remains untouched, and no optimized full107s replacement has been rendered.

Kai narration and subtitle timing retained; no new TTS/provider requests. New synthetic panel-slide foley follows revised action and is zero after93.2s; all other components and pre78s audio retained. Independent final encoded audio QA confirms29s/1,392,000PCM samples and correlation0.997664 with new WAV78–107s; these establish association only, not listening or perceptual sync. Camera audit samples414 frames93.2–106.967s: minimum exterior gap from closed front-door worldY bounds0.754091m; this is not whole-scene collision certification.

Residual P2: hook foreground clutter10–20s, low new information86–90s, transparent noisy facets98–100s. Two unsuccessful hook-clutter diagnostics were stopped, not adopted; three tail repair rounds retained. Actual listening, real-time audience experience and platform engagement remain unverified; all combined/audience/audio scores null, status NEEDS_REVIEW. No formal90/85 gate pass claimed. Current unittest discovery:66 tests passed13.430s; expected simulated Blender crash test is not an actual production render failure.


## EP02 approved optimization — complete107s version (2026-10-30)

User explicitly approved the new A/B candidates: “我看了一下可以，继续完整的版本”. This authorizes EP02 only, retaining Kai, old versions and all other-episode/publication holds. Full production is `revisions/EP02/ep02-optimization-20261030/visual/full-approved-6f286c2f963023ab57c5/EP02.mp4`; playback `comparison/full-watch/index.html` within the optimization directory. Actual SHA256 b2272e56ac48bb1175fa59cc26b7ebf2bf9139031259a3077af41f77d76b9e3a independently confirmed by Director.107.000s/3210frames, H.264/AAC1080×1920@30; native540×960@30 upscaled, not native1080p. All3210 frames newly rendered using one frozen renderer; no cross-version source frames reused. Render exited0 and lock released. A draft caught an aim-order integration issue before any render, was preserved as SUPERSEDED, and is not used.

Decoded pixel consistency confirms720 opening frames match accepted hook,1590 middle frames match baseline,870 ending frames match accepted tail.30 frames77–78s preserve approved preparatory camera easing for continuity. Inventory SHA2568b885acfbeb2034b45c8d53e5325868c134b94af79c49e17e5542d9a44b081af. Original correct CAD/source hashes retained. ffprobe and full audio/video decode passed. Director inspected actual encoded103s frame and final SHA.

Independent Visual QA actually inspected all3210 source frames, all52 encoded caption midpoints and25 additional encoded keyframes, and independently decoded the complete film. Captions single-line/nonoverlapping/max17characters.24s and77–78s boundaries continuous; completed closure precedes93.716s caption; print49–69s and front-door96+s schematic labels actually visible. No new definiteP0/P1; existing P2 clutter/occlusion, connection referent, thin line/ghosting, slow holds and tail facets retained. Report `qa/full-optimized-review/final-visual-review.json`.

Independent Audience QA inspected318 source samples,52 actual caption midpoints and265 encoded opening/ending samples, records stronger continuous opening discovery and closure-to-frame ending payoff, with no new definite audienceP0/P1. This is sampled frame evidence, not real-time viewing or platform metrics. Report `qa/full-audience-review/audience-review.json`. Independent final Audio QA full decode107s/5,136,000samples, I-23.82LUFS/TP-0.56dBTP/LRA4.2; zero-delay whole-film source correlation0.997645 supports association only. Original Kai retained, only previously approved panel-slide synthetic foley changed; no new provider requests. Audio technical and distinct appeal reports are `audio-qa/full-optimized/` and `audio-qa/full-optimized-appeal/`. Actual listening and real-time audience experience remain unavailable, all comprehensive/audio/audience scores null; status OPTIMIZED_FULL_GENERATED_NEEDS_REVIEW, no unsupported90/85quality pass.

Full playback page links actual hash-verified film; page syntax/link/format checks pass, real browser playback not independently exercised. Prior66-test suite result remains applicable to unchanged application code; this production-only turn did not add implementation tests. `git diff --check` passed.
