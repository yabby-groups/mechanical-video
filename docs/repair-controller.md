# 会话驱动的持久化修复控制器

2026-11-09。新制作使用 production_checks v5；历史 v1–v4 仍可只读评估，不能通过新制作入口获得 v5 合格状态。Python 不调用或模拟协作工具，真实派工由 Director 会话执行。身份是工具返回结果的会话记录，不是密码学认证。

## 入口与执行

`python -m mechanical_video.cli production --record director-record.json initialize --payload tasks.json`

也可直接运行 `python -m mechanical_video.repair_controller`，支持 initialize / next / claim / complete / resume。payload 是对应函数的 JSON 关键字参数；不得把 Agent 自称的身份当作工具回执。

1. initialize 把任务 DAG、能力、独占路径、输入 SHA 写入既有 director-record 的 repair_controller。已有状态不重置。默认阶段是原题、局部小样、独立检查、实测配音时间线、预检、渲染、独立后审、交付。
2. next 返回 ready / blocked / running。Director 仅对 ready 任务调用真实 spawn_agent 或 followup_task，然后 claim 写回 agent_id 和原工具回执。
3. 同一次真实派工包含多项顺序任务时，可用 reuse 和完全相同的回执认领下一项；上一项必须已完成，不消耗新的 spawn/followup，但仍计交接。默认最多四个 Agent，每人一次 followup，二十次交接，第四个新身份保留给独立评审。没有会话重置预算接口。
4. complete 使用唯一 completion_id。重复相同事件幂等，变更内容重用事件 ID 拒绝。生产者完成后自动进入独立评审，生产者和上游生产身份均不能自审。
5. 失败需 issue_id、owner、severity、required_checks、hash 证据及新版本 repair_outputs；可给 repair_inputs 限定受影响输入。自动建立唯一责任人的修复任务。修复提交后再次独立审查，覆盖全部必查项才关闭。最大三轮，两轮无改善停止；换名字不清零。多问题必须全部关闭才释放原检查。
6. resume 保留 running/uncertain 任务，报告待核实执行；不重新配音或渲染。受控命令在启动前持久化 uncertain 回执，完成后写 returncode；同一任务有回执就拒绝再次启动。中断/供应商结果未知需要核实原执行，不能另建任务规避。

新生产命令仍走 `python -m mechanical_video.production_run --record ... --stage narration|full-render|delivery -- command`，但现在要求 v5、同版先决任务及实际 claimed 的阶段任务。命令 argv 同时绑定原制作检查与控制器。queue 的 production enqueue 必须绑定 v5 记录及模型 manifest；worker 每个任务重验，不把旧队列自动升级，生产失败/中断不自动重跑，retry 不重置生产计数。旧脚本生成的文件仍是未验收产物。

## 同一动作事件时钟

`event_timeline.build(events, measurement, audio, alignment_evidence)` 从实测语音区间生成事件与字幕。每事件包含 id、原题 requirement、phrase、caption、animation、foley。拒绝比例估时、旧音频、遗漏事件、重叠区间和超过 20 字单行字幕。对齐来自真实 forced_alignment 或独立听审；该模块核对数据关联，不声称听过语音。

v5 full-render/delivery 要求 assets.event_timeline、narration_audio、timeline、motion、foley_timeline 同版。字幕必须直接使用事件时间，motion/foley_timeline 的 event_bindings 必须逐项匹配事件 ID、起止时间和相应 animation/foley binding。所有原题要求都须出现在事件中。现有动作核对、场景预检和内容契约继续执行，不能只凭新控制器状态通过。

## 能力依赖与验收范围

continuous_av/audio 不能仅用能力字符串启用：需相同 adapter 的 hash 绑定基准报告，记录已发现 action_contradiction、occlusion、speech_desync。报告仍需 Director 核实来源和真实执行，控制器不认证感官能力。默认独立前检/后审在该能力缺失时保持 blocked。

本次没有发现可调用的连续视听适配器，也没有实际语音不同步检出基准。因此全视听、真实题意完整性、节奏情绪及点赞/收藏/关注价值后审未完成，不能宣布整个改造验收完成。预测不代表真实增长。

跨题材实验使用卷尺和按压笔的实际运动数值片段，但几何、字幕和无声诊断视频是明确标注的简化测试代理。它验证自动检测/派修/独立复验的技术路径；没有在原片场景中证明同样效果，也没有覆盖原题全部机制。不得将该实验 PASS 晋级为正式视频交付。

## 证据和恢复

实验目录保存 v1、v2、原始来源 SHA、控制器事件、独立报告和环境崩溃日志。归档保留原始字节和原临时绝对路径以免改写评审关联；归档清单给出原路径与持久化副本的映射。恢复该实验时先按清单核对并还原原路径，再 resume；不要直接修改旧报告里的 hash。真实新任务应从开始就在永久 episode 目录初始化。
