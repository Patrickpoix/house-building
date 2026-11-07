# Tripo Studio 功能与后处理
2026-11-07；项目 house-building

## 两层界面，绝不混淆

**左侧独立模块**（截图）：图片、模型、部件拆分、重拓扑、智能UV、纹理生成、绑定。点选其中一个会切换工作流程，可能各自另收费，并非全是当前“生成模型”的参数。

**模型模块内部**：高精度模型 H3.0/H3.1（主力）或智能网格 P2.0（另一条生成路线）、输入图片/文本、PBR、纹理、去光、三角/四边拓扑、面数、AI补全、分部件生成、纹理2K/4K、超清精度等。参数是否同时存在、是否互斥与真实积分，均以当前UI为准。
**P2.0智能网格太贵：平时不使用，也不需要对它进行批量价目穷举。** 官方基准约100积分/次，不等于完整PBR成品价。

## 左侧模块：家具用途与默认决策

| 独立工具 | 作用 | 家具生产中的策略 |
|---|---|---|
| 图片 | Studio内生图/处理图 | 优先复用资产或Codex Images2.6，避免重复付费 |
| 模型 | 从图/文本生成3D；HD与Smart Mesh两种路线 | 主要H3.0/H3.1，同配置同价优先H3.1，允许较长生成时间；P2不作为常规路线 |
| 部件拆分 | **生成之后**将已有模型切成可独立操作的件 | 柜门、抽屉、把手、锅盖等有价值；检查分割精度、闭合、材质保留、加价；先比Blender免费拆分 |
| 重拓扑 | **生成之后**降低面数、重建拓扑 | Blender方案优先；仅在能显著减少返工时使用。官方文档提示可能导致原UV/贴图失效，须核验返贴图的总成本 |
| 智能UV | **生成之后**自动展开贴图UV | 非常规必选；官网限制三角≤8万、四边≤4万；变更UV可能丢原贴图，且需单独收费 |
| 纹理生成 | **独立后处理**：给现有/上传网格生成或重绘材质 | PBR与纹理是最终成品硬要求；2K默认、4K按需、8K不使用。若模型生成时已得到合格PBR，不要再付费重复做一遍 |
| 绑定 | **后处理**：角色骨架与动作 | 家具项目基本不用；柜门/抽屉开合在Blender做刚体层级、旋转轴与关键帧，无需人物骨骼 |

**重要区别**：生成模型面板的“分部件生成” ≠ 左侧独立“部件拆分”；生成时的“纹理生成” ≠ 左侧对已有网格重新纹理化。避免为了同一结果重复收费。

## 生产阶段用法
当前64组理论配置已完成主要报价调查：32组有生成前按钮价、32组因模型内分部件与纹理互斥不适用。价格与截图证据见 STUDIO_PRICE_MATRIX_REPORT.md、STUDIO_PRICE_MATRIX.csv 和 price-evidence/。

日常使用高精度HD生成+完整PBR与纹理（通常2K，近景重点4K），同价优先H3.1。去光默认开启、AI补全/增强在已测不加价且质量有益时优先开启；各项实际生成前核对界面报价与最终质量。独立部件拆分、重拓扑、智能UV和纹理/PBR后处理只在相应资产确实需要时采用，并检验原UV和贴图的保留。

已有A030生成及PBR/近景验证见 outputs/A030/QUALITY_REVIEW.md。后续优化参数应以真实资产质量和Blender返工成本为依据，结合现有积分与房间资产计划安排生产。


## 官方制作工艺核对
- Tripo Studio多视角输入可用2—4张一致参考，主要按正、左、背、右；顶视和其他辅助视角在Blender校形及场景中使用。
- 单件资产优先清晰、独立、光照均匀的参考图。整屋先固定空间尺寸、AABB占位和物体清单，再逐件替换与精修。
- Remove Lighting针对BaseColor中的烘焙光照，不改变网格；导出GLB后核对PBR贴图通道和UV。需要保留四边面的进一步编辑，可考虑FBX并复核导出结果。
- Tripo Codex与Blender室内案例：https://developers.tripo3d.com/en/cookbook/codex-blender-interior-scene
- 多视角说明：https://www.tripo3d.ai/product-doc/model-generation/multi-view-to-3d
- 导出说明：https://www.tripo3d.ai/product-doc/export-and-integration/export-dcc
## Tripo官方参考资料
- https://www.tripo3d.ai/product-doc/getting-started/pricing-credits
- https://www.tripo3d.ai/product-doc/module-post-processing/segmentation
- https://www.tripo3d.ai/product-doc/module-post-processing/retopo
- https://www.tripo3d.ai/product-doc/module-post-processing/smart-uv
- https://www.tripo3d.ai/product-doc/module-post-processing/texture-pbr
- https://www.tripo3d.ai/product-doc/module-post-processing/rigging-animation