# assets/ — PBR 资产库

本目录是项目主体：**36 类 / 144 个 PBR 资产**，全部可单独取用。

| 子目录 | 内容 |
| --- | --- |
| [`by_category/`](by_category/README.md) | ★ **36 类 / 144 个独立资产**，按类别分目录，每个资产一个独立包 |
| [`_textures/`](_textures/README.md) | 16 材质 × 8 通道 = 128 张 4096×4096 PNG |
| `_library/` | Blender 母库 `asset_library.blend`（144 个 `AST_` Collection），供房屋场景做实例引用 |
| `catalog.csv` | 144 个资产的唯一索引（ID / 类别 / 尺寸 / 材质 / 部件数） |

完整索引与逐类明细见 [`../docs/02_资产总表.md`](../docs/02_资产总表.md)，
取用与迁移见 [`../docs/08_迁移指南.md`](../docs/08_迁移指南.md)。

## 单个资产包结构

```
by_category/03_Sofas_沙发/AST_03_001_沙发_A/
├── model.blend    ★ 资产本体：完整 4K / 8 通道 PBR，引用共享贴图（// 相对路径）
├── preview.png    Cycles 真实材质预览（360×360）
└── meta.json      尺寸 / 材质 / 部件 / 顶点 / 依赖贴图清单
```

每个资产只有**一份几何 + 一套完整 4K PBR**。不再同时存一份内嵌 1K 缩略贴图
的 glTF 副本（几何与 `model.blend` 完全重复，144 份约 500 MiB，已删除）。

## 依赖约定

- `model.blend` 用 `//` 相对路径引用 `_textures/`，**保持整个 `house-building/`
  文件夹结构即可整体搬走复用**；只拷单个目录时按 `meta.json` 的 `textures`
  字段连对应材质贴图一起带，或在新位置跑 `relink_textures.py`。
- 贴图文件名格式固定 `<材质>_<通道>.png`，`config.tex_by_name()` 依赖它做重定位。
- **要拿到别的 3D 软件 / 网页里用**：按需导出自包含 GLB，见下方「可选：导出 GLB」。

## 可选：导出 GLB（按需，不预生成）

需要把某几个资产交给 Unity / Unreal / three.js / 网页查看器时，一条命令临时导出
内嵌贴图的自包含 GLB，用完可删，不影响工程本体：

```bash
blpython src/04_tools/export_glb.py -- AST_01_001_餐椅_A       # 单个资产
blpython src/04_tools/export_glb.py -- 01 03 07                # 按类别号
blpython src/04_tools/export_glb.py -- all                     # 144 个全量
```

产物写到各资产目录的 `model.glb`（内嵌 1K 贴图，单文件 2–4 MB）；
`model.blend` 始终保持完整 4K 引用，不会被改写。
