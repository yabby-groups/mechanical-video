# Mechanical Video

当前方向：**拆开真实机构，讲清可见的机械因果**。以[六集当前规划](docs/printer-series-plan.md)为准：保留已获用户认可的 EP01/Kai 与现有 EP02，后续依次讲 XY 传动、四角升降、热端与两路冷却、热床支撑及第一层间距。打印机系列音色为 `qwen3-tts-flash / Kai`；旧十二集和固定八镜头模板不再作为新制作依据。

EP02 优化全片已生成，实时观看、听审及相关 QA 仍待完成，保持 NEEDS_REVIEW；规划不替代验收。旧批量队列继续暂停，历史素材及批准记录保留。正式集数至少90秒，短测试不算正式交付。
新版独立保存在 `series/3d-printer-v2`，旧版成片和素材保留。使用
`.venv/bin/python -m mechanical_video.cli remake status` 查看历史重制队列；[重制版说明](docs/series-remake.md)保留旧实现背景。现有 `remake plan/render/worker` 尚不读取六集新规划，不要用它重新生成旧计划或恢复批量生产。

## 《拆解一台 3D 打印机》原版系列（已被重制队列替代）

使用固定版本官方 Voron 2.4r2 CAD，共享装配模型、Ethan 普通话配音和工业视觉模板。实际可运行入口：

```sh
.venv/bin/python -m mechanical_video.cli series init --name 3d-printer
.venv/bin/python -m mechanical_video.cli series plan --season 1
.venv/bin/python -m mechanical_video.cli series render --episode 1
.venv/bin/python -m mechanical_video.cli series render --episodes 1-3
.venv/bin/python -m mechanical_video.cli series continue --count 3
.venv/bin/python -m mechanical_video.cli series status
```

输出在 `series/3d-printer/output/`，每集包含独立脚本、分镜、音频、字幕、时间轴、缩略图和验收报告。已完成文件按哈希保护，重跑跳过；保留预览、场景、帧序列和版本化脚本供恢复。12 集已有脚本，EP04–12 尚未完成实际成片验收。CAD 来源、BRep 修复侧车、近似与已知显示限制见 [系列说明](docs/series-production.md)，实际结果见 [验证记录](docs/validation.md)。


## 通用演示：90秒中文配音

以下为通用演示流程，不是当前打印机系列制作入口；打印机系列使用 Kai，并按六集规划逐集准备。项目已本地安装 audiogen 原始脚本及 openai 依赖，通用默认 `qwen3-tts-flash` / `Ethan`。先生成90秒基础视频：

```sh
.venv/bin/python -m mechanical_video.cli batch --templates explanation --seconds 90
# 已有持续 worker 会自动处理；否则执行：
.venv/bin/python -m mechanical_video.cli worker
```

在运行配音命令的终端设置 `OPENAI_API_KEY`；可选 `OPENAI_BASE_URL`，默认 `https://huabot.com/v1`。不会自动读取 `.env`。将任务编号替换为入队输出：

```sh
.venv/bin/python -m mechanical_video.voiceover artifacts/videos/任务编号/video.mp4 \
  --script docs/narration-90s.zh.txt \
  --out artifacts/机械拆解-90秒-中文.mp4
```

讲解稿每行作为一个配音片段，保留原文；按实测片段时长生成中文软字幕，句间补停顿对齐视频时长。稿件仅为教学示例，镜头仍使用现有 explanation 三阶段动画，并未实现逐句智能运镜。语音超过视频长度时拒绝截断，需缩短稿件或延长视频。输出包括原始MP3、拼接音频、SRT、最终MP4和验证记录；播放器需启用中文字幕轨。

重跑相同稿件、模型、音色、服务地址和脚本版本会复用语音缓存。为避免不确定请求重复计费，提交标记存在且音频缺失时停止，检查后才能显式删除标记重试。已存在的成片不会覆盖。配音后的独立成片尚不自动加入工作台任务列表。

项目级机械 CAD → 拆解动画 → H.264 视频流水线。针对 Apple M3 / 16GB：Eevee、单渲染 worker、独立 STEP/STL 零件、缓存复用、SQLite 队列、失败重试及逐帧断点续跑。

## 快速运行

已安装依赖的本项目可直接执行：

```sh
.venv/bin/python -m mechanical_video.cli demo
.venv/bin/python -m mechanical_video.cli status
```

新环境使用项目内依赖（系统 Python 3.9 不适用）：

```sh
UV_CACHE_DIR=/private/tmp/mechanical-video-uv uv sync --python 3.11
uv run mechanical-video demo
```

Blender 自动检测 `/Applications/Blender.app/Contents/MacOS/Blender`，或通过 `BLENDER_BIN` 指定。FFmpeg/ffprobe 必须在 PATH。macOS 的 Codex 沙箱可能在 Metal 探测阶段触发 Blender 崩溃，需按审批机制批准渲染进程的 GPU 访问，无需修改沙箱配置。所有 Skill 位于 `.agents/skills/`，没有安装全局 Skill。

macOS 流水线启动 Blender 前检查 Metal 设备：不可见时保留待处理任务及尝试次数。子进程因信号退出时任务标为 `blocked`，重启 worker 不会自动重试；检查日志和系统崩溃报告后，可用 `retry` 显式恢复。流水线自身不能授予沙箱外权限，需由执行器授权或在具有 GPU 访问的终端启动。

## 批量与持续生产

```sh
# 创建十种主题；重复命令不会重复创建同一任务
.venv/bin/python -m mechanical_video.cli batch
.venv/bin/python -m mechanical_video.cli worker
# 一直监测新增任务（Ctrl-C 停止）
.venv/bin/python -m mechanical_video.cli worker --watch
# 正式竖屏 1080×1920，仍复用同一 CAD
# 可用 --module 1.5 生成不同尺寸的独立参数缓存
.venv/bin/python -m mechanical_video.cli batch --portrait --production
# 查看失败并显式重置已耗尽的三次重试
.venv/bin/python -m mechanical_video.cli status
.venv/bin/python -m mechanical_video.cli retry
```

也可直接使用 `scripts/batch.sh` 与 `scripts/continuous.sh`。

`--root PATH` 放在子命令前可隔离任务库。默认 1280×720、30fps、5秒，Eevee测试采样8；1080p采样32；`--portrait` 为720×1280；`--production` 切换1080p。`--seconds` 可设至120秒。`--engine cycles` 使用 Metal GPU（已实际通过 M3 GPU 渲染验收）。

| 模板 | 内容 |
|---|---|
| overview | 整体360°相机环绕 |
| shell | 仅外壳和螺丝移出 |
| internals | 隐藏壳体并分离内部零件 |
| explode | 全部零件爆炸拆解 |
| gears | 固定齿圈下太阳轮/行星轮的运动关系 |
| closeup | 太阳轮特写 |
| transparent | 透明壳体观察内部 |
| assembly | 从爆炸图反向装配 |
| working | 关键传动过程及工作关系 |
| explanation | 分阶段完整拆解及字幕讲解 |

动画为教学运动学展示，非动力学仿真。齿轮使用采样渐开线，行星轮缩放0.97、内齿圈空腔缩放1.06以提供教学展示间隙，非标准制造齿形；18齿太阳轮、15齿行星轮、48齿内齿圈，固定齿圈速比3.667:1。独立零件含盖板、内齿圈、太阳轮、三行星轮、三销轴、行星架、输入/输出轴、四螺丝，共17件。尚未完成制造级干涉、间隙、轴承寿命和应力验证，不作为加工图使用。

## 图片上传与 AI 分析

```sh
export VISION_ENDPOINT='你的兼容 chat/completions 的完整 URL'
# 默认使用 gpt-6-luna；仅在需要覆盖时设置：
# export VISION_MODEL='其他模型名'
# 需要认证时在当前终端设置 VISION_API_KEY；不要写入仓库
.venv/bin/python -m mechanical_video.web
# 打开 http://127.0.0.1:8766 上传图片
# 或使用 CLI：
.venv/bin/python -m mechanical_video.cli image product.png --templates explode shell
.venv/bin/python -m mechanical_video.cli worker --watch
```

图片识别默认模型为 `gpt-6-luna`，CLI 与工作台共用项目配置；`VISION_MODEL` 可覆盖默认值。模型名称已配置，不代表服务商已验证支持该名称及图片输入。

上传会把图片发送到你配置的视觉服务。当前支持从视觉分析结果路由到**行星减速器**参数化家族（可调模数/整体尺寸，齿数与拓扑固定）或 **cordless_drill 电钻概念模板**。电钻模板按本项目参考照片估算外形，并不自动还原任意电钻；隐藏结构采用常见原理推测。其他产品会保存分析并明确拒绝建模，不能把通用示例冒充识别结果。没有提供视觉服务配置或真实产品图片，因此本次未验证外部视觉推理。全部内部结构和图片估计尺寸标记为 `inferred`，不能从单张外观图断言真实内部结构。模型按几何参数缓存，图像与分析按内容哈希归档。

TripoSR 保持可选且禁用，ARM64 实际推理未验证，详见 docs/triposr-compatibility.md。基础建模和视频生成完全独立。

## 资产与恢复

- `artifacts/models/<hash>/`：每个零件 STEP/STL、assembly.step、assembly.json；参数和模型版本决定缓存键。
- `artifacts/videos/<hash>/`：job.json、scene.blend、PNG逐帧、blender.log、video.mp4、video.verification.json、字幕。
- `artifacts/inputs/<sha256>/`：原图、结构分析及不确定性记录。
- `artifacts/queue.sqlite`：状态、尝试次数、异常、时间；`render.lock` 防止重复渲染。

中断后重启 worker，会恢复 running 任务；已有 PNG 不重渲染。每任务最多自动尝试三次，失败不伪造成功文件。新 worker 还会对保存场景做零件数量、取景边界、圆周运动和360°相机轨迹验收。完成标准为 H.264、规定分辨率/30fps/时长，加 FFmpeg 全片解码。队列长期运行，生产者持续加入新图片/参数/镜头任务；相同任务去重，不无限制造重复文件。

```sh
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m mechanical_video.cli verify artifacts/videos/任务ID/video.mp4
```

生成可播放的本地视频目录：`.venv/bin/python -m mechanical_video.catalog`，然后打开 `artifacts/index.html`。字幕为英文软字幕和 SRT，未集成语音配音。

当前交付验证与实际视频路径见 [docs/validation.md](docs/validation.md)。

## 工作台生产与版本复用

工作台现在支持选择主题、画幅、720p/1080p、时长和 Eevee/Cycles Metal。点击“复用示例模型生成”即可直接生产；图片识别未配置时仍可使用此入口。视频卡片显示真实时长、分辨率及引擎，播放器支持 HTTP Range 拖动定位。

新任务会把渲染、场景验收和字幕脚本存入任务目录的 `renderer/`。脚本内容指纹参与任务编号：更改镜头或材质后重新入队会生成新视频任务，同时继续复用原 CAD。旧任务重试使用归档脚本，归档缺失或遭修改会明确失败，不混用旧帧。

持续监听使用 `worker.lock` 保证只有一个消费者，实际渲染期间才持有 `render.lock`。可在 worker 空闲时执行独立验收，无需停止监听：

```sh
.venv/bin/python -m mechanical_video.acceptance --wait
```

`metrics.json` 记录新 worker 的任务耗时。Cycles 必须找到 Metal GPU 才启动，拒绝静默回退 CPU，设备证据保存到每条 Cycles 任务的 `hardware.json`。首次使用需要编译 Metal 内核，启动时间可能明显长于后续任务。


## 本机最新验收

14条真实MP4已通过场景与全片解码验收，包括1080p五秒爆炸视频、M3十核GPU的Cycles Metal一秒特写，以及从工作台实际提交的一秒Eevee任务。浏览器已实际播放1080p与工作台生成的视频；持续监听可同时支持空闲验收。详见 docs/validation.md。图片分析仍需配置视觉服务，当前CAD家族为行星减速器和电钻概念装配；TripoSR禁用。


## 照片引导的电钻装配

```sh
.venv/bin/python -m mechanical_video.cli model --family cordless_drill
```

`mechanical_video/drill.py` 为可复用的 build123d 源，`gen_step()` 返回命名装配。模型缓存含每件独立 STEP/STL、assembly.step、assembly.py 和 assembly.json；所有尺寸及内部结构显式标为推测。支持 overview、shell、internals、explode、transparent、assembly、explanation；不支持减速器专用 gears/working 运动仿真及 closeup。CLI 图片入口可路由电钻，但在线视觉服务尚未验证，当前照片由助手直接观察。详细假设见 docs/briefs/cordless-drill.md。

将 `model` 打印的清单路径交给现有 `enqueue`，再运行同一 artifacts 根目录的 worker，即可复用缓存。渲染脚本按现有指纹规则归档；不要修改归档或混用不同任务帧。

### 电钻长片：实测旁白驱动分镜

`drill_film` 将九段中文旁白逐段合成并测量，依次编排整机、电池拆出、分壳、夹头、减速器、电机、控制件、电池内部及完整爆炸图。每段末尾的停顿均来自目标时长与实测语音长度之差，不按字数猜测时间。若语音超过目标时长，在渲染前明确停止。

```sh
.venv/bin/python -m mechanical_video.drill_film \
  --manifest artifacts/models/drill-4c0dddd1fb5480aa/assembly.json \
  --script artifacts/films/cordless-drill-90s/narration.zh.txt \
  --output artifacts/films/cordless-drill-90s/drill-90s-zh.mp4 --seconds 94
.venv/bin/python -m mechanical_video.cli worker
```

按 `render-task.json` 查到对应静音视频后，用 `film_audio` 合成 AAC 中文旁白、烧录字幕和中文章节（新的输出文件名）：

```sh
.venv/bin/python -m mechanical_video.film_audio \
  --storyboard artifacts/films/cordless-drill-90s/storyboard.json \
  --video artifacts/videos/TASK_ID/video.mp4 \
  --output artifacts/films/cordless-drill-90s/cordless-drill-94s-zh.mp4
```

配音默认 `qwen3-tts-flash / Roy`，使用项目 audiogen runner；凭据仅从环境变量读取。已有有效音频直接复用；不明状态的请求保留 submitted 标记，避免重复提交。分镜和独立零件运动完整写入队列规格，参与任务指纹；保存逐帧缓存、scene.blend 和渲染脚本快照。`film_audio` 额外保存音频、SRT/ASS、章节、制作脚本及校验报告。字体采用 macOS Arial Unicode MS，工具仅支持本项目已有的 macOS 生产环境。
