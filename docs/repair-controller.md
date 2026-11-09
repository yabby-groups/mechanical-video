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

## 主控本地执行与实测语音入口

主控亲自承担 `owner=Director` 的生产任务时，`claim` 使用 `dispatch_kind=director`，回执为 `{"agent_id":"/root","source":"active_session","role":"Director"}`（身份必须填写当前实际主控身份）。这是会话执行记录，不是假造的 spawn 工具结果。一个记录只能绑定一个主控；主控不消耗子 Agent 名额，仍计任务交接，不能以 director、reuse 或 followup 自审。独立评审继续记录真实协作工具回执。

`uv run --extra alignment python -m mechanical_video.speech_alignment --audio existing.wav --transcript spoken.txt --model MODEL --revision COMMIT --output alignment-v1.json --events events.json --timeline events-v1.json`

该入口只读取已有音频，不合成语音。FFmpeg 解码为 16 kHz；CTC 按实际声学输出、卷积步幅与感受野对齐逐字位置，并记录原音频 SHA、模型版本、识别文本和时间量化精度。完整原稿必须包含输入中的全部语音。事件短语须按序出现在原稿及贪心识别中；整段文本不符、关键短语缺失、低声学支持、无效逐字区间或旧音频均阻止生成事件时间线。对齐文件保留为候选证据；识别错字不能通过手工改写识别结果或降低门槛消除。

安装依赖和模型缓存均留在环境/缓存目录，运行证据和生成时间线留在忽略的生产目录，不入库。已有输出拒绝覆盖。此入口提供实测时间候选，不替代独立听审、连续视听评审或原题完整性检查；关键动作仍须调用既有动作检查器对照实际逐帧 motion。

### 实测语音回归范围

2026-11-09 已在卷尺与按压笔既有语音的隔离副本上运行：加入 0.5 秒延迟，CTC 事件时钟分别检出 0.5 秒和浮点等价的 0.5000000000000002 秒，裁掉检出的延迟后重新推理，时钟漂移检查通过。`event_timeline.compare_clocks` 重验两个时钟及其原音频/证据哈希，再检查相同事件的起止漂移；默认容差 0.1 秒。该实验的对象是真实原声，但缺陷是人工注入，未证明原片不存在声画错位。

卷尺完整 U7 的两套本地识别均出现同音字，完整句子的强制对齐未获准进入事件时钟；成功的卷尺实例限定为“回卷就能继续”，按压笔实例限定为“缩回”。不能把局部动作短语通过扩大成整段或整片通过。原片 P1、连续视听能力基准、画面遮挡与核心动作的跨题材成片验证仍独立保留。独立检查产生的修复任务即使继承 independent-check 阶段，也必须按生产任务处理，再生成独立复验，不能因为阶段名称错误而阻断责任人接单。

## 自动交付出口与团队内部处理

用户要求优化的是无需逐版人工质检的制作工作流。新 v5 交付必须为 formal，评审草稿只能在内部流转；命令入口和控制器 complete 都拒绝以 REVIEW_DELIVERY 完成。正式出口除既有五项验收与原题门禁外，还重新校验 `assets.perceptual_review`：整片连续视频、音频、字幕与连贯覆盖，同版媒体哈希，实际独立后审 Agent 的回传证据，以及与基准一致的 continuous_av_model 工具。用户点头不能代替这些检查，历史 v1–v4 结论保留。

默认八阶段链路通过 review_by 将原题/最小动作样片交同一次独立前检，将实测时间线交独立 preflight，将渲染交独立后审；不再在已有评审之前重复生成评审任务。默认成功路径是八任务、十六次认领/完成事件。delivery 是只交接已验收文件的终点，不能生成新的未审素材。自定义独立诊断任务仍保留生产后自动独立复验。

默认工作流及新 v5 工作流在最小样片、配音时间线、渲染、交付前检查 audio/continuous_av 能力及实测基准。缺失时 next 返回 DEPENDENCY_BLOCKED，责任人为 Director，不返回等待用户质检。只有实际解决并运行适配器基准后，才可用 `capability --payload benchmark.json` 注册；payload 包含 name 与 benchmark，基准必须绑定 adapter、三类已检出缺陷及证据哈希。注册不证明适配器真实执行，实际工具回执仍由主控核实，不得用测试夹具替代生产能力。

complete 的 needs-review 与 fail 都必须带 failures：稳定 issue_id、owner、required_checks、severity、evidence 和新版本 repair_outputs。缺能力的修复可指定 repair_capabilities=[] 以便先安装/接入检查工具，随后独立复验仍继承原检查能力；不会通过多次派修把感官要求丢掉。未完成修复也累积原问题次数。新控制器绑定唯一 record_path，带状态的副本不能认领任务或重置台账；这不是对任意外部脚本的操作系统拦截，不允许新建空台账规避。

自动化回归使用明确标识的 fixture Agent、基准与媒体证据，覆盖完整调度链、待审禁止交付、能力前检、内部派修、陈旧证据和同记录恢复。它证明程序控制流程，不证明实际视听工具已经具备能力，也不证明合格内容已经无人干预产出。原片不用来验证调度代码，不为这些回归重新渲染影片。
