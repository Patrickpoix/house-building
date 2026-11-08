# _textures/ — 4K / 8 通道 PBR 贴图库

**16 种材质 × 8 个通道 = 128 张 4096×4096 PNG**，按材质分子目录。
文件名固定为 `<材质>_<通道>.png`，全局唯一，便于按文件名重定位。

## 8 通道

| 通道 | 色彩 | 用途 |
| --- | --- | --- |
| `basecolor` | RGB | 基础色（albedo） |
| `normal` | RGB | 切线空间法线（高度场微分） |
| `roughness` | L | 粗糙度 |
| `metallic` | L | 金属度 |
| `ao` | L | 环境光遮蔽，乘到 Base Color |
| `height` | L | 高度场，驱动 Bump |
| `displacement` | L | 位移强度 |
| `specular` | L | 高光 / IOR Level |

## 16 种材质

| 分组 | 材质 |
| --- | --- |
| 木材 | `oak_wood`、`walnut_wood`、`painted_wood` |
| 石材 / 陶瓷 | `marble`、`floor_tile`、`concrete_floor`、`white_ceramic`、`glazed_terracotta` |
| 织物 / 皮革 | `linen_fabric`、`wool_fabric`、`leather`、`rattan` |
| 金属 | `brass`、`brushed_steel`、`black_steel` |
| 涂料 | `wall_paint` |

## 生成方式

- 8 种材质以 AI 生成的平光俯视 albedo 为源（`reference/ai_source/`），
  其余 8 种为程序化合成；全部再派生出另外 7 个通道。
- 生成脚本：[`../../src/00_textures/make_ai_textures.py`](../../src/00_textures/make_ai_textures.py)
  （`python src/00_textures/make_ai_textures.py oak_wood` 可只重跑单材质）。
- 检视图：`renders/04_材质检视/texture_atlas_4k.png`、
  `pbr_channel_sheet.png`、`ai_source_sheet.png`。

## 材质节点接法

资产库与住宅统一使用 **世界坐标 Position → BOX 三平面投影**（`projection_blend`
≈0.12–0.15），避免薄板拉伸与切段墙竖条纹；AO 乘 Base Color，Height 驱动
Bump，Displacement 接 Material Output，Specular 接 IOR Level；布艺加 Sheen、
釉面加 Coat、拉丝金属加 Anisotropic。4K 贴图**不打包进 `.blend`**，以 `//`
相对路径引用，工程保持轻量且可迁移。
