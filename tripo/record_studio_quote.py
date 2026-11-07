"""将人工核对的 Studio 报价及对应界面证据增量写入矩阵。"""
import argparse
import csv
import datetime
import os
from pathlib import Path
import re
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument("row_id")
parser.add_argument("price", type=int)
parser.add_argument("--input", choices=("none", "A030"), required=True)
parser.add_argument("--verify", action="store_true")
args = parser.parse_args()
root = Path(__file__).resolve().parent
evidence = root / "price-evidence" / f"{args.row_id}.txt"
image = evidence.with_suffix(".png")
if not evidence.is_file() or not image.is_file():
    raise SystemExit("缺少当前报价的界面状态或截图")
state = evidence.read_text(encoding="utf-8")
if f"生成 {args.price}" not in state:
    raise SystemExit("界面状态未显示指定报价")
path = root / "STUDIO_PRICE_MATRIX.csv"
with path.open(encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))
    fields = list(rows[0])
matches = [row for row in rows if row["id"] == args.row_id]
if len(matches) != 1:
    raise SystemExit("矩阵编号不存在或不唯一")
row = matches[0]
if row["topology"] != "quad" or row["face_count"] != "50000" or row["split_parts"] != "off":
    raise SystemExit("该记录不是四边面可报价组合")
if row["preview_valid"] and not args.verify:
    raise SystemExit("记录已有状态，拒绝覆盖")
checks = {
    "模型": row["model"] in state,
    "面数": bool(re.search(r"slider 50000\b", state)),
    "四边面": "checkbox 四边面, Value: 1" in state,
    "纹理分辨率": f"checkbox {row['texture_resolution'].upper()}, Value: 1" in state,
}
for label, expected in (("分部件生成", "0"), ("纹理生成", "1"), ("PBR", "1"),
                        ("去光处理", "1" if row["delight"] == "on" else "0"),
                        ("AI补全&3D增强", "1" if row["ai_enhance"] == "on" else "0")):
    checks[label] = bool(re.search(r"text [^\n]*" + re.escape(label) + r"[^\n]*\n(?:(?!\s*\d+ text (?!试用)).*\n)*?\s*\d+ switch " + expected + r"\b", state))
if row["model"] == "H3.1":
    checks["超清关闭"] = bool(re.search(r"text 超清几何精度[^\n]*\n(?:(?!\s*\d+ text ).*\n)*?\s*\d+ switch 0\b", state))
failed = [name for name, valid in checks.items() if not valid]
if failed:
    raise SystemExit("界面证据不匹配：" + "、".join(failed))
if args.verify:
    if row["preview_valid"] != "yes" or row["ui_price_credits"] != str(args.price):
        raise SystemExit("矩阵价格或状态与指定值不一致")
    raise SystemExit(0)
row.update(
    ui_price_credits=str(args.price), preview_valid="yes",
    price_stage="Studio生成前按钮；" + ("A030参考图" if args.input == "A030" else "无输入图片"),
    price_updated_at=datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
    notes=f"50,000四边面；PBR/纹理开；界面证据price-evidence/{args.row_id}.txt及.png；非实际扣费",
)
with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="", delete=False, dir=root) as f:
    temp = f.name
    writer = csv.DictWriter(f, fieldnames=fields, quoting=csv.QUOTE_ALL)
    writer.writeheader()
    writer.writerows(rows)
os.replace(temp, path)
