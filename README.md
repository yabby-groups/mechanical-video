# Mechanical Video

## 90秒中文配音

项目已本地安装 audiogen 原始脚本及 openai 依赖，默认 `qwen3-tts-flash` / `Roy`。先生成90秒基础视频：

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

上传会把图片发送到你配置的视觉服务。当前支持从视觉分析结果路由到**行星减速器**参数化家族（可调模数/整体尺寸，齿数与拓扑固定）；其他产品会保存分析并明确拒绝建模，不能把通用示例冒充识别结果。没有提供视觉服务配置或真实产品图片，因此本次未验证外部视觉推理。全部内部结构和图片估计尺寸标记为 `inferred`，不能从单张外观图断言真实内部结构。模型按几何参数缓存，图像与分析按内容哈希归档。

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

14条真实MP4已通过场景与全片解码验收，包括1080p五秒爆炸视频、M3十核GPU的Cycles Metal一秒特写，以及从工作台实际提交的一秒Eevee任务。浏览器已实际播放1080p与工作台生成的视频；持续监听可同时支持空闲验收。详见 docs/validation.md。图片分析仍需配置视觉服务，当前CAD家族仍为行星减速器；TripoSR禁用。
