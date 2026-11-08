# CHANGELOG

当前交付版本 **v4.1（工程化重构 · 资产可迁移化 · 去重瘦身 · 任意组装）**，也是工程内保留的唯一版本。
历史基线、旧版产物与过程记录已清理；实测数据与质量边界见 `docs/04_验收报告.md`。

## 当前版本做了什么

**起因**：产物目录混乱、资产藏在单个 `.blend` 里不可见、路径硬编码；
后续要求支持按类查看、单独取用、整包搬家、跨会话接手，且**每个资产保留一份
完整可复用的 PBR**、不存重复实现。

### 结构

- 原地重构，不建副本；只保留最新版，删除历史基线、旧版对比图、`.blend1`
  备份、过时脚本与空目录。
- `src/` 按流水线 5 阶段分层（16 个脚本）；`assets/` 分 `_textures` / `_library` /
  `by_category`；`renders/` 按 4 类用途分目录；128 张贴图按 16 材质分子目录。

### 零硬编码 / 可迁移

- `config.py` 作为唯一路径源：用自身位置推导 ROOT，支持
  `HOUSE_BUILDING_ROOT` 覆盖；`src/` 下全部脚本 `import config as C`。
- 全项目 `.py` **0 处**绝对路径字面量；所有 `.blend` 贴图为 `//` 相对路径，
  由 `config.rel()` 统一计算；`relink_all.py` / `migrate_check.py` 支持搬家后
  一键修复与自检。

### 36 类 / 144 个资产真实可见、每个可复用

- `export_assets.py` 把母库拆成 144 个独立目录，每个含 **`model.blend`**
  （完整 4K / 8 通道 PBR，引用共享贴图）、**`preview.png`**（Cycles 真实材质
  预览）、**`meta.json`** 三件套。
- 36 个类别各配 `README.md`（4 变体对照表）与 `preview.png`（2×2 拼图）。
- 预览由灰模改为 Cycles 12 采样 + OIDN 降噪，并按 4K albedo 平均色写回
  `diffuse_color`，任意视图模式下颜色都与真实贴图一致。

### 去重瘦身（本次）

同一份资产不再存两套。删除的重复实现：

| 删除项 | 体积 | 原因 |
| --- | --- | --- |
| 144 个 `model.glb` | 503.7 MiB | 几何与 `model.blend` 完全重复，内嵌的是 1K 缩略贴图 |
| `asset_library_showcase.blend` | 44 MiB | 144 个模块的几何副本，仅用于出一张陈列图 |
| `renders/05_版本对比/` 3 张 | 2.4 MiB | 版本沿革图，工程只保留最新版 |

工程体积 **1.20 GiB → 0.66 GiB**。`model.blend` 仍是每个资产独立、完整、
可整体搬走复用的 PBR 本体。跨软件单文件复用的能力不丢，改为按需：
`src/04_tools/export_glb.py` 按资产 ID / 类别号 / `all` 临时导出自包含 GLB，
用完可删，默认不生成任何重复文件。`showcase.py` 只渲染 PNG、不再落盘副本 blend。

### 文档与自检

- 9 份文档；入口 `README.md`，验收依据 `GOAL.md`，接手指南 `docs/01_目录规范.md`。
- `verify.py` 检查 `portable`（144 资产三件套完整性 + 相对路径）、`structure`
  （文档 / 源码 / 配置齐备）与 `layouts`（布局 JSON 合法性）；
  `migrate_check.py` 无 bpy 也能跑基础自检。

### 任意组装（本次新增）

用户核心诉求：**保留高质量 PBR 资产，像参考视频那样能用资产库任意组装成不同房屋**。
此前只有一栋把房型与摆设写死在 `build_house.py` 里的固定住宅。新增：

- `src/02_scene/assemble.py`：读一份声明式布局 JSON（房间尺寸 / 隔墙 / 门窗 /
  资产清单 / 相机 / 灯光），从母库 `asset_library.blend` 按 ID 实例化资产，用同一套
  共享 4K 贴图生成建筑壳体，输出一栋全新的 `.blend`。改 JSON = 换房型，不碰建模代码。
- `scene/layouts/` 3 份开箱即用布局：`family_100.json`（100㎡ 三居 / 27 资产）、
  `studio_45.json`（45㎡ 公寓 / 20 资产）、`loft_open.json`（无隔墙 Loft / 25 资产）。
- `scene/assembled/` 三栋实测房屋 `.blend` + 俯视预览 + 对比图（可再生，可整目录删除后重跑）。
- `docs/09_任意组装指南.md`：完整字段手册、查资产命令、5 步拼新房流程。
- 自检纳入布局 JSON 合法性与资产 ID 校验（`verify.py` / `migrate_check.py`）。

三栋房屋均用同一套 144 个资产拼出，资产本体零改动、零新增副本。
