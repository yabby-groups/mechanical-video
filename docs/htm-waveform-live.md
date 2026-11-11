# HTM 实时波形实验台

本机入口：http://127.0.0.1:8766

```sh
PYTHONPATH=. reports/htm-audio-runtime/venv/bin/python -m mechanical_video.htm_waveform_live \
  --audio series/everyday-mechanisms/episodes/EVERYDAY_EP03/neil-voice-20261110/Tape-measure-Neil-workprint.mp4 \
  --port 8766
```

这是连续读取文件音轨的实时 HTM 检查器，不是麦克风输入，也不是预生成动画。
启动时以原生采样率/声道解码一次，随后从新建 SP/TM 开始，播放时按 10 ms 逐帧推进官方运算。
不加载模型，不修改视频、已有模型或报告。运行仅保存在本进程内存；停止进程会丢失未导出的会话。

## 使用

- 开始运行 / 暂停 / 下一帧：实时、慢速或单步观察。每个音频帧都计算，界面约 100 ms 刷新一次。
- 在线学习：默认开启；暂停后可关闭，用当前已学习状态进行推理。
- 保留学习 · 重播：保留 SP/TM 学习权重，重置 TM 时序状态，重新读取同一音轨。保留历轮摘要，本轮详细帧记录重新开始；需要时先导出。
- 从零重置：清除本会话模型与历史，重新初始化；不会改磁盘模型。
- 拖动时间滑块或点击曲线：暂停并回看已经计算的帧，不重新推进或学习。
- 声道选择 / 点阵悬停：查看对应样本、振幅档、SDR 地址及位值。
- 原音播放器独立运行；供听音对照，不声称与 HTM 显示同步。听音副本为 16-bit PCM；模型输入仍为原始解码 float32。
- 导出：导出本轮完整 SDR、SP 列、TM 预测/活跃/赢家细胞、异常、输入及运行指纹；导出不暂停运算，但持锁获得一致快照。

## 可见的真实数据

1. PCM：当前帧全部原始样本，固定 [-1,1] 幅度。
2. SDR：每声道/采样位置点亮一个 64 档振幅位；地址 `(channel*width+position)*64+bin`，末帧填充不激活。
3. SP：真实 `columns.sparse`，512 列；直接作为 TM 参数输入。
4. TM 预测：调用官方 `activateDendrites(learn)` 后、当前帧 `compute` 前的预测细胞，表示前序状态对当前帧的预测。`compute` 复用有效 dendrite 计算并更新细胞、官方 anomaly；不提前学习未来帧。
5. TM 输出：`getActiveCells` / `getWinnerCells`。每列 8 细胞，网页每组 4×2，按列 ID 排列。
6. anomaly：官方原始异常，并用 `未预测的活跃列数/活跃列数` 独立重算。首帧无上下文仍显示异常；此页不计算缺陷评分。

核对项包括 SDR 实际激活数、唯一性、范围、TM 活跃细胞反推列与 SP 输出是否一致、重算异常是否等于官方异常。
这些是数值/传递正确性检查，不代表波形编码具备声音质量判别能力。

## 验证

`PYTHONPATH=. reports/htm-audio-runtime/venv/bin/python -m unittest discover -s tests -p 'test_htm_waveform*.py'`

检查器与官方原始 `Engine.sequence` 的单遍输出逐帧一致；重播保留权重、冻结不改权重、回看不学习、重置恢复初始权重均有测试。
只绑定 loopback，浏览器只访问固定音频文件及本地 API，无上传/发布。
运行速度受主机计算和定时精度影响；不会为追赶墙钟跳帧。整段已解码音频和本轮帧历史驻留内存，适用于短视频，尚非无限长流服务。
