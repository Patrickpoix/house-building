"""在已有门窗白模上建立可替换的整宅家具体块研究。"""
from pathlib import Path
import sys

import bpy

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
from build_s001_whitebox import aim, box, material

OUT = ROOT / 'stages' / 'S001'


def main():
    bpy.ops.wm.open_mainfile(filepath=str(OUT / 'openings-study.blend'))
    bpy.context.preferences.filepaths.save_version = 0
    wood = material('study_oak', (0.42, 0.28, 0.16), 0.55)
    pale = material('study_linen', (0.69, 0.67, 0.59), 0.9)
    olive = material('study_olive', (0.27, 0.32, 0.23), 0.85)
    white = material('study_ceramic', (0.78, 0.79, 0.75), 0.3)
    dark = material('study_dark', (0.075, 0.08, 0.07), 0.45)

    def part(name, center, dimensions, mat):
        obj = box('STUDY_' + name, center, dimensions, mat)
        bevel = obj.modifiers.new('soft_edges', 'BEVEL')
        bevel.width = 0.012
        bevel.segments = 3
        obj.modifiers.new('normals', 'WEIGHTED_NORMAL')
        return obj

    def cabinet(name, x0, y0, x1, y1, height, mat=wood):
        part(name, ((x0+x1)/2, (y0+y1)/2, height/2), (x1-x0, y1-y0, height), mat)

    # 家具体块沿用已检查的平面范围，不冒充正式资产。
    part('bed_base', (1.10, 1.30, 0.22), (1.60, 2.10, 0.35), wood)
    part('mattress', (1.10, 1.30, 0.47), (1.54, 2.02, 0.18), pale)
    part('bed_head', (1.10, 0.30, 0.65), (1.60, 0.10, 1.10), wood)
    for x in (0.72, 1.48):
        part('pillow', (x, 0.62, 0.59), (0.56, 0.38, 0.10), white)
    cabinet('wardrobe', 3.20, 0.25, 3.90, 2.00, 2.25)
    part('shower_tray', (4.60, 0.65, 0.05), (0.90, 0.90, 0.10), white)
    part('shower_screen', (5.05, 0.65, 1.05), (0.025, 0.90, 2.00), pale)
    cabinet('vanity', 4.15, 1.50, 4.80, 2.40, 0.78)
    part('basin', (4.48, 1.95, 0.81), (0.60, 0.65, 0.08), white)
    part('toilet', (5.65, 2.02, 0.27), (0.55, 0.72, 0.54), white)
    cabinet('washer', 4.15, 2.65, 4.80, 3.35, 0.85, white)
    cabinet('utility_storage', 6.20, 2.65, 6.90, 3.40, 2.15)
    cabinet('entry_storage', 9.15, 2.10, 9.80, 3.80, 2.25)
    part('sofa_base', (0.70, 6.70, 0.27), (0.90, 2.20, 0.40), olive)
    part('sofa_back', (0.34, 6.70, 0.66), (0.18, 2.20, 0.68), olive)
    cabinet('bookshelf', 0.22, 8.50, 0.55, 9.65, 2.10)
    part('reading_chair_seat', (3.02, 9.02, 0.42), (0.75, 0.75, 0.16), pale)
    part('reading_chair_back', (3.02, 9.33, 0.76), (0.75, 0.13, 0.70), pale)
    part('dining_top', (6.05, 7.40, 0.75), (1.80, 1.50, 0.08), wood)
    for x in (5.30, 6.80):
        for y in (6.82, 7.98):
            part('table_leg', (x, y, 0.36), (0.07, 0.07, 0.72), wood)
    cabinet('kitchen_base', 9.10, 4.70, 9.80, 9.60, 0.88, olive)
    part('kitchen_worktop', (9.45, 7.15, 0.91), (0.70, 4.90, 0.06), white)
    cabinet('north_counter', 7.15, 9.10, 9.05, 9.80, 0.88, olive)
    part('north_worktop', (8.10, 9.45, 0.91), (1.90, 0.70, 0.06), white)
    part('hob', (9.43, 6.10, 0.95), (0.55, 0.58, 0.025), dark)

    scene = bpy.context.scene
    scene.camera.location = (18, -15, 25)
    scene.camera.data.clip_start = 0.1
    scene.camera.data.ortho_scale = 15
    aim(scene.camera, (5, 5, 0))
    scene.render.resolution_x = 1400
    scene.render.resolution_y = 1400
    scene.cycles.samples = 32
    scene.render.filepath = str(OUT / 'furnished-study.png')
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'furnished-study.blend'))
    bpy.ops.render.render(write_still=True)
    print('整宅体块研究已保存；家具、材质与碰撞仍待正式验收。')


if __name__ == '__main__':
    main()
