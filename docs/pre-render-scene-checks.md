# Blender 出图前的画面结构检查

2026-11-09。此前存在静态 CAD、rest-state 清单与渲染后小样，但缺少对实际自定义逐帧姿态的统一预检。尤其 EP03 V6 在 `pose(frame)` 中直接改变几何、相机和字幕，每帧随后出图，最后才 `pose(1)` 并保存场景。只检查保存的 `.blend` 不能覆盖实际动画。

## 新入口：求值，不出图

`mechanical_video.scene_preflight.audit` 在 Blender 已构建真实场景之后、第一次 `bpy.ops.render.render()` 之前调用。传入正式渲染完全相同的 pose 回调；检查每个必答机制窗口的每个整数帧，不采用只看首尾两帧的方式。恢复原帧/姿态，不保存源场景、不调用渲染或生成服务。

```python
from mechanical_video.scene_preflight import audit

# --preflight-only 模式：沿用正式场景与 pose，不进入任何出图循环。
report = audit(scene, policy_path, source_path, __file__, new_report_path, pose=pose)
if report['status'] != 'PASS':
    raise RuntimeError('Pre-render scene proof blocked')
# 先退出预检模式；Director 绑定报告后，通过 production_run 启动正式制作。
```

新渲染器必须将场景构建、pose 和出图循环分离，提供预检后退出的模式，不能 import 一个会立即渲染的旧脚本来检查。已归档及其他会话正在使用的渲染脚本不回写；新任务在其独占新版本中接入。现有场景有真实保存关键帧时可用 `pose=None` 与 `pose_mode:saved_animation`；有自定义姿态函数时必须 `renderer_callback`，不能只打开复位后的场景替代。

## 当前能够阻断的缺陷

- 关键零件不存在或被 render/collection 隐藏。
- 关键零件 evaluated 包围盒出相机视锥或近远裁切范围，或在最终编码分辨率下过小。
- 指定关键表面锚点被壳体、其他零件或自身遮住；用 evaluated mesh 建 BVH 从相机发射几何射线。外部按钮应有外部可见锚点，不能只检查拆壳后的按钮。
- 指定输入/连接两侧锚点间距超出源结构允许值，发现脱开、漂浮等明确连接错误。
- 规定窗口内关键件没有足够的实际位置/方向/形状包围盒变化。
- 缺帧、漏掉原题 requirement、报告与实际源/渲染器/策略/实现 hash 不一致。

检查策略 schema_version=1，要求 `pose_mode` 和非空 `requirements`。每项有稳定 id、`frames:[起帧,止帧]`、motion_object、min_motion、targets、connections。target 包含 object、本地表面 point、min_pixels 和世界坐标 tolerance；connection 两端分别包含 object/point 及世界坐标 max_distance。每项的帧区间、源件与容差由 Director/机械评审按实际机制明确，不能以默认宽松值代替。可运行策略与新建合成场景见 `scripts/validate_scene_preflight.py`。

变形网格的表面锚点可用非负整数 `vertex_index` 或 `face_index` 代替静态 `point`，两种索引不能并用。它们分别读取当前求值网格的顶点或多边形中心，并在释放临时网格前复制坐标；面中心可避免恰好命中三角形边缘的数值歧义。索引越界或对象不是网格会阻断，不能回退静态点。刚性连接仍优先使用来源明确的本地坐标。该支持的单元验证不替代真实 Blender/正式 pose 复验；旧局部扩展产生的报告不因共享实现新增支持而追认通过。

## 与制作门禁绑定

v4 full-render/delivery 现在必须有 `assets.scene_preflight`。报告 inputs 的 source/renderer/policy 分别与 assets 的 `scene_source`、`renderer`、`scene_preflight_policy` 完全对应，使用绝对路径/hash；所有报告输入都列入 assets。报告覆盖的 requirement ID 必须与原题契约完整一致；每个规定窗口不漏整数帧，PASS 且无失败，输入和检查实现未变化。缺任何一项都会 BLOCKED。

最小动作小样也应先调用同一无出图预检；全片前再用完整实际动作窗口预检。预检本身属于生成局部媒体之前的准备步骤，不受“先要有小样才能合成配音”的循环依赖限制。

## 不可扩大结论

读脚本可以发现显式逻辑错误，但只靠文本不能知道 Blender 修改器、约束和相机求值后的结果。这里实际执行场景构建和姿态计算，仍没有渲染像素。

几何射线不理解透明材质、光照、反射、文字可读性、运动模糊、景深和观众理解；因此透明/剖开教学场景可能得到保守的遮挡阻断，不能随意关闭检查来放行。相机 border/panorama、集合实例和特殊可见性不在支持范围，须明确阻断或补专用检查。包围盒位移不是动力学验证，连接锚点不是源零件拓扑证明，检查单个可见点不代表整个接触面清晰。CAD 精确实体干涉和源对应继续用 CAD 门禁；最终感官仍需实际小样/成片复核。不能承诺“读脚本一定发现所有画面问题”。

## 验证状态

单元与门禁集成检查见 validation.md。已准备六个 Blender 无出图回归：正常可见、壳体遮挡、出框、过小、断连、无动作。回归脚本设置 render_pre 禁止渲染。首次启动被既有 render.lock 占用挡住，Blender 未启动；实际运行结果仅在 reports/pre-render-scene-20261109/results.json 存在并核对后才成立。不得把夹具或程序测试冒称生产片实测。


### 动作声明与逐帧状态核对（2026-11-09）

本次卷尺V7复核已确认开头/结尾动作与字幕相反或错位；执行[动作声明核对](caption-action-alignment.md)，v4 full-render/delivery 必须绑定 action_alignment、action_alignment_policy、motion、timeline 及原题requirement。门禁会重算，不信单独PASS；“回收”却拉出、“解除”却加锁不能交给用户发现。场景预检目标必须包含穿壳连片及关键接触件，不能只测整个机构/可见按钮。新增检查不能倒填为旧V7已经通过；原片与旧批准记录保留。
