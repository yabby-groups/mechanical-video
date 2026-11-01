# EP03 / EP04 / EP05 存储清理（2026-11-01）

用户要求重点清理三集的大量临时数据。当前生产约束要求保留帧、音频、来源、归档和回滚证据，因此本轮以去除冗余未压缩存储为主，不把历史版本直接判为无效。

## 范围

- EP04：`visual/tube-repair-v1/lossless0-v5/frames/*.png`。
- EP05：`visual/series-realignment-v1/local-6f6da3afd1658fb0675d/frames/*.png`。
- 三集用于音频分析的 `.f32le` 临时PCM文件。

每个文件以 gzip level 1 无损归档到同目录的原名加 `.gz`；读取归档并解压，验证原始字节 SHA256 一致，再删除未压缩副本。仅保存确实缩小的归档。未修改 PNG 编码、画面、音频采样或已归档脚本。所有处理路径、原始/归档大小及双 SHA256 见[机器清单](ep03-ep05-storage-cleanup-20261101.json)。清单 `status=COMPLETE` 才代表整个迁移完成。

## 使用与恢复

现有渲染器、编辑器及历史清单仍指向原始路径，未改写历史记录。要重新编辑、直接查看源帧、运行依赖原始文件的 QA 或恢复任务，先解压所需文件，例如：

```sh
gzip -dk series/3d-printer-v2/episodes-current/EP04/visual/tube-repair-v1/lossless0-v5/frames/000001.png.gz
```

上例文件名仅说明形式，应以机器清单的 `archive` 字段为准。`gzip -dk` 保留压缩归档，不覆盖现有文件。恢复后应比对 `original_sha256`。全量恢复需要预留机器清单所列的原始大小空间；在空间有限时逐帧/按需读取，不要同时展开全部帧。

## 保留与验证边界

EP03约3.5 GiB的旧视觉任务主要已是压缩JPEG，重复压缩几乎无收益，未删除；共享场景仍可能服务EP04/EP05。21个Blender备份均不同于主文件，仍保留。成片、付费配音缓存、原始WAV、CAD、场景、脚本、研究、审批、问题及QA报告保留。

执行期间持有项目现有worker/render/production锁；不并行重建或渲染。三集当前交付视频及交付指针SHA256在处理前后验证，Git索引哈希保持不变。本轮为存储迁移，不是新的视觉、听觉或正式验收，不改变任何批准或NEEDS_REVIEW状态。

## 后续用户明确扩展：删除临时图片、视频和音频

用户随后明确要求定位生成的临时图片并删除，临时视频及音频也清理，最后扩展到EP01/EP02。本轮不再仅做压缩：对明确被当前任务替代的旧任务目录，删除其生成帧、旧预览/合成视频和派生混音；保留源CAD、场景、脚本、JSON审计/审批、QA报告、原始配音及付费缓存。

- [EP03–EP05删除清单](ep03-ep05-obsolete-media-deletion-20261101.json)：逐项原路径、大小、SHA256和类别。
- [EP01–EP02及追加派生混音删除清单](ep01-ep02-obsolete-media-deletion-20261101.json)。
- EP03保留continuous-motion-v3视觉帧与场景，以及speed-sound-v4当前交付和音轨。删除更早的visual/tasks、optimization、formal生成帧与旧编辑输出。
- EP04保留当前tube-repair/lossless0-v5完整帧的无损归档、当前成片、批准局部对照、现用XY-Z混音/拟音及原始配音；删除更早B96、phase75等旧实验生成帧和旧视频。
- EP05保留series-full-v1当前整片及完整帧、获批series-realignment局部片及其帧无损归档；删除旧split/causal/recovery策略生成的中间帧和临时视频。
- EP01保留已接受完整成片和完整生产帧，以及仍未被正式替代的data-driven候选；删除被完整生产帧取代的稀疏preview图片。
- EP02保留最新full-approved成片/帧、approved-full对照、获批corrected-panel片段、共享source-corrected场景；清理更早指纹任务的preview/keyframes、预览视频与mixed-audio/synthetic-foley，原始narration不删除。

删除后的旧实验媒体不再可直接播放或回滚；若需要，必须由保留源输入与归档脚本重新生成。历史清单、旧审计和冻结锁中的已删除路径仍作为历史记录保留，不代表文件继续存在。例如EP04当前归档合成脚本的旧baseline-video PCM对比步骤引用了已删除的旧XY-Z成片；现用混音/拟音和当前成片保留，但原脚本的该历史对比不能原样重跑。EP03更早混音实验同样可能需要先重建中间音轨。不得把“成片哈希未变”解释为所有历史生产命令仍可直接执行。
