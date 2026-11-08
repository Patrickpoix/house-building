"""迁移自检：把整个项目搬到别的文件夹 / 别的电脑后，跑一遍确认无损。

检查：
  1. config.ROOT 是否正确解析到当前位置（不残留任何绝对路径）
  2. 目录树是否完整
  3. 128 张 4K 贴图是否齐全
  4. 36 类 / 144 个资产独立包是否齐全
  5. 所有 .blend 内贴图是否为可解析的相对路径（抽查母库 + 房屋 + 抽样独立资产）
  6. 所有 .py 是否不含硬编码绝对路径
  7. 声明式布局 JSON 是否齐全、资产 ID 是否合法

用法（在任意位置、任意文件夹名下）：
    python src/04_tools/migrate_check.py

只依赖 config.py + 标准库 + PIL；Blender 检查需要 blpython（bpy）环境，
缺失时自动跳过并提示。
"""
from __future__ import annotations
import sys, os, re, json, glob
from pathlib import Path

# --- 路径自举 ---
sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents
                            if (p / "config.py").is_file())))
import config as C

OK, BAD = "  OK   ", "  FAIL "
issues: list[str] = []


def chk(label, cond, detail=""):
    print(f"{OK if cond else BAD} {label}{('  ' + detail) if detail else ''}")
    if not cond:
        issues.append(label)


def main():
    print("=" * 66)
    print("house-building 迁移自检")
    print(f"解析到的项目根：{C.ROOT}")
    print("=" * 66)

    # 1. 目录
    print("\n[1] 目录树")
    missing_dirs = [str(d.relative_to(C.ROOT)) for d in C.ALL_DIRS if not d.is_dir()]
    chk("全部必需目录存在", not missing_dirs, str(missing_dirs) if missing_dirs else "")
    chk("config.py 位于根目录", (C.ROOT / "config.py").is_file())

    # 2. 贴图
    print("\n[2] 4K PBR 贴图")
    missing_tex = [str(p.relative_to(C.ROOT)) for p in C.all_textures() if not p.exists()]
    chk(f"{len(C.MATERIALS)} 材质 × {len(C.CHANNELS)} 通道齐全", not missing_tex,
        f"缺 {len(missing_tex)} 张" if missing_tex else "128/128")
    try:
        from PIL import Image
        bad_size = []
        for m in C.MATERIALS:
            p = C.tex(m, "basecolor")
            if p.exists() and Image.open(p).size != (4096, 4096):
                bad_size.append(m)
        chk("basecolor 均为 4096×4096", not bad_size, str(bad_size))
    except ImportError:
        print("  SKIP  PIL 不可用，跳过分辨率检查")

    # 3. 资产包
    print("\n[3] 独立资产包")
    cat_dirs = [p for p in C.BY_CATEGORY.iterdir() if p.is_dir()] if C.BY_CATEGORY.exists() else []
    asset_dirs = [p for p in C.BY_CATEGORY.rglob("AST_*") if p.is_dir()] if C.BY_CATEGORY.exists() else []
    chk(f"类别目录 {len(cat_dirs)} 个", len(cat_dirs) == len(C.CATEGORIES))
    chk(f"资产目录 {len(asset_dirs)} 个", len(asset_dirs) == 144,
        f"期望 144，实得 {len(asset_dirs)}")
    required = ("model.blend", "preview.png", "meta.json")
    incomplete = [str(p.relative_to(C.ROOT)) for p in asset_dirs
                  if any(not (p / f).exists() for f in required)]
    chk("每个资产三件套齐全", not incomplete,
        f"缺 {len(incomplete)} 个" if incomplete else "144/144")

    # 4. 零硬编码
    print("\n[4] 零硬编码绝对路径")
    hardcoded = []
    for py in sorted((C.SRC).rglob("*.py")):
        for i, line in enumerate(py.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(r'["\']/(workspace|root|home|Users)/', line):
                hardcoded.append(f"{py.relative_to(C.ROOT)}:{i}")
    chk("源码内无绝对路径字面量", not hardcoded, str(hardcoded[:5]))
    # .blend 相对路径
    print("\n[5] .blend 贴图相对路径")
    try:
        import bpy
        for blend in (C.LIBRARY_BLEND, C.HOUSE_BLEND):
            if not blend.exists():
                chk(f"{blend.name} 存在", False)
                continue
            bpy.ops.wm.open_mainfile(filepath=str(blend))
            imgs = [i for i in bpy.data.images if i.source == 'FILE']
            abs_p = [i.filepath for i in imgs if i.filepath and not i.filepath.startswith('//')]
            broken = [i.filepath for i in imgs
                      if not os.path.exists(bpy.path.abspath(i.filepath))]
            chk(f"{blend.name} 全相对路径", not abs_p, f"{len(imgs)} 张")
            chk(f"{blend.name} 贴图可解析", not broken,
                f"断链 {len(broken)}" if broken else "")
        # 抽样 3 个独立资产
        samples = [p / "model.blend" for p in asset_dirs[::max(1, len(asset_dirs) // 3)][:3]]
        for s in samples:
            if not s.exists():
                continue
            bpy.ops.wm.open_mainfile(filepath=str(s))
            imgs = [i for i in bpy.data.images if i.source == 'FILE']
            broken = [i.filepath for i in imgs
                      if not os.path.exists(bpy.path.abspath(i.filepath))]
            chk(f"抽样 {s.parent.name} 贴图可解析", not broken,
                f"断链 {len(broken)}" if broken else f"{len(imgs)} 张")
    except ImportError:
        print("  SKIP  当前 Python 无 bpy，跳过 .blend 检查（用 blpython 重跑可完整校验）")

    # 6. 交付文件
    print("\n[6] 场景与文档")
    for p in (C.HOUSE_BLEND, C.PLACEMENT_JSON, C.ROOT / "README.md",
              C.ROOT / "docs" / "01_目录规范.md", C.ROOT / "docs" / "08_迁移指南.md",
              C.ROOT / "docs" / "09_任意组装指南.md",
              C.ROOT / "src" / "02_scene" / "assemble.py"):
        chk(str(p.relative_to(C.ROOT)), p.exists())

    # 7. 声明式布局（任意组装能力）
    print("\n[7] 声明式布局")
    layouts = sorted(C.LAYOUTS.glob("*.json")) if C.LAYOUTS.exists() else []
    chk("至少 1 份布局 JSON", len(layouts) >= 1, f"共 {len(layouts)} 份")
    ids = {ln.split(",")[0] for ln in C.CATALOG_CSV.read_text(encoding="utf-8")
           .splitlines()[1:] if ln.strip()}
    for p in layouts:
        L = json.loads(p.read_text(encoding="utf-8"))
        bad = [a["asset"] for a in L.get("assets", []) if a["asset"] not in ids]
        chk(f"{p.name} 资产 ID 合法", not bad, f"{len(L.get('assets', []))} 个资产")

    print("\n" + "=" * 66)
    if issues:
        print(f"发现 {len(issues)} 项问题：")
        for x in issues:
            print("   -", x)
        sys.exit(1)
    print("全部通过：本副本可独立继续开发与渲染。")
    print("=" * 66)


if __name__ == "__main__":
    main()
