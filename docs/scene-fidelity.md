# 基线场景一致性

EP07 session `01a19cbe-6a2d-7f01-b746-3340fd94c295` 的首版保留了 914 个网格，却重置了配套矩阵并删除 8 个无 `part_id` 的支撑。234 个零件因此落到舞台下方。逐帧“固定件不动”只能证明没有继续移动，不能证明初始状态正确。

新制作使用 `production_checks.schema_version: 2`；历史 v1 仅按原口径读取，不迁移或重写原报告。`--production` 新任务要求 v2。自定义制作在配音、全片、交付检查命令加 `--require-version 2`；历史恢复仍核对原授权、指纹、hold、锁和旧记录，不因版本变化重跑已接受影片。

## 在实际进程中采集

先打开认可的 `.blend` 并设置选定的基线帧，在当前进程记录参考场景。参考清单可按相同源/工具哈希复用。新渲染器打开相同源场景、完成本集必要调整后，在施加拆装动作前记录实际 rest state；不在全片后另启动 Blender 作为编码前置条件。

```python
from mechanical_video.scene_fidelity import write_inventory

# source_blend 是本次实际打开的认可场景；renderer 是实际冻结执行源。
# 调用前已设置所记录的基线/rest 帧；该函数更新依赖图，不加载或渲染场景。
write_inventory(task_dir / 'scene-inventory.json', scene, source_blend, renderer)
```

输出使用独占创建，不覆盖旧清单。记录所有场景对象，包括无 `part_id` 的支撑、舞台、相机和灯光；MESH 使用求值后的网格与世界矩阵，保留变形后的皮带/导管配对。记录世界边界、材质/节点、对象/集合可见性、原生输出设置及采集实现指纹。清单是 rest state 证据，不能代替完整动作、净空、取景、最终编码或感官检查。

参考/实际清单必须来自同一源场景。世界矩阵平移和边界默认容差 0.001mm，线性矩阵元素 1e-7；网格哈希精确匹配。单位比例改变也会报差异。

## 默认原生采集入口

macOS 本机的独立采集默认使用执行器已授权的 host GPU 路径；不先在无 Metal 的沙箱内启动 Blender。默认命令：

```sh
.venv/bin/python -m mechanical_video.native_capture \
  --scene /absolute/path/to/baseline.blend \
  --renderer /absolute/path/to/frozen-renderer.py \
  --output /absolute/path/to/new-capture-task
```

该命令在启动前检查 Metal，独占 render.lock，保留原生场景设置，并复制本次采集 worker、记录输入指纹及完整 Blender 日志。只读加载保存场景并导出 `scene-inventory.json`；renderer 参数只用于关联，不执行该渲染器、不渲染影片、不覆盖源场景。默认使用保存帧，可用 `--frame` 明确选择；超时默认120秒，无自动重试。

在无 GPU 的受限执行器中，命令不启动 Blender、不创建采集目录，返回退出码3和 `GPU_ACCESS_REQUIRED`。Agent 应直接通过工具的单次 host GPU 授权执行同一命令；脚本不能自行授予 GPU 权限，也不修改 sandbox 或 macOS 安全配置。不要用 CPU 替换原渲染设置。可用 Metal 且实际清单成功才返回 PASS/0；真实失败保持 BLOCKED、保留日志，使用新版本任务排查。

该独立入口用于读取已有场景、参考清单或明确的重载检查；新全片仍优先在已有渲染进程内调用 `write_inventory`，避免重复启动 Blender。技术采集成功不代替实际画面、动作或感官验收。

## 声明最小差异

`scene-policy.json` 默认为 `{"schema_version":1,"changes":[]}`。必要的相机、字幕或教学几何差异逐项写为：

```json
{
  "schema_version": 1,
  "changes": [{
    "object": "$scene",
    "field": "camera",
    "before_sha256": "SHA256_OF_OLD_VALUE",
    "after_sha256": "SHA256_OF_NEW_VALUE",
    "reason": "本集机构近景相机"
  }]
}
```

值的哈希使用 `mechanical_video.scene_fidelity.canonical(value)`。对象字段直接用清单名称；全局设置为 `$scene`，整个对象的新增/删除字段为 `$object`，缺失值为 JSON null。重复、无理由、过期和未使用的例外阻断；不允许笼统忽略所有运动零件。运动件仍须有正确初始位置，再由动作审计验证路径。

```sh
.venv/bin/python -m mechanical_video.scene_fidelity baseline.json scene-inventory.json \
  --policy scene-policy.json
```

命令只读并向 stdout 输出报告；0=PASS，1=差异/过期例外，2=输入错误。将结果保存到本次新任务目录，供独立复核。哈希是关联和完整性检测，不是真实性签名。

## v2 门禁关联

在既有 director-record 的 `production_checks.assets` 增加以下资产 ID，沿用 `{path,sha256}` 格式：

| ID | 内容 |
| --- | --- |
| `baseline_scene` | 实际认可源 `.blend` |
| `renderer` | 本次冻结渲染入口源文件；其他脚本仍作为依赖资产列出 |
| `baseline_inventory` | 实际参考清单 |
| `scene_inventory` | 实际新渲染进程采集的 rest-state 清单 |
| `scene_policy` | 最小差异清单 |

全片与交付新增全局 `kind: baseline_fidelity, action: null` 检查，沿用覆盖、全量资产指纹、producer/reviewer 不同及 evidence 哈希要求。evidence 必须含比较报告 JSON 和实际 A/B 图；`reviewed_views` 至少包含 `whole_machine, bottom, routing, mechanism`。打印机的 routing 同时检查皮带和 PTFE 供料通路；不存在的结构在独立报告说明，不补造几何。

Director 和独立 QA 分别查看这些实际视图，覆盖整机/底部、皮带/导管及机构近景。门禁重算清单差异并关联源/渲染器指纹，不能只凭报告的 PASS 放行；工具不验证评审者身份真实性，也不代替实际 A/B 判断。

保存后重载若不可用，保留其独立缺口；同进程采集不伪称完成保存场景重载验证。归档脚本保持不变，新源进入新任务；不能复用不同渲染器的帧。
