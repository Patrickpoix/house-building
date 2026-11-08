"""house-building 唯一路径源（Single Source of Truth）。

设计契约
--------
1. 本文件位于项目根目录。**整个 house-building/ 文件夹可以任意改名、搬到
   任何磁盘 / 任何操作系统**，所有路径自动跟着变，不需要改任何一行代码。
2. 根目录解析优先级：环境变量 HOUSE_BUILDING_ROOT > 本文件所在目录。
   仅在把 config.py 单独拆出去使用的特殊场景才需要设环境变量。
3. 所有脚本一律通过 ``import config as C`` 取路径，禁止再写死绝对路径。
4. 所有 .blend 内的贴图引用一律使用 Blender 相对路径 ``//``，由
   ``config.rel()`` 统一计算；迁移后跑 ``src/04_tools/relink_textures.py``
   可一键重定位。

目录约定见 docs/01_目录规范.md；迁移步骤见 docs/08_迁移指南.md。
"""
from __future__ import annotations

import os
from pathlib import Path

__version__ = "4.1.0"

# ---------------------------------------------------------------- 根路径
_env_root = os.environ.get("HOUSE_BUILDING_ROOT", "").strip()
ROOT: Path = Path(_env_root).expanduser().resolve() if _env_root else Path(__file__).resolve().parent

# ---------------------------------------------------------------- 顶层目录
SRC: Path = ROOT / "src"
ASSETS: Path = ROOT / "assets"
SCENE: Path = ROOT / "scene"
RENDERS: Path = ROOT / "renders"
REFERENCE: Path = ROOT / "reference"
DOCS: Path = ROOT / "docs"

# ---------------------------------------------------------------- 资产库
LIBRARY_DIR: Path = ASSETS / "_library"
LIBRARY_BLEND: Path = LIBRARY_DIR / "asset_library.blend"
CATALOG_CSV: Path = ASSETS / "catalog.csv"
TEXTURES: Path = ASSETS / "_textures"
BY_CATEGORY: Path = ASSETS / "by_category"

# ---------------------------------------------------------------- 场景
HOUSE_BLEND: Path = SCENE / "house.blend"
PLACEMENT_JSON: Path = SCENE / "placement.json"
VERIFY_JSON: Path = SCENE / "verify_result.json"

# 声明式布局（组装器的输入）与组装产物
LAYOUTS: Path = SCENE / "layouts"          # 每份 JSON = 一栋房屋的配置
ASSEMBLED: Path = SCENE / "assembled"      # 由布局生成的房屋 .blend（可再生，不入库）

# ---------------------------------------------------------------- 参考素材
AI_SOURCE: Path = REFERENCE / "ai_source"
VIDEO_FRAMES: Path = REFERENCE / "video_frames"

# ---------------------------------------------------------------- 渲染输出
R_SHOTS: Path = RENDERS / "01_空间主图"
R_CLOSEUPS: Path = RENDERS / "02_资产特写"
R_HERO: Path = RENDERS / "03_4K主图"
R_SHEETS: Path = RENDERS / "04_材质检视"

# ---------------------------------------------------------------- 常量表
CHANNELS: tuple[str, ...] = (
    "basecolor", "normal", "roughness", "metallic",
    "ao", "height", "displacement", "specular",
)

MATERIALS: tuple[str, ...] = (
    "oak_wood", "walnut_wood", "marble", "linen_fabric",
    "leather", "brass", "white_ceramic", "rattan",
    "brushed_steel", "black_steel", "concrete_floor", "floor_tile",
    "glazed_terracotta", "painted_wood", "wall_paint", "wool_fabric",
)

CATEGORIES: tuple[tuple[str, str, str], ...] = (
    ("01", "餐椅", "Seating"),
    ("02", "桌案", "Tables"),
    ("03", "沙发", "Sofas"),
    ("04", "柜体", "Cabinets"),
    ("05", "床具", "Beds"),
    ("06", "收纳与布艺", "StorageTextile"),
    ("07", "灯具", "Lighting"),
    ("08", "厨电", "Appliances"),
    ("09", "锅具", "Cookware"),
    ("10", "餐具", "Tableware"),
    ("11", "杯具", "Drinkware"),
    ("12", "瓶器", "Vessels"),
    ("13", "水槽龙头", "Sinks"),
    ("14", "洁具", "Sanitary"),
    ("15", "门", "Doors"),
    ("16", "窗", "Windows"),
    ("17", "五金", "Hardware"),
    ("18", "电子", "Electronics"),
    ("19", "绿植", "Plants"),
    ("20", "书本", "Books"),
    ("21", "装饰摆件", "Decor"),
    ("22", "挂画", "WallArt"),
    ("23", "地毯", "Rugs"),
    ("24", "窗帘", "Curtains"),
    ("25", "靠垫", "Cushions"),
    ("26", "毛巾织物", "Towels"),
    ("27", "餐具小件", "Utensils"),
    ("28", "调味容器", "Condiments"),
    ("29", "清洁用品", "Cleaning"),
    ("30", "厨具", "KitchenTools"),
    ("31", "户外阳台", "Outdoor"),
    ("32", "办公", "Office"),
    ("33", "卫浴配件", "BathAcc"),
    ("34", "结构件", "Structural"),
    ("35", "生活杂项", "Misc"),
    ("36", "收纳容器", "Containers"),
)

ALL_DIRS: tuple[Path, ...] = (
    SRC, ASSETS, SCENE, RENDERS, REFERENCE, DOCS,
    LIBRARY_DIR, TEXTURES, BY_CATEGORY,
    AI_SOURCE, VIDEO_FRAMES,
    R_SHOTS, R_CLOSEUPS, R_HERO, R_SHEETS,
    LAYOUTS, ASSEMBLED,
)


# ---------------------------------------------------------------- 工具函数
def ensure_dirs() -> None:
    """创建全部目录（幂等）。脚本启动时调用一次即可。"""
    for d in ALL_DIRS:
        d.mkdir(parents=True, exist_ok=True)
    for m in MATERIALS:
        (TEXTURES / m).mkdir(parents=True, exist_ok=True)


def tex(material: str, channel: str) -> Path:
    """某材质某通道的 4K 贴图绝对路径。"""
    if channel not in CHANNELS:
        raise ValueError(f"未知通道 {channel!r}，应为 {CHANNELS}")
    return TEXTURES / material / f"{material}_{channel}.png"


def tex_by_name(filename: str) -> Path | None:
    """从贴图文件名（如 ``oak_wood_basecolor.png``）反查绝对路径。

    用于重定位 .blend 内的历史贴图引用：无论文件被移到哪个材质子目录，
    只要文件名保持 ``<材质>_<通道>.png`` 就能找到。
    """
    stem = Path(filename).stem
    for m in MATERIALS:
        prefix = m + "_"
        if stem.startswith(prefix):
            channel = stem[len(prefix):]
            if channel in CHANNELS:
                return tex(m, channel)
    return None


def all_textures() -> list[Path]:
    """全部 128 张贴图路径（顺序稳定）。"""
    return [tex(m, c) for m in MATERIALS for c in CHANNELS]


def rel(target: Path | str, from_blend: Path | str) -> str:
    """计算从某个 .blend 出发的 Blender 相对路径（``//`` 前缀）。

    Blender 的 ``//`` 是相对 .blend 所在目录，跨平台统一用正斜杠。
    """
    t = Path(target).resolve()
    base = Path(from_blend).resolve().parent
    relpath = os.path.relpath(t, base).replace(os.sep, "/")
    return "//" + relpath


def category_dir(no: str, cn: str, en: str) -> Path:
    """某一类资产的目录：assets/by_category/01_Seating_餐椅/"""
    return BY_CATEGORY / f"{no}_{en}_{cn}"


def asset_dir(no: str, cn: str, en: str, asset_id: str) -> Path:
    """某一个资产的目录。"""
    return category_dir(no, cn, en) / asset_id


def bootstrap() -> Path:
    """供任意层级的脚本调用：把项目根加入 sys.path，返回 ROOT。

    用法（每个脚本开头三行，零硬编码）：
        import sys, pathlib
        sys.path.insert(0, str(next(p for p in pathlib.Path(__file__).resolve().parents
                                   if (p / "config.py").is_file())))
        import config as C
    """
    import sys
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    return ROOT


if __name__ == "__main__":
    print(f"ROOT = {ROOT}")
    print(f"贴图数 = {len(MATERIALS)} 材质 x {len(CHANNELS)} 通道 = {len(MATERIALS)*len(CHANNELS)}")
    print(f"资产类别 = {len(CATEGORIES)}")
    for d in ALL_DIRS:
        print(("OK  " if d.is_dir() else "MISS"), d.relative_to(ROOT))
