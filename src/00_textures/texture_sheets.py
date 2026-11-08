"""生成 PBR 贴图检视图 / 材质总览图。

产出（renders/04_材质检视/）：
  texture_atlas_4k.png     — 16 种材质 basecolor 网格
  pbr_channel_sheet.png    — 8 种 AI 材质的 8 通道矩阵
  ai_source_sheet.png      — 8 张 AI 原图（albedo 源）
"""
from PIL import Image, ImageDraw, ImageFont
import os

# --- 路径自举：项目可任意改名/搬家，向上找到 config.py 即可 ---
import sys as _sys, pathlib as _pathlib
_sys.path.insert(0, str(next(p for p in _pathlib.Path(__file__).resolve().parents
                            if (p / "config.py").is_file())))
import config as C
C.ensure_dirs()

CHANNELS = C.CHANNELS
OUT = str(C.R_SHEETS)
AI_NAMES = ["oak_wood", "walnut_wood", "marble", "linen_fabric",
            "leather", "brass", "white_ceramic", "rattan"]


def font(sz=15):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        if os.path.exists(p):
            return ImageFont.truetype(p, sz)
    return ImageFont.load_default()


def atlas():
    names = sorted(m for m in C.MATERIALS if C.tex(m, "basecolor").exists())
    cell, cols = 300, 4
    rows = (len(names) + cols - 1) // cols
    sh = Image.new('RGB', (cols * cell, rows * (cell + 26)), (245, 245, 245))
    d = ImageDraw.Draw(sh)
    for i, n in enumerate(names):
        im = Image.open(C.tex(n, "basecolor")).convert('RGB').resize(
            (cell, cell), Image.LANCZOS)
        x, y = (i % cols) * cell, (i // cols) * (cell + 26)
        sh.paste(im, (x, y))
        d.text((x + 5, y + cell + 4), n, fill=(20, 20, 20), font=font(14))
    sh.save(os.path.join(OUT, "texture_atlas_4k.png"))
    print("ATLAS", len(names), sh.size)


def channel_sheet():
    cell, lab = 170, 26
    cols = len(CHANNELS)
    rows = len(AI_NAMES)
    sh = Image.new('RGB', (cols * cell, rows * (cell + lab) + 32), (250, 250, 250))
    d = ImageDraw.Draw(sh)
    for j, c in enumerate(CHANNELS):
        d.text((j * cell + 5, 6), c, fill=(20, 20, 20), font=font(15))
    for i, n in enumerate(AI_NAMES):
        for j, c in enumerate(CHANNELS):
            p = C.tex(n, c)
            if not p.exists():
                continue
            im = Image.open(p).convert('RGB').resize((cell, cell), Image.LANCZOS)
            x, y = j * cell, 32 + i * (cell + lab)
            sh.paste(im, (x, y))
            if j == 0:
                d.text((x + 4, y + cell + 4), n, fill=(20, 20, 20), font=font(13))
    sh.save(os.path.join(OUT, "pbr_channel_sheet.png"))
    print("CHANNEL_SHEET", sh.size)


def ai_source_sheet():
    cell, cols = 280, 4
    sh = Image.new('RGB', (cols * cell, 2 * (cell + 26)), (245, 245, 245))
    d = ImageDraw.Draw(sh)
    for i, n in enumerate(AI_NAMES):
        p = C.AI_SOURCE / f"src_{n}.png"
        if not p.exists():
            continue
        im = Image.open(p).convert('RGB').resize((cell, cell), Image.LANCZOS)
        x, y = (i % cols) * cell, (i // cols) * (cell + 26)
        sh.paste(im, (x, y))
        d.text((x + 5, y + cell + 4), n, fill=(20, 20, 20), font=font(14))
    sh.save(os.path.join(OUT, "ai_source_sheet.png"))
    print("AI_SOURCE_SHEET", sh.size)


if __name__ == "__main__":
    atlas()
    channel_sheet()
    ai_source_sheet()
    print("SHEETS_DONE")
