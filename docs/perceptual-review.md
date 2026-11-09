# 连续视听评审与交付门禁

2026-11-09修复：静帧扫描报告不能作为整片体验结论。现有视频/观众评分权重和正式片门槛不变。本流程补上可执行的播放、时间码、理解复述及证据导入路径，不代表工具已经具有自动视频/音频感知能力。

## 先检查能力与身份

Director在准备本集时明确生产者ID及独立评审者，检查后者是否能实际连续观看和听审。独立QA名额优先预留，不先耗尽派工预算再以生产者自检替代。代理预算不足或感官能力缺失，只记录一次具体缺口并继续不依赖该缺口的制作；交付只能是待审版，不能标正式通过。已获用户接受的历史版本不重复要求接受，历史独立QA缺口仍保留。

只有静帧工具时不派“完整体验审核”任务，不靠提高模型、ASR、解码、音量曲线或自动播放补齐听审。连续视听模型只有在实际工具能力和调用返回被验证后才可登记；本次没有验证可用的自动连续视听接口，也没有发起供应商调用。可由具备能力的独立人工评审使用本地播放器，或由以后验证可用的连续视听工具按同一证据契约提交。工具修复者不可独立验收依赖本次修复的影片。

## 1. 生成原片播放包

```sh
.venv/bin/python -m mechanical_video.perceptual_review prepare /absolute/final.mp4 \
  --output /absolute/new-review-packet --producer-id actual-producer-id
```

输出目录必须不存在；包含原片独立复制、task.json、review-template.json和review.html。原片不改写、不重编码、不调用生成。prepare退出3，明确仍是NEEDS_REVIEW。可直接打开review.html用本地浏览器播放；浏览器若限制本地媒体，使用普通本地静态服务器并只绑定127.0.0.1。无需上传文件。

页面可以标时间码、填写观察并导出播放日志。事件日志只说明播放器事件，不证明注意力、听见声音或理解。正常速度全片连续观看并听审，在必要位置暂停复查；仅拖动播放头或顺序查看静帧不能登记为实时体验。保持整个输入版本不变，所有路径使用绝对路径。

## 2. 独立评审填写证据

复制模板至新的review.json，不覆盖原模板。task.json中的producer_ids由Director依据实际任务冻结，不能由评审者改成自己想要的列表。review.json填写：

- 实际评审者ID、独立声明、使用工具、方法与完成时间。
- 实际观察日志/模型原始响应等证据文件的绝对路径及SHA256。报告和日志不得引用不存在或已变更文件。
- video/audio/captions/continuity四类实际观察区间、具体观察与证据引用。完整片必须覆盖整个片长，局部片段不得冒充整片。
- 八个带时间码的问题：开头问题是什么；首次因果是否看懂；中段新增什么；能否复述答案；点赞潜在价值；收藏潜在价值；后续关注理由；结尾是否兑现。
- 首次因果或可复述答案为unclear/absent时，记录REWORK。点赞/收藏/关注价值的缺失是具体诊断，不自动变成P1；不得强行增加求赞/关注口播。
- 缺陷保留已有issue ID、严重度、时间段、责任人与修复计数；本工具不关闭旧问题或重置上限。

内容标准：评审不得先读制作方解释来替观众补全画面。第一遍记录自己实际看到的“谁动了、碰到哪里、结果为何改变”；再核对事实与生产说明。阅读脚本能够理解不等于原片清楚。每段明确新增信息，移动相机不是新信息；结尾完整回答本集，不扣留答案制造关注。

校验：

```sh
.venv/bin/python -m mechanical_video.perceptual_review validate /absolute/review.json \
  --task /absolute/new-review-packet/task.json
```

COMPLETE表示证据契约齐备，不是评分通过、机械事实认证、正式影片验收或增长保证。校验器可检查哈希、身份声明、时间范围与内容字段，无法认证身份真伪，也不能从日志证明真实感知。Director仍须核对实际评审者和原始证据，不能用伪造JSON满足门禁。

## 3. 导入到新报告

观众评审另填dimensions，沿用audience_qa.WEIGHTS中的六项；每项包含score、time、evidence（证据路径列表）、rationale。视频专项另填video_dimensions，沿用video_qa.WEIGHTS，音频维度仍从同版本独立Audio QA报告获得，不能由视频评审补分。技术扫描已发现的问题保留。

```sh
.venv/bin/python -m mechanical_video.perceptual_review finalize /absolute/review.json \
  --task /absolute/new-review-packet/task.json --kind audience \
  --base-report /absolute/audience-qa-report.json --output /absolute/new-audience-reviewed.json
```

video专项使用--kind video和同版本qa-report.json。输出必须是新文件；失败/理解不清导入为REWORK而非丢失缺陷，缺证据不能导入通过。历史报告不改写。独立视频与观众身份仍按原角色职责核实，不能由一个生产者填写两份报告代替两类独立判断。

## 4. 核对交付

audience_qa.delivery_gate现在重新核对同版哈希、两类连续视听证据、独立身份、覆盖、评分字段和总分；裸PASS/高分不能放行。CLI的--technical-report路径也调用这一门禁。生成扫描报告新增review_kind、blocking_gaps和formal_acceptance=false，防止扫描结果被称作影片通过。

门禁返回PASS仍只是视频/观众这一组条件；正式交付另外保留两类最终混音QA、机械事实、用户批准/hold和其他既有门槛。不得将delivery_gate单独称为发布许可。旧generic acceptance模块是历史渲染资产检查，不是本系列独立观众验收，禁止据其ACCEPTED输出发布本系列。

## 本次落实与残余

已实现本地播放器、证据校验、评审导入和防标签绕过门禁，并准备近期两条原片待审包。测试中的独立评审数据是合成测试fixture，不能作为真实影片结论。实际完整观看、听审和独立观众评分仍未完成；下一责任人为具备连续视听能力且未参与相关生产/本工具修复的评审者。没有完成事件前，影片状态保持NEEDS_REVIEW。本次不请求用户重复批准，不自动重剪、不改平台。


### 2026-11-09内容优先的时长规则

用户明确新片不能凑时长而漏掉最关键内容。以AGENTS当前规则为准：取消统一90秒下限，先证明标题答案、关键接触/状态切换、完整动作周期，再编排必要的展开与回装。记录实际时间码与看懂证据；缺少核心因果不能正式通过，技术检查与片长不替代内容验收。旧报告与已批准媒体不改写。
