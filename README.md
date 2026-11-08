# house-building

用 Blender（headless `bpy`）程序化生成的一套 **36 类 / 144 个 PBR 资产库**，
用这套资产搭建固定样板住宅，并提供**声明式布局组装器**——改一份 JSON 就能把
同一套资产拼成任意房型的房屋。交付全部可复现脚本。

> 参考视频只作**质量标尺**（建模完成度 / 资产数量 / PBR 完整度），不照搬其风格。
> 住宅为自主设计的「温暖日光 · 现代自然风」。

## 一眼看懂

| 项 | 结果 |
| --- | --- |
| PBR 资产 | **36 类 / 144 个**，每个资产独立目录，含 `model.blend`（完整 4K PBR）+ 预览 + 元数据 |
| 贴图 | **16 材质 × 8 通道 = 128 张 4096×4096 PNG**（BaseColor / Normal / Roughness / Metallic / AO / Height / Displacement / Specular） |
| 几何 | 1416 部件 / 45 万顶点，含曲面软包、位移布料、参数化叶片、路径圆管、平滑旋转体；205 个部件带真实顶点位移 |
| 住宅 | 10×10 m = 100 ㎡，107 个资产实例 / 76 种资产，真实板条地板、门套、开关、筒灯、窗帘、窗外天空 |
| 出图 | 6 机位主图 + 5 张资产特写 + 3840×2160 4K 主图 + 材质检视图 |
| 可组装 | **声明式布局 JSON → 任意房屋**：`src/02_scene/assemble.py` 读布局，从母库实例化资产，改 JSON 就换房型（内置 3 栋示例） |
| 可迁移 | **零硬编码**，整个文件夹可改名 / 搬到任何电脑；`.blend` 全用 `//` 相对路径，保持目录结构即可整体复用 |

## 先读这几份

| 文档 | 内容 |
| --- | --- |
| [`docs/01_目录规范.md`](docs/01_目录规范.md) | **接手先看**：目录树、命名约定、改哪里、为什么这样分层 |
| [`docs/02_资产总表.md`](docs/02_资产总表.md) | 36 类 / 144 个资产的完整索引 |
| [`docs/03_快速开始.md`](docs/03_快速开始.md) | 依赖、流水线顺序、局部改动怎么重跑 |
| [`docs/04_验收报告.md`](docs/04_验收报告.md) | 自检数据、质量边界、诚实说明的不足 |
| [`docs/08_迁移指南.md`](docs/08_迁移指南.md) | **搬到别的电脑 / 单独取用资产**的完整步骤 |
| [`docs/09_任意组装指南.md`](docs/09_任意组装指南.md) | ★ **像搭积木一样把资产拼成不同房屋**（布局 JSON 手册） |
| [`assets/by_category/README.md`](assets/by_category/README.md) | 按类浏览 144 个资产 |

其它：`docs/05_视频解析.md`、`docs/06_平面布局.md`、`docs/07_环境说明.md`。

## 目录速览

```
house-building/            可整体改名 / 搬家
├── config.py              ★ 唯一路径源（改路径只改这里）
├── src/                   源码，按流水线阶段分 5 个子目录
│   ├── 00_textures/        贴图生成与检视图
│   ├── 01_assets/          资产母库构建 + 144 独立资产导出
│   ├── 02_scene/           固定住宅搭建 + ★ 声明式组装器
│   ├── 03_render/          出图
│   └── 04_tools/           自检 / 迁移 / 路径修复 / 按需导出 GLB / 对比
├── assets/
│   ├── _textures/          128 张 4K 8 通道贴图（按材质分目录）
│   ├── _library/           Blender 资产母库
│   └── by_category/        ★ 36 类 / 144 个独立可迁移资产
├── scene/                 住宅工程 / ★ 布局 JSON / 组装房屋 / 自检数据
├── renders/               按用途分类的最终出图
├── reference/             AI 源图与视频关键帧
└── docs/                  文档
```

## 快速开始

```bash
cd house-building
python src/04_tools/migrate_check.py       # 先自检结构是否完整
blpython src/04_tools/verify.py            # 全面自检（需 bpy）
```

完整流水线见 [`docs/03_快速开始.md`](docs/03_快速开始.md)。
`blpython` = 装了 `bpy==4.5.x` 的 Python。

## 四种使用方式

1. **整套继续开发**：整个文件夹拷走 → `migrate_check.py` → 按流水线改脚本。
2. **只拿几个资产**：进 `assets/by_category/<类别>/<资产ID>/`，取 `model.blend`
   （完整 4K PBR）并连同它用到的 `assets/_textures/<材质>/` 一起拷；
   要交给别的 3D 软件，就用 `export_glb.py -- <资产ID>` 按需导出自包含 GLB。
3. **任意组装成不同房屋**：改 `scene/layouts/*.json`（面积 / 隔墙 / 资产清单），跑
   `blpython src/02_scene/assemble.py -- <布局.json> --render`，见 `docs/09_任意组装指南.md`。
4. **看成果**：`renders/01_空间主图/`、`renders/03_4K主图/hero_4k.png`、
   `scene/assembled/三栋房屋对比.png`。

## 质量边界（如实说明）

没有 Tripo / image2.6 / 扫描资产 / GPU，因此：
法线来自高度场微分而非高模烘焙；几何是参数化曲面而非手工雕刻，
形态仍偏规整；部分合成材质（釉面陶土 / 刷漆木 / 乳胶漆）观感偏平；
只交付静帧。这些是工具链硬约束，详见 `docs/04_验收报告.md`。
