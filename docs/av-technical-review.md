# 视频技术审查

本地网页 http://127.0.0.1:8768 的“技术审查”可选择 A/B，生成时间码、测量证据、原片回看及 JSON。视觉/音频 HTM 仅提供预测新颖度上下文；确定性检测器检查近黑、低运动、短时亮度闪变、静音、满幅削波。全部结果需要语境判断，不自动通过或修改视频。

## 启动

在 mechanical-video 仓库，分别启动现有 HTM 与审查代理（当前已有会话时不要重复启动或重置）：

```sh
PYTHONDONTWRITEBYTECODE=1 reports/htm-audio-runtime/venv/bin/python -m mechanical_video.htm_av_live --video /absolute/video.mp4 --port 8769
PYTHONDONTWRITEBYTECODE=1 reports/htm-audio-runtime/venv/bin/python -m mechanical_video.av_review_live --port 8768 --upstream 8769 --output reports/av-review-jobs
```

独立扫描无需等待 HTM 初始化：

```sh
PYTHONDONTWRITEBYTECODE=1 reports/htm-audio-runtime/venv/bin/python -m mechanical_video.av_technical_review /absolute/video.mp4 --output reports/new-review
```

可添加 `--htm-database /absolute/history.sqlite --lane A --pass-number 4` 关联指纹匹配的历史。输出目录应使用新路径；HTML 与 media.mp4 一起保留。报告中的 source.path 记录扫描时的输入路径，网页任务临时输入会清理，永久原片副本是 report/media.mp4，可按 SHA-256 核对。

## 检测边界

策略 av-technical-v3：有效 64×64 RGB 像素，近黑亮度≤12、覆盖≥98%、≥0.1秒；相邻帧平均RGB差≤0.1、连续≥0.5秒；亮度跃迁≥45、≤0.16秒内回到原值±20；原生声道10ms窗口≤−65dB、持续≥0.08秒；数字满幅≥0.995、窗口占比≥1%、连续同号平顶≥8样本，相邻幅值差≤1e−6。低电平历史失真、全部爆音、全分辨率细节不在能力范围内。

原生帧和样本完整扫描，但空间分析是64×64。HTM关联只读，不额外训练；在线学习历史不是冻结推理，新颖度0.8阈值未经缺陷校准。首帧无历史，不作为新颖度候选。未覆盖机械正确性、字幕/动作对应、漏字、可懂度、音画同步及吸引力。

## 实测（2026-11-10）

基准目录 `reports/av-review-benchmark-20261110-v3`：66段无损合成视频；2个开发来源、4个隔离测试来源，各11变体。策略及代码哈希先冻结，测试来源与字节哈希无交叉。以下只计隔离测试，每类4个正例、24段正常控制：

| 检测 | TP / FP / FN | 正常片误报率 |
|---|---|---|
| 近黑 | 4 / 4 / 0 | 16.7% |
| 停滞 | 4 / 4 / 0 | 16.7% |
| 静音 | 4 / 4 / 0 | 16.7% |
| 闪变 | 4 / 0 / 0 | 0/24 |
| 削波 | 4 / 0 / 0 | 0/24 |

4/4召回的95% Wilson下界仅51.0%，不能推断真实素材100%可靠。最大边界误差约0.000000333秒。黑场、静止和停顿的正常控制刻意保留，不能靠删除这些案例制造高精确率。所有类型 production_qualified=false。

v1暴露响亮正弦误报削波，v2增加同号平顶检测；网页验收又发现停滞区间跨过运动合并，v3改为严格连续相等帧对，并增加回归。每次修复重新冻结代码并换新测试来源（v1:301–304，v2:501–504，v3:701–704）。旧报告保留，不代表当前结果。

Neil工作片SHA-256 `64070fbe432b8f4a2efdc966e63400db7013f7f68089cfeb91e690264c7be32d`：1382帧、2211200样本、48000Hz单声道完整覆盖，4.839秒。当前39条观察：停滞17、静音22，其余0；并非39个确认缺陷。当前网页任务 `c3dc9413297c4f73995dc730f919cc2b`，关联HTM第4轮。

10项单元测试通过。ego-browser实际点击开始审查、报告时间码（提前0.25秒预滚）、原片可播放、JSON下载均通过；39行记录，readyState=4，无横向溢出；下载数据与持久报告一致。证据在 `reports/av-review-browser-20261110`。

## 距离正式视频审查

已完成从响应曲线到可定位技术观察的第一阶段。还需要真实独立标注缺陷集、创作意图/剪辑时间线以区分正常黑场静止停顿，以及机械动作/字幕/旁白/音画对应的独立资格验证。暂不能给出整体完成百分比或自动通过结论。

## 自动运行（2026-11-10 接入）

审查不依赖浏览器。`av_auto_review` 后台进程直接调用解码器和确定性检测器，关闭所有网页不会停止扫描。网页8770只是可选的只读报告目录；8768实验台无需打开，也无需点击“开始审查”。

- 正式 `production_run` 的 full-render/delivery 成功后，自动扫描 controller 中声明的视频输出（包括目录内视频），把报告指纹及状态写入原 execution/task，自动传给独立后审任务。
- 常驻服务扫描本仓库 `series/`、`output/`、`artifacts/`，每5秒检查一次；文件稳定15秒后自动扫描。首次启动的159个已有视频只登记基线；新片及内容修改版自动处理，旧报告保留。以上目录之外的文件只有正式制作入口显式输出时才会处理。
- 检查范围仍是近黑、停滞、闪变、静音、削波；自动通路不训练SP/TM，也不借用其他视频的HTM历史。完整内容/语义审查和自动修复尚未实现，不能把扫描完成当作独立验收。观察由Director内部承接，不要求用户逐条复核。
- 同一路径、相同内容与相同实现的完整报告可复用；输出媒体和报告哈希均检查。修改版单独生成报告。源文件扫描期间变化则拒绝旧结果；解码失败持久记录，不无休止重试、不自动重跑制作命令。再次修改源文件可重新触发。
- 正式制作命令成功、技术扫描失败时，命令receipt仍保留returncode=0，runner退出2并返回自动审查失败；不能据此重跑未知/已完成制作。未声明视频输出时记录no_video_outputs，后续组装片由后台发现。

本机已安装并运行用户LaunchAgent `local.mechanical-video.av-auto-review`，登录后自动启动，异常退出自动拉起。服务状态与报告：`reports/av-auto-review/{state.json,index.html,jobs/}`；日志：`service.log`和`service-error.log`。后台恢复只恢复扫描，不派工、不渲染、不调用付费模型、不发布。

```sh
# 查看实际运行状态
launchctl print gui/$(id -u)/local.mechanical-video.av-auto-review
# 前台排障入口（常驻服务运行时不要再启动第二个实例）
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m mechanical_video.av_auto_review
```

LaunchAgent配置位于 `~/Library/LaunchAgents/local.mechanical-video.av-auto-review.plist`；使用项目.venv与本机FFmpeg PATH。守护服务和制作钩子共用队列锁，阻止重复扫描。测试验证目录 `output/av-auto-review-acceptance-20261110` 中的文件明确为测试素材，不是真实作品验收。
