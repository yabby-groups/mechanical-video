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

## 2026-10-30 — `.codex` agents 协作规范静态验证

本次仅更新13个角色的 developer_instructions 并新增 [统一交接规范](../.codex/agent-workflow.md)。未修改角色名称、description、并发配置或模型继承方式，未修改影片、归档脚本、批准记录、队列或其他项目。未启动真实派工、渲染、配音、ASR 或发布，也未调用生产供应商。官方 [Subagents 文档](https://learn.chatgpt.com/docs/agent-configuration/subagents) 已实际读取，用于核对独立 TOML 的 name/description/developer_instructions 必填字段及继承约定；未迁移现有 max_threads 配置。

使用 `.venv/bin/python` / tomllib 实际解析 `.codex` 下全部14个 TOML：通过；13个角色必填字符串非空、名称唯一且与文件名一致：通过。与 Git HEAD 比较，除 developer_instructions 外各角色字段完全相同，config.toml 仍为 agents.max_threads=4，无新增 model/effort 覆盖：通过。全部角色的四个公共入口路径与统一规范的7个相对文档链接存在：通过。下表为人工静态流程推演，并非实际生产复现或独立 QA 评分。

| 情况 | 责任人及交接物 | 静态推进与停止条件 | 结果 |
| --- | --- | --- | --- |
| 源 CAD 错配 | Director → Research 的源 STEP、occurrence 映射/变换和独立导出哈希对照 → Visual 局部 A/B → Video QA | 先排查源再评镜头；证据不足停止相关几何结论的下游采用，不能换镜头遮掩。修复后保留旧缓存和失败证据 | 责任、证据和停止边界明确 |
| 保留基线的小改 | Director 给批准基线哈希、允许范围及独占目录；Creative Director/Script/Visual 给基线内局部 A/B，Audio 保留批准旁白 | 不启动新集三开场重做或重配；A/B 未满足范围或存在关键不确定性时不能扩大到完整片/正式验收；受修复次数上限约束 | 责任、基线和停止边界明确 |
| 尾段提前后的拟音同步 | Visual 给动作差异及时间线 → Editor 联查拟音、字幕、标签、邻段和预备运动 → 独立 Audio QA/Audio Appeal QA 对实际最终混音复核 | 统一冻结渲染器整合，不混帧；解码/相关性不证明听感。缺听审或严重音画失配不能正式验收，保留旁白及原版本 | 联动交接物和验收停止条件明确 |
| 局部批准后续做全片 | Director 读取批准原话/哈希/范围 → Visual 同版整合 → Editor → 两类最终混音 QA → Video QA → Audience QA → Director | 已授权本集继续完成，无需重复确认；保留其他集和发布 hold。分别记录生成、批准和 QA；新全片缺门槛仍为 NEEDS_REVIEW | 续做责任和授权边界明确 |
| 缺听审能力 | Audio QA、Audio Appeal QA 报实际文件哈希、已完成解码/测量与未验证维度 → Director 人工复核项 | 相关分数 null，不用 TTS/ASR/PCM 代替听感，不因能力缺失重复生成；明确文件、shot ID、时间码和待回答问题，未知则写 unavailable；停止正式验收 | 能力限制、下一责任人和停止条件明确 |

另对照当前 AGENTS.md、approved-video-style、production-lessons、video-qa、audio-qa、audience-qa：正式验收90/85门槛、音频一次贡献、独立吸引力、单行≤20字符字幕、正式旁白片≥90秒及短片例外一致；问题最多三轮、同策略两轮无改善停止且不以改名重置一致；Metal 预检/blocked/显式 retry、不可变归档和 render.lock 边界一致。`git diff --check` 通过；新增规范另检尾空白和末尾换行通过。静态检查仅证明配置与流程一致性，不证明运行时加载、真实派工、感官能力或任何影片制作验收已通过；本次无应用代码变动，未新增测试或运行 unittest/CAD/FFmpeg/渲染。

### 同日补充 — 13角色权责边界

补齐统一规范的13角色权责表，每项包含唯一主责、交付物、决策权、不可越权项和下一责任人；同样写入各角色 TOML。明确 Research 查证而 Visual 实施生产 CAD/映射修复；Script 负责文字和语义计划，Editor 负责最终时间线及拟音制作/改时/混音；Audio 仅负责旁白合成。Director 指定唯一修复主责、协调争议和汇总状态，不能覆盖独立 QA 结论或用户批准边界；独立 QA 仅在新证据/版本上更新自身结论。修复 Director 公共指令中“向 Director 报告”的自指措辞。

实际静态检查：项目 Python 成功解析14个 TOML；13个唯一角色均有且仅有一行权责表，角色指令均含主责、决策权、越权限制和交接；与 HEAD 比较名称/description/其他字段未变，并发仍为4，无新增模型覆盖；规范相对链接及尾空白检查通过，`git diff --check` 通过。静态交接推演：几何异常为 Research → Visual → Video QA；改词为 Editor → Script → Editor；动作改时为 Visual → Editor → 两类音频 QA；QA 冲突由 Director 留存原结论、补证后交原 QA 复核；能力缺失由 Director 接收并保留未验证门槛。各路径有明确所有者，未启动实际派工、生产或平台操作。

### 同日再分析 — 依赖、版本有效性与问题闭环

本轮发现并修正规则缺口：首轮脚本/实测音频可能循环等待；QA 未明确随版本失效；原评审者离线无接替路径；代码故障归属不清；修复自报完成缺独立关闭条件；失败与未验证状态混淆；综合评分报告责任不明。已在统一规范和全部13个角色中补齐适用要求，未新增角色、评分权重、工具或生产执行。

| 静态情况 | 责任与预期推进 | 停止/复核条件 |
| --- | --- | --- |
| 首次配音无实测时长 | Script 先交可合成文案/估计计划，Audio Director → Audio 实测 → Script/Editor 定时 | 估计不可冒充实测；旁白 QA 不等待尚未存在的最终混音；同步维度仍待实际画面复核 |
| 只改拟音/混音 | Editor 新版本 → 两类最终混音 QA，并联动受影响 Video/Audience 体验复核 | 旧报告不能改哈希冒充新片通过，不因此重配批准旁白 |
| 仅重新编码 | Editor 新文件 ffprobe/全片解码 → 对应 QA 验证画面/音频/时序关联 | 仍需绑定当前哈希；技术关联不能单独证明感官体验 |
| 原 QA agent 离线 | Director 指定同角色且未参与相关生产的替代者，新建评审报告 | 保留原报告/身份/原因；没有独立评审能力则未验证，不让生产者自审 |
| 生产 CAD 导出器故障 | Research 查证复现 → Visual 明确源文件修复/测试 → 新指纹任务与独立复核 | 不修改归档，不让 Research/Visual 同时写同一生产文件 |
| QA 工具自身故障 | Director 派独立工具修复任务，另一个真实独立人员验收依赖该修复的资产 | 工具修复者自测不算独立验收，无人可复核则保留未验证 |
| 修复者说已解决 | 生产者交新版本/证据、标待复核 → 原角色或独立替代 QA 复核 → Director 关闭 | 问题 ID/计数保持，QA 不直接向生产者派冲突任务，失败和 P2 不静默删除 |
| 写入者中断或所有名额等待 | Director 只派输入就绪工作；确认旧写入者停止、锁归属和输出后移交 | 不删活动锁、不并发续写、不重复未知提交；遵守实际环境并发限制 |
| 缺综合评分或已有解码失败 | Video QA 按既有口径形成综合/技术报告，Director 核对专项与同版证据 | 缺维度分数 null；已知失败保留 REWORK/FAIL，不淡化为只有 NEEDS_REVIEW |

实际项目 Python/tomllib 检查通过：14个 TOML 可解析，13角色必填字段/唯一名称及权责表一致；角色非指令字段、并发配置及模型继承相对 HEAD 未变；统一规范全部相对链接、尾空白检查通过。`git diff --check` 通过。以上为人工静态推演和配置检查，尚不证明真实调度死锁已被运行测试排除、工具修复有效或视频感官验收通过；本轮未启动真实派工、渲染、配音、ASR、发布或应用测试。

## 2026-10-30 — 抖音数据驱动的吸引力与互动评估

使用 ego-browser 一个任务空间只读访问用户指定运营页、主机械视频总览/流量分析、7个实际留存悬浮节点及另一机械图文详情；浏览器任务已正常 finish。没有上传、存平台草稿、发布、发送评论或修改平台内容。观察时间保留在每份原始快照首行及留存 JSON；原始证据和 SHA-256 清单见 [抖音复盘目录](analytics/douyin-20261030/review.md) 与 [证据清单](analytics/douyin-20261030/evidence-manifest.json)。截图已实际查看。

主视频页面读数2448播放、15赞、1分享、0评论、8收藏、4涨粉；平均13秒、完播3.31%、5秒完播51.72%。实际悬浮节点显示2/5秒留存高于平台同类，9秒32.16%、18秒15.86%、27秒10.35%低于同类，支持优先检查5–27秒信息推进，但本轮没有播放/听审发布版或取得本地哈希关联，不能判定具体镜头缺陷。账户10月23—29日区间读数与作品当前读数分别记录；第二条实际是23张图文，不能当视频对照实验。平台同类群组、部分分母/截止延迟不明均保留限制。

新增 [吸引力与互动评估](audience-growth.md)，明确留存、点赞、分享/收藏、评论和关注的发布前证据与发布后验证闭环；更新统一交接规范及 Director、Creative Director、Script、Audience QA、Audio Appeal QA、Growth Analyst 六个相关角色。沿用现有角色、权重和门槛，不新增增长评分或无依据的爆款阈值。后台建议均标观察/候选解释/最小修改/验证指标，未改动影片、旁白、批准记录或归档脚本，未启动生产或定时观察任务。

实际检查：项目 Python/tomllib 解析14个 TOML，通过13角色必填/唯一性及相对 HEAD 非指令字段一致性检查，并发与模型继承未改；新规范/复盘文档相对链接及尾空白检查通过；7个实际 tooltip 可解析、证据文件哈希已记录；`git diff --check` 通过。人工静态推演确认：低5秒留存与5秒后流失分别诊断；单次分享不作因果结论；0评论不推断动机；图文不混视频；新窗口数据不覆盖旧快照；增长预测不替代感官 QA 或发布授权。未运行应用 unittest、渲染、FFmpeg、配音或ASR，本次不声称视频制作验收或互动增长已通过。

## 2026-10-30 — 数据驱动流程、评估与局部制作落地

用户进一步授权根据数据优化流程、评估和视频制作。真实角色派工与唯一输出责任记录在 [Director记录](../series/3d-printer-v2/revisions/EP01/data-driven-20261030/director-record.json)，实现跟进见 [production-followup](analytics/douyin-20261030/production-followup.md)。本次只做EP01局部36秒对比，不恢复其他集队列、不发布、不覆盖原批准资产。

流程：AGENTS.md接入数据驱动制作；audience-growth增加逐段信息兑现表和实际A/B检查条件，audience-qa要求分别检查继续观看、点赞、分享/收藏、讨论和关注理由。数据源/预测、技术/感官/平台效果分开，未知保持未知。

评估实现：episode_performance支持实际5/9/18/27秒留存、2秒跳出、互动率及作品归因涨粉；率仍为0–1、计数仍须非负整数。比较要求媒体类型metadata相匹配，已知视频不能混入图文或类型未知的旧记录；旧格式保持兼容，并在未知类型比较结果中显式披露限制。新增回归覆盖真实读数保存、百分数字误作小数率、非整数/负涨粉和媒体混比。`.venv/bin/python -m unittest tests.test_episode_performance` 4项通过；`.venv/bin/python -m unittest discover -s tests` 全68项通过，11.812秒，模拟Blender SIGSEGV是既有失败路径测试而非本轮渲染崩溃。原始后台记录按观察来源/时间分别导入任务measurement/performance.sqlite，实际比较为NO_COMPARABLE_PEERS，未合成优化后数据。

制作：基线实际SHA ee0664aae24fbc8e771b3883104b49f093cd33f4921de3129e05f75dff324dc3、100秒H.264/AAC；Creative实际编码抽样检查并比较三策略后选B，Visual先关键帧，独立Audience关键帧仅支持标记清晰度实验，保留AUD-CAND-04硬段关系问题，不扩整片。新独立源scripts/ep01_data_driven及冻结任务visual/3deac0274714eadc860a保留，原脚本/归档未改。Metal沙箱预检无设备时在Blender前停止；既有GPU许可路径关键帧和渲染成功。0–36秒1080张新帧原生540×960@30，渲染exit0约9分17秒，逐张JPEG解码/尺寸/连续编号通过；1079邻接相机/部件/齿轮接触方向数值审计通过。两版冻结源姿态重算显示0–5秒相机位置/旋转/scale差为0，5/27/34秒邻接连续；不等于实际像素相同或感官通过。三份齿轮STEP独立重读共4个实体均valid/正体积（50T为双实体复合）；复用修正源缓存，没有新几何生成，不宣称物理接触仿真。

Editor最终输出均36.000秒/1080帧/H.2641080×1920@30/AAC，全片音视频解码通过。A SHA1e085d7c694298f22398997a03ff2989cd13772ba07d60c125d90631d4e6e188；B SHAfdcfd3229bca396fa43626e131db18e8dd16083a041783a5c33f7a5fbefce309。A原生1080，B原生540上采样且使用修正源，非严格单变量平台实验。12字幕单行/max16/无重叠；末字幕36.360裁至36.000，36秒是34–42.064语句中截点，不评价自然结尾/完整热端段。原Kai音轨时点保留、无TTS/ASR/provider请求。

[实际A/B页面](../series/3d-printer-v2/revisions/EP01/data-driven-20261030/comparison/index.html)已在ego-browser打开，双片元数据36秒/1080×1920、实际播放时钟推进、暂停和12秒定位通过，无media error；截图已查看。首次暂停引用过期后重新snapshot并用语义按钮恢复成功。浏览器任务正常finish；仅证明播放控件与媒体运行，静音且不构成实时感官观看或听审，证据browser-check.json。

独立Audio QA最终报告绑定B准确SHA，A/B实际PCM均1,728,000样本、完全相同；与锁定mix起点0相关性0.9999554858，mean−25.2dBFS/peak−1.2，无≥1秒低于−50dB静音。来源关联不证明听感/音画语义同步。Audio Appeal独立绑定B并实际查看7张编码字幕帧，重复预告仍在。两类音频分数null、NEEDS_REVIEW，缺实际听审/音频理解与词级强制对齐。最终Video/Audience评审另记于后续交接条目，不能以该阶段技术完成自动视为通过。

当前校验：4个新制作Python源AST解析/尾空白、14个TOML解析、相关文档链接及git diff --check通过；独立重算原片/旁白/混音/字幕/时间线哈希未变，editorial hold保留。媒体与帧、场景、失败/准备版本、归档和证据均保留。

最终交接补充：两类音频复核后，独立Video QA完成（B全解码；1080张缩略源帧逐序静态与56张实际编码B样本分开记录），随后独立Audience QA检查10个A/18个B编码样本及12–21秒逐秒静态序列。准确最终报告分别在video-qa/final和audience-qa/final，Director独立重算四类报告及A/B哈希，并写delivery-manifest.json。可确认环标记静态可辨性提升；AUD-CAND-04新信息不足、重复预告及B预览噪点等P2保留，未扩全片。所有综合/技术/观众/音频分数null、NEEDS_REVIEW；人审明确12–21、23–27、7.410–11.408和27–36秒问题，shot ID unavailable。完整局部制作交付不冒充全片正式验收或增长成功。最终文档链接/TOML/新源解析、原片及锁定音频字幕哈希和git diff --check再次通过；无新增生产源修改后的额外测试必要，沿用本轮68项实际测试结果。


## 2026-10-30 — 打印机六集规划与入口纠偏

用户选择保留 EP01/EP02、按机构收敛集数，并授权实施规划。[当前六集规划](printer-series-plan.md)新增实际批准 EP01 内容依据、EP02 待验收边界、旧十二集到六集的迁移表、后续单集新增信息、EP03 源走线/运动验证及三个开场候选。打印机系列明确使用 qwen3-tts-flash / Kai，不改动已有批准音频；通用 Ethan 默认与历史 Andre 记录不作为新打印机任务的声音依据。

README、系列说明、AGENTS.md 和项目内 mechanical-video 技能接入当前规划；旧实现章节保留并标明历史范围。旧 CLI 仍执行原有内容，本次没有实现六集运行时、迁移队列或修改历史计划。旧 editorial hold、影片、批准/QA、归档脚本及帧保持原样；没有启动 worker、子角色生产、渲染、配音、ASR 或平台操作。

实际静态检查：六份入口/规划文档共20个本地 Markdown 链接目标存在；六集及历史 EP01—EP12 迁移覆盖、Kai 配置、NEEDS_REVIEW 边界检查通过；改动路径仅为文档及项目指令，git diff --check 通过。新增规划文件另行检查尾空白。未运行 unittest、CAD 生成、ffprobe、FFmpeg 或感官 QA，文档修改不需要新媒体生成；不沿用旧测试结果冒称本轮媒体验收。下一制作门槛为 EP03 皮带路线、固定点、源实例及输入/位移对应验证，尚未执行；EP02 原有听审与实时观感门槛未关闭。

## EP02 临时数据清理（2026-10-30）

用户授权清理后，在 worker/render 双锁下删除 87 个旧实验场景快照、12 个自动备份、72 个字节码缓存，合计 6,749,532,678 字节（6.29 GiB）。保留的 29,256 个文件逐一 SHA256 核对一致；全部音视频、渲染帧、批准及 QA 记录、源归档和 EP01 依赖保留，Git index 哈希未变。最新 107 秒 H.264/AAC 成片 ffprobe 和 FFmpeg 全片解码通过。历史场景路径可能已清理，重做需从归档重建；本次不改变 NEEDS_REVIEW 或历史验收结论。详见 [清理范围、哈希与恢复边界](ep02-cleanup-20261030.md)。文档链接与 git diff --check 通过；未运行渲染或配音。

## 2026-10-30 — 新六集 EP03 制作启动与机械门槛

用户授权开始 EP03。真实 Research、Creative Director、Visual、Script 分别独占新目录，详见 [Director记录](../series/3d-printer-v2/episodes-current/EP03/director-record.json)。旧十二集 EP03、EP01/EP02批准资产、归档和editorial hold未改；没有启动历史worker或平台操作。

已完成三开场比较（选直线结果连续揭示两路输入）、六段Kai文案草案和56条单行字幕文本（最长19字符，时码未测量，不是SRT）。Research实际查看官方路线/夹持页，独立读取原STEP两带并核对实例、有效正体积及10mm层距；Visual重读33项XY STEP/STL、解析两条开口带边界及端帽。五组1mm小位移等长检查仅为几何候选，不证明电机输入、接触、切向或真实传动。

发现P1：左右滑架原STEP本身无效，Research与Visual独立证据一致。两轮planar修复虽在内存有效，STEP导出重读仍无效，策略停止并保留失败文件；没有覆盖源缓存。端帽与夹槽接触、输入/带轮/滑架映射尚未通过。默认Metal预检失败，未启动Blender、未请求GPU升级审核，未消耗渲染任务。配音合成、局部影片及整片渲染均未启动，状态NEEDS_REVIEW；缺失评分保持null。

本轮实际检查包括源CAD独立读取、几何边界与等长数值检查、JSON/Python AST及字幕字符检查、文档链接与git diff --check。当前实际运行 unittest discover -s tests：68项通过，10.059秒；输出中的模拟Blender SIGSEGV为既有失败路径测试，非本轮生产崩溃。未运行ffprobe、FFmpeg或感官QA；无新媒体可供解码。后续只读OCP诊断已定位两滑架各一处SelfIntersectingWire，基于该新证据的第三/最后一轮显式ShapeFix自交/共享拓扑修复后，两件STEP重读仍无效，体积漂移≤1.09e-8。已达到项目每问题最多三轮自动修复上限，停止自动修复、配音和渲染。下一门槛为针对共享edge及相邻面一致性的专业/人工CAD修复，并独立验证STEP往返；接触和输入映射仍未通过，尚未进入真实关键帧/局部A-B。


## 2026-10-31 — EP03 热门样本校准与原创 CoreXY 原理片（制作中）

用户追加授权“找爆款的视频进行分析，学习经验然后制作”。[实际对照报告](../series/3d-printer-v2/episodes-current/EP03/benchmark/analysis.md)记录三个百万播放B站样本、抖音高互动机械密封及同题CoreXY专业参照的作品页数值、观察时间、截图覆盖与限制。未把点赞当播放；未取得可比曝光、留存或涨粉归因，不宣称已验证爆款因果。独立Creative检查了本地影片编码帧/字幕，比较三种开场，采用“先预测单输入、12秒内兑现斜行，再解释夹持/双输入直行”的N1。

原Voron滑架P1及三轮失败修复保持，未重试或隐藏。另建明确标注的原创简化CoreXY教学装置，不是原源已修好，也不是整机实测拆解。Research提供有限半径、双层开口夹持皮带及固定材料坐标的解析模型；45件独立STEP重读有效正体积单实体、STL闭合，连接链独立核查。该证据不等于动态仿真、制造精度或全工作空间碰撞验证。

原生1080×1920/30fps、30秒900帧的真实A/B已生成及全解码，Editor加入同一Kai音轨/字幕。A SHA256 `1ae932f572e94cbac10beea08156bdebfd27a418350239c4a420b64c89dbf988`，B `0a78e220af1a679706059d0cb31355b2284327e893e4cc7989f48cd2f807c604`。两版都是新N1，只比较12–22秒机位，不是旧/新叙事或平台效果实验。独立音频两QA、VideoQA及AudienceQA检查准确版本，B夹持端更清楚；轨迹误认实体杆、输入环偏小、10–16秒静音节奏待实际观看为P2。缺实时观看/听审及可靠评分，仍NEEDS_REVIEW。页面播放、暂停、定位和切片同时间保持已在ego-browser验证，不代表听审。

正式120秒任务冻结为 `3a3d214fac69b27a0516`；新renderer仅在12<=t<22隐藏投影轨迹/初始见证点，保留45物理件与连续动作。12张实际smoke及75–82秒210帧证据片完成；独立preflight完整解码、核验全部210原帧哈希，并查看28张编码顺序样本，支持上灰A03转向轮运动、下B输入停止，无新增已证P0/P1。679个数值帧支持73–95.608秒A输入变化/B保持；静态样本不冒充实时观看。Director已放行同指纹3600帧续渲，不混旧A/B帧。最终全片尚未在本条记录时生成或验收。

5段开头与4段尾部Kai原语音锁定，实测90.672秒自然语音排入120秒，48条单行字幕最长17字符。尾字幕按字符比例估时，并非强制对齐。完整混音23311fbd0534131a52c7已准备；Editor报告静态增益平衡、峰−2.964dBFS无削波，不做压限或变速。两音频QA仅完成锁忙期间的静态哈希/来源/时间线预检，未冒称独立波形测量。增益历史元数据由版本外附注明确；待锁释放后的实际完整混音和最终AAC复审。

详细身份、任务、独占目录与放行证据见[当前Director记录](../series/3d-printer-v2/episodes-current/EP03/benchmark-production/director-record.json)。旧集、批准范围、队列与editorial hold未变；没有上传、保存平台草稿或发布。最终影片、全片解码、实际字幕遮挡/语义同步和音频/视频/观众QA需后续记录，缺失维度保持null。

正式素材补充：同一冻结任务已实际完成3600/3600帧、scene.blend及120秒静音H.264素材，原生与编码均1080×1920/30fps。视频SHA256 `78dae85ed16f637bafe2376edf2227ced1caeda7ffa969f11567f425c0c300cc`，Director独立重算一致；ffprobe与全片解码通过。3600原帧哈希清单保留，75–82秒210原帧与preflight清单完全一致。Visual本轮实际 unittest discover：68项通过，9.861秒；模拟SIGSEGV是fixture，非此次生产崩溃。Director另检查8份冻结Python AST、3份当前JSON、本条文档链接与git diff --check通过。Editor三张smoke+ASS合成预检18/80/106秒已查看（不是最终MP4抽帧）：无已证P1，80秒下B标签浅字压青底对比偏低P2保留。静音素材及排版预检不替代最终混音/字幕成片独立QA。

最终成片补充：Editor生成120.000秒/3600帧H.264/AAC成片，原生=编码1080×1920/30fps，完整AV解码通过。准确SHA256 `4f1668a3778efc26aa1b4ee8365a58869a3671d31e753f2192a222704610b25b`，Director独立重算一致。两类独立最终音频QA均绑定该哈希：音频技术短持锁解码5,760,000个实际AAC样本，mix相关性0.99997429/lag0，峰−2.9948dBFS，无满幅；9源自然速/实际增益/placement重建speech逐样本一致，mix加和误差≤1LSB。音频吸引力另查22张实际编码帧；未进行实际听觉理解或实时观看，不能据此通过语音自然度/精确词界/F04F05语义同步，分数全null。报告见当前任务audio-qa/final-full-233与audio-appeal-qa/final-full-233。VideoQA及随后AudienceQA尚在进行，80–84秒下B标签对比P2与输入标记辨认/节奏风险继续保留。

最终独立VideoQA完成：实际全片AV解码/3600帧规格及来源清单通过，查看114张编码样本（覆盖48字幕中点），无新增已证P0/P1。随后AudienceQA独立查看36张实际编码样本，建议保留成片做针对性人审；32–69秒全景/小喷头运动分量辨认、78–85秒下B标签对比、101.5–119秒当前转角与细旧轨迹区分仍为P2，不凭笼统吸引力推测再次重渲。Director实际查看四张最终编码联系表，范围是静态抽样，不声称实时观看。

Director重新核对最终MP4、10项Editor资产、四类最终报告全部准确哈希，写入[交付清单](../series/3d-printer-v2/episodes-current/EP03/benchmark-production/delivery-manifest.json)，[最小人审问题](../series/3d-printer-v2/episodes-current/EP03/benchmark-production/human-review.md)按时间/段ID列明；shot ID未独立分配，不冒充已有镜头编号。正式生产交付完成，状态PRODUCTION_DELIVERED_NEEDS_REVIEW；所有所需综合/技术/观众/音频技术/音频吸引力评分保持null，未通过正式验收。完整120秒实时观看、实际听审、F04/F05语义对应和可靠感知评分仍是明确门槛；没有上传、平台草稿、发布或增长效果结论。旧资产、失败版本和所有源/模型/场景/帧/音频/指纹归档保留。最终文档链接/当前JSON及hash检查、git diff --check通过；无新增代码变动需要重复已通过68项测试。


## 2026-10-31 — EP03 三处局部优化（用户授权，制作中）

用户在明确三处建议后指令“优化”。锁定此前120秒233成片（SHA256 `4f1668a3778efc26aa1b4ee8365a58869a3671d31e753f2192a222704610b25b`）、9段Kai/原混音、48字幕与全部时间、45CAD及机械动作/机位朝向。范围仅32–69秒分量辨认、78–85秒B标签对比、101.5–119秒旧轨迹与当前转角区分；不改旧片、不恢复原源修复/旧队列、不发布。

Creative在局部策略中按原字幕估时确定横梁→相对横梁的滑架→合成，以及前后抵消/左右抵消顺序；时码仍非强制对齐。Visual冻结新任务7ea93cfe64e7bd2cfd3d，F05移除此前六段累计图解及初始注释球，保留当前两腿轨迹；不是移除物理零件。机械motion-audit与原片逐字节一致、camera/pose代码块一致，1111条中段投影区分beam世界方向与carriage相对beam方向。7张smoke、3段2秒proof及7精确时点原帧已生成，保存185个本任务原帧供同指纹续渲。

Editor局部版本0cfa9bd6e186d4f2c03c在真实投影上加分段框/箭头和短callout，80秒两标签28→36px移空白区加深色背板。三组实际A/B（36–38、54–56、104–106秒）1080×1920/30fps各60帧，全部AV解码、同窗音轨PCM逐字节相同。独立QA查看raw7smoke/24proof样本、composed48样本、7精确图和80native，9局部MP4独立完整解码，无新增已证P1，三项有可观察改善；[局部报告](../series/3d-printer-v2/episodes-current/EP03/benchmark-production/qa/optimization-v1/local/report.md)保留薄暗轮廓手机辨认P2及实时/听审缺口。Director实看新旧116秒图、35.5/55/80合成图，并放行同指纹3600帧续渲；没有以2秒片段冒称完整语义/邻段通过。中段细暗轮廓另安排一次overlay-only白主线/暗边对比（该问题第2次），不影响冻结原生渲染，不改标签/几何/音频，不得静默采用未验看版本。

记录见[本轮Director范围与尝试计数](../series/3d-printer-v2/episodes-current/EP03/benchmark-production/optimization-v1/director-record.json)。正式优化全片尚未生成，需新MP4/实际混音/VideoQA/AudienceQA，所有缺失感知评分保持null。原233交付与旧报告仍保留，优化授权不等于正式验收或平台授权。

优化续渲实际完成：任务7ea93cfe64e7bd2cfd3d全部3600帧、120秒原生=编码1080×1920/30fps/H.264静音素材。SHA256 `36fdfba3124e067155537c71702cfcf201e2e9e6ddfbc5fd56754945a9436edf`，Director独立重算一致；ffprobe/全解码/全部帧哈希与185张保留原帧及归档源哈希复核通过。机械动作/相机/正实体CAD不变，本轮实际验证为冻结AST、3600数值、真实渲染、解码与哈希；未为纯图解改动重复unittest，上一轮68项/9.861秒明确仅为历史结果。

中段描边第2attempt c889e6f78423262de3ec已实际合成35.5/55秒图及两段2秒片，独立QA查看native/16编码样本：白色滑架边界和灰底箭头可辨性改善，无新已证P1，选择c889。839条原drawing保持精确path/time仅黑5px外沿+白2.5px主线双层化，其余ASS（含80标签）、mix/SRT/timeline保持字节一致；两片60帧独立全AV解码与相对0cfa PCM一致。Director也查看两张native图，按该限定放行完整新MP4组装；第2次有可测改善，不发起第3次同策略修复。新片仍需两类finalmix和Video/Audience独立新哈希复核。

优化新成片已生成：[EP03-optimized.mp4](../series/3d-printer-v2/episodes-current/EP03/benchmark-production/editor/optimization-v1/final-versions/9c78127c97f17d28868e/EP03-optimized.mp4)，SHA256 `960fd013adf62e93747f036018165ab3230e0175310464d0b68d28bd73a64ca3`，Director独立重算一致。冻结runner c71985465e41a8431650+c889 overlay+7ea93 raw组装，120秒/3600帧、原生=编码1080×1920/30fps/H.264AAC，全片AV解码/ffprobe通过，48条单行字幕最长17字符且无重叠。完整AAC直接复制233，没有重新合成/变速/混音/有损重编码；独立AudioQA对新旧fresh解码5,760,000样本PCM字节一致、ADTS相同、5626包payload和PTS/DTS/duration/size/flags全同。AudioAppeal另看16张实际编码帧，确认指代参照更具体，但缺听觉理解/实时体验，不以静态清晰或音频相同通过语义同步。两类评分均null/NEEDS_REVIEW；报告绑定当前新hash。Director当前15份Python AST、2份root JSON、优化条目链接及git diff --check通过；最终Video/Audience结论待后续补充。

本轮最终交接：独立VideoQA完成3600帧全AV解码、source/ASS哈希/48字幕及170张实际编码样本（含强调起止±0.3秒与邻段），无新增已证P1；三处具体外观子问题在当前新hash采样范围内可核验修复，不再保留“细暗轮廓/下B压青底/结尾旧迹堆叠”为未经处理的同一外观结论。独立AudienceQA另查35张实际编码样本、三联系表与native35.2/81.5/119秒，建议保留优化版并停止本轮自动修改。仍未验证动态分量理解、长全景节奏、实时轮子身份、完整听审和F04/F05语义同步；91–96秒原图解是否误认实体杆也未由本轮局部清理关闭。全体感知与综合分null，正式验收未通过。Director查看三张最终编码联系表，方法仅静态抽样，未冒称实时观看。

Director再次重算新MP4、6项最终资产和四类新hash报告一致，更新[本轮交付清单](../series/3d-printer-v2/episodes-current/EP03/benchmark-production/optimization-v1/delivery-manifest.json)及[剩余人审窗口](../series/3d-printer-v2/episodes-current/EP03/benchmark-production/optimization-v1/human-review.md)，latest-delivery.json指向优化版，旧233影片/原清单/报告全部保留。生产状态OPTIMIZATION_COMPLETE_NEEDS_REVIEW，三个优化均已实做；未以局部或外观改善宣称涨粉效果，也没有上传、平台草稿或发布。最终JSON/哈希/本地链接与git diff --check通过；没有编辑旧归档、其他项目、全局技能或ambient Git工作。


## 2026-10-31 — EP03 配音优化空间分析（未改媒体）

用户要求分析配音。Director、AudioQA与AudioDirector分别独占audio-analysis-v1根/technical/direction，核对当前优化片960fd013…64ca3。实际AAC新测−27.98LUFS、−2.99dBTP、LRA8.2LU；speechsolo−27.95LUFS，混音短长段RMS差仅0.186dB。逐段字数/源时长、源头尾/内部低电平与峰分布已测，前后均值4.66/3.89字秒不当作音节或听感，去头尾及≥.35秒内部低电平后proxy差降至7.9%。−50dBFS实际低电平9.367–16.142秒约6.775秒为检查候选，不自动视作无用静音。稀疏短峰限制整体增益，保留−1dBTP时仅约1.99dB余量，不指定统一平台响度或盲增10dB。结论及F04正序身份/F05直接结论等文字候选见[配音分析](../series/3d-printer-v2/episodes-current/EP03/benchmark-production/audio-analysis-v1/analysis.md)。

没有实际听觉理解工具，未声称听到机械腔、错读或情绪问题；评分null。未TTS/ASR/provider请求、未变音频/混音/字幕/成片或平台操作。实际短持render.lock测量后已释放；报告/JSON/新测脚本AST及hash/空白检查通过，git diff --check通过；分析不需要新CAD/渲染或重跑生产测试。


## 2026-10-31 — EP03 字幕位置记录、修复与局部配音优化

用户授权记录字幕位置、修复EP03并优化配音。以用户指定正常的EP02 b0d7成片为实测基准：1080×1920白字底边约Y1530–1531、底距388–389px；原EP03约Y1681–1682，低约151px。已新增[字幕位置规范](subtitle-placement.md)，并在approved-video-style链接。EP03采用Subtitle an8 pos(540,1484)，运动轨迹Note由Y1500移至1410；四组实际局部A/B及11张新句字幕样本由独立QA检查，未见采样裁切/重叠。该基准不等于平台UI遮挡测试通过。

AudioDirector给最小四稿，Director作为Script审定后用现有audiogen生成qwen3-tts-flash/Kai，只替AD03/F04整源；4句实测1.896/2.928/2.136/17.664秒，分别放12/16/73/78秒，均完整保留自然速，其余7源保留。12秒仅追橙带、16秒才说两端连接；F04先A路转向轮正身份再排除B驱动轮。F03/F05及120秒机械动画保持。开头间隔是重新分配，不声称净消除静音或听感已改善。新句静态RMS匹配后统一+1.8dB，无动态压缩；独立重建11源/拟音误差≤1LSB。

新版[EP03-subtitle-audio-v2.mp4](../series/3d-printer-v2/episodes-current/EP03/benchmark-production/subtitle-audio-fix-v2/editor/final-versions/87aa9856d786b05aa426/EP03-subtitle-audio-v2.mp4)，SHA256 `42814ded876b3f762910e885481fdfa001dbf3fc1b30d71fec31c6325cd07d37`，从冻结无字幕7ea93源新合成，120秒3600帧，原生=编码1080×1920/30fps H.264/AAC，全片AV解码通过。46条单行字幕最长17字符，无时间重叠；新句分句时间按源时长估计，不冒充强制词对齐。最终AAC独立实测−26.16LUFS/−1.17dBTP/LRA8.6，满足本轮≤−1dBTP门槛，PCM与mix相关0.999979798/lag0支持来源关联，不能替代听感。AD03b末20ms低幅能量P2仍待听审，未据此裁尾/自动重生成。

本轮18份Python AST/56份JSON读取检查及新增文档链接、git diff --check通过；实际四句合成/局部AB/全片编码与解码已执行。未改变CAD或机械渲染器，不重复CAD生成或历史unittest。两类音频、Video与Audience最终报告绑定新hash；实际听审、完整实时观看、精确词对齐及平台UI覆盖缺失项仍需复核，感知评分null，正式状态NEEDS_REVIEW。保留全部旧片、源、报告和editorial hold，无平台上传/草稿/发布。

最终独立VideoQA对新hash完成3600帧计数/完整AV解码与82张实际样本（全46字幕中点及邻居）复核，AudienceQA另看45张实际样本，未见新增已证P0/P1；20秒字幕持留候选经原生第600帧核实撤回，不记修复。Director实看最终18/80秒原生与最终联系表，四类最终报告hash已绑定[本轮清单](../series/3d-printer-v2/episodes-current/EP03/benchmark-production/subtitle-audio-fix-v2/delivery-manifest.json)，latest-delivery已指向新版；状态SUBTITLE_AUDIO_OPTIMIZATION_COMPLETE_NEEDS_REVIEW。完整听审/实时与平台覆盖门槛仍保留，详见human-review.md。


## 2026-10-31 — EP03 持续运动修复（制作完成，待实时复核）

用户反馈新版播放时机构停住、要求机器持续运动。以42814ded…07d37影片为基线，独立QA核源发现42.5秒机构静止：0–3、10–22、28–32、48–51、56–57、68–72、96–101.5、110–120；实际encoded六窗口420帧无相邻精确重复帧，不能将有压缩差异或相机动视为机械持续运动。

本轮单程八模式覆盖120秒（A0–22、X22–30、B30–50、X50–57、Y57–72、A72–99且B保持、X99–104.5、Y104.5–120），无重复往返或循环凑时长。第1候选23c53长smoothstep保留但停用：低速候选最长5.27秒；第2候选ac84e47c5d1c43cb446a采用0.4秒余弦速度ramp和中段恒速。独立QA核3600状态/3599邻帧工具位移均非零、位置与速度连续、解析速度误差4.66e−9mm/s，B72–99含端点811样本恒定。低于1mm/s最长13帧0.433秒仅数值口径，不等于实时观感通过。45实体及缓存无几何变化，带长/端点/切线约束全运动审计通过，不重复实体生成。

当前unittest discovery：test_video_qa.py 3项、test_film_audio.py 2项、test_ep02_continuity.py 2项全通过。Visual新任务归档/投影重算，Editor锁11旁白、46字幕及其时点/位置/增益，按新速度更新合成拟音；原片/原音/旧任务/holds保留。实际局部AB、完整新片与最终独立四类QA尚待本轮完成，未更新latest交付指针或宣称P1关闭。

持续运动版全片已生成：[EP03-continuous-motion-v3.mp4](../series/3d-printer-v2/episodes-current/EP03/benchmark-production/continuous-motion-v3/editor/final-versions/c6d43dae194d76eaaf7f/EP03-continuous-motion-v3.mp4)，SHA256 `ae39a625b13c1f7e0b682709c065a4e928b89a39f77c25c35cef1165a943871f`，Director独立重算一致。冻结ac84原生3600帧1080×1920/30fps，续渲约37分14.5秒；3600JPEG哈希/尺寸、480同任务proof逐hash保持和120真实renderpose对应审计通过。raw SHA256 `1bef286ec9f22317a2fd0c7ed4e1cdad7ae61185ec12ec4448147f91d443e044`。新c23d runner+f2b overlay/mix锁定来源组装120秒H264/AAC，ffprobe/3600计数/完整AV解码通过，原片未覆盖。

当前11旁白speech-mix、46单行字幕（max17）/文字/时点/位置均与v2字节一致，新拟音按真实du/dt重建误差<1LSB，源零速度时拟音为零、首末样本和末20ms为零，不能代替无click听审。完整新AAC独立测−26.19LUFS/−1.20dBTP/LRA8.6，满足本轮≤−1dBTP上限，5,760,000样本120秒解码与mix相关0.999980750/lag0，11段相关各>0.99，仅证明来源关联。44Python AST/49JSON预检及7项当前unittest已通过，最终四类QA继续收尾；完整实时视觉/听审分仍null，不能以数字非零位移宣称体验或涨粉通过。

本轮最终交付：四类独立报告绑定ae39新hash。VideoQA核119张实际样本、完整decode/3600计数、所有字幕/源/模型哈希及轮组/转角邻段；AudienceQA独立核同片并复看119图及3native，建议保留版、停止自动修改。Director实看最终80/119秒原生及尾段联系表；数值长plateau0秒和采样实际位移支持机械停留源修复，不能关闭实时体验整体问题。所有感知评分null，EP03-V3-MOTION-HOLD-01体验项仍待完整120秒实际实时观看/听审，未虚构通过。记录见[本轮交付清单](../series/3d-printer-v2/episodes-current/EP03/benchmark-production/continuous-motion-v3/delivery-manifest.json)及human-review.md，latest-delivery已指向新片；旧版/归档/holds保留，无平台操作。最终资产及四报告hash、JSON、本地路径、git diff --check再核。


## 2026-10-31 — EP03 机械声增强及1.12倍速（制作完成，待试听）

用户确认现有连续运动版视频可以，指出机械声不见、速度偏慢；经明确选择授权整片节奏及旁白稍加快。锁定ae39视觉构图/机械路径/字幕位置与原Kai11源，独立按1.12统一调速、旁白atempo保音高、不新TTS、不改CAD或重渲染。字幕46条文字/坐标不改，派生SRT/ASS/timeline时刻÷1.12，参考fad150→134ms，实际已烧字幕随画面统一调速而不二次烧录。

独立AudioQA诊断原机械声−55.15LUFS，比speech−26.11低29.04LU，RMS低26.25dB；相对v2机械声降6.71LU，约96%功率集中80–250Hz，新du/18使绝大多数运动帧幅度包络小于1/3。不能用轨道存在反驳听不到。Editor制作+10/+16以及+16加温和3/4/5谐波候选（系数.35/.22/.13），12个实际局部片及3份完整WAV保留。独立重建derivedspeech/foley逐样本相同，presence原速公式误差<1LSB；speech无新增gain/压缩，861样本仅补零无裁词。presence相对原foley改善16.512dB RMS，250–500/500–1000Hz相对纯+16增加6.47/15.19dB，Director条件选择presence为生产候选，非听审优选或手机可闻证明。

第一完整快版82a生成107.166667秒3215帧H264AAC并全AV解码；AAC独立−26.36LUFS/−1.20dBTP/LRA9、107.142854秒，尾差23.8125ms<1帧，正确派生mix相关0.999958374/lag0。最终画面映射复核发现P2 V4-CFR-MAP-01：默认-r30使五点约固定落后44–64ms，并非seek误标；未把仅规格通过当字幕同步通过。保留82a，显式fpsfilter+passthrough诊断五精确帧匹配源帧，误差约4–15.5ms均<1帧，关键字幕切换正确；独立QA支持新编码，原AAC直接复制且待新媒体payload/PCM验证。

本轮test_film_audio2项/test_video_qa3项unittest discovery全通过，12PythonAST/25JSON预检通过。新fpsfix完整片及四类最终报告仍待绑定；无实际听审，手机可闻性、提速自然度、AD03b尾字及语义同步等感知分null，未声明正式验收或平台操作。

唯一最终fpsfix新版：[EP03-speed-sound-v4-fpsfix.mp4](../series/3d-printer-v2/episodes-current/EP03/benchmark-production/speed-sound-v4/editor/final-versions/ecd6aa99088958c6a5a9/EP03-speed-sound-v4-fpsfix.mp4)，SHA256 `1fa11d7a5240611bd1f4adde237154a10bfab5f7dac41fb1e34eae3d0057351b`，Director独立重算一致。显式fps/passthrough后3214帧107.133333秒视频，音频107.142854秒、两start0、音频尾多9.521ms小于一帧，格式约107.143秒且大于90秒，H264/AAC1080×1920/30fps全AV解码通过。新音轨与82a的ADTS/PCM及packetpayload/PTS/DTS/duration/size/flags独立逐项同，核原报告hash后复用−26.36LUFS/−1.20dBTP/LRA9实测，不额外重测未变音轨。

最终VideoQA对新媒体无seek精确五点及首末、46metadata/源hash/完整解码检查通过；五点映射误差15.48/7.14/−4.76/3.57/13.10ms均小于一帧，第2143帧下句正确，V4-CFR-MAP-01仅在这一技术覆盖范围修复，不当全片词级同步通过。AudienceQA另核唯一新hash及5原生图，建议保留版、停止自动增益/调速。四类最终新hash报告已绑定[交付清单](../series/3d-printer-v2/episodes-current/EP03/benchmark-production/speed-sound-v4/delivery-manifest.json)，Director实看最终2143图；latest-delivery指向fpsfix，保留所有旧版。手机机械声可闻/掩蔽/自然度、1.12Kai语速及AD03b尾字等需完整107秒实际实时AV试听，分null，NEEDS_REVIEW，无发布操作。最终JSON/路径/hash及git diff --check再核。

### 2026-10-31 EP03 制作经验归档（仅文档）

新增 docs/ep03-production-lessons.md，并从 docs/production-lessons.md 建立入口；记录字幕实际位置、连续机械运动、机械拟音、Kai 配音与整体调速的经验和验证边界。两份文档共25个本地链接检查通过，git diff --check 通过。按用户要求另存长期记忆补充。未修改媒体或调用生成服务；本次不运行测试、CAD生成或渲染。


## 2026-10-31 — Context efficiency and read-only usage audit

Implemented the authorized instruction simplification and usage audit; no production scheduler, model, concurrency, sandbox, provider, media asset or publication state was changed. Core rules remain in AGENTS.md; detailed ownership, safety, dependencies, repair limits and version-specific independent QA remain in .codex/agent-workflow.md. All 13 role configurations retain their identities and role-specific procedures, now using task-scoped reading and concise handoffs. Printer-series Kai precedence is explicit in both audio production/directing roles.

- Instruction size (AGENTS + workflow + 13 roles): 65,145 → 51,925 UTF-8 bytes, 20.3% reduction. This is file-size evidence, not a measured token or billing saving.
- `.venv/bin/python -m unittest discover -s tests`: **85 passed**, including **17 audit tests** covering cumulative snapshot deduplication, cache gaps/invalid counts, resets, malformed records, both tool formats, session copy conflicts, linked/missing/orphan/cyclic children, stage attribution, read-only output and errors. Final run log: `/private/tmp/mechanical-video-token-tests.log` (temporary diagnostic, not a durable artifact).
- All 13 TOML roles parse with unique matching names; required fields and unchanged role descriptions checked against HEAD. Project concurrency remains `max_threads = 4`; no model or capability overrides were added. Local Markdown links resolve; `git diff --check` passes.
- Independent replay of the two frozen root session files matches latest token counters, source SHA-256 and both tool-output formats. Counts: noncached input 438,885 / 235,120; outputs 93,579 / 72,784; output characters 2,215,640 / 1,881,221. No resets observed. See [frozen baseline](token-usage-baseline.json). Child trees are not supplied, so team coverage is incomplete; all usage is stage-unattributed. No account/billing totals inferred.
- [Static walkthrough](token-usage-audit.md#workflow-walkthrough-static-not-production-acceptance) covers new episode, visual-only local revision, approved continuation, render recovery and missing listening capability. Preserves independent QA, exact-hash evidence, approved assets, three-round issue limit/two-round strategy stop and explicit publication authorization. This does not prove live dispatch or production acceptance.
- Custom-agent fields checked against [official OpenAI documentation](https://learn.chatgpt.com/docs/agent-configuration/subagents#custom-agent-file-schema) using OpenAI Docs. Only supported existing `name`, `description`, `developer_instructions` fields are used.

No render, CAD generation, TTS/ASR, media re-acceptance or live agent production was performed: only documentation/configuration and the independent read-only audit tool changed. Actual savings remain unmeasured until the next already-authorized comparable production task; no new production is authorized by this record. Changes are uncommitted and unstaged.

## EP04 current-six-episode local preparation and keyframes (2026-10-31)

User authorization is “开始 EP04 的制作”; this is the current fixed-bed/four-corner gantry-lift episode, not the historical twelve-episode motor lesson. EP03 speed-sound-v4 remains independently NEEDS_REVIEW. Source/Creative/Visual evidence and current dispatch ownership are recorded in `series/3d-printer-v2/episodes-current/EP04/director-record.json`.

Research's 28 recorded asset hashes all matched. Creative direction output and ten content/asset inputs matched; AGENTS/workflow inputs had changed, so current process requirements were reread and the impact logged without treating the proposal as media acceptance. Connection Research independently extracted four source-belt envelopes, eight clamp ends and top-idler axes; geometric middle radius 6.051mm is not a verified neutral layer or the nominal 20T GT2 pitch radius 6.3662mm. Clamp contact, tooth engagement and safe machine travel remain unverified.

Visual's first segmented source-tooth-mesh deformation is REWORK (pitch/tangent preservation failed); no working-transmission claim is permitted. A separately marked toothless geometric illustration preserves moving endpoints/fixed envelopes and numerically checks four corners ×601 states over an illustrative 24mm finite lift. These mathematical/mesh checks do not establish physical contact, simulation or safe travel.

Authorized GPU execution rendered actual source keyframes despite the earlier sandbox-only missing-Metal precheck. Independent Video QA reviewed six v2/v3/v4 actual frames in `qa/local-v1/`: label/colour improved, while endpoint-to-bottom-wrap visibility remains P1 REWORK. Explicit 8-sample Eevee v4 introduces P2 grain; actual-movie flicker/thin-line readability still needs review. v3 was normally interrupted (exit130), its 13 complete frames preserved and lock availability confirmed; v4 uses a new frozen fingerprint and no mixed frames. Native 540×960@30, planned 1080×1920@30 encoding is upsampled. The two 20-second silent local previews are in production, not formal EP04 films, and have no user approval. No TTS was submitted. Real-time viewing/listening capability remains unavailable to the independent QA; scores remain null. Prior reports are immutable. Current JSON parsing/input-hash checks and git diff --check pass; final MP4 ffprobe/full-decode results will be added after encoding.

### EP04 v4 complete local frame production

Both authorized GPU/Eevee runs exited0: A1 12m21.985s and A2 10m38.372s. The frozen v4 fingerprint is `65f8e57d6e3cf313e0770601fc11447b8c2e1d07b55eef6dda7d86d8dbe785ef`. All1200 PNGs fully decoded at540×960, numbered0001–0600 per variant; file and decoded-pixel SHA256 are recorded. Common first91 frames have identical decoded pixels. Frame manifest SHA256 `4e919deedffae7b410c9ea7833872e631822d8d4a443e8ee20588d2039d5a5e1`. Final render.lock nonblocking acquisition/release confirmed idle. No v1/v2/v3 frames are mixed. Editor received frozen frames for actual MP4 encoding. These checks do not replace ffprobe/full movie decode, continuous viewing or acceptance; QA002 remains P1 REWORK and QA003 P2 remains open.

### EP04 actual diagnostic A/B and repair ceiling

Editor encoded `editor/local-v1/EP04-A1-silent-local-v1.mp4` SHA256 `039767585042b404e265043dc7b1931bbbe2b48e7133d364e2f0884a8694610e` and A2 `75107cd8d378f7ef7bbe4abae4862d43e144a07f1038615e20b1ce245f167a4f`: each20s/600frames, H.2641080×1920@30, no audio stream,540×960 native explicitly upsampled. Editor input/frame hashes, ffprobe/full decode passed. Independent Video QA reran project video_qa --visual, full decoded both and viewed10 actual encoded stills. Formal-duration/AAC tool FAIL reports are retained;20s silent previews are explicit exceptions, not formal narrated episodes. This exception does not override independent known visual failure.

QA002 P1 remains REWORK. Round1 changed corner with measurable but insufficient improvement. Round2 stopped motion at12s, separated independently source-checked clamp parts and n00774 two full source solids; actual15/19s frames still did not explain correct bottom20T/U-return. Round3 used plane-normal view and independently source-checked complete bearing n00736 teaching separation; actual15s endpoints improved, but actual19s remained blocked by foreground80T n00739. Independent QA also confirmed misleading20T label association on visible80T (linkedQA004 P1). Three rounds reached: automatic repair stopped, no further full render, no request for user approval to bypass failure. Reports are `qa/local-v1/v5-static-review.md` and `v6b-static-review.md` (SHA256 `d0c8ef2ded21b85c32110d7342511961d616b100a0e422738d0d0ec65215a5a3`).

N00774 source solids remain unchanged; periodic display meshing failed then recovered within three recorded mesh-repair rounds using existing same-analytic-face/UV recovery and exact mesh cleanup. Independent actualSTL reread found closed/winding-consistent positive-volume meshes; display-discretization volume differences0.0653%/0.0593% are not manufacture accuracy. Original failures/source/caches are preserved. A ray-method defect (origin incorrectly behind candidate camera) was retained and corrected to actual near-plane; nine fixed candidates were evaluated once, not an exhaustive visibility proof. Neither repaired-tool selfchecks nor numerical rays replace independent actual images.

Current overall QA is REWORK with all formal scores null. Real-time motion, audience acceptance and low-sample flicker remain unverified. No Kai/TTS requests or full narratedEP04 film were produced. Next responsibility is Director/Research plus capable human mechanical/visual reviewer to consider a new source-grounded broader stopped teaching separation or explanation strategy; no automatic implementation or platform action is authorized by these diagnostics.

Final scope checks:60 EP04 Python sources compiled in memory,107 EP04 JSON files parsed, both actual MP4 SHA256 values recomputed and matched, README relative links resolved, git diff --check passed. No shared application package code changed; unrelated project unittest/render/provider runs were not invoked. CAD/mesh and actual rendering/encoding evidence above remain separate from failed perceptual/mechanical acceptance.

### EP04 user correction: reuse actual EP03 production scene (2026-10-31)

User instructed “参考EP03的方式，不要再重新造一遍”. Director reviewed actual continuous-motion-v3 scene/build sources, original teaching CAD cache and speed-sound-v4 postproduction chain. Exact11 input hashes are in EP04/ep03-reuse-inputs.json; component-by-component reuse/minimum-change review is ep03-reuse-review.md. Original EP03 sceneSHA57a3083ec99e0b07dd5ab8e6b791b0ffe6a05f2d77c0f3bd413289b1656a8e07 is a125-object teaching scene, not official fullVoron. All EP03 originals/archives remain unchanged.

Original Visual directly opened thatscene: retained Stage,World,threeAREA lights,material datablocks,AgX,orthographic orientation,Eevee16samples,native1080×1920/30. XY-specific objects/annotations are hidden rather than reclassifiedZ. Only36 already checkedZ sourceSTL occurrences are added with one original matrix then unit conversion/sharedtranslation. Existing EP03 crossbar mesh is instanced for explicitly idealized teaching reference geometry. No1428-part full reconstruction,no new belt/mesh repair chain,no TTS.

V1 three actualnative PNGs established concrete reuse but independently found cropped overview and added teaching beam hiding smallwheel. One minimum layout correctionv2 altered only orthographic target/scale,teachingbeam position/size and scope/role captions; all36 sourceidentity/meshSHA/matrix records compare exactly equal. Three new PNGs passed ffprobe1080×1920/fullFFmpegdecode, render.lock released. ActualSHA256:01 90353738003b59a0be0ee6941cd592bc365460ceb715983852b2b95eb354ba29;02 65330b48cc8097e6ba87fe65546f3f52a57e4a1baf8da662b9ae977547eb7d0a;03 8857daf36870aa94ba3e224be7874b29a4a7f82f5a2fb5e24db10d53ca17e250. AdaptedsceneSHA1efb0b03867c212fee3c403064b48c9a1d560ebfaf249fcd34cb7efdeb44eaa9.

Independent originalVideoQA actually reviewedv2 all3 images and source/hash records: edgecrop resolved,cyan smallwheel/shaft/longbeltentry andorangebigwheel/shortbelt readable,teaching roles andEP03style maintained. Reportqa/local-v1/ep03-reuse-v2-review.md SHA256 b82b818946d7b25061f31fe9e681ef7c430a559fd776c26ba134a531cf64436c supports moving to minimum localanimationvalidation, not workingtransmission approval. Fixedbed/gantrymotion,longbeltend/clamp/return dynamics andactualcontinuous experience remain unverified. OldQA0023rounds/QA004P1REWORK are retained; this user-directed mature-scene reuse does not resetcounts or close them. No currentvideo/audio or formal score is claimed.

### 2026-10-31 — Default to established episode production assets

User requested future episodes follow the EP03 reuse approach without repeated correction. Added mandatory baseline-first reuse, concrete paths/hashes and minimum-change handoff, source-grounded teaching representation, and early independent comparison to AGENTS.md and .codex/agent-workflow.md. This is documentation only; no scene, media, provider, approval or existing repair counter changed. Verified the EP04 reuse-review target, workflow relative AGENTS link and heading anchor; git diff --check passed. Runtime tests/renders/provider calls are not applicable. Existing validation history retained.

### EP04 continued reuse production: actual8s narrated local and stopped-source keyframes

User continuedEP04 production after reuse-v2. OriginalVisual/VideoQA/Editor were reused; independent Script,AudioDirector,AudioProduction,AudioTechnicalQA,AudioAppealQA andAudienceQA produced exclusive outputs recorded inEP04/director-record.json. Current review deliverables and same-version reports are frozen inEP04/delivery-current.json; noEP03 source/archives or other episode content changed. No extra render/QA branch remains running.

Visual reusedEP03full_motion.progress0.4s ramps and originalscene to render240native1080×1920/30frames,8seconds,onefinite80mm teaching-frame rise(.6–7.4s),fixedbed/guides/originreferences. All36static source-drive objects were hidden throughout this displacement-onlylocal; no staticbelt falsely drives the risingframe. Original independentVideoQA inspectedfirst/mid/last actualimages and prescribed240states before the samefrozenrender; all240framesdecoded/numbered/hashed. Frame-manifestSHA81f91ff7 is fully recorded by delivery links. Separate stopped-source4actual1080×1920images show n00631motor,n00630/n00655input/shortbelt,n00649/n00645/n00647large80T/shaft/small20T,n00866/n00039/n00559longbelt/clamp locations. No source-chain fullclip,shaftrotation,beltdeformation ornewcontactverification was generated.36loaded-source matrices remain exactly unchanged at all4stages; originalpre-saveJSON vsBlenderroundtrip maxdifference1.4527461456026458e-8 is reported rather than called byteidentical.

Script minimum-revised462characterfull draft,48single-linecaptions max17characters andAudioDirector21complete-sentenceguidance are ready; fullscriptTTS remains gated. OnlyLOCAL-U01was released,one actualqwen3-tts-flash/Kairequest,5.808s. Raw48kWAV SHA357a37b839669e48e9a7eaf54ec246065fa4364a738980179de54509fe1a436e. Independently decoded rawpeak-3.401dBFS/RMS-24.592,no fullscale samples. Script produced3localcaptions max9characters using measured duration;2.830/4.785s splitpoints remain energycandidates,notforcedalignment.

Editor actual8sreviewMP4 `editor/reuse-local-v1/EP04-reuse-local-v1-review-only.mp4` SHA256 dc8e86dadf2f9d0dbcdfe4a089038a8bfecce1884e91323000feb97251f3d593 is native=encoded1080×1920/30,H.264/AAC48k,240frames; fullAVdecodePASS. Kai remains originals speed/gain,offset.800/end6.608,nofoley. Editor peak-3.41dBTP/LUFS-25.40 are measurements,notlistening. IndependentAudioQA finalmixdecode/SHA/PCMsourceassociation verifiedoffset.800,corr.999978; correlation establishes source/timing only. IndependentVideoQA actual1.5/3.5/5.5s plus0.4/7.6s sampledframes:subtitles legible,unobstructed; actualwhiteglyphbottomY1531matchesEP03layout,notjustASSorigin. Its projectvideo_qa run retainedformal<90stestexception without padding. AudienceQA actual0.1/1.5/3.5/5.5/7.8stills confirms bounded fixed/movingrolevisual evidence. Neither role claimed realtimeplayback. Bothindependentfinalaudio roles,AQ/VQ/Audience reports bindthisexactMP4; realtimelistening/perceptionandallformalscoresremainnull/NEEDS_REVIEW. Exacthumanreview windows2.430–3.230and4.590–4.980splus‘上升’semanticcorrespondenceare preserved.

Independent stopped-source4image review supports minimum stoppedhighlight/cameraclip only:actual20T/80T/shaftdistinguishable,clampsposition-only. NonblockingP2titlecrossingdarkverticalstrips can be handled later by lightweightEditorcompositing; no scenerebuild needed. Crucially,this8sillustration plus staticpartsdoesnotprovefullsource liftcoupling. OldQA002 P1 remainsREWORKwith3automaticroundsSTOPPED: source longbelt-end/clamp-to-gantrytransfer/fixedwheelreturn has no same-version actual dynamicclosure. Director/Research andcapable independenthumanmechanicalreviewer mustjudge the next truthful minimalexpression/strategy; noautomatic continuation oruserapproval waivesP1. Oldv6bQA004misleadinglabel remainsfailedarchive andisnotreused. Noformal>=90sepisode/fullmix orpublication.

Final current checks: 101 EP04 Python sources compiled in memory; 171 JSON files parsed; actualMP4/WAV/allcurrentreport/sourceimage SHA256 values recomputed and matched; README links resolved. Existing unittest test_video_qa.py3 andtest_film_audio.py2 passed. git diff --check passed; no unrelated fullrender/providercalls orfullspeechgeneration.

### EP04 correction to actual EP02 CAD structure

Latest user explicitly requires real structure, not a schematic. Reused EP02 corrected-source.blend (SHA127891d30a27a658b986f0b9bc42d9b8cd2d445d0f24f7fcfa71db236cd447ec) and actual job placement/source paths; retained735 necessary real parts: Frame180,bed16,Gantry structure311,Zdrives/idlers/stoppedbelts228. Teaching rods/frame/boxbed removed; no independent rod rearrangement,scalechange,newCADexport/mesh repair/fullmachine reconstruction. Single commontranslation and camera retarget place real assembly above nonmechanicalStage; originalfirstimage/frozenversions preserved.

Actual native1080×1920 real-source-structure.png SHA8489ed637f192bbc47e7fdc37d38e4bdb2779ca954fc78bf383bb770f6d8f4e0,ffprobe/fullPNGdecodePASS. Original independentVideoQA actually compared EP02/oldEP04/newimage,confirmed realextrusiongrooves/cornerbrackets/fasteners/rails/innergantry vsfixedouterframe; checked735unique sourceIDs/path/originaljobmatrices. Commontranslation residualmax2.14e-8m,rotationfloatdifference1.45e-5,notexactelementidentity. QA reportSHA59e7073c8198e483d1f838de09d272cd9288143e48ade6f8e1f44cd722f4e66d. source-mapping and source-reuse-report plus fullhashes underEP04/visual/ep02-frame-reuse-v1; current sharedentry/deliveryupdated and oldteaching deliveryarchived.

This closes only staticreuse/realstructure inspection coverage. No newanimation,rigidmoving-set/contactverification,TTS,audiomix orformalepisodeacceptance. FixedouterFrame mustnotbeanimatedasGantry; oldQA0023roundstop/QA004failedarchive retained. ExistingKai unchanged,so no newaudio review branch. Nativeimagehash,JSON/sourcecompilation/READMElinks/gitdiffchecks pass. render.lock released,noactiveproduction.


## 2026-10-31 EP04 real-source continuation — motion keyframes and narration preparation

- User approved real-source structure image SHA256 `8489ed637f192bbc47e7fdc37d38e4bdb2779ca954fc78bf383bb770f6d8f4e0` and continued EP04; no other episode or publication authorized.
- Frozen real motion task `7a94fb9572da7ca06bf9cc7f8870a199c3ecce33195f817ee3915cd8e41e6df8`, renderer SHA256 `9901358c3a2de1b97fc063a7135eaf26a9a55870d198b853948308bba85f4b5c`: three actual GPU frames generated; Director viewed first/end, independent Video QA reviewed all three. Report `qa/local-v1/real-motion-keyframes-review.md` SHA256 `dc6215efd8bb91f08a989b13b9e4be8ac8755fcce3a6a9943783ebe3e0b019eb` supports same-freeze short clip, not continuous/perceptual acceptance. Full 240-frame process running; completion not yet asserted here.
- Independent Research verified original-shape zero/restore STEP binding and source-derived drive phase. Old QA002 three rounds and QA004 failures retained; no inherited pass.
- New true-structure local Kai WAV SHA256 `492d989c89312a3663c2715b39d98f412b9aa4a3794f8b055060735893f2008e`, measured 6.936s, full decode and no-fullscale checks. Independent technical/appeal reports remain NEEDS_REVIEW, null scores, actual listening coverage zero. Script supplied measured-duration three captions, max12 characters; exact word/speech-motion sync unresolved.
- Full six-paragraph source-grounded Kai narration preparation released after Audio Director recommendation and actual Frame rail/Gantry slider path confirmation; no fabricated TTS duration, no forced slowing. Actual source mechanism closeups proceed independently of absent listening.
- Paths above are relative to `series/3d-printer-v2/episodes-current/EP04/`. Formal acceptance remains unverified; no publication.

### EP04 same-freeze 8s actual MP4 and full narration measured follow-up

Current review MP4 SHA256 `798466ac46290e1c154b8e767a8b083986d6b455c93d8e46c382ef29c5e37fb6`; actual native/encoded1080x1920@30,8s240frames. Independent Video QA report `qa/local-v1/real-motion-mp4-review.md` SHA256 `6b4d3b30cddf98141636dab77ad199b79f4a4ac37d34da04f234abcb48014ab7` verifies fullAV decode and6sampled frames, captions6/12/9characters. Actual realtime/listening coverage0/8s; fine source connections/drive phase unverified from wide views. Explicit short-review exception to90s; not formal acceptance. QA executed readonly checks before render.lock coverage confirmation: recorded as process deviation, not retroactively covered; no competing render/production mutation evidenced. Future acceptance acquires lock first.

Six actual natural Kai paragraphs now measured14.304/16.056/18.048/17.424/17.184/17.424s, sum100.440s(not final film duration). `script/real-structure-measured-v1/` preserves22sentences/49captions(max15characters), internal timing remains candidate, exact speech alignment null. Full review-only visual/editor production continues, no static loops/unsupported teardown and no forced audio speed. All necessary perceptual gates stay NEEDS_REVIEW/null; old known failures retained. Current documentation `git diff --check` passes.

### EP04 real-source stopped explosion and full3014 rendering

Actual exploded image SHA256 `b52bd3b3eee15e520c160c360d2d96c8bf899bf612b33eab25a4feb7f95e9edd`; independent static review `qa/local-v1/real-source-exploded-v1-review.md` SHA256 `e31eb5ba62e8fe250ff855c99cda9526ccd7e23ad71cc710845be572ffa54eca` confirms actual20T/shaft visible and source-mapped. Source housing/fasteners and original80/shortbelt displaced along independently established axis; no proxy parts or hidden geometry. This resolves REAL-CAMERA-001 static-visibility scope only. Actual continuous return and numeric matrix residual remain pending. OldQA002/004 remain archived failures. Stage edge/status text crossing extrusion retainedP2, not erased.

Full-v1 bitwise matrix reassignment assertion failed before any frame; archived failure retained. New full-v2 frozen fingerprint `6a82004104f0a7bc0d14585a30d32eae1bfecb173462f630b62acd017f79d6e0` uses max element residual<1e-6, unchanged geometry/action/camera, actualGPU frames now Saved. Target3014frames@30=100.4667s to cover natural100.440s speech. No mixed-version frames. Event32–36stopped source separation,36–43observation,43–47return; Editor alone adds stopped-state label32–47. Full render not yet complete; independent full-media acceptance not asserted.

One minimal syntheticfoleyAB uses existing deterministic function parameters, no global gain or speech change: selectedB during actual.6–7.4s lift measures−37.40LUFS/−27.66dBTP, RMS10.02dB below speech,200–1600Hz energy28.27percent; chosen mixSHA `00de8de2d3629b163127e240694359b918e925777f16462ec30c395c5dcd4c9e`. These are diagnostics, not listening or phone audibility acceptance. No invented impact/stopped mechanism sound.

### EP04 final101s review delivery — same-version specialist evidence

Final MP4 `series/3d-printer-v2/episodes-current/EP04/editor/real-structure-full-v1/revision-v2/EP04-real-structure-full-B96-review-only.mp4` SHA256 `07edc98585920f69459eb18bd95b3e4e5d16cf4e0df733f6ba6dc36b9bece4ec`. Generation complete: native and encoded1080x1920@30,3030frames,101s,H264/AAC48k,fullPNG and fullAV decode PASS. NaturalKai100.992s plus8ms picturetail. Six paragraph sources preserved, only necessaryS02 wholeparagraph once corrected停机时的→这里的; otherfive locked. No forcedspeed/wordcut/providerretry.

Source96 independently checked in research96range-review:8actualSTEP valid/hashmatch, seam8.98e-6mm/tangent7.33e-7rad/lengthdelta1.42e-10mm; actual railmargin124.32–124.82mm after96 is not safety proof. B96 actualfixedcamera3s21.185px vsA24 5.296px. Frozenade65e527b6cd582fd7229b1ad223a6581dbecd9eca94e602a785f1f470e1964 uses continuous.6–30.9120→36mm and48.960–100.15236→96mm; S03stoppedtrue-source axial separation/restore. Allbelts,wheels,gantry,clamps shareprogress. Oldfullv2 longholdP1 was interruptedexit130 at256frames, preserved and not reused. Actualframe1428 return735matrices error1.192e-7(production); independentVideo alternatecalculation fixed2.384e-7/gantryremoved36mm1.490e-7, not conflated methods.

SamefinalMP4 reports ALL COMPLETE atqa/full-b96-v1: AudioTechnicalSHA0bce96e8255f0d7a47e9b887fdb9180e18fcaf0237a7fa54da7034fc6390db41; AudioAppealSHA8c23d55cbafd8c88d09434aa811aa8809fa600a38530a1636f8ddc7e23070c46; VideoSHA1da27e46c6fac843ed1d2fbde6dc88c4513901c077a7ffe442d4def30840559c; AudienceSHAd751ea26a7d42d2bca771fa86ff67d454d43c8634d54f258679a5e4a510fdf6f. Their methods/coverage govern conclusions: current20/shaft and realreassembly supported;147captionboundary/24mechanicalneighborframes checked,49captionsmax15singleline. Actualfullrealtime/listening0,forcedalignment absent,formalall scoresnull/NEEDS_REVIEW. TechnicalsourceAACcorrelation.999969 does not prove listening. No currentestablishedP0/P1 reported; olderQA002/004FAIL archives unchanged.

RetainP2stageedge. Specific18.244–21.304s upperidlercaption correspondence under boundedfactcheck, actualspeechwordwindow null; do not invent alignment or turn singleframe into wholefilmFAIL. Userasked龙门accuracy: source internalXYGantrymoves,orangeFrame/bedfixed is accurate;一整圈canambiguously suggestouterframe, clarification suggested only, no newrerecord/render from factualquestion. Generation,continueauthorization andformalQA remain separate. README/delivery-current now point to101s film; no publication.

EP04 RC010 follow-up correction: Editor actual11frames18.244–21.304 plus frozen17–21samebottomcamera knots confirm finalASS18.57–20.94 wholecaption上面的轮子让它转向overbottomZdrive, withoutupperidleronscreen. This is now a confirmedcaption-picturecorrespondencegap, no longer just20s singleframecandidate. Actualspeechwordwindow remainsnull, so no inventedphoneticmisalignmentfinding. Evidence: EP04/editor/real-structure-full-v1/revision-v2/rc010-readonly-check/result.json. Frozen07edMP4unchanged; localtrue-sourceupperidlerderivedrepair proposed, nofullrerender/wordcutautomaticallystarted. Currentdelivery anddirectorrecords updated with the exact residual.


### EP04 XY+Z continuation — source phase correction in progress (2026-11-01)

- Actual local 54–62s clip: `episodes-current/EP04/editor/motion-appeal-xy-v1/B-real-XY-Z-54-62-review.mp4`, SHA256 `0565fc508617d0ae5726c7d0fbb2ad4baf499da653ebd9df0b515a08dd4a7838`; 240 frames, native/encoded1080×1920@30, full AV decode PASS. Independent local report SHA256 `98361003a6fd6dc95b41a7b613f1d97c516cf3a77f708cbb1f523f1fb719365a`: actual frame coverage only; no realtime/listening acceptance or XY wheel phase proof.
- All3030 actual AB/guide/chain caches independently checked, report SHA256 `338bd332f7a24ece712fd45a68f84a226624fbcc5c599e6d853a1907f3193fb6`; reused unchanged. Original full render fingerprint `6ffaef12495c39467bac9b1972b1bb2f82d30c03bacf4b53d55f151058691cb7` stopped;316 frames preserved. New source/settings require a new frozen task.
- P1 `EP04-XY-WHEEL-PHASE-001`: actual22-key pixel-ray visibility establishes nine necessary source wheels; old nonanimated phase remains REWORK. Source phase contract SHA256 `3098d592a890a2bd5614b74c2f46478b634181c45c1d210e562ab6742aeb18e2`; original mesh four-pose rigid test maximum edge error1.269e-13mm, zero/restore identity. Production mapping/material/matrix review pending; source contract is not final film acceptance.
- Compression100 same-RenderResult four representative images have identical decoded RGBA pixels to compression15. Preserve original assets; runtime capacity guard and exact downstream budget required before new render. No quality/resolution reduction or deletion authorized.
- Locked Kai narration and selected synthetic mechanical sound style/base level retained. Current entry remains baseline SHA256 `07edc98585920f69459eb18bd95b3e4e5d16cf4e0df733f6ba6dc36b9bece4ec`; no new full XY film yet. Perceptual scores remain null/NEEDS_REVIEW. `git diff --check` PASS before this append; rerun on completed record updates.


### EP04 complete914-source XY+Z review film — 2026-11-01

- Final current entry: `series/3d-printer-v2/episodes-current/EP04/editor/motion-appeal-xy-v1/full-v1/EP04-real-structure-914-XY-Z-full-v1-review-only.mp4`, SHA256 `3ac2fd7145b38d590d44624e3b18324364f28f96920b70f1ba04fce3d090445a`. 101s/3030frames, native and encoded1080×1920@30, H264/AAC48k; native complete sequence and final AV decode PASS. Render74458/verify64059 exit0, lock released.
- Unique source task `55613f78f635713a051e5323796b5bb285579f395e27b99116979f3ad8ea3044`, phase75 manifest SHA `1c41323139c42d6453fa245721c176ddf0cfd611da12cf13fcb983fb449ccf5a`. Old316+229frames preserved, not mixed. One authorized same-RenderResult60/75/100 comparison: four representative RGBA SHA identical, mean encoding0.280/0.501/4.088s; selected75 without native/sampling/CAD/action/audio change. First150actual204.536s/1.364s per frame, perframe1GiB guard; no ENOSPC.
- Nine visibleXY wheel production independent report `research/motion-appeal-xy-v1/xy-wheel-phase-production-review.json` SHA `128fea1e10d1279a5ed8dfbd2277e8fbe415ad636fc475fa37f38190c029f6b2`. Four source variants retain12realSTEPsolids; support/motorbody assignments retained, originaluniform material/smooth. Phase0 world vertex error2.65e-8m, idealangleerror0, float32matrix max4.036e-7. Oldtess/source bounds0.01707mm disclosed; not originalSTL byteidentity or physical simulation proof. Full3030guide/AB/chains caches reused unchanged.
- Editor frozen artifacts SHA `5c6854ec09599319fe5f4238095db0d9c4f64867f0d9caa444870102bd89957b`, handoff SHA `c68b68b7e47ae0bbf7649be66e38dc36bdbcb0fcc58f0d0728086e46a157d4db`; lockedKai100.992s/49ASS retained, mix SHA `5e385f6984a589f73ce9a8a06e9420b13b746240baa0f164cdd201bf6bcd3b5e`; stopped30.912–48.960 synthetictexture nonzero samples0. Editor static147captionedges+54mechanicalneighbors/12tables+guide1813–15; not realtime/listening acceptance. Finalmix−25.06LUFS/−1.67dBTP.
- Samefinal independent reports: AudioTechnical md `596e37e244183b477f4f94dc59c748c1d07b85ffaf22bccf8960238cfd5aedba`; AudioAppeal json `d90c4c5b7a4d3b30081dd50122096847494ed94737576aae33b702d194538b89`; replacementVideo json `9f20fd03cfedce0193e296ec710643875cd393960990a56fbbf9adc92d554bf6`; Audience md `dcca782ed766701b009106789803e26f85d070759cc5d2fafe4f29848f7c3332`, all under `qa/motion-appeal-xy-full-v1/`. All NECESSARY scoresnull/NEEDS_REVIEW. Video replacement independently8existingimages; Audience20/55fullframes+16thumbnails. Actual realtime/listening0. No current newly establishedP0/P1; historical failures remain tied to originalversions, not blindly inherited.
- Originalpreview_qa provider413 twice; independent same-role replacement `xy_full_video_qa_replacement` wrote new report, old report not overwritten. Root identified PID48118 as oldpureQAfcntl+sleep1500holder and normally terminated its own orphan, no lockfile deletion/renderer interruption. Subsequent realwork locks released.
- Current delivery/README point unique3ac2newfilm, old07eddelivery archived unchanged. RC010 new18.4–21.2trueupperidler hold covers18.57–20.94caption; actual20s encodedframe checked; original07edgap retained only there. Formal full101s human realtime/listening/wordalignment/causal experience still required; source upperguideanchor/variant/chainbaselinegap and stageedge/wordingP2 retained. No newTTS, other episode or platform action.


### Agent task-based model configuration — 2026-11-01

- 13 role TOMLs parsed: Sol5/Terra7/Luna1; root model, max_threads4, sandbox, TTS and media untouched. Updated AGENTS and workflow with task routing, precedence-safe upgrades, ownership/repair-count preservation and independent QA.
- CLI0.166.0; tool definitions reloaded. Actual read-only director/script/audio trials completed. Session turn_context confirms gpt-6.1-sol low / gpt-6.1-terra low / gpt-6-luna medium. All three extracted identical correct facts from the same existing EP04 report; no new media acceptance.
- Evidence, exact session IDs, input SHA, bounded timing/token comparison and limitations: [agent model validation](agent-model-validation-2026-11-01.md), [usage metadata](agent-model-usage-2026-11-01.json). Main-thread token attribution unavailable; no cost/savings claim.
- TOML/schema/count/concurrency and obsolete-rule checks PASS; git diff --check PASS before this append, rerun on final tree. Documentation/config-only: no production unittest/render/CAD/provider calls needed; no media playback/listening or full production-quality benchmark claimed.

### Luna-first agent routing — 2026-11-01

- User-authorized optimization supersedes the earlier Sol5/Terra7/Luna1 default mapping. Current 13 TOMLs: Luna8 (director/visual/editor/video_qa/audio_qa/research/growth_analyst/audio), Terra5 (creative_director/script/audio_director/audience_qa/audio_appeal_qa), Sol0. TOML parsing, expected model counts, role names, absence of fixed reasoning settings and unchanged max_threads4 PASS.
- AGENTS and workflow now route deterministic checks to scripts, routine execution and technical QA to Luna, expression/audience judgment to Terra, and only evidenced complex problems or reasoning failures to explicit Sol escalation. Avoid default-entry model omission inheriting root Sol; preserve unique ownership, independent QA, repair counters and acceptance thresholds. Quality regressions trigger scoped escalation rather than permanently switching an entire role to Sol.
- Runtime role definitions refreshed in this session. New research read-only trial `/root/luna_routing_check`, session `01a194dd-89bb-7852-a257-c86dbf5b4d0a`, independently confirmed counts and escalation text; session JSONL `turn_context.model` is `gpt-6-luna`. This validates one newly created role, not all roles or supplier internal routing. Existing agents/root retain their original models.
- Historical model-validation report annotated as superseded; original measurements preserved. No media, TTS, sandbox, root model, concurrency or production assets changed. Configuration/docs checks only; no production tests, renders, provider or perceptual-quality benchmark required or claimed. Final git diff --check PASS.

### EP04 grey tube repair — 2026-11-01

- User scope: repair the grey head tube in the current `3ac2fd…445a` review film; no new narration, other episode or platform action. Stable issue `EP04-TUBE-001`, two geometric repair rounds. Original media, all candidates/archives and the 177-frame interrupted compression75 full attempt are preserved; previous current records are snapshotted in `series/3d-printer-v2/episodes-current/EP04/delivery-history/tube-repair-v1-before/`.
- Research independently traversed the source STEP occurrence n01683 (`4x3mm_PTFE_Guide_Tube`), verified placement, valid one-solid positive volume 3862.635749 mm³ and independent STEP export. Actual upper attachment remains unknown; no invented anchor. New swept tube is explicitly a teaching representation. Source and investigation: [source review](../series/3d-printer-v2/episodes-current/EP04/research/tube-repair-v1/source-review.md).
- Round1 removed the85s kink/flap but independent QA found endpoint seams at0/95s. Round2 uses parallel transport of cross-section normals and a smooth constant-length centreline. All3030 numerical checks, four watertight/winding-consistent single-component positive-volume STL reimports and actual native keys/local clips are recorded in [production report](../series/3d-printer-v2/episodes-current/EP04/visual/tube-repair-v1/production-report.md). These are not contact, collision, manufacturing or dynamic simulation certification.
- Final frozen task `aad925a3ebe8fb8b96e929ce2aa905c1ac2c6c07d98a5aa5fe49723863229529`: 3030 fresh native1080×1920@30 frames,101s; all PNG signatures/full-chunk CRCs/dimensions/per-frame SHA verified,12 sources+43 inputs unchanged. Frame manifest SHA `7bbcbdb616c21983132cb62c8f5a779cbbc80f3992074af67684878bf5d24000`; actual render3265.496s and18,886,826,280 frame bytes. No cross-version frame mixing.
- PNGcompression75→0 is a separate frozen encoding change, with actual independent same-RenderResult decoded RGBA equality. Across separate render calls, three keys are exact and85s differs at11 non-tube pixels by≤1/255; original same-compression repeat control also differs at23 pixels. These differences are preserved, not reported as four-frame exact equality. All other geometry/motion/camera/lighting/material sources and dependencies are unchanged. Independent association: [encoding review](../series/3d-printer-v2/episodes-current/EP04/qa/tube-repair-v1/encoding-v5/review.md).
- Final [review-only MP4](../series/3d-printer-v2/episodes-current/EP04/editor/tube-repair-v1/full-lossless0-v5-review-v1/EP04-914-XY-Z-tube-repair-lossless0-v5-review-v1-review-only.mp4) SHA `43854b0cb55c5b720b4335e7f328c1fc1659127d41cadfe7c2b4b08b76e72b45`; encoded1080×1920@30 H.264/AAC48k,3030 frames/101s; ffprobe and full AV FFmpeg decode PASS. Locked original mix, Kai100.992s,49 single-line/nonoverlapping captions≤20 characters and timeline preserved. Independent new/old decoded AAC PCM is byte-identical:9,695,232 bytes, SHA `46b1805a6bfd62c1be85ddb98b8a28f53369fe572ea1a625c041095fe282d88c`.
- Same-final independent reports: AudioTechnical JSON `cd551e7bc44fbe1bad5bc7ac3478279ea2895e6ddd93b4ee24bab21a6ef00fec`; AudioAppeal MD `805f9f23a0e76c912d60931dbd13dfd5e51826d602f9be6eba200740979a295c`; Video JSON `9f8e0416aa03a71e27240f919c2788ca98471f09a085e7e582dd0baecc26cd8e`; Audience JSON `885c5e92de5c49bd74d23c6056e6a32022a02e73cd07a23279eb9ad881f198c9`. Links/hashes in [current delivery](../series/3d-printer-v2/episodes-current/EP04/delivery-current.json). Video QA inspected four native encoded keys plus28 global/neighbor samples and associated394 ordered local thumbnails/four paired encoded samples. It verified sampled85s kink/flap and0/95s seams repaired, with no newly established visualP1 in inspected coverage; whole motion is not certified. Historical QA002/004 remain at their original versions.
- Retained P2 `EP04-TUBE-LABEL-P2-001`: at95s the top beam obscures the small teaching label; other inspected views are readable. Audience QA saw no static evidence that this blocks the main lift explanation, but phone-scale realtime notice sufficiency remains unverified. All four reports remain NEEDS_REVIEW/null: full101s realtime viewing, listening, word alignment and semantic/causal synchronization are not established. Existing FULL-AQ-01…04, source-upper-anchor/chain/variant, wording and stageedge limitations are retained. The project video tool's audio-score schema mismatch (`audio_sha256` versus `subject.sha256`) is preserved as a tool limitation, not a media SHA failure; no tool or old QA report was rewritten to force a pass.
- Project unittest discovery:85 tests PASS in11.010s. Producer syntax/pipeline checks, JSON/hash/link-scope validation and final `git diff --check` apply; no TTS/provider/publication calls. Current delivery/README/Director records point to43854; old3ac2 media and prior-record snapshot hashes independently verified. Formal acceptance remains separate from this completed repair-review delivery.

### EP04 user acceptance — 2026-11-01

- User watched the current tube-repaired film and stated “我看了，已经满足条件”. Recorded USER_ACCEPTED for MP4 SHA `43854b0cb55c5b720b4335e7f328c1fc1659127d41cadfe7c2b4b08b76e72b45`; [immutable acceptance record](../series/3d-printer-v2/episodes-current/EP04/user-acceptance-tube-repair-v1.json). Exact viewing/listening duration and device were not supplied.
- Current delivery/Director/README updated; pre-acceptance metadata snapshotted. Independent QA reports/null scores, source limitations and P2 label occlusion remain unchanged; user acceptance does not fabricate specialist scores or authorize new production/publication. Metadata-only update: file/SHA associations and JSON/link validation apply; no render, TTS or repeat media tests.

### EP05 final local A/B — 2026-11-01

- Final local preview task `task-b7ca1910671567e32e9e` reuses the EP03 Eevee scene/style and pinned STEP branch. A SHA `1b6125cc790f0e42925acb60776e419b3636c6a9dd59e6c2f24ebeea7959c2f3`; B SHA `8ddc4c457104ce49c61d7b0e79f58edc62894b7b606a79b91a8c33544ddeb2f4`. Both are H.264 1080×1920, 30 fps, 120 frames/4 seconds, intentionally silent; ffprobe metadata and full FFmpeg decode passed. `render.lock` was released after render completion.
- Independent Video QA report [local-ab-v2](../series/3d-printer-v2/episodes-current/EP05/qa/local-ab-v2/video/review.md) SHA `63e2abe3a331e9375823d7f60fc3490ef337a77f5e6e9f4591d50f9164bd6697` decoded encoded B frames 1/18/27/93/111/120 and verified the caveat, callout margins and subject clearance at those boundaries. It confirms camera push/lateral move while STEP parts remain still. This closes `EP05-LOCAL-LABEL-001` for this version at attempt 3; it does not verify actual thermal paths or mechanical operation.
- Independent Audience QA report [local-ab-v2](../series/3d-printer-v2/episodes-current/EP05/qa/local-ab-v2/audience/report.md) SHA `4f7799b40f7947bcae2fcb46360068e2451b7119f2d13e9cfe4b01eb6af55660` checked five encoded time samples at 360×640. It found the labels complete and the caveat legible but small in static scaling; real-time playback, device readability and appeal scores remain unverified/null. The four-second opening is scoped as a question hook; whether the full film pays off heat isolation and the two cooling purposes remains open.
- Source mapping is limited to the selected Stealthburner body and fan occurrences. The detached graphic says `通用原理示意，非该模型剖视`; it does not establish a hotend assembly, fan-to-path correspondence, airflow, heat flow or operating state. The 90.144-second Kai narration remains technically decoded but independently unaudited by listening; sentence/word alignment and all 49 subtitle times are null. Full episode render/editor integration has not started and remains held. Status is `NEEDS_REVIEW`, not formal acceptance; no user approval or publication is recorded.
- Documentation/record update only: preserve the concurrent EP04 acceptance entry above. Applicable checks are JSON parse, paths/hash associations and `git diff --check`; no tests, new render, TTS or provider request were run in this record update.

### EP05 filetrans word-time candidate — 2026-11-01

- At the user's direction, used `/Users/lmj/yuntan/esp32/myna-server/tools/skill2api/skills/transcribe` with one `qwen3-asr-flash-filetrans` request (`--words --srt --language zh`) against the existing narration; no TTS or follow-up provider request. Local source MP3 SHA `ddbec4457bce33a23b9d589236dd7bf18b71af81899fb7fc50132133eea567a`, source text SHA `0e66e15dfcf002511aa341d16478fef5bffca0a1c363cd1e63c7d332a5892b37`, duration 90.144s. Task ID `f8d44d0a-54cb-435f-a5b6-1276858a4034` matches submission/completion; terminal status `SUCCEEDED`.
- Raw JSON [filetrans-v1](../series/3d-printer-v2/episodes-current/EP05/script/measured-v2/transcribe-filetrans-v1.json) SHA `6a61e3dca95896525270d79290b8043c31229c78ae69c2181c27a2b623a85152`; provider returned 13 sentence segments and 451 per-character word-time entries through 90.100s. Audit found monotonic ordered times, no overlap or reverse order, 10 zero-duration entries, 85 inter-entry gaps totaling 20.580s (maximum 0.900s). Source and ASR normalized text have equal length; five substitutions are homophones (`地/的`, `再/在`, three `形/型`) and remain unconfirmed. The raw response does not itself contain the local source hash; the exact local file path/hash were checked around this single invocation.
- [Candidate captions](../series/3d-printer-v2/episodes-current/EP05/script/measured-v2/candidate-source-v2.srt) SHA `c8455f158e3319b9f72c1d9598a2c83ced62d966e13ad5adfc40d914da8ee838` has 48 single-line cues, maximum 19 characters, and no overlap. This maps the recognized per-character boundaries onto the locked source wording without scaling times; it is ASR timing, not forced alignment or listening confirmation, and remains unapproved for final burn-in. Full audit and reproducible method are in `script/measured-v2/filetrans-handoff-v2.md` SHA `cd48a57fa5497d1d07d8a01ec3ac1235a6822c5876a4d5cc00aabfe1503412c6`.
- The selected STEP/cache has no source-backed teardown order, fan-specific rotation axis or separate 4010 rotor; see [motion feasibility](../series/3d-printer-v2/episodes-current/EP05/research/fan-motion-feasibility-v1/report.md) SHA `c38956e75beef8a08f3fd8885c5d8912904b563ecfe9029f1fda6bbbfea9187d`. Visual production is limited to static source geometry plus a clearly detached generic schematic. Independent audio QA/appeal still have no actual listening capability and retain `NEEDS_REVIEW`/null scores. A new 0–18.88s causal preview A/B is in progress; full render has not started.

### EP05 causal preview continuation — 2026-11-01

- Candidate 3 task `2294a1739bd42af04370` produced A/B files using the pinned EP03 Eevee scene, STEP occurrences, locked narration and ASR-timed caption excerpt. A SHA `22439af83b75f67c606530630fff1bf78b58108264f6180f746a04f5b7df3843`; B SHA `245f833b372862dce9de2735e7c27a57c92993b8eb8294b4653e9319d5f56bea`. Both independently probe as H.264 1080×1920@30, 566 frames/18.866667s, with AAC mono/24kHz; full audiovisual and audio-only decode passed. Decoded audio PCM matches across variants. The original render command exited 1 after media verification because caption contact-sheet assembly raised `KeyError: cue`; `technical-verification.json` and the contact sheet were not produced. Evidence and exact scope: [technical addendum](../series/3d-printer-v2/episodes-current/EP05/visual/ep03-reuse-EP05-v1/causal-preview-v1/task-2294a1739bd42af04370/technical-completion-addendum.md).
- Independent Audience QA report [causal-preview-v1](../series/3d-printer-v2/episodes-current/EP05/qa/causal-preview-v1/audience/report.md) SHA `c0e46637066c4d6430766f3d318f628879d7a61bfe27e6d39401b539740b6051` is `NEEDS_REVIEW`, with perceptual scores null. It identifies a P1 semantic/action concern around “打开工具头”, notes the B generic frame extends beyond both encoded edges and overlaps the subject at 04.000s, and cannot independently read the complete thermal cause from static samples. I inspected native B render frames 90/120/150/255 (3.000/4.000/5.000/8.500s): the STEP body remains present; the over-wide generic outer frame crosses the image and overlays the body at 04.000s. This is a frame-level observation only, not realtime or audio-sync acceptance.
- Creative Director prepared an unrendered alternative at `creative/causal-preview-v2/rework-direction.md`, SHA `33122c8a59e04902e49ff5980f436f3c27f1f04d67f7ad143cc2259416c35f37`: a smaller detached generic material-path schematic, with both purposes previewed at the first “两路冷却” mention and deposited-plastic detail retained for its later narration. This changes the current candidate timeline's “do not show deposited-plastic cooling early” constraint and needs Director/Script review. It also does not by itself resolve the locked phrase “打开工具头”. It is not approval or render authorization.
- Independent Video QA report [causal-preview-v1](../series/3d-printer-v2/episodes-current/EP05/qa/causal-preview-v1/video/review.md) SHA `230c8b9b1ec52e2ec5ca858360b12ca16fc690f9696a4cedec1cba9f8e6ff49c` sampled the exact encoded A/B files, including B frames 90–233 at roughly 0.2-second intervals. It confirms the STEP body/fans stay assembled while the detached generic shell moves under the “打开工具头” caption (P1 attribution concern), and the B outer frame crosses both edges and overlaps the model around 3.97–4.57s (P1 layout concern). It found the source-caveated generic diagram insufficient to establish the actual source hotend/thermal path or both cooling mechanisms. Technical/video QA is complete for this local scope; realtime playback, listening, forced alignment, phone playback and audience comprehension remain unverified, with scores null.
- Script review [causal-preview-script-review-v1](../series/3d-printer-v2/episodes-current/EP05/script/measured-v2/causal-preview-script-review-v1.md) SHA `710c569442d21ff5fdd1711bbbb5bab155c5c018b3df907374d1f72bc63f2501` finds that previewing the lower deposited-plastic target at the opening conflicts with the existing first-introduction point around 43.52s. It supports only an abstract two-purpose hint at the opening and recommends leaving that target out until its narration. A generic diagram reveal can accompany “打开工具头” as a teaching presentation, but does not establish the source STEP assembly opening; actual same-version audience playback/listening must assess residual ambiguity.
- Director issue ledger keeps `EP05-CAUSAL-SCHEMATIC-001` open at three candidates and adds `EP05-CAUSAL-ATTRIBUTION-001`; neither finding reopens or resets the separately closed `EP05-LOCAL-LABEL-001` at attempts 3. Creative proposal `creative/causal-preview-v2/rework-direction.md` remains unapproved pending adjustment to the existing timeline constraint. The three-round issue limit is reached, so no fourth automatic preview repair/render is started. Full-episode rendering/editor integration remains held pending an explicit user decision on any further manual revision. Narration listening, forced alignment, final captions, later second-cooling-path payoff and final-hash QA remain open; status `NEEDS_REVIEW`, not episode acceptance. No new transcription request or narration change occurred in this continuation.
- Documentation/record update only: existing EP04 acceptance and historical EP05 entries preserved. `git diff --check` applies; no CAD, rendering, tests, TTS or transcription request was run for this record update.


### Agent continuation and task routing optimization — 2026-11-01

- Clarified Director decisions within existing authorization, child-to-Director escalation, local A/B decision ownership, and one-time reporting of unchanged capability gaps. Separated review-version delivery, user acceptance and formal independent QA; preserved locked assets, explicit preview holds, known blocking defects and repair limits, including existing EP05 limits.
- Kept all 13 role models, root-session model, concurrency and sandbox unchanged. Set the eight Luna roles to explicit medium effort; documented direct Sol/high routing for evidenced complex tasks without requiring an initial failed attempt. Terra roles retain existing settings. Current tool role metadata exposes the new Luna effort settings.
- PASS: parsed project config and all 13 role TOMLs, checked required fields and unique names, verified eight Luna effort settings and local links in AGENTS/workflow, and ran git diff --check. Existing validation entries were preserved.
- Documentation/configuration change only: no video production, provider calls, agent smoke dispatch or end-to-end render was run. Behavioral reduction in questions and media production success remain to be measured on an authorized task; no formal QA scores claimed.


### Evidence-based role upgrade and pre-synthesis checks — 2026-11-01

- Session 01a1952f showed premature narration freezing, unsupported action wording, repeated layout repairs and no completed EP05 film. Updated director/visual/editor/research to gpt-6.1-sol with explicit low effort at user request; five Terra and four Luna roles remain. Root-session model, sandbox and concurrency are unchanged.
- Added core phrase-to-visual feasibility before first synthesis, provenance for approval/lock claims, bounded source supplementation when STEP lacks joints, and early Terra/Sol routing for expression/implementation root causes. Existing approved audio, editorial holds, issue IDs and exhausted repair counts remain intact; no EP05 render or provider request was authorized by these configuration changes.
- Validation PASS: 14 TOMLs parsed, 13 unique roles and required fields, four Sol roles all low, local document paths, working-tree and cached whitespace checks. Tool role metadata reflects Sol/low. A real read-only Sol/low child inspected role/workflow/AGENTS consistency; it found one Research-default wording conflict, which was corrected and independently rechecked. This was configuration verification, not media QA or an end-to-end production test.
- Existing index/ambient changes were preserved; no staging or commit performed by this task.


### EP05 continuation recovery decision — 2026-11-01

- Live SHA-256 checks match the recorded source STEP, occurrence cache, EP03 baseline scene and Kai narration. Independent Creative Director prepared [a concrete recovery proposal](../series/3d-printer-v2/episodes-current/EP05/creative/recovery-decision-v1.md): exact local narration replacement and a distinct separated layout. This is a proposal, not media acceptance.
- Existing P1 findings, three exhausted schematic repair attempts, archived assets and full-render hold are preserved. Await explicit decision on the exact audio change and further local repair; no synthesis, rendering or platform action performed.
- Documentation/record checks: JSON parse and git diff --check; no code or CAD changes, so runtime tests/renders are not applicable.


### Stage-based agent routing refinement — 2026-11-01

- Main thread is the sole coordinator; Sol/low is recommended but the active root model is not changed. Director child is now an explicitly requested read-only adviser, with conflicting production/ledger permissions removed. Visual and Editor remain Sol/low and reuse their existing agent across related versions. Research returns to Luna/medium for bounded extraction; complex source/mechanical questions route directly to explicit Sol/low default with Research duties. Five Terra roles and required independent QA remain intact; 13 roles are responsibilities, not mandatory concurrent processes.
- Added six stage exits covering source feasibility, key local action, synthesizable text, measured audio/timing, full production, and review delivery/formal acceptance. Capability gaps are checked once per unchanged asset/capability; repairs require a root-cause hypothesis and minimal observable validation. Added outcome measurements for the next comparable authorized task; these are workflow rules, not a programmatic state machine. Existing locks, explicit holds, P0/P1 gates, specialist thresholds and exhausted repair counts are unchanged.
- PASS: all 14 TOMLs parse, 13 unique required role definitions, three Sol roles explicitly low, Research Luna/medium, five Luna/five Terra defaults, unchanged max_threads=4 and no root-model setting, local document paths, git diff --check. A real read-only Luna Research child successfully checked simple/complex research routing and unchanged listening-capability behavior against the workflow; no contradiction found.
- Static walkthrough: new narration requires key-action feasibility before synthesis; visual-only changes retain approved audio; full production waits for relevant local defects/usable timing; missing perceptual capability permits only the applicable review delivery; known P1/explicit holds still block dependent production; an exhausted repair count remains exhausted after model/phase changes. This is rule validation, not media or end-to-end production acceptance.
- No rendering, TTS, ASR, platform requests, QA score changes, staging or commit. Prior validation and ambient edits preserved.


### EP05 authorized recovery continuation — 2026-11-01

- Continued existing `recovery_authorization_v1`, preserving exhausted original attempts=3, both open P1 issues, historical assets and the full-film render hold. Director inspected actual native frame347 of frozen `task-6c7f49a1df29de5dfa80` and wrote a local-only proof gate; Visual owns serialized rendering. This is implementation authorization, not user media acceptance.
- Reused both completed Kai replacement MP3/WAV pairs (6.216s and 4.776s); actual hashes and four full decodes verified, no TTS/ASR request repeated. Independent Audio QA and Audio Appeal QA wrote exact-input reports under EP05 `audio-qa/recovery-v1/` and `audio-appeal/recovery-v1/`: actual listening unavailable, NEEDS_REVIEW/null, not a verified speech or final-mix verdict.
- Script provided explicitly provisional PCM-gap caption candidates, not forced alignment. Editor assembled `editor/recovery-v1/assembled-review-only.wav`, SHA256 `04a6af2ff36da833ffea866680a9141019d4aa0ed3edc0c0311538d7c5e3296b`, measured 92.636s. Three retained original PCM segments and two replacements are byte-identical to inputs; WAV full decode PASS. All 48 caption candidates are single-line, max16 characters and nonoverlapping. This verifies data/timing contracts, not listening or audiovisual correspondence.
- Director/timing JSON parse and `git diff --check` passed. No new CAD geometry, platform actions, staging or commit. Local visual/mixed delivery and independent same-version visual/audience review remain in progress; the full-film branch stays held for P1 review.

- Local recovery delivery completed: `editor/recovery-v1/local-narration-caption-review-only-v1.mp4`, SHA256 `642eea28f0a6bcaeb2dc24d81127ac7c8fbd8a4ab604b80a5cc11d138eb5d4c8`, native/encoded1080x1920@30,566frames,18.866667s,H264/AAC; full decode PASS. Actual subtitle inkY1486-1531;566 frame glyph-mask and57 boundary-neighbor checks PASS. No foley. Same-local-hash independent Video/Audience and two final-local-mix audio reports remain NEEDS_REVIEW/null. Director closes only original physical cropping/overlap for this local hash; unsupported explicit opening phrase removed, but attribution interpretation remains OPEN pending realtime playback/listening. No full-render release.
- Full-source preparation is separately frozen as `visual/recovery-full-v1/task-d543ae23d47d4f384d08`:15 native keyproof frames (not a movie), planned2780frames/92.666667s, same CAD caches and fixed split layout, retimed softening and later separate deposited-material principle target. Director inspected native proof1666; sparse visual evidence does not replace motion/thermal/semantic acceptance. No full render, new CAD, TTS/ASR or platform action.
- Final verification PASS: film-audio unittest discovery2tests, splice synthetic sample-exact/guard fixture, real PCM/caption verifier and git diff --check. Delivery and precise unresolved question recorded in EP05 delivery-current.json; source assets, archives, original attempts and ambient edits preserved.


### EP05 series realignment from EP01–EP04 — 2026-11-01

- User rejected the detached-chart direction and requested comparison with EP01–EP04 before continuing. Director and Creative inspected actual encoded frame samples from the selected four films and current EP05:60 retained samples, source paths/hashes/probes in `EP05/series-realignment-v1/references.json`. Four film hashes match their current selected records. This is sampled static evidence, not realtime viewing/listening. EP04 current hash43854b0… is user-accepted despite its historical review-only filename; formal specialist scores remain separate.
- Research downloaded/actually inspected official Stealthburner assembly pages39/41/53/55/56/66/67 and freshly imported9 existing valid positive-volume source STEP exports. Corrected the previous overstrong sibling-branch exclusion:Revo front/rear are the nested cartridge and Stealthburner_Body is the external fan cowl. Official CAD was reference-only and never replaced production geometry. Source facts/matrices/hashes are under `research/series-realignment-v1/`; original reports preserved. A measured n00124 solid4 surface point replaces the incorrect wire-inclusive bounding-box leader target; no production solid was split/exported.
- Visual actually opened EP01/EP04 scenes and EP03 stage, then recorded selected baseline hashes and minimal reuse in `visual/series-realignment-v1/minimal-reuse-plan.md`. Existing EP04 context/stage/light/material/camera and EP01 reveal method are reused;914 source occurrences retained and15 meshes refreshed from corrected cache. No whole-machine reconstruction.
- Geometry proof rounds1/2 corrected cowl/front projection overlap and source-referent labels; one separate timing correction reveals the lower body by8.4s before the original8.48s speech candidate and postpones front return until19.4s. Stable7-key proof `task-5ca0ca1e9b2da31c867b` independently checked by Video/Audience QA with no known sampled P1 blocker; Director viewed contact/native253 and released only a new24s/720frame local render. Static evidence does not certify intermediate collision/continuity, word alignment or listening. Original schematic attempts3 and prior recoveryround1 are unchanged.
- Editor retained original Kai decoded PCM prefix19.32s byte-identically (candidate low-level cut, not listening/forced alignment) and14 original candidate captions(max13,nooverlap). No TTS/provider retry. New local syntheticfoley is tied to actual source-module movement events; audibility is reviewed separately from synchronization and technical peaks.
- Reference extraction script py_compile, film identity/sample-record checks and git diff --check PASS. Local render/mix/encoded glyph/full decode and same-version QA are still in progress; no full-film render or platform action.

- Local B24 completed as `editor/series-realignment-v1/EP05-series-realignment-local-v1-review-only.mp4`,SHA256 `56c75e2f22dbe47202f86115bce59ec292c56a4180f74fa783fe95e2446193e5`:720newnative1080x1920@30frames,24s,H264/AAC,fullAVdecodePASS. Render733.287s,total751.077s,lockreleased. Newrunner mechanicalcode-equivalence/diff links stableproof5ca and newlocal6f6;no mixedframes.
- Director viewed actualencoded0/3/8.4/12.8/18.5/23.9s samples;independentAudience exacthash12samples support returntosame-machine style/no newdefiniteblocker in coverage. Formal realtime/listening/phone/wordalignment and complete two-target90s payoff remain unverified;no score/useracceptance claimed. Both newhash finalmix independentaudio reports remain NEEDS_REVIEW/null.
- Editor actualAAC -26.92LUFS/-4.51dBTP;14 singlelinecaptions,max13,nooverlap. All720decodedglyphcrops+69boundaryneighborframes0maskmismatch,inkX217-833/Y1486-1531. V2isolatedfoley activeRMS-39.68dBFS comparedsamewindow EP03-37.68 and V1-56.63;voice unchanged and staticfoley0. Phonepresence/notmasking still needs actual listening.
- FinalPASS:Visualpipeline12unittests(expected simulatedSIGSEGV failurepath,notrenderfailure),film_audio2unittests,py_compile,realPCMandcaption/event/sourcehashchecks,JSONparse and gitdiffcheck. Editor agent503 CPUoverload was orchestration-only;continued existing output checks with no reencode/TTSretry. Olddelivery/source/attemptcounts preserved;newdelivery-current points onlyto24slocal,notafullfilm. No newCADconstruction,providerrequests,platformaction,stagingorcommit.

- Same-file independent Video QA finalized: `qa/series-realignment-v1/video/local-video-review-v1.md`, SHA256 `e412ab452b201df7842c01b02808f5e99b8cbd9876b94d0adada27a3f9112b69`, linked to mixed MP4 `56c75e2f…6193e5`;18 encoded event/neighbor samples plus caption/source associations, full decode PASS. Audience and both final-mix reports link the same MP4. All perceptual scores remain null. The formal90s gate does not fail this explicit24s local preview. Director selects this mechanism-led local over the rejected chart based on sampled evidence, without claiming user acceptance, complete two-target payoff or full-motion/listening certification. Full EP05 has not been rendered.


## 2026-11-01 EP05 approved-series full continuation — render release

- User accepted mechanism-led 24s preview SHA256 `56c75e2f22dbe47202f86115bce59ec292c56a4180f74fa783fe95e2446193e5` and instructed completion; original Kai90.144s retained without synthesis.
- Minimal full adaptation reuses original scene/cache, extends two-target explanation, moves teaching return to66.16–69.04s, and explicitly labels bed-material cue; source static tip-bed gap27.009293mm is not presented as active printing.
- Canonical issue `EP05-AUDIENCE-PROOF-001` / Visual alias `EP05-FULL-MATERIAL-LABEL-001` retains rounds1–3. Round3 actual four ASS overlay proofs independently reviewed by Video/Audience: source marker touches visible material upper edge, dark-bed label is legible and clear of subtitle band1480–1540. Scoped proof resolution is not full realtime/listening acceptance.
- Full task `task-6557f72a447828630492`: manifest `214b7f5ed9b7183a4dd29a01b6cb61882d616ac9ce51708f958b167b42342138`; proof report `af06df3bbff225606ab660f3c5bb275bd214ab2f09d28c8c5b3037ecc624fb3d`. Director matching release saved; serialized2705frame render started; full movie not yet asserted complete.
- Applicable unittest discovery: `test_pipeline.py` 12 tests PASS (mock SIGSEGV failure-path output is expected); `test_film_audio.py` 2 tests PASS. `git diff --check` PASS before this append.
- Fixed full mix SHA256 `db0b6444f7807d68de3d5b1d1ccd038e7169d2f571ef68c90e6f7cfd9efa32c5`; full WAV decode passes, approved19.32s mixed/foley PCM preserved, original voice reconstruction error0. Independent Audio QA/Audio Appeal lack actual listening capability, remain NEEDS_REVIEW/null; no new provider request or fabricated score.
- First full Video QA agent failed HTTP413 due media payload; independent replacement used small static images. This service failure is not a film defect or acceptance evidence. No platform action.


## 2026-11-01 EP05 complete series-aligned review film

- Final: `series/3d-printer-v2/episodes-current/EP05/editor/series-full-v1/EP05-series-full-v1-review-only.mp4`, SHA256 `e71cd9ce92cd841ef892542aefab43d336e8b8a08f61bf76240e485fdceab254`. Native and encoded1080×1920@30,2705frames/90.166667s,H264/AAC; original Kai90.144s retained, no newTTS. Final full FFmpeg AV decode PASS, independently repeated by VideoQA.
- All2705 encoded subtitle-band ink checks and269 boundary-frame checks PASS,0failures;48singleline captions,max19characters. Actual AAC−27.25LUFS/−2.96dBTP. Independent AudioQA decodedAAC correlation0.9999663 to frozenmix,8movementevents/staticfoley0 verified; no claim this proves listening or semantic alignment.
- Storage failure: disk filled during2200 write;2199valid PNGs preserved byte-exact in gzip after SHA/RGBA verification, truncated2200 retained as failed evidence. Only same fingerprint task recovered506frames2200–2705 using new archived recovery wrapper executing unchanged frozen scene. All2705 exact PNG byte sequences retained in `frames-lossless-gzip/`, full pose audit regenerated; no frame mixing, source change, historical asset deletion or other-project cleanup. Migration saved7,745,513,084bytes. Applicable recovery py_compile and12pipeline tests PASS (mockSIGSEGV test is expected).
- All580native opening frames compared to approved local:209RGBA identical,371 differ in at most40pixels/frame;global channel difference≤6/255,none>8. PNG bytes all differ. Side-by-side worst-difference contact shows no observable structural change; this is not claimed pixel identity or a proven cause of differences. Approved19.32s mixed/foley PCM prefix is byte-identical.
- Same-finalhash AudioQA,AudioAppeal,VideoQA and independentAudience reports associated in `delivery-current.json`; bounded static checks found no new known P0/P1. Material-label issue round3 closed only in checkedproof/finalsample scope. Seven P2 freeze candidates remain unconfirmed pending realtime contextual review. Actual full realtime viewing/listening,phone experience,word alignment and audiovisual semantic correspondence remain unverified; scores null/statusNEEDS_REVIEW. Technical completion and local user approval do not imply formal acceptance of this new full hash.
- Director inspected actual final12-frame encoded contact and native final-label crop. Prior delivery archived, current delivery points to fullfilm. No platform action, staging or commit. Final scoped JSON/file/hash/diff validation recorded by current session.

## 2026-11-01 无效临时数据清理

- 用户授权分析数据并清理无效临时数据。清理前目录分配大小约81 GiB，主要集中于series（73 GiB）和artifacts（7.1 GiB）；按逻辑大小PNG约58.64 GB、JPG约7.68 GB。大部分为生产帧及证据，保留。
- 非阻塞取得现有worker/render/production锁后，仅删除Git未跟踪、有对应源文件的Python字节码及.DS_Store，共514个文件、4,556,891字节（4.35 MiB）。不修改.venv、Git索引、场景、帧、音视频、CAD、来源、归档、任务或回滚证据。21个.blend1均与主文件不同，全部保留。
- 删除路径、大小和SHA256见[清理清单](cleanup-20261101-manifest.json)。其余89,976个文件的大小和mtime_ns前后一致（不是逐文件内容哈希证明）；Git索引SHA256前后一致。ps受沙箱限制不可用，未绕过沙箱；使用项目锁协调。
- 清单JSON解析及git diff --check通过；此次无代码或媒体修改，不运行单元测试、渲染、配音或新的媒体验收。保留本次前已有的validation.md修改，不暂存或提交。

## 2026-11-01 EP01–EP05 临时媒体清理完成

- 用户依次明确授权清理EP03/04/05大量临时数据、生成临时图片、临时视频与音频，再扩展至EP01/EP02。按旧任务版本删除生成媒体，保留最新交付、仍用复用基线/已批准局部、原始配音/付费缓存、CAD/场景/脚本、审批及QA文字记录。
- 删除36,636个文件，逻辑大小29,567,879,288字节；另3,758个PNG/PCM无损gzip归档节省13,520,670,574字节。合计减少43,088,549,862字节（40.13 GiB）；目录du约81 GiB→41 GiB，df可用约14 GiB→54 GiB。APFS快照/克隆可能使实际空间变化与逻辑统计不同。
- 按集删除及归档总节省：EP01约0.07 GiB、EP02约1.58 GiB、EP03约2.85 GiB、EP04约29.36 GiB、EP05约6.27 GiB。明细及精确数字见[汇总](episode-cleanup-20261101-summary.json)、[说明与恢复边界](ep03-ep05-storage-cleanup-20261101.md)及其链接的逐项清单。
- 验证PASS：36,636个删除路径均不存在；3,758个归档逐个核对压缩文件SHA256（迁移时已逐个解压核对原始SHA256）；五集当前视频、批准EP02片段及当前交付指针共10个文件SHA256不变。执行期持有现有项目锁；Git索引哈希不变。git diff --check通过。
- 清理旧媒体后，旧清单及冻结脚本中的部分历史路径不再存在。EP04旧baseline视频已删除，当前混音/拟音保留；归档脚本的旧baseline PCM对比不能原样重跑。重做旧实验需先由保留源文件重建，不承诺历史命令直接运行。当前帧gzip恢复方法及完整边界已记录，不改写历史报告。
- 此次无生产代码或成片内容修改，未运行单元测试、渲染、TTS或新的感知验收；未暂存、提交或发布。原有validation.md改动保留。

## 2026-11-01 artifacts 旧生成媒体清理

- 用户明确授权清理artifacts旧生成媒体。删除6,865个文件，逻辑大小7,268,149,697字节（6.77 GiB）：6,807张旧演示生成图片、56条旧演示/电钻/中文讲解视频、2条可由保留分段重建的拼接音频。
- 全部inputs/models/qa、场景及备份、renderer归档、原始配音/付费缓存、SQLite/日志/JSON/HTML/字幕、锁文件保留。1,394个保留文件前后逐项SHA256一致；打印机系列当前交付及批准片段哈希保持不变。Git索引哈希不变，持有项目现有worker/render/model锁，不改队列。
- 机器清单及恢复边界：[删除与保留文件哈希](artifacts-cleanup-20261101.json)、[说明](artifacts-cleanup-20261101.md)。旧HTML与脚本引用的已删除演示视频不再存在，若重做须重建媒体；不承诺历史演示直接恢复。
- 清单解析、删除路径不存在验证及git diff --check通过。本轮无代码/当前成片修改，未运行单元测试、渲染、TTS或新的感知验收；未暂存、提交或发布，保留此前工作。

## 2026-11-01 完成作品的中间数据最终清理

- 用户先要求继续深度清理，随后明确：“视频都已经完成了，中间的数据没有必要留着。”据此调整保留策略，不再保留已完成制作的渲染帧、压缩帧、旧局部预览和派生缓存。此指令不自动改写历史QA/批准状态。
- 前置深度阶段删除1,872个旧A1/A2生成图、局部导管测试帧及旧proof场景，共3,479,114,276字节；旧guide.npy归档当时节省690,340,739字节。用户进一步明确后，该归档亦作为中间数据删除。
- 最终阶段删除24,911个文件，共25,931,115,599字节：包括五集剩余渲染帧/帧包、旧/局部/静音视频、派生数组、PCM分析、混音/拟音及冗余场景快照。两阶段净逻辑减少30,100,570,614字节（28.03 GiB）。项目du约34 GiB→5.8 GiB，df可用约61 GiB→90 GiB（APFS实际回收可能不同于逻辑大小）。
- 六个交付/风格MP4与七个最小场景前后SHA256一致；全部保留文件逐项SHA256一致，删除路径不存在核验PASS。执行期间持有既有项目锁，执行器前后Git索引SHA256一致。外部已暂存的先前清理记录保持原样，本轮不暂存/撤销/提交。
- 记录：[本轮汇总](completed-episodes-cleanup-summary-20261101.json)、[最终阶段逐项删除与保留哈希](completed-episodes-intermediate-cleanup-20261101.json)、[前置深度清单](deep-cleanup-20261101.json)、[保留范围与不可恢复边界](completed-episodes-intermediate-cleanup-20261101.md)。早期清单是阶段快照；旧帧归档恢复指南不再适用于已删除的包。
- 清单解析、当前成片/场景哈希、删除路径及git diff --check通过。本轮无生产代码或最终MP4内容修改，未运行单元测试、渲染、TTS或新感知验收，未发布。重新制作须重建中间数据，不承诺历史脚本直接重跑。


## 2026-11-01 — Session 01a195a8 workflow optimization

- Added `docs/production-preflight.md`, linked from AGENTS/workflow/subtitle placement: actual baseline comparison for continuation as well as new work, first-proof combined captions/labels/leaders, fixed-input handoffs, capability-gap reuse and completion/exception notification. Existing approval, holds, repair limits and independent acceptance remain in force; no new parallel episode ledger.
- Added read-only `scripts/render_storage_preflight.py`: largest representative stored frame × remaining frames × safety factor, plus adjustable encoding/copy temporary space and reserve, checked against target filesystem free space. Exit 0/1/2 = budget PASS / insufficient space / invalid input. No automatic renderer integration is claimed; Director must run and record it before full render/resume. Sample settings and transient disk use limit the estimate.
- Validation: `.venv/bin/python -m unittest discover -s tests` — 88 tests PASS, including three storage-budget tests covering largest-sample budgeting, existing-file accounting, insufficient space and invalid estimates. CLI synthetic-size smoke covered exit codes 0/1/2 and no file mutations. 28 local documentation links resolved; all `.codex/**/*.toml` parsed; `git diff --check` PASS. Test-suite simulated failure output is expected test coverage, not an actual render failure.
- No media/provider calls or production renders were performed. This is workflow/read-only-tool validation, not perceptual acceptance or measured token/cost improvement. Preserve pre-existing staged cleanup records and validation history; changes were not staged or committed.


## 2026-11-01 EP06 production preflight (in progress)

- User authorized EP06 production after public-reference and EP01–EP05 style analysis. Records: `series/3d-printer-v2/episodes-current/EP06/director-record.json`, `analysis/series-inventory.json`, `analysis/viral-research.md`, `analysis/production-decisions.md`. Existing staged changes preserved; no platform actions.
- Actual local full media hashes/ffprobe checked for EP01–EP05; Director viewed 2/15/45/80s encoded sample contacts for all five. This is static sample evidence, not realtime viewing/listening. Public references have four actual opening-time page screenshots and cumulative page metadata, not proven growth causality or full-film analysis.
- EP06 Research independently re-exported/re-read 46 valid positive-volume bed/support/frame occurrences with source path and transforms matched. Additional n00124 composite failed validity; precise tip/gap measurement is excluded. Existing EP04 scene opens with bed/support objects; baseline copy reused, no machine rebuild.
- Default sandbox Metal probe failed; scoped elevated read-only probe and source-scene inspection succeeded with existing sandbox configuration unchanged. Blender5.2.3LTS.
- Current unittest discovery: `.venv/bin/python -m unittest discover -s tests` —88 tests PASS in9.826s. Simulated Blender SIGSEGV output belongs to an existing mock test, not production render failure.
- Early visual proof identified bed support occlusion (EP06-SUPPORT-VIS-001); synthesis/full render held pending affected action review. Independent perceptual/word alignment scores remain null. More production validation will be appended when new media exists.

### EP06 measured narration and local preparation

- Kai/qwen3-tts-flash s1..s7 each succeeded once (85.272s). Added only s5b once after official generic first-layer fact check and actual same-space concept feasibility; original7 PCM unchanged. Current narration-v2.wav SHA256 `9aa6bbcb5ce7c207e9a9c372140fee0ee3624f669ee32011782b69404a92713b`:93.336s,2240064samples/24000Hz mono,all8segment sample hashes match,full decode PASS. Independent technical AudioQA and AppealQA reports preserve unavailable listening/null scores. Existing ASR plain-text association correction has only one same-sound 磁/瓷 substitution;7metadata-induced differences were not speech evidence. No provider retry/resynthesis.
- Two actual16s A/B1080x1920/30 silent clips480frames each full-decode PASS. A1 SHA `6c6c3f072c3f7f3868e390dec373e67d9632511006865a93d0beb90301752117`, A2 `5ab93dee4c999e6e58bc6ce64fc52179cfad192a9d489eb7d8c4f759bca02d1b`. A2 discarded after actual4.8s frame showed raised sheet clipping concept nozzle/line; no repair or further work on discarded A2. A1 chosen within authorized local decision. Actual614.484/616.259s render samples imply about1.282s/frame;full estimate~60min is not guaranteed.
- Editor actual ASS calibration and scene composites keep white glyphY1486–1531;one-time burn only. Layer-front-edge and label contrast repairs independently reviewed;EP06-SUPPORT-VIS-001 original3attempts retained. EP06-LAYER-CUE-001 attempt1 corrected14s magnet/plate mismatch;13native/13ASS and7encoded actual-PTS boundary proofs reviewed. Missing336/374 intermediate frames and all dynamic/perceptual evidence remain unverified. Reports under EP06/editor/overlay-layercue-v1 and qa/video/layercue-repair-review.md.
-45source-text captions are explicitly UNCALIBRATED_REVIEW_CANDIDATE:measured8segment bounds with character-weighted initial cues snapped within250ms to PCM low-energy candidates,not verified word alignment. Director permits review-only assembly;formal timing acceptance stays open. Global cue/action timing issue EP06-SEMANTIC-TIMING-001 first repair is now task-cc7b09ce93b411e48ed3,94actual proof frames before full render. Old renderer tasks retained immutable.

### EP06 final-mix-v2 technical association (2026-11-01)

Review-only WAV `series/3d-printer-v2/episodes-current/EP06/editor/full-v2/mix.wav`, SHA256 `0db7001c0483461c1962d9b6fd8e1c6727d402d1cc1ee48feeadd4c8746e531b`: independent Audio QA confirms full decode, exact mix=speech+synthetic-foley PCM equality, unchanged speech reconstruction 0 LSB, three action-event windows, zero clipped samples and true peak -1.44 dBTP. Reports: EP06/audio-qa/final-mix-v2/report.md and EP06/audio-appeal/final-mix-v2/report.md. No actual listening; appeal/masking/alignment remain NEEDS_REVIEW with null scores. Final MP4/AAC association pending. No publication.

### EP06 fixed-source full-render release (2026-11-02)

Task `0f34095b2f15d531973a`, frozen scene SHA256 `73697cee5183a74388c54198417a10744941b40d29a878366ea363b47e7b5b68`: actual 2801-pose audit and caption-free audit pass. Director viewed native fallback3frames, actual encoded3frame contact and1133 longest-caption proof. Independent `EP06/qa/video/route-static-independent.md` finds original cue14 P1 whole-frame occlusion not reproduced in those3static samples; dynamic acceptance remains open. Editor `camera-0f-proof-v1/handoff.md` verifies4actual ASS/H264 proofs and unchanged three mechanical-foley event associations. Root ran `scripts/render_storage_preflight.py` with actual0751/0825 PNG40 samples,2801remaining,1.25safety,6GiB temporary+2GiB reserve: required17180706630B/available92569600000B PASS. Director released review-only full rendering under existing lock; render/completion/final-media acceptance not yet claimed. Existing user-staged content preserved.

### EP06 final review-only AV delivery (2026-11-02)

Final `series/3d-printer-v2/episodes-current/EP06/editor/final-review-v1/EP06-full-review-only.mp4`, SHA256 `d13c6a558492d07238671d519db25e4c59ef86c010360f72ee302ec9719c7801`,36644029B: H.264/AAC,2801frames,93.366667s video; native and encoded1080x1920/30. Editor strict fullAV decodePASS; root independently rehashed file. Actual decoded58frames cover45candidate caption midpoints/layer-adjacent boundaries/route repair/longest15character line. Director viewed all5final contact pages; independent Audience checked58PNGs+45native-caption strips and found no new sampled static collision/causal contradiction/style drift. Independent finalAAC AudioQA full decode/24kmono/2240064samples and source mix correlation0.999973,residualSNR42.54dB,zero clipped,-25.89LUFS/-1.45dBTP PASS. Final Audio Appeal samehash report retains actual listening0/nullscores. Source/render/frame,ASS,mix,event association and frozen provenance in final delivery-manifest.json/freeze-index.json.

Status COMPLETE_REVIEW_ONLY / NEEDS_REVIEW; not formal sensory acceptance. Actual realtime motion, listening/foley audibility and sentence-level subtitle synchronization remain open;45candidate captions are not verified wordalignment. No publication. Root delivery.md local links check PASS; git diff --check PASS. Existing88unittest preflight PASS retained; no tracked application-code changes requiring unrelated rerender/provider calls. Independent VideoQA finalsamehash report pending at this entry; current later Director record is authoritative.

EP06 finalsamehash independent VideoQA completed: `qa/video/final-review-v1.md/json`, exactMP4 d13c6a558492d07238671d519db25e4c59ef86c010360f72ee302ec9719c7801. Independent ffprobe/fullAVdecode PASS;actual58frames/45captionstrips and original inspected boundary/route/longestcaption frames no reproduced sampled P1. 11automatic low-motion P2 candidates are not established defects;exactintervals in report for contextual/realtime review. Numeric formal scores remain null, NEEDS_REVIEW;no new render or provider call.

### EP06 user-requested real toolhead repair preflight (2026-11-02)

Issue EP06-REALHEAD-MOTION-001 attempt1 addresses original conceptual-orange-nozzle motion with static realhead and missing XY mechanical sound. Reuse plan in EP06/visual/repair-realhead-v1/reuse-plan.json: EP04 accepted131part head+106crossbeam+27/18chains+tube+9wheel helpers, original scene/material/captions/Kai retained. Source n00124 compound remains invalid; original solid0 independently reexported/reloaded valid668.275750629mm3, STEP SHA1a23e9a43cbf1e550ab3e78950d7d7a068273c2ac0919113e960eafa525bf851. Cone/endring/bore faces and mounted surface anchor verify lower source end;actual source bedgap27.009293mm, no fake extrusion/contact claim.

Actual8s48-56s encodedAB completed: B SHA c49d8070a8056e5b81a99134a6bc546b83e75a0a991d3b9bead43b26c9a1876f,240frames1080x1920/30 H264/AAC/fullAVdecodePASS;Director viewed A/B9framecontacts and1495/2090fullkeys. Truehead shell visible motion57.2px;orange substitute removed. Independent Video/Audience finite static scopes found no new establishedP1;small-tip occlusion recognition risk retainedP2. New speeddriven synthetic headfoley v2 WAV47a30cfa4de37eb99340a737b8fef5f3116dcd8109c78828524d0af8ebf9986a: independent PCM/source reconstruction0LSB,head only5movementwindows/stoppedhead0,finite smoothduck,0clip/-1.44dBTP PASS. Actual listening/realtime/no-pump/wordalignment scores remain null.

New full-task-dbdf3806e59559815455 preserves c6 all presentation source bytes;new entry+2801cache only. 47cachekeys at257sharedframes and49posefields exact_equal;new1495/2090decode pixels equal c6. Independent qa/video/realhead-full-delta-v1.md verifies sameimage hashes/1133static no newP1.2801pose/source914visibility/captionfree/tube audits completed, no former-task frame reuse. PNG40 actual3sample storagepreflight safety1.25+6GiBtemporary+2GiBreserve PASS17.760GBrequired/84.787GBavailable. Full repair rendering not yet started at this entry.


## 2026-11-02 EP06 床层/工具头穿插局部修复与整片放行

- 保留上一版 f6bfe840…，明确为已知 P1 返工版本；问题 EP06-BED-HEAD-INTERSECTION-001 attempt 1，其他 issue 计数不变。
- 选定局部 task475181efc9d182bd55d6：九床件先 Z+12mm/Y−310mm 移至机前，再分层；回装逆序。独立源重算及编码局部样点检查见 EP06/qa/video/bedclearance-independent-v1.md、bedclearance-local-encoded-v1.md。此为结构教学展开，不宣称维修顺序。
- 两段局部 B 1080×1920/30 H.264/AAC 严格全解码通过；字幕只叠一次。新混音 a0a3a315…ea352a0 保留 Kai 与头声，床声随六阶段动作重新对时；独立音频技术与观众静帧审查未确认新 P0/P1。
- full-task-0bede0b63d974439cabf 冻结源关联通过；全2801帧新渲，禁止跨任务混帧。实际存储预算需15.76GiB，可用68.66GiB，已放行。渲染/最终编码尚未完成，本条不记完成或正式验收。
- 实时观看、听审、逐词同步证据缺失，相关分数 null；局部静帧/源检查不能代替上述验收。git diff --check PASS；未改应用代码，不重跑无关测试。


### EP06 同版完整交付补记

- 全2801新帧渲染完成，render5033.38s，后处理45.85s；完整clean silent SHA21d50d9276e1dabbf791608413682b69ed9af57093bf8fc44c04394024f8ab1e。
- 最终带声字幕MP4 SHA0092bf1d3c02b10dee30090c07eb45756ee2ebcb30a4071b2d9856cd6c8d87cd，93.366667s，原生/编码1080×1920@30，H.264/AAC。独立hash/ffprobe/完整AVdecode PASS。
- 两类最终音频报告、独立VideoQA绑定同hash。AAC与新mix全片零延迟相关0.999972，满幅样本0；实际听审0，评分null。Director与独立专项QA均看过9contacts共104编码样点，含旧8–16s穿模窗、各回装阶段、45cue中点；在源+编码静态证据范围闭合BED-HEAD P1 attempt1。
- 所有914源件每帧不隐藏，45.41s归位后1438帧残差0mm。未混帧、未重配Kai；原字幕一次叠加。正式实时运动/听审/逐词同步仍NEEDS_REVIEW，不因技术完成填分。最终待审交付说明EP06/bedclearance-repair-delivery.md。
