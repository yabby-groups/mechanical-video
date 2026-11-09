# 字幕动作与实际运动的出图前核对

2026-11-09卷尺V7复审发现：原有长度、端点、实体和编码检查没有判断“字幕说收回时，实际是否在收回”。开头与结尾用段落百分比独立安排动作，字幕则按段内文字权重估时，两条时间轴都合法却互相矛盾。

新增 `mechanical_video.action_alignment`。它不推测语音或自动理解所有中文；Director/Script/独立内容评审必须从冻结文案列出明确动作断言，再以实际逐帧运动计算复核。关键动作应在制作前落为可检查的声明，不能留到用户看成片才判断。

```sh
.venv/bin/python -m mechanical_video.action_alignment \
  --motion /absolute/frozen-motion.json --timeline /absolute/measured-timeline.json \
  --policy /absolute/action-policy.json --output /absolute/new-action-report.json
```

策略 schema_version=1，requirements 与原题契约 ID 完整对应，每项列 assertions：caption_text（冻结字幕精确文本）、channel（实际 motion.poses 数值通道）、relation。递增/递减用 increasing/decreasing 和正值 min_change；保持状态用 held_above/held_below、bound、min_fraction。姿态时间必须覆盖每个整数帧、频率一致；字幕匹配不存在/有歧义、通道缺失、非有限值、缺帧、动作方向错误或期望状态未达到，都不能通过。

v4 full-render/delivery 必须绑定 `assets.action_alignment`、`assets.action_alignment_policy`、`assets.motion`、`assets.timeline`，使用绝对路径/hash。门禁不只看 PASS，会重新读取源数据重算，校验原题ID完整对应；缺报告或不一致即 BLOCKED。配音前可先用估计时间线验证表达可实现性，配音后必须再按实测时间线核对；不能据此宣称词级音画同步通过。

卷尺V7的真实回放：12个声明中5个失败——“再让它回去”时仍拉出；结尾“压脚压住尺带就能保持”时未处于锁住状态；“解除锁止”时仍在加锁；“卷簧释放能量”和“把尺带收回”时尺带仍保持20mm。用现有文件就能查到，原评审遗漏由制作流程承担。

断言必须由实际机制决定，不能全局把“能收回”的条件句机械等同于正在收回。错误策略会误报或漏报；独立评审须检查原题/文案覆盖及断言合理性。该检查不验证摩擦/力学，不替代词级对齐、听审、机械来源与实际成片检查。不得通过放宽阈值或删除失败声明来掩盖实际错误。

同时应将穿壳连片等关键因果件列入前检目标；只选可见按钮而漏掉不可见连片，不能证明传动链已经展示。卷尺本次用冻结场景及正式pose、四个姿态的几何射线复核证实连片采样点不可见，不将有限采样冒称整段全表面不可见。
