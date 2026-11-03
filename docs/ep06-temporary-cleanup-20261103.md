# EP06 临时数据清理 — 2026-11-03

用户授权分析并清理EP06临时数据。本轮删除三版已编码全片及局部测试的批量`frame_*.png`（目录full-A1、full-B、local-A1、local-A2、local-B、clip-B），以及Python字节码缓存，共9955个文件、22,606,048,419字节（21.05GiB）。EP06文件逻辑体积由25,503,998,522字节降至2,897,950,103字节（2.70GiB）。此前进度估算混用了十进制GB与GiB，以本记录实测为准。

保留全部42个MP4、20个Blender场景、CAD/源码、Kai原始配音/混音、字幕/时间线、proof及decoded-proof取证图、JSON审计、研究/审批/交付记录。Director记录当前0092bf交付为USER_ACCEPTED_CURRENT_0092_DELIVERY；不改写历史正式QA缺口或验收状态。

删除帧无备份；历史报告及脚本中的帧路径可能失效。重新渲染或原生逐帧复核须重新生成，不承诺旧命令直接复跑。保留成片仍可播放。

执行期间非阻塞持有项目render.lock。删除项均未被Git跟踪；删除前记录逐项大小和SHA256，全部保留文件逐项前后SHA256一致，Git索引SHA256不变。机器清单：[ep06-temporary-cleanup-20261103.json](ep06-temporary-cleanup-20261103.json)。未修改源码、成片或既有记录，未调用配音或渲染服务，未暂存/提交。
