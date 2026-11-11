# 波形 SDR 音频入口 v1

独立入口 `mechanical_video.htm_waveform`；旧特征、分类器、模型与资格记录不变。
本入口 **UNQUALIFIED**，仅输出预测异常候选，尚不能承担完整听审或自动修复验收。

```sh
HTM_PY=reports/htm-audio-runtime/venv/bin/python
$HTM_PY -m mechanical_video.htm_waveform train --audio normal-a.wav normal-b.wav --model reports/new-waveform-model --epochs 3
$HTM_PY -m mechanical_video.htm_waveform review --audio unseen.wav --model reports/new-waveform-model --output reports/new-waveform-review --threshold 0.8
PYTHONPATH=. $HTM_PY scripts/run_waveform_experiment.py --output /private/tmp/new-waveform-trial
PYTHONPATH=. $HTM_PY -m unittest discover -s tests -p 'test_htm_waveform.py'
```

输出目录必须不存在，防止覆盖证据。阈值 0.8 是实验操作点，未经独立校准。
不导入识别、对齐、人工语速/音高特征或其他模型。不同采样率/声道必须用匹配配置的模型；不自动转换规格。

## 编码与状态

FFmpeg 以原始采样率和声道解码 f32 PCM，固定幅度范围 [-1,1]；超出范围拒绝，不逐帧归一化。
默认 10 ms，以整数有理边界连续覆盖；11025 Hz 等规格交替帧长，末帧实际长度保留。
SDR 地址为 `(channel * width + sample_position) * 64 + amplitude_bin`。
振幅档为 `min(63, floor((sample+1)*32))`。每个真实样本、每声道恰好一个激活点，不连线，不点亮填充位置。
完整等长帧密度 1/64；短帧相对于固定总维度的密度自然下降，不能补点伪造固定密度。

官方 htm.core SP/TM 使用固定 seed。小规模学习后先固定 SP，再重建并训练 TM，避免同时变化的空间词汇干扰时序学习。
每条独立音频重置 TM，同条连续推进。审查 SP/TM 均 learn=False；核对 SP permanence/duty/boost/学习计数与 TM 突触一致。
官方序列化含推理计数，文件变化本身不代表学习。磁盘模型另有组件哈希验证。

## 可检查证据

`timeline.json` 含每帧精确样本边界、时间、有效样本数、激活数与 TM anomaly；
`report.json` 含合并候选区间、完整覆盖、冻结参数哈希和输入来源。
第一帧无上下文，保留异常值但不计入候选。
`waveform.npy` 保存全部解码 PCM，shape=(samples,channels)，无图片中间文件。
可用 `numpy.load` 加载，按报告配置调用 `Config.frames` 重建任一帧完整二值点阵。
这是精确波形证据，不是感官听审证明。内存解码适合短视频音频，尚未实现长录音流式处理。

## 2026-11-10 实测

报告目录 `reports/htm-waveform-v1/`：初始 trial、分阶段 followup、最终 staged、实际配音 narration、命令行 cli。
初始三个运行保存对应 implementation.py，避免后续实现哈希漂移影响溯源。
2 条 AISHELL 正常录音训练，同一冻结模型测试 2 条未见录音及各自正常/停顿/BGM/断音/削波/重复/反转拼接/增益突变，共 16 个用例。
变体由脚本控制注入；“修复后”为同源原始音频，非真实制作返工或独立听审标签。
BGM 为低幅合成正弦代理，不能代表真实音乐混音的完整验收；反转片段仅代表一种受控拼接。

初始正常高异常帧比例 0.38% / 1.15%；分阶段训练后 0% / 0.29%。
分阶段削波注入窗口高异常帧覆盖均 100%；增益突变约 58% / 50%。
断音、重复窗口均 0%；反转拼接约 3.8% / 0%，没有可靠区分。合理停顿及低幅 BGM 代理有少量误报。
这些是逐帧操作点结果，不是事件召回率或准确率；不得用覆盖比例替代独立缺陷标注。

另用 EP02 配音前连续 8 秒学习，测试未见 EP03 完整 95.03 秒，原生 48 kHz 单声道配置。
初始冻结模型高异常帧约 56.6%，无独立缺陷标签，不能将这些候选断言为配音错误。
该实际配音测试与 16 kHz 录音使用匹配规格模型；每条测试音频不重新训练。

结论：编码和时序学习机制可运行、状态测试通过，但检测有效性未通过。
分阶段训练的有限修正仍不能解决漏检，未扩大训练规模、未接入生产资格门禁。
真实爆音、真实音乐变化、真实修复对照及完整配音/BGM听审仍未完成资格验证；本轮未实现完整工具目标。

补测：同一最终冻结 16 kHz 模型审查 2 ms、0.99 幅度的脉冲爆音，所在 0.88 秒帧 anomaly=0.05，阈值 0.8 下漏检；证据 `reports/htm-waveform-v1/pop/`。
最终验证：新增 5 项 unittest、原 HTM 音频 35 项 unittest 均通过；真实 CLI review 已成功执行并保存完整波形和时间线，`git diff --check` 通过。
这些验证不改变上述检测失败结论。
