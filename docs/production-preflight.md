# 制作放行记录与磁盘预算

适用于新集、续做及受影响局改。Director 将以下字段追加到**当前集既有 director-record**，不另建状态台账；既有授权、hold、修复计数与独立 QA 门槛不变。未具备的项目记录具体缺口，不填虚假的 PASS。

新制作使用 `production_checks` v2，新增[实际基线一致性](scene-fidelity.md)与[就绪交接/阶段事件](production-handoff.md)。历史 v1 记录继续按原口径只读评估，不改写历史结论；`--production` 新任务要求 v2。

## 局部制作前

- `baseline_comparison`：实际参考片/场景/制作源路径及 SHA-256、批准范围、已查看的时间码/帧、沿用项和最小差异。打印机系列先看 EP03 基线及相关机制集；已有方向偏离时补看 EP01～EP04 的对应片段。只读文档、沿用旧任务或列路径不算已查看实际画面。
- `capabilities`：分别记录实际可用的静帧、实时播放、听审、对齐能力与方法；缺口给出下一复核责任人和准确问题。相同资产/能力未变时引用首次记录，不派同能力 agent 重复证明缺口。
- `ready_handoff`：唯一所有者、固定输入及哈希、独占输出、当前出口、完成/失败通知条件。缺上游先留在 Director 待办，不提前启动 agent 占位等待；相关任务复用原 agent，生产与独立 QA 身份保持分离。

派工前按[就绪交接格式](production-handoff.md)运行只读检查；输入未齐不派工，同输入/能力/问题的运行中或已完成结果优先引用。局部静音片用 `video_qa --profile local-silent`，有声局部片用 `local-av`，默认 formal 的长片要求不下调。

## 全片渲染前

- `style_review`：Director 与独立 QA 对照实际早期帧/局部片和基线，记录主体占比、构图、空间关系、连续运动、字幕与声音的同异；指出检查方法和覆盖，静帧不能证明运动或声音。未解决的风格偏离先处理，不等用户发现。
- `baseline_fidelity`（v2）：在本次实际渲染进程中采集 rest-state 清单并与认可基线比较，检查整机、底部、走线和机构。网格、矩阵、支撑、可见性、舞台/相机/灯光/材质及原生设置的差异必须有逐项依据；“其余对象不动”不证明初始状态正确。比较、资产 ID 和独立 A/B 证据格式见[基线一致性](scene-fidelity.md)。
- `overlay_review`：最小样帧从第一轮就合成实际字幕、场景标注和引线，按目标编码尺寸检查；覆盖最长字幕、最密集标注、机构近景及相关动作/字幕切换边界。用原生帧与实际编码样帧核对，不用空白保护框替代字幕。记录样帧/编码哈希、帧号、重叠缺陷和独立复核；参照[字幕位置规范](subtitle-placement.md)。最终编码仍须自己的字幕/标注检查。
- `storage_preflight`：使用下列只读工具记录目标文件系统可用空间、样帧存储设置、剩余帧数、临时空间与余量、报告时间及结果。开始/续渲前重跑；其他任务占用空间或存储格式变化后旧报告失效。BLOCKED 时先制定可逆存储方案，不自动删除素材、改归档或绕过锁。

上述记录由 Director 维护；下述可执行制作放行工具检查完整性与证据关联。它不是全局调度器，风格、字幕、机械与感官结论仍由相应责任人依据实际证据记录。

## 只读磁盘预算工具

```sh
.venv/bin/python scripts/render_storage_preflight.py \
  --sample /absolute/path/to/representative-frame.png \
  --sample /absolute/path/to/dense-frame.png \
  --output-dir /existing/render/output/directory \
  --remaining-frames 2705 --temporary-gib 4 --reserve-gib 2
```

工具只读取样帧文件大小与目标目录所在文件系统的空闲空间，不创建目录、不渲染、不清理、不调用供应商。输出 JSON；退出码 0=预算可容纳，1=空间不足，2=输入错误。若需留档，将 stdout 显式保存到当前新任务目录，并在既有 director-record 引用。

预算为 `最大样帧字节 × 剩余帧数 × 安全系数 + 新增编码/复制临时空间 + 保留空间`。默认安全系数 1.25，临时和保留空间各 2 GiB，必须按实际制作链调整。样帧需与计划帧格式/压缩设置一致，并覆盖复杂场景；低分辨率 proof 或已压缩旧帧不能估算未压缩原生输出。样本最大值和余量是估计，不保证未来所有帧大小或其他进程的磁盘用量。

续渲仅填尚未生成的帧数；已保留文件已扣在系统空闲空间里，不重复扣除。会同时保留原文件和压缩副本、恢复/拼接或跨盘复制时，把峰值新增占用计入临时空间；不同文件系统分别运行预算。空间通过不授予渲染权限，不替代指纹/锁/hold 检查。

## 长任务通知与图像读取

执行者持有长任务进程，完成、失败或阶段变化时通知 Director；Director 收到结果前不反复询问状态。等待使用现有完成机制，在工具与会话进展要求允许的时长内等待；超时本身不是发送追加任务或重复磁盘/帧数查询的理由。只在异常、预计完成时间明显超出或需要作决定时查状态，用户请求状态时正常回应。

视觉定位先读适当分辨率联系表，再打开有疑点的原图/裁剪；字形、指向、细小几何等检查保留所需原生细节。日志中的图片 base64 字符数不按文本 token 解释，也不由此推算费用；缓存、非缓存、输出和协调用量分别审计。

## 可执行制作放行

统一入口（只读、不调用供应商、不渲染）：

```sh
.venv/bin/python scripts/production_gate.py --record /path/to/director-record.json --stage narration --require-version 2
.venv/bin/python scripts/production_gate.py --record /path/to/director-record.json --stage full-render --require-version 2
.venv/bin/python scripts/production_gate.py --record /path/to/director-record.json --stage delivery --require-version 2
```

退出码 0=当前阶段可推进（交付可能仅 `REVIEW_DELIVERY`），1=BLOCKED，2=输入错误。输出 JSON。缺新版字段的旧记录保守阻断，不迁移历史结论。Director 在**既有记录**增量追加 `production_checks`，不得另建制作台账；历史开放问题不能静默删除。工具校验声明与证据关联，不能证明实际碰撞、听感、连续运动或评审者身份真实性。

`production_checks` 共用字段约定（历史 v1 保留；新制作 v2 另需基线资产及检查）：

| 字段 | 内容 |
| --- | --- |
| `schema_version` | 新制作 `2`；历史 `1` 按原口径读取 |
| `assets` | `{资产ID: {path, sha256}}`；必须包含源件、工具头、运动/渲染源、实际时间线、字幕/标注和音效依赖；交付再包含最终媒体。路径相对 director-record 所在目录或绝对路径 |
| `actions` | `{动作ID: [开始秒, 结束秒]}`；完整列展开、回装和相关附件运动，不以检查自己的短区间缩小覆盖 |
| `required_interval` | 当前检查范围 `[开始秒, 结束秒]`，全局检查覆盖全段 |
| `critical_mechanical_uncertainty` | 已依据源件消除关键机械不确定性才填 `false` |
| `holds` / `issues` | 活跃 hold 列表；问题保留 `issue_id, severity, status, repair_attempts, rounds_without_improvement`；仅明确 closed/resolved/verified 视作关闭，不把局部静态关闭升级为全片关闭 |
| `checks` | 以下检查数组，保留旧版本；新增证据必须关联当前资产指纹 |
| `capability_gaps` | 具体缺失能力、方法、首次记录、待答问题与下一评审人；同资产/能力下复用首次记录 |
| `delivery_mode` | `review` 或 `formal`；待审可交付不等于正式验收 |

每个检查必须包含 `kind, action`（全局项为 null）、`status: PASS`、`asset_fingerprints`（资产ID→SHA-256，全量精确相符）、`coverage: [开始秒,结束秒]`、`method, scope, producer, reviewer`、`evidence: [{path,sha256}]`。生产与独立复核身份必须不同；工具只验证声明。几何方法按当前机构选择，不能用一般包围盒零交集替代精确净空验证。工具头、路径或依赖变化必须更新资产，旧检查随即失效。

- narration：每个动作需 `source_action`；附 `source_parts`、`representation: real|teaching|mixed`、`explanation_roles`，说明实际源件与明确标注示意件各承担什么讲解，并引用最小真实画面证据。
- full-render：每个动作需 `source_action, unfold, reassembly, attachments, clearance, neighbors, overlays, foley`；全局需 `style, local_encode, storage`。分别覆盖完整路径、移动附件联动、受影响固定件净空、邻段、实际字幕/标注与机械声时点。`local_encode`/`final_encode` 引用实际 MP4/MOV/MKV 与共享技术包 JSON（identity.media_sha256 匹配，probe/decode 成功且结果摘要完整）；`local_encode` 引用实际局部编码及其检查报告，不接受仅原生静帧。
- `storage` 另需 `created_at`（Unix 秒），预算报告为第一份 evidence，必须由现有磁盘工具生成 PASS 且不超过 15 分钟；每次开始/续渲重跑，参数/目标盘/占用变化立即失效。工具验证报告及新鲜度，不重新测磁盘、不保证未来空间。
- delivery：需全局 `final_encode` 同版最终媒体技术检查。review 模式可保留具体感官缺口，已知 P0/P1、关键机械不确定性、hold 和修复上限仍阻断。
- v2 的 full-render 与 delivery 另需全局 `baseline_fidelity`；门禁根据输入清单重算差异并关联源/执行源哈希，独立 A/B 图及 `reviewed_views` 仍由真实评审负责。历史评估省略 `--require-version 2`，不自动迁移或触发生产。
- formal 另需 `acceptance` 中 `overall≥90, technical≥90, audience≥85, audio_technical≥90, audio_appeal≥85`；各项必须有 score、PASS、当前 asset_fingerprints、不同 producer/reviewer 和 evidence；`all_established_gates_passed: true` 且无能力缺口。分数由实际独立评审提供，工具不计算感官分，也不替代专项 QA 原有维度门槛。

新派工统一引用该阶段结果。通用 CLI 的 `--production` 要求 `--record`，worker 可用 `--record` 在消费前检查；历史 series/remake 入口继续原有 hold。直接 Python API、自定义/手工脚本和未传 record 的非 production 演示不被全局拦截。归档渲染器完全不改。通过工具也不授予制作、批准或发布授权。
