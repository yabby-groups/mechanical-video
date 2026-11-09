# Evidence-first video QA

Run `.venv/bin/python -m mechanical_video.video_qa VIDEO --output NEW_DIRECTORY --visual`.
The directory must not already exist. The report records the source hash, sampled
frames, full decode result, candidate intervals and the actual provider response.
Exit codes: 0 PASS, 2 REWORK, 3 NEEDS_REVIEW, 4 FAIL. A formal video needs
1080p (portrait or landscape), H.264 and AAC. New work has no universal minimum
duration: preserve complete core causality rather than padding to 90 seconds. Long black, frozen,
or silent intervals are candidates, not proof of defects. Inspect their context.
The visual request describes five actual sampled frames; it is not motion,
mechanical, audio, subtitle, or shot-level certification. Scores remain null
until those dimensions have reliable evidence. Never treat null as a pass.

This is an initial inspection tool, not an automated production or repair
system. Existing series queues, immutable archives, editorial hold, and render
lock remain authoritative. Do not use this report to approve or release a film.


## 连续视听评审入口｜2026-11-09

完整审片必须执行[连续视听评审与证据导入](perceptual-review.md)，扫描工具的NEEDS_REVIEW不能称为通过。使用原片播放包记录实际覆盖与理解时间码，独立评审后导入新报告；缺感官能力则保留明确缺口。delivery_gate重新校验连续视听证据和原始评分，不信任单独PASS标签。


## 内容完整性优先｜2026-11-09

用户原话：“视频不能为了凑时长，而把最关键的漏掉”。对新制作取消统一90秒下限；时长由完整答案决定，不放宽清晰度、源事实或视听验收。审核必须指出标题答案、关键接触/状态切换、完整动作周期的实际时间码。关键因果缺失或看不清，即使时长达标、画面精美也不能内容验收通过；先删重复介绍/拆装/总结，不挤掉核心解释。为展示新证据所需的慢动作可保留，不能将所有慢动作误判为凑时长。旧报告不回写。
