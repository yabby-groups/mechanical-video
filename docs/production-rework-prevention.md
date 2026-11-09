# 从反复返工追溯到上游门禁（2026-11-09）

问题不是缺少计划，而是计划没有约束实际制作；几何、记录、局部认可被误当成核心解释成立。由 Director 在制作前发现、定位并处理这些问题，不能把用户当第一轮质检。

## 已查到的实际失效

1. 原始 [EP03 简报](briefs/everyday-mechanisms-batch-20261106.md) 要求卷簧回卷、制动锁止与释放。实际 `EVERYDAY_EP03/reference-remake-v3/narration.txt` 完整讲尺头厚度补偿；同目录 narration/full-render 门禁为 READY，delivery 为 REVIEW_DELIVERY。动作清单可自行改写，门禁只核对新清单，从未追溯原题。
2. `EVERYDAY_EP02/director-record.json` 的 `PEN-CONTACT-CLARITY-001` 已三次修复，仍写着因果接触不清楚。局部造型认可不能关闭这一 P1。反复整片制作放大了未解决的小样问题。
3. `EVERYDAY_EP03/internal-repair-v7/repair-record.json` 记录 V6 壳体遮住外部按钮/槽、尺钩缺翻边和铆接关系。正体积、可导入 CAD 不证明输入能操作、连接真实或功能完整。
4. 自定义 Python 渲染脚本可直接运行，命令未绑定门禁；旧版问题移到 `prior_version_issues` 后不再阻断。末端感官评审只能发现成片缺陷，无法预防这些制作浪费。

以上路径相对 `series/everyday-mechanisms/episodes/`。详见 [实物记录回归](../reports/rework-prevention-20261109/historical-audit.json)，不改写历史结论。

## 新制作执行顺序

1. Director 从原始简报冻结 `assets.approved_brief` 和 `assets.content_contract`。contract schema_version=1，包含原题 question、brief 路径/hash、requirements。每项有稳定 id、原文 brief_quote、可见 observable、source_parts。独立评审须对照原简报确认完整性；不得把未解决的原题改成容易做的旁题。改变原题需要用户授权，普通实现决策由 Director 自主处理。
2. 在任何新配音/整片制作前，先做最小静音动作小样。固定叙述草稿，在 `production_checks.content_review` 逐项回答：脚本哪句解释它，源件是什么，实际输入如何经过连接/接触产生输出，前后状态在哪，是否看得清。局部小样制作属于发现问题的上游步骤，不要求先有最终片或正式感官分数。
3. 独立评审对照实际源件与小样审查：完整外壳状态下按钮可达、穿壳连接连续、接触/释放/复位成立、主物可辨认、关键因果可复述。只看正体积、拆开后的内部或无输入的独立零件不足。关键信息不清先改镜头/表示方法，再审同一局部，不能先扩成整片。缺能力时 Director 定位阻断分支，不反复重渲或要求用户来找缺陷。
4. 合格后再配音、实测时长、分配整片结构。核心动作与问题答案优先，时长随解释需要；无统一 90 秒下限。终片每个 requirement 必须对应最终媒体 hash、时间区间和实际复核证据，避免剪辑漏掉关键段落。
5. 保留旧问题 id/计数；v4 同时检查 prior_version_issues。未关闭 P0/P1 继续阻断；局部认可、改名字、换版本不清零。达到已有修复上限停止该策略并诊断，不能用新名字重跑。

## 可执行入口

新记录用 `production_checks.schema_version=4`。v4 继承 CAD/基线/独立评审规则，同时校验题意追溯、脚本原文、完整 requirement 集、独立身份、全部资产 hash、前后状态、真实可解码小样、输入/连接/输出说明；交付再校验最终片中的对应区间。缺项即 BLOCKED。字段的可运行范例见 `tests/test_content_contract.py`；测试数据仅证明程序行为，不是影片评审。

自定义新配音、整片渲染、交付命令必须走：

```sh
.venv/bin/python -m mechanical_video.production_run \
  --record /absolute/path/to/director-record.json --stage full-render \
  -- /absolute/path/to/python /absolute/path/to/frozen-renderer.py
```

完整 argv 必须同时等于 `production_checks.execution[stage]` 与独立评审记录的 `production_checks.content_review.execution[stage]`；把实际 renderer、scene、脚本和参数配置文件列入 assets，独立评审使用同一份指纹。入口在启动前重复检查 v4 和记录身份；BLOCKED 不运行子进程。生产 CLI 的 `--production` 与显式带记录的 worker 也要求 v4。原始归档脚本不回写；历史 v1–v3 只读评估口径保留。

## 能力与责任边界

这是明确的程序阻断和证据追溯，并不是自动理解视频的模型。名字不同不能证明独立代理真实存在；填入原文不能证明理解正确；两张状态图不能证明连续动作或情绪体验。独立评审必须真实执行且留下观察证据。当前未接入经过验证的自动连续视听评审能力，因此不能宣称机器已经包办共鸣、听感与全片因果理解。

入口是协作执行约束，不是操作系统级拦截：直接运行旧脚本仍可绕开，运行时并发改文件也没有被全局锁住。不得宣称所有路径已强制接管。新任务须由 Director 使用该入口、冻结源文件、独占输出；无授权不触碰在制 V7，也不伪造其评审。执行成功仅说明命令退出，绝不代表内容正式验收。


EP03 的原题约束已按原简报提取为 [内容契约](briefs/EVERYDAY_EP03-content-contract-20261109.json)。它固定回卷、锁止、释放复位三个必答点，不代表 V6/V7 已通过。生产记录的 approved_brief 使用契约中相同的绝对路径/hash；content_contract 绑定本文件的实际路径/hash。


### 渲染前检查实际姿态（2026-11-09）

新渲染器必须在第一次出图前，用正式制作同一个 pose 回调逐帧运行 [场景预检](pre-render-scene-checks.md)，检测关键部件出框/过小、指定表面遮挡、连接锚点脱开和缺失运动。静态保存场景不能代替自定义 pose 求值。v4 full-render/delivery 额外要求绑定同版 source/renderer/policy、完整 requirement 和逐帧覆盖的 `assets.scene_preflight`。缺失或失败先阻断，不等用户发现；不把几何 PASS 宣称为完整视觉/因果理解。保留在制与归档脚本，接入独占新版本；当前真实 Blender 回归状态见 validation.md。
