# 就绪交接与阶段审计

以下工具只验证输入和声明的输出所有权，不启动 agent、不调度渲染、不授予授权，也不代替制作门禁。字段追加在既有 director-record，不建立第二套状态台账。历史影片与记录不自动迁移。

## 输入齐备后再派工

Director 在 `production_handoffs` 按任务 ID 追加记录。示例：

```json
{
  "production_handoffs": {
    "local-video-v1": {
      "state": "pending",
      "owner": "independent-video-qa-agent",
      "producer": "visual-agent",
      "role": "video_qa",
      "goal": "检查本版局部编码",
      "scope": "固定版本、指定动作和邻段；不评全片",
      "inputs": {"media": {"path": "editor/local-v1.mp4", "sha256": "ACTUAL_SHA256"}},
      "outputs": ["qa/video/local-v1"],
      "checks": {"decode": "local_exec", "motion": "realtime_playback"},
      "capabilities": {
        "local_exec": {"available": true, "method": "本机 FFmpeg"},
        "realtime_playback": {
          "available": false,
          "question": "本片动作及相邻切换是否连续？",
          "next_reviewer": "具备实时观看能力的独立评审"
        }
      },
      "completion_events": ["completed", "failed", "stage_changed"]
    }
  }
}
```

输入同时列出本次需要的时间线、源事实、技术包及字幕等固定依赖。只有实际可读且哈希匹配才就绪。输出必须在本集目录内，不能覆盖输入、非空旧版本目录或其他 ready/running 任务的输出；真实写入仍由唯一 owner 负责。QA owner 必须不同于 producer。

```sh
.venv/bin/python -m mechanical_video.production_handoff check \
  --record /path/to/director-record.json --handoff-id local-video-v1
```

- `READY`：只派 `ready_checks`；`deferred_checks` 保留具体能力缺口，不把它们当成已经通过。
- `CAPABILITY_GAP`：没有可产生新证据的检查，不派同能力 agent 重复证明缺口。
- `REUSE`：相同角色、目标、范围、固定输入及能力已有 running 任务或有效 completed 结果，引用 `reuse_handoff`，不重复启动。
- `BLOCKED`：输入过期、输出冲突、非独立 QA、缺交接信息等需先解决。退出码1；格式错误退出2；READY/REUSE退出0。

完成后 Director 将任务 state 改为 `completed`，追加 `results: [{path,sha256}]`；运行中为 `running`。改变资产、能力或准确待答问题才建立新版本。失败问题保留原 ID、轮次和证据，不借新任务重置。工具不检查进程存活、不持有文件锁；既有锁、门禁和独立验收继续适用。

每轮一次交齐缺陷清单，保留唯一负责人、根因假设、最小验证、预期可观察改善及受影响邻段。完成、异常或实质阶段变化时通知 Director；等待超时不触发重复消息/续派。先联系表定位，再打开必要原图；要求逐帧检查时明确区间和具体问题，字幕和细小几何保留原生细节。

## 显式阶段开始与结束

以下命令生成当前 UTC 事件，只输出 stdout：

```sh
.venv/bin/python -m mechanical_video.production_handoff phase \
  --phase visual --event start --thread-id REAL_THREAD_ID
```

Director 在实际阶段变化时将输出追加到同一 director-record 的 `workflow_events` 数组；结束用 `--event end`。每条包含 `type: phase_start|phase_end, phase, thread_id, timestamp`，时间戳必须带时区。phase 可为 research/creative/script/visual/audio/editing/qa；记录真实线程，不把所有并行 agent 归到主线程。不能根据事后消息内容补猜时间。

```sh
.venv/bin/python scripts/audit_token_usage.py /explicit/session/logs \
  --root-session REAL_THREAD_ID --production-record /path/to/director-record.json
```

同线程阶段不得重叠，结束必须配对；未结束、无法匹配线程或超出可见日志的事件保留覆盖限制。跨阶段边界的两个累计快照之差无法精确分配，保留为 unattributed；相邻阶段内的明确区间才归属。命令不修改原 session 日志。这是人工记录+只读校验，不是已实现的自动生产调度器。

## 下一次实际制作的比较

Director 在既有记录追加 `workflow_metrics`，未知值用 null：`first_delivery_seconds`、`major_reworks`、`full_rerenders`、`user_found_defects`（保留问题 ID）、`qa_completeness`、`scope`、`quality`。首次交付从授权制作开始到首个完整审看文件交付；用户等待时间单列，不能混入制作耗时。重大返工指已进入全片后因 P0/P1 或用户确认缺陷改变源/场景并重建受影响媒体。

用量审计分别报告缓存/非缓存输入、输出及协调次数，结合交付耗时、重渲和 QA 完整度评估。相同范围与质量且团队覆盖完整才计算变化率；图片载荷字符不是文本 token，不能由此推算费用或承诺节省。


### 主动修复闭环（2026-11-09）

执行[多Agent主动发现、修复与复验](agent-repair-loop.md)。Director在每次已授权制作内主动安排前检、小样和后审，不等待用户指出缺陷；根据实际失败证据交唯一所有者修复，回传后重跑失败检查并交独立评审复验。v4的P0/P1关闭状态必须有稳定issue_id、非空required_checks及同版resolution（对应issue_id、verified、不同producer/reviewer、完整asset_fingerprints、覆盖全部必查项的checks_covered和有效evidence），否则BLOCKED。制作完成不等于修复关闭；上一版本问题同样保留。真实感官能力不足不填分，不重复派同能力代理。当前没有无人值守内容修复调度器，不能将交接检查或渲染worker称为自动内容闭环。
