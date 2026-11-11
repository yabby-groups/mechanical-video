# HTM 音视频实时检查与双片对比

> 2026-11-10 修正：旧 `potentialRadius=16` 视觉模型实测连接数为零，旧视觉曲线、命中率和 2.30× 性能结论失效。详见 `reports/htm-av-validation-20261110/invalidation.json`。当前使用完整输入感受野 786432，并强制检查每列存在连接及受控输入响应。

独立入口，保留 `htm_waveform_live` 音频页。模型不加载预训练权重；A/B 使用同配置的同一未学习状态副本，各自独立推进。异常表示预测新颖度，不是缺陷、质量或爆款判断。

```sh
cd /Users/lmj/yuntan/esp32/mechanical-video
PYTHONDONTWRITEBYTECODE=1 reports/htm-audio-runtime/venv/bin/python -m mechanical_video.htm_av_live
# 指定来源与独立会话目录（目录必须尚不存在）
PYTHONDONTWRITEBYTECODE=1 reports/htm-audio-runtime/venv/bin/python -m mechanical_video.htm_av_live \
  --video /absolute/A.mp4 --reference /absolute/B.mp4 --port 8767 \
  --output reports/my-new-av-session
```

打开 http://127.0.0.1:8767 。默认 A 为 Neil 卷尺工作片。B 可用本地文件选择器导入：文件送往本机回环服务并保存到会话目录，不发送外部服务。导入 B 会让 A/B 一起从初始权重开始新一轮。同哈希 B 明确显示“同源测试副本（非真实参考）”。默认只监听 A，可切换 B 或静音。

## 编码与模型

- FFmpeg 自动应用显示旋转，按源 PTS 解码全部帧，不重采样帧率；按显示宽高比双线性缩放，居中填入 64×64 RGB 画布。填充不产生 SDR 位。
- 每有效像素每通道恰好一位：`((y*64+x)*3+channel)*64+floor(value/4)`。输入 786432 位，无逐帧归一化或语义特征。悬停查看 RGB、bin、位地址及三个 64 位条。
- 视觉 SP：2048 列、全局抑制、potentialPct=0.01、seed=42；**potentialRadius=786432**（覆盖完整输入，避免 1% 密度下的零候选退化）；其余官方默认。TM：每列 32 细胞，其余官方默认。此项是对原计划的必要修正；不能继续沿用旧性能数据。
- 音频复用 `htm_waveform.Config/Engine`：原生采样率/声道、10 ms、64 档，512 列、每列 8 细胞。独立于视觉，未改变旧音频入口或报告。
- AAC 按容器有效时长裁掉尾部填充。保留音频原始起点，音频事件在样本区间**结束**时进入模型；视频事件在 PTS 到达时进入。无音轨运行视觉；音频异常明确显示并停该通路。非连续音频 PTS 明确停音频，不隐式补样或重采样。HDR/PQ/HLG 输入拒绝。
- 每步检查 SP 列与 TM 实际活跃列一致；前序预测先于当前细胞激活读取。未预测活跃列比例重算异常并核对官方输出。首帧无历史上下文单独标记。

## 控制、回看与对比

播放、暂停、0.1/0.25/0.5/1/2×、下一视频帧、下一音频帧。单步将所有不晚于目标事件的通路按时间推进，不提前输入未来数据。计算不跳帧，显示约 4 Hz；媒体由计算进度限制，处理落后时暂停等待。

保留学习重播只重置 TM 时序上下文；从零重置复制初始权重。二者均新增轮次，旧记录不覆盖。学习开关只允许暂停时修改，保存各通路生效 cursor 和时间。历史滑块和轮次选择只读数据库，不重新训练。

B 正偏移表示在 A 的时间轴上延后开始。必须在本轮处理前设置；有记录时先重播。无自动时长拉伸或语义匹配。曲线为原始异常/命中率；差值只计算共同覆盖的同模态区间。汇总采用片段持续时间加权。音频规格不同或任一无音轨时禁用音频差值。不同模态不相减、不综合评分。

## API 与数据

- `GET /api/state`：初始化阶段、进度、学习状态、来源配置、cursor、速度、错误。
- `POST /api/control`：JSON `action=play|pause|step|restart|reset|settings`；step 的 `mode=video|audio`、`lane=A|B`；settings 的 `learning/speed/offset`。
- `POST /api/reference`：本地文件原始 bytes，可选 URL 编码的 `X-Filename`。
- `GET /api/frame?lane=A&mode=video&index=0&pass=1`：仅选中帧的大数组、RGB/波形、输入 SDR、SP/TM、预测、异常和学习状态。
- `GET /api/timeline?pass=1&start=0&end=10`：标量曲线及同窗口加权对比。
- `GET /api/export?format=html|sqlite`：独立 HTML 图表报告或全部历史数据库；不带 format 导出曲线 JSON。页面可另存曲线 PNG 和逐帧 JSON。
- `GET /media?lane=A&pass=1`：支持 Range 的原始视频，不是编码缩略图。

SQLite 按帧保存 gzip 压缩块，每帧提交；元数据包含来源 SHA-256、每轮配置/偏移、运行代码及官方二进制指纹、学习切换记录。全部数组不持续推送，只按帧请求。原始数据读取示例：

```python
import sqlite3, gzip, json
c = sqlite3.connect('history.sqlite')
row = c.execute('SELECT detail FROM frames WHERE pass=1 AND lane="A" AND mode="video" AND idx=0').fetchone()
frame = json.loads(gzip.decompress(row[0]))
```

会话历史持久保存；当前版本不从数据库恢复已学习模型进程。命令重启创建新会话，不能把旧记录当作已恢复模型。

## 2026-11-10 历史实测（视觉结果已失效）

[完整覆盖与性能](../reports/htm-av-validation-20261110/acceptance.json)、[独立 HTML 对比报告](../reports/htm-av-validation-20261110/comparison.html)、[受控变体](../reports/htm-av-validation-20261110/controlled-variants.json)、[原始历史](../reports/htm-av-validation-20261110/history.sqlite)。浏览器交互证据在同目录的 `browser-checks.json` 和截图/导出文件；真实网页会话保存在 `reports/htm-av-browser-20261110/`。

- 源 SHA-256：`64070fbe432b8f4a2efdc966e63400db7013f7f68089cfeb91e690264c7be32d`。
- A/B 各完整处理 1382 视频帧、4607 音频帧、2211200 有效样本，全部 SP/TM 与异常重算校验通过；同源 A/B 逐帧包括全部原始数组一致。
- 双片初始化 14.21 秒；双片全通路计算及落盘 20.02 秒，对应 46.067 秒素材，2.30× 实时；合计 138.08 视频帧/秒，同时处理双路音频。首次较高压缩级别为 55.41 秒，优化为低级别无损压缩后重跑，未丢帧。
- 修改第 10 帧的复制帧、局部颜色、替换转场三种受控输入：逐帧证实输入变更位置，记录两条响应。响应是否改变不作为质量结论。
- 回归覆盖纯色、渐变、单像素、颜色区分、无效填充、加权区间、官方数值、同源初始化、只读回看、重播/从零恢复、30 fps/VFR/旋转/非零音频起点/无音轨、HDR 拒绝、不同音频配置、偏移与历史轮次。

```sh
PYTHONDONTWRITEBYTECODE=1 reports/htm-audio-runtime/venv/bin/python -m unittest discover -s tests -p 'test_htm_*live.py' -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. reports/htm-audio-runtime/venv/bin/python scripts/validate_htm_av.py --output reports/new-av-coverage
```

性能属于此机器和此素材的测量，不代表任意分辨率/编码/声道配置都能实时。当前 B 为验收测试副本，未指定真实参考作品；没有质量排名、缺陷验收或观看留存结论。

## 播放与位图修正

完成一轮后主按钮显示“重新播放”，点击保留权重并开启新一轮，旧历史保留。真实输入 SDR 按 `id=y*1024+x` 展示，1 像素对应 1 位，支持滚动及悬停；原量化图不再冒充 SDR。SP/TM 以保持比例的格子显示真实 ID 和激活数。视觉初始化在独立子进程构建未学习模板，避免官方扩展持有 GIL 导致页面无法响应。

修复后复验：`reports/htm-av-connected-20261110/coverage.json` 与 `comparison.html`。A/B 各 1382 视频帧、4607 音频帧、2211200 样本，逐帧相同；整片产生 93 种视觉 SP 输出。初始化 138.93 s，处理与落盘累计 37.76 s（计算比率 1.22×，不等同于播放器墙钟基准）。11 项回归通过，包含每列非零连接、黑白输入不同响应。浏览器逐像素核对 6912 个 SDR 亮点与原始 ID 完全一致。当前修复页面仍为 http://127.0.0.1:8768 ，服务连接到有效模型会话；旧视觉报告已显式失效。
