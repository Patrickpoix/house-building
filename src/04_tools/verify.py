"""自检：逐条核对 GOAL.md 质量基准，并校验目录结构 / 可迁移性。

只读，不修改任何工程文件。结果写入 scene/verify_result.json，
是 docs/04_验收报告.md 的数据来源。

检查项：
  textures  — 4K / 8 通道 PBR 完整覆盖率、albedo 客观质量
  assets    — 36 类 / 144 资产几何、材质节点、真实位移修改器
  house     — 100 ㎡ 住宅实例、建筑收口、板条地板
  portable  — 144 个独立资产文件（.blend/preview/meta）完整性与相对路径
  renders   — 分类目录下的出图数量
  structure — 文档 / 源码 / 配置是否齐备
"""
import bpy, os, csv, json, glob
import numpy as np
from PIL import Image

# --- 路径自举：项目可任意改名/搬家，向上找到 config.py 即可 ---
import sys as _sys, pathlib as _pathlib
_sys.path.insert(0, str(next(p for p in _pathlib.Path(__file__).resolve().parents
                            if (p / "config.py").is_file())))
import config as C

CURVED = ("soft", "cloth", "leaf", "tube", "lathe")
CHANNELS = C.CHANNELS


def albedo_quality(path):
    """在 512px 缩略尺度上量化 albedo 的客观质量（不改动任何贴图）。"""
    with Image.open(path) as im:
        a = np.asarray(im.convert('L').resize((512, 512), Image.BILINEAR),
                       dtype=np.float32) / 255.0
    gx = float(np.abs(np.diff(a, axis=1)).mean())
    gy = float(np.abs(np.diff(a, axis=0)).mean())
    mirror = float(np.abs(a[:, :256] - a[:, 256:][:, ::-1]).mean())
    return dict(luma_std=round(float(a.std()), 4),
                detail_energy=round((gx + gy) / 2, 5),
                mirror_asymmetry=round(mirror, 4))


def check_textures():
    """4K / 8 通道完整 PBR 贴图库校验（按材质子目录）。"""
    names = sorted(m for m in C.MATERIALS if C.tex(m, "basecolor").exists())
    resolutions, per_material = {}, {}
    channel_complete = 0
    for n in names:
        have = [s for s in CHANNELS if C.tex(n, s).exists()]
        per_material[n] = have
        if all(s in have for s in CHANNELS):
            channel_complete += 1
        with Image.open(C.tex(n, "basecolor")) as im:
            resolutions[n] = list(im.size)
    all_files = [p for p in C.TEXTURES.rglob("*.png")]
    total_bytes = sum(p.stat().st_size for p in all_files)
    quality = {n: albedo_quality(C.tex(n, "basecolor")) for n in names}
    qs = dict(
        mean_luma_std=round(float(np.mean([q["luma_std"] for q in quality.values()])), 4),
        mean_detail_energy=round(float(np.mean([q["detail_energy"] for q in quality.values()])), 5),
        mean_mirror_asymmetry=round(float(np.mean([q["mirror_asymmetry"] for q in quality.values()])), 4),
        wood_mirror_asymmetry={n: quality[n]["mirror_asymmetry"]
                               for n in ("oak_wood", "walnut_wood") if n in quality},
    )
    return dict(
        material_sets=len(names),
        channel_names=list(CHANNELS),
        channel_complete_sets=channel_complete,
        texture_4k_sets=sum(1 for r in resolutions.values() if r == [4096, 4096]),
        basecolor_resolutions=resolutions,
        total_texture_files=len(all_files),
        total_texture_mb=round(total_bytes / 1e6, 1),
        ai_material_sources=len(list(C.AI_SOURCE.glob("src_*.png"))),
        per_material=per_material,
        albedo_quality=quality,
        albedo_quality_summary=qs,
    )


def check_assets():
    rows = list(csv.DictReader(open(C.CATALOG_CSV)))
    cats = sorted({r["category_no"] for r in rows})
    parts = [int(r["parts"]) for r in rows]

    bpy.ops.wm.open_mainfile(filepath=str(C.LIBRARY_BLEND))
    ast_cols = [c for c in bpy.data.collections if c.name.startswith("AST_")]
    with_bevel = with_multi_mat = with_curved = 0
    shape_counter, seen_mats = {}, set()
    total_verts = total_faces = 0
    sheen = coat = aniso = nmap = bumpn = dispn = aon = 0
    tex_node_count = packed = displace_objs = 0
    for c in ast_cols:
        objs = list(c.objects)
        is_curved = False
        for o in objs:
            n = o.name.rsplit("_", 1)[-1]
            shape_counter[n] = shape_counter.get(n, 0) + 1
            if n in CURVED:
                is_curved = True
            if o.type == 'MESH':
                total_verts += len(o.data.vertices)
                total_faces += len(o.data.polygons)
            if any(md.type == 'DISPLACE' for md in o.modifiers):
                displace_objs += 1
            if o.active_material and o.active_material.name not in seen_mats:
                seen_mats.add(o.active_material.name)
                mat = o.active_material
                if mat.use_nodes:
                    types = {nd.bl_idname for nd in mat.node_tree.nodes}
                    imgs = [nd for nd in mat.node_tree.nodes if nd.bl_idname == 'ShaderNodeTexImage']
                    tex_node_count += len(imgs)
                    labels = {nd.label for nd in imgs}
                    if 'ao' in labels:
                        aon += 1
                    bs = next((nd for nd in mat.node_tree.nodes
                               if nd.bl_idname == 'ShaderNodeBsdfPrincipled'), None)
                    if 'ShaderNodeNormalMap' in types:
                        nmap += 1
                    if 'ShaderNodeBump' in types:
                        bumpn += 1
                    if 'ShaderNodeDisplacement' in types:
                        dispn += 1
                    if bs:
                        def val(k):
                            try:
                                return bs.inputs[k].default_value
                            except (KeyError, TypeError):
                                return 0
                        if val('Sheen Weight') > 0:
                            sheen += 1
                        if val('Coat Weight') > 0:
                            coat += 1
                        if val('Anisotropic') > 0 or val('Anisotropic IOR Level') > 0:
                            aniso += 1
        if any(any(m.type == 'BEVEL' for m in o.modifiers) for o in objs):
            with_bevel += 1
        if len({o.active_material.name for o in objs if o.active_material}) > 1:
            with_multi_mat += 1
        if is_curved:
            with_curved += 1
    for im in bpy.data.images:
        if im.source == 'FILE' and im.packed_file:
            packed += 1
    curved_parts = sum(v for k, v in shape_counter.items() if k in CURVED)
    return dict(
        asset_count=len(rows), category_count=len(cats),
        total_parts=sum(parts), min_parts=min(parts),
        avg_parts=round(sum(parts) / len(parts), 2),
        collections_in_blend=len(ast_cols),
        collections_with_bevel=with_bevel,
        collections_with_multi_material=with_multi_mat,
        total_mesh_vertices=total_verts, total_mesh_faces=total_faces,
        avg_vertices_per_asset=round(total_verts / max(1, len(ast_cols)), 1),
        curved_parts=curved_parts,
        collections_with_curved_geometry=with_curved,
        shape_breakdown=dict(sorted(shape_counter.items())),
        materials_with_sheen=sheen, materials_with_coat=coat,
        materials_with_anisotropic=aniso,
        materials_with_normal_map=nmap, materials_with_bump=bumpn,
        materials_with_displacement_node=dispn, materials_with_ao=aon,
        texture_image_nodes=tex_node_count,
        packed_images=packed,
        objects_with_displace_modifier=displace_objs,
    )


def check_house():
    bpy.ops.wm.open_mainfile(filepath=str(C.HOUSE_BLEND))
    inst = [o for o in bpy.data.objects
            if o.instance_type == 'COLLECTION' and o.name.startswith("INST_")]
    src = {o.instance_collection.name for o in inst if o.instance_collection}
    walls = [o for o in bpy.data.objects if o.name.startswith("wall_")]
    glass = [o for o in bpy.data.objects if o.name.startswith("glass_")]
    lights = [o for o in bpy.data.objects if o.type == 'LIGHT']
    cams = [o for o in bpy.data.objects if o.type == 'CAMERA']
    doors = [o for o in bpy.data.objects if o.name.startswith("door_")]
    trims = [o for o in bpy.data.objects if o.name.startswith(("crown_", "picture_", "window_sill"))]
    elevated = [o for o in inst if o.location.z > 0.2]
    textured = sum(1 for m in bpy.data.materials
                   if m.use_nodes and any(nd.bl_idname == 'ShaderNodeTexImage'
                                          for nd in m.node_tree.nodes))
    plank_objs = [o for o in bpy.data.objects if o.name.endswith("_planks")]
    plank_faces = sum(len(o.data.polygons) for o in plank_objs)
    plank_variants = sum(1 for m in bpy.data.materials if m.name.startswith("plank_oak_"))
    displace_objs = sum(1 for o in bpy.data.objects
                        if any(md.type == 'DISPLACE' for md in o.modifiers))
    imgs = [i for i in bpy.data.images if i.source == 'FILE']
    broken = [i.filepath for i in imgs if not os.path.exists(bpy.path.abspath(i.filepath))]
    absolute = [i.filepath for i in imgs if i.filepath and not i.filepath.startswith('//')]

    def count(prefix):
        return sum(1 for o in bpy.data.objects if o.name.startswith(prefix))
    house_verts = sum(len(o.data.vertices) for o in bpy.data.objects if o.type == 'MESH')
    return dict(
        plank_floor_objects=len(plank_objs), plank_faces=plank_faces,
        plank_material_variants=plank_variants,
        scene_displace_objects=displace_objs,
        door_casings=count("casing_"), switch_plates=count("switch_"),
        downlights=count("downlight_"), vents=count("vent_"),
        curtain_panels=sum(1 for o in bpy.data.objects
                           if o.name.startswith("curtain_") and o.type == 'MESH'),
        sky_backdrop=count("sky_backdrop_plane"),
        total_mesh_vertices=house_verts,
        instances=len(inst), distinct_assets_used=len(src),
        wall_segments=len(walls), glass_panes=len(glass),
        lights=len(lights), cameras=len(cams), door_leaves=len(doors),
        total_objects=len(bpy.data.objects),
        engine=bpy.context.scene.render.engine,
        device=bpy.context.scene.cycles.device,
        architectural_trims=len(trims),
        elevated_decor_instances=len(elevated),
        textured_materials=textured,
        texture_images=len(imgs), broken_texture_paths=broken,
        absolute_texture_paths=absolute,
    )


def check_portable():
    """36 类 / 144 个独立资产的可迁移交付校验。"""
    rows = list(csv.DictReader(open(C.CATALOG_CSV)))
    cat_dirs = sorted(p for p in C.BY_CATEGORY.iterdir() if p.is_dir()) if C.BY_CATEGORY.exists() else []
    asset_dirs = []
    missing = []
    counts = dict(blend=0, preview=0, meta=0)
    for no, cn, en in C.CATEGORIES:
        cdir = C.category_dir(no, cn, en)
        for r in rows:
            if r["category_no"] != no:
                continue
            adir = C.asset_dir(no, cn, en, r["id"])
            asset_dirs.append(adir)
            for key, fn in (("blend", "model.blend"),
                            ("preview", "preview.png"), ("meta", "meta.json")):
                if (adir / fn).exists():
                    counts[key] += 1
                else:
                    missing.append(f"{r['id']}/{fn}")
        if not (cdir / "README.md").exists():
            missing.append(f"{cdir.name}/README.md")
    # 绝对/失效贴图路径检查：抽查母库与房屋
    rel_ok = True
    for blend in (C.LIBRARY_BLEND, C.HOUSE_BLEND):
        if not blend.exists():
            rel_ok = False
            continue
        bpy.ops.wm.open_mainfile(filepath=str(blend))
        for im in bpy.data.images:
            if im.source == 'FILE' and im.filepath:
                if not im.filepath.startswith('//') or not os.path.exists(bpy.path.abspath(im.filepath)):
                    rel_ok = False
                    break
    return dict(
        category_dirs=len(cat_dirs), asset_dirs=len(asset_dirs),
        expected_assets=len(rows),
        files=counts,
        missing=missing[:40], missing_total=len(missing),
        all_relative_texture_paths=rel_ok,
    )


def check_renders():
    groups = {
        "空间主图": C.R_SHOTS, "资产特写": C.R_CLOSEUPS, "4K主图": C.R_HERO,
        "材质检视": C.R_SHEETS,
    }
    out = {}
    total = 0
    for name, d in groups.items():
        files = sorted(d.glob("*.png")) if d.exists() else []
        out[name] = len(files)
        total += len(files)
    empty = [str(p.relative_to(C.ROOT)) for d in groups.values() if d.exists()
             for p in d.glob("*.png") if p.stat().st_size < 5000]
    return dict(total_png=total, by_group=out, empty_files=empty)


def check_structure():
    need = [
        "config.py", "README.md", "GOAL.md", "CHANGELOG.md",
        "docs/01_目录规范.md", "docs/02_资产总表.md", "docs/03_快速开始.md",
        "docs/04_验收报告.md", "docs/05_视频解析.md", "docs/06_平面布局.md",
        "docs/07_环境说明.md", "docs/08_迁移指南.md", "docs/09_任意组装指南.md",
        "assets/catalog.csv", "assets/_library/asset_library.blend",
        "scene/house.blend", "scene/placement.json",
        "src/01_assets/export_assets.py", "src/02_scene/assemble.py",
        "src/04_tools/migrate_check.py",
    ]
    return {p: (C.ROOT / p).exists() for p in need}


def check_layouts():
    """声明式布局 JSON 有效性：可解析、资产 ID 合法、坐标落在 shell 内。"""
    import glob
    ids = {r["id"] for r in csv.DictReader(open(C.CATALOG_CSV, encoding="utf-8"))}
    layouts = sorted(C.LAYOUTS.glob("*.json")) if C.LAYOUTS.exists() else []
    detail = []
    ok = True
    for p in layouts:
        try:
            L = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            ok = False
            detail.append(f"{p.name}: JSON 解析失败 {e}")
            continue
        sh = L.get("shell", {})
        bad_ids = [a["asset"] for a in L.get("assets", []) if a["asset"] not in ids]
        out = []
        for a in L.get("assets", []):
            x, y = a["pos"][0], a["pos"][1]
            if not (sh.get("x0", 0) <= x <= sh.get("x1", 0)
                    and sh.get("y0", 0) <= y <= sh.get("y1", 0)):
                out.append(a["asset"])
        if bad_ids or out:
            ok = False
        detail.append(dict(name=p.name, id=L.get("id"), assets=len(L.get("assets", [])),
                           bad_ids=len(bad_ids), out_of_bounds=len(out)))
    return dict(layout_count=len(layouts), all_valid=ok, detail=detail)


def main():
    result = dict(textures=check_textures(), assets=check_assets(),
                  house=check_house(), portable=check_portable(),
                  renders=check_renders(), structure=check_structure(),
                  layouts=check_layouts())
    C.VERIFY_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(C.VERIFY_JSON, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    # 只打印摘要，完整数据落 JSON
    print(json.dumps({
        "textures": {k: result["textures"][k] for k in
                     ("material_sets", "channel_complete_sets", "texture_4k_sets",
                      "total_texture_files", "total_texture_mb")},
        "assets": {k: result["assets"][k] for k in
                   ("asset_count", "category_count", "total_parts",
                    "total_mesh_vertices", "objects_with_displace_modifier")},
        "house": {k: result["house"][k] for k in
                  ("instances", "distinct_assets_used", "total_mesh_vertices",
                   "broken_texture_paths", "absolute_texture_paths")},
        "portable": {k: result["portable"][k] for k in
                     ("category_dirs", "asset_dirs", "expected_assets", "files",
                      "missing_total", "all_relative_texture_paths")},
        "renders": result["renders"],
        "structure": result["structure"],
        "layouts": result["layouts"],
    }, ensure_ascii=False, indent=2))
    print("VERIFY_DONE")


if __name__ == "__main__":
    main()
