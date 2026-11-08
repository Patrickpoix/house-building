# Wood Floor 材质试验

- 来源：[Poly Haven — Wood Floor](https://polyhaven.com/a/wood_floor)，作者 Dimitrios Savva，页面标注 CC0，2026-11-08 获取。原图块宽约 1.7 m；本目录为 2K 原始 JPEG：Diffuse、Rough、OpenGL Normal。木材是非金属，试验材质 Metallic 为常数 0。
- 三图均已完整解码为 2048×2048；Blender 中颜色图为 sRGB，粗糙度和法线为 Non-Color，法线经 Normal Map 节点。`scripts/build_s003_floor_study.py` 按 1.7 m 平铺用于 S003 的独立房间试验，保留外部相对路径。
- 封顶日光研究稿 `stages/S003/daylight-study/` 已额外渲染餐厨及地板近景；局部原像素可辨木纹与板缝，但未对整个区域逐处检查贴图重复、板方向、边界和最终灯光。正式地面还需核查真实材质、厚度、墙边收口、门口过渡和湿区适用性；不能把试验面计为正式资产。
