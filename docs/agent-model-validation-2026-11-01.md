# Agent 模型分配验证 — 2026-11-01

> 以下 Sol5/Terra7/Luna1 为首轮配置的历史验证，已由当日后续 Luna 优先配置取代：Luna8/Terra5/Sol0。原试派和用量数据保留，不作为新配置的完整运行验证；后续验证见 [validation.md](validation.md#luna-first-agent-routing--2026-11-01)。旧文末“恢复对应角色 Sol”策略也由当前工作流的按子任务升级规则取代。

## 配置与实际执行

13 个角色 TOML 可解析：Sol 5 个、Terra 7 个、Luna 1 个；并发配置仍为 `max_threads = 4`。未更改主会话模型、权限、TTS、媒体或批准范围。角色职责和升级入口见 [协作规范](../.codex/agent-workflow.md#模型分配与升级)。

客户端 `codex-cli 0.166.0`。配置写入后，当前会话工具自动更新并显示绑定模型，三个只读试派均成功。运行模型以本地 session JSONL 的 `turn_context.model` 为证据，不采用 agent 自述推断；供应商内部路由不可独立核验。

| Agent | 角色 | session ID | turn_context 模型 / effort |
| --- | --- | --- | --- |
| model_smoke_sol | director | 01a1948b-b6df-75c1-a2d9-8b5261a758cb | gpt-6.1-sol / low |
| model_smoke_terra | script | 01a1948b-c79b-7030-9161-631e22b9cac0 | gpt-6.1-terra / low |
| model_smoke_luna | audio | 01a1948b-e84b-7cf3-836a-dbfcdcf72680 | gpt-6-luna / medium |

Sol、Luna 显式传与角色相同的模型，均未设置 reasoning override；Terra 通过固定模型的 script 角色启动，实际 effort 为 low。未验证所有 13 个角色的逐一执行，也未现场模拟生产问题升级/回退。

## 固定输入比较

复用现有片段报告，不查看/生成媒体，不重新验收影片：输入为 `series/3d-printer-v2/episodes-current/EP04/qa/motion-appeal-xy-full-v1/video-replacement-review.json`，SHA256 `9f20fd03cfedce0193e296ec710643875cd393960990a56fbbf9adc92d554bf6`。

三个 agent 接到相同只读任务：仅从该文件提取影片哈希、图片数量、实时观看/听审覆盖及是否通过，缺失写 unavailable，最多 200 字。三者均正确提取影片 SHA256 `3ac2fd7145b38d590d44624e3b18324364f28f96920b70f1ba04fce3d090445a`、8 张图片、实时/听审各 0 秒、null 分数与 NEEDS_REVIEW，均未擅自判定通过。重做次数为 0；主代理直接核对原 JSON，属于事实提取核验，不是独立媒体 QA。

| 模型 | 比较轮耗时秒 | 累计缓存输入 | 累计非缓存输入 | 累计输出 | 其中 reasoning 输出 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Sol | 6.220 | 77952 | 25593 | 234 | 0 |
| Terra | 9.552 | 132352 | 25277 | 506 | 0 |
| Luna | 4.867 | 76288 | 24577 | 482 | 82 |

耗时为第二轮 turn_context 到最后事件的墙钟差，不包含主线程等待/准备；token 为各子线程两轮（配置冒烟与报告提取）的最新累计计数，包含工具调用上下文，不是比较轮独立 token。角色指令不同、缓存状态不同、样本仅一次，不构成受控速度或成本排名。reasoning 是输出子项，不重复相加。

用量由 `scripts/audit_token_usage.py <三个session.jsonl> --format json` 只读审计；结果见 [原始元数据审计](agent-model-usage-2026-11-01.json)。协同动作另计：主线程 3 次 spawn、3 次 followup、1 次 list；Terra 子线程另有 2 次 send_message。主线程 token 未做本任务独立归因，完整协调用量 unavailable，不汇总为总成本。

## 结论与后续门槛

配置解析、运行模型及固定输入的事实提取检查通过；Terra 当前可执行，不再是此前工具列表缺失时的阻塞。配置规则已说明自定义角色模型优先级，跨模型升级须通过未固定模型入口并保留职责、问题及修复计数。

本次未运行生产流程、媒体实时观看/听审、整集创意比较或完整制作成本实验；这些不属于配置成功证据。媒体评分仍为 null/NEEDS_REVIEW，未承诺节省比例。未来真实固定片段任务需记录同等验收质量的返工、完整用量和独立 QA；出现质量下降或返工增加按协作规范恢复对应角色 Sol，保留比较记录。
