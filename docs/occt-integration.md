# OCCT 技术评估与渲染前检查

## 当前栈与能力重叠（2026-11-05 实查）

| 层 | 已有能力 | 本次选择 |
|---|---|---|
| build123d 0.13.0 | STEP 层级导入、Location、solid、布尔、网格导出 | 继续使用，不另建 CAD 系统 |
| OCP 8.0.1.1 | 当前由 cadquery-ocp-novtk/proxy 8.0.1.1.0 提供 | 复用已安装绑定，不加第二套内核 |
| series.py | 递归 assembly、独立 STEP、全局实例矩阵、正体积验证、ShapeFix | 保留；新检查器也支持独立 occurrence 清单 |
| series_geometry.py / canonical_printer_brep.py | 直接 OCP sewing、solid、BREP 操作 | 已直接使用 OCCT，不重复引入 |
| EP09 check_gear_phase.py | 有界相位交集检查 | 将诊断能力提取为可测试、可绑定的通用检查 |
| scene_fidelity | Blender evaluated rest-state、bounds、矩阵、geometry hash | 复用 inventory；新增 CAD/Blender 边界和位置验证 |
| technical_evidence | 内容寻址、文件摘要、确定性结果 | 复用 digest/canonical，CAD 证据独立于媒体，前移检查 |
| production_gate | 记录、资产及证据绑定 | 新增 v3 full-render/delivery CAD 检查；v1/v2历史兼容 |

直接 OCP 的必要范围：BRepCheck 有效性、BRepExtrema 最短距离和见证点、BRepAlgoAPI_Common 交集体积/包围盒。继续让 build123d 处理导入、实例和变换。全量两两检查 O(n²) 不适合打印机数千实例；显式邻接对/运动对用于局部教学机构，不能冒称整机无干涉。

原型使用 EP09-VIS-004 的 n00149/n00201 独立源 STEP、geometry-audit 源矩阵；149只选小输出 solid。保留原件、历史三轮计数、交付状态。复现成功后才接入门禁。该诊断不生产第四轮媒体修复。

几何通过不能证明齿比、约束、柔性、摩擦、扭矩、动力学、制造或真实机器可运行。有限路径采样可能漏掉样本之间的碰撞。允许接触和过盈必须有明确零件对、理由、体积/间隙阈值；默认不能忽略微小相交。

## 已实现接口与使用

```sh
.venv/bin/python -m mechanical_video.cad_preflight path/to/manifest.json --output new-cad-report.json
.venv/bin/python scripts/production_gate.py --record director-record.json --stage full-render --require-version 3
```

输出文件/回归输出目录必须是新路径，避免覆盖历史证据。返回码：0=所列几何检查通过，1=阻断或输入错误。检查器不修复、不覆盖 CAD、不渲染、不请求供应商。

manifest v1 必填 `schema_version:1, units:"mm"`，以及：

- `parts:[{id,step,matrix_mm}]`：局部独立 STEP 与 mm 世界刚体矩阵。实例 ID 唯一，同一 STEP 可以多次实例化。可提供 `expected_matrix_mm` 检查独立预期装配变换。`solid_selection:"smallest"` 只用于明确选定的小输出轴；会记录选择，不静默丢弃其他实体。
- 或 `assembly_step`：通过现有 build123d XCAF 导入递归解析 STEP 层级，稳定遍历 ID、parent、名称和累积世界矩阵；禁止同时提供 parts。没有标签的 STEP 不会凭空恢复装配语义。
- `pairs:[{parts:[id1,id2],mode,min_gap_mm,max_gap_mm,...}]`：必须显式列邻接对，避免把未检查整机视为安全。默认 clearance 不允许超过 1e-7 mm³ 的交集。数值容差上限 1e-6，不能用放大数值容差掩盖工程干涉。
- `mode:"contact"` 要求 `reason`，默认接触距离容差 .001 mm，仍禁止超容差体积交集。`mode:"press_fit"` 要求 `reason,max_intersection_mm3`；仅允许本零件对、本上限内的交集，不是通用白名单。reason 应引用设计/源证据，算法不能判断该说明是否真实。
- 运动对增加 `samples:[{time,transforms:{id:matrix}}]`，time 非负严格递增，至少两点；matrix 是作用于静态世界形体的**世界增量**刚体变换，不是局部矩阵或绝对装配矩阵。报告精确失败时点与见证点。采样密度由实际运动/小特征确定；跨样本穿越仍可能漏检，PASS 仅限所列状态。不要拿设计过盈策略放行本不允许的运动穿越。
- `scene_inventory,blender_to_mm,scene_objects:{part_id:object_name}`：完整映射所检查 CAD 实例到实际 scene_fidelity inventory，显式单位换算。可用刚体 `scene_from_cad_mm` 表达有来源的舞台平移/旋转；不能通过任意拟合掩盖装配错位。
- `require_mesh_geometry:true`：inventory 中对应对象必须有 `cad_geometry`，通过 `capture_scene(scene,source,renderer,cad_objects=[...])` 在实际 evaluated rest frame 采集。检查包围盒、全部三角面闭合/方向、体积及至多256个确定性顶点到CAD表面的距离。默认 `mesh_tolerance_mm:.3, mesh_volume_relative_tolerance:.02`，由三角化精度和零件尺度明确设定。孔洞、体积或采样偏差失败输出 P1。顶点采样、总体积和边界不构成双向 Hausdorff/精确拓扑等价证明；少于采样尺度的局部差异仍需检查。

## 生产集成与兼容

`production_checks.schema_version:3` 继承全部 v2 门禁，full-render/delivery 新增确定性 CAD 报告关联：`assets.cad_preflight={path,sha256}`；将报告 `inputs` 中每份清单/STEP/scene inventory 也列入 assets。报告源、实现、OCP/build123d版本、结果摘要必须有效且 PASS；每份 CAD 实例需要实际 mesh 几何检查，scene inventory SHA 必须匹配当前 `assets.scene_inventory`。只有旧 bounds 的 inventory 会阻断 v3，须在现有采集流程补采指定对象，不能伪造字段。

正式 `cli --production` 入口要求 v3。脚本/直接 Blender 启动不是受该 CLI 自动拦截的沙箱，Director 必须先运行 v3 full-render gate；本集成没有声称拦截任意 Blender 脚本。历史 v1/v2只读评估保留，不自动迁移已批准记录，不替换 EP09 当前交付。baseline_fidelity、独立机械/视听QA、问题修复计数、人工批准和正式分数门槛全部保留；CAD PASS 不关闭已有问题。

## 真实历史原型结果

EP09-VIS-004 源状态：149/201 交集 **1.26500490499 mm³**；202/207 **0.0083817601463 mm³**，均在渲染前 BLOCKED/P1。149/201 交集范围约为 X122.616..125.260、Y147.500..150.700、Z122.125..124.564 mm。报告同时保留最短距离见证点和修复建议，不把 OCCT 交集顶点当作唯一修复位置。

历史独立 `source-pinion.stl` 与源 STEP：4333顶点，采样256；最大表面偏差约 **5.4053e-6 mm**，体积相对误差 **5.9378e-5**（0.00594%），闭合与方向检查 PASS。该证据仅验证实际历史交换网格，不冒称本次打开 Blender 后修改器执行结果。最终 JSON 路径见 reports/occt 的运行记录；早期报告保留原实现摘要，不与新版实现混用。

可实证的收益是将同类源齿形交集提前复现并阻断渲染；新增测试还证明可拦截重复实例变换错误、缺失接触/间隙、超额过盈、路径中间状态碰撞、网格孔洞/形变、单位/包围盒不一致、证据过期。没有进行对照生产任务，不能量化已经节省的工时/返工次数，也没有修复源齿形或证明真实齿轮不能运转。

## 实际 Blender evaluated-mesh 验证补证

现有 `native_capture` 增加可重复 `--cad-object 对象名` 参数，在保持 host-Metal 预检、render.lock、禁止自动执行场景脚本、输入哈希保护和失败任务保留的前提下，采集局部机构的实际 evaluated mesh。`write_inventory` 同样支持 `cad_objects`。不重建生产系统，也不修改源场景。

最终采集 [blender-capture-v2/capture-result.json](../reports/occt/blender-capture-v2/capture-result.json) PASS，Blender 5.2.3 LTS、1442对象；源场景 SHA `3ec2cb0b2d4a38bb66e85ba8866112314ea3682c58cfd0d46279f3fc6513f1d4` 保持不变。首次实际采集暴露 IDPropertyArray JSON 序列化错误，修复为显式列表后创建新任务；失败 v1/日志/部分输出保留，不伪造 PASS。

使用场景保存的 `presentation_shift_m` 作为明确来源的坐标变换，而非拟合偏移。源 STEP 与本次实际 Blender 网格对照结果：

| 实例 | 顶点数 / 采样数 | 最大表面偏差 mm | 体积相对误差 | 结果 |
|---|---|---|---|---|
| n00201 | 4360 / 256 | 0.00001716 | 0.09240% | PASS |
| n00202 | 5979 / 256 | 0.00002252 | 0.04899% | PASS |
| n00207 | 5005 / 256 | 0.00002305 | 0.07865% | PASS |

全部闭合/方向检查通过，完整映射和包围盒检查也通过。然而202/207源齿形实体仍有约0.00838176 mm³交集，所以 [实际 Blender 对照报告](../reports/occt/ep09-blender-v1/cad-report.json) 整体仍是 BLOCKED/P1；转换一致不能冲销源装配问题。验证基于可复用静态源场景，不是现有 EP09 当前影片全部运动或新版媒体验收。

复现：先用 native_capture 采集这三个对象，再运行：

```sh
```

该回归脚本退出0只表示预期回归行为成立（网格检查通过、源干涉按预期阻断），不表示其 CAD 报告 PASS。生产 gate 只接受实际 CAD 报告本身的 PASS。

本地 EP09 验证助手与报告不随仓库分发。新环境使用上面的通用 `mechanical_video.cad_preflight` 入口，并自行提供有来源记录的 manifest；维护中的几何回归测试位于 `tests/test_cad_preflight.py`。
