"""通用双图对比工具：给任意两张图片生成带标签的左右对比图。

不依赖任何基线目录：把优化前后的两张图路径直接传进来即可。

用法：
    python src/04_tools/compare.py <图A> <图B> <输出名.png> ["A 标签"] ["B 标签"]

第 3 个参数即输出图片路径（想放哪就写哪），不绑定任何固定目录。
"""
from PIL import Image, ImageDraw, ImageFont
import os, sys

# --- 路径自举 ---
import pathlib as _pathlib
sys.path.insert(0, str(next(p for p in _pathlib.Path(__file__).resolve().parents
                            if (p / "config.py").is_file())))
import config as C
C.ensure_dirs()

try:
    FONT_S = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 15)
except OSError:
    FONT_S = ImageFont.load_default()


def load(path):
    return Image.open(path).convert("RGB") if os.path.exists(path) else None


def fit(im, w, h):
    c = im.copy()
    c.thumbnail((w, h), Image.LANCZOS)
    return c


def side_by_side(a_path, b_path, out_path, label_a="BEFORE", label_b="AFTER",
                 cw=760, ch=500, bar=34):
    a, b = load(a_path), load(b_path)
    if a is None or b is None:
        print("SKIP 缺少输入", a_path if a is None else b_path)
        return False
    fa, fb = fit(a, cw, ch), fit(b, cw, ch)
    sh = Image.new('RGB', (cw * 2 + 12, ch + bar), (248, 248, 248))
    sh.paste(fa, ((cw - fa.width) // 2, bar + (ch - fa.height) // 2))
    sh.paste(fb, (cw + 12 + (cw - fb.width) // 2, bar + (ch - fb.height) // 2))
    d = ImageDraw.Draw(sh)
    d.text((12, 8), label_a, fill=(20, 20, 20), font=FONT_S)
    d.text((cw + 24, 8), label_b, fill=(20, 20, 20), font=FONT_S)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    sh.save(out_path)
    print("COMPARE", out_path, sh.size)
    return True


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) >= 3:
        side_by_side(args[0], args[1],
                     args[2],
                     args[3] if len(args) > 3 else "BEFORE",
                     args[4] if len(args) > 4 else "AFTER")
    else:
        print(__doc__)
