# 阶段脚本

这些脚本和结果尚未构成最终住宅交付。所有路径均相对 `house-building/`。

## Blender 阶段

使用 Blender 5.2.3 LTS，以下命令从项目目录运行；`--python-exit-code 1` 确保 Python 异常产生非零退出码。

书架局部精修对照（先生成书架研究稿；分别覆盖各自研究目录）：

```powershell
# 保留原背板，只加入底座和托销；历史 --geometry-only 调用仍可用
& .tools/blender-5.2.3-windows-x64/blender.exe -b -t 4 --factory-startup --python-exit-code 1 --python scripts/refine_s003_bookshelf.py
# 背板改用较大图块并加入底座和托销；该背板视觉方案目前未采用
& .tools/blender-5.2.3-windows-x64/blender.exe -b -t 4 --factory-startup --python-exit-code 1 --python scripts/refine_s003_bookshelf.py -- --alternate-back
```

起居书架分板与材质研究（依赖 S003 日光试验和 `assets/materials/white_oak_veneer/` 三图，重跑覆盖该研究目录的同名输出）：

```powershell
& .tools/blender-5.2.3-windows-x64/blender.exe -b -t 4 --factory-startup --python-exit-code 1 --python scripts/build_s003_bookshelf_study.py
```

S003 封顶日光试验（需要先生成地板试验工程，输出会覆盖 `stages/S003/daylight-study/` 同名试验）：

```powershell
& .tools/blender-5.2.3-windows-x64/blender.exe -b -t 4 --factory-startup --python-exit-code 1 --python scripts/build_s003_daylight_study.py
```

该工程启用已有 3 m 天花和 Blender 5.2.3 的多重散射天空，输出起居、餐厨与地板近景；房间、家具、窗外和最终灯光仍须验收。

开放起居餐厨木地板材质试验（另存于 `stages/S003/floor-study/`，会覆盖该目录同名试验）：

```powershell
& .tools/blender-5.2.3-windows-x64/blender.exe -b -t 4 --factory-startup --python-exit-code 1 --python scripts/build_s003_floor_study.py
```

运行前需保留 `assets/materials/wood_floor/` 三张原图；来源和验收限制见该目录 README。脚本不覆盖 S003 基线。

阅读椅结构预检引导（非正式资产；输出在 `stages/S003/reading-chair-guide/`，重跑会覆盖该目录的同名工程与视图）：

```powershell
& .tools/blender-5.2.3-windows-x64/blender.exe -b -t 4 --factory-startup --python-exit-code 1 --python scripts/build_reading_chair_guide.py
```

```powershell
& .tools/blender-5.2.3-windows-x64/blender.exe -b --factory-startup --python-exit-code 1 --python scripts/build_s001_whitebox.py
& .tools/blender-5.2.3-windows-x64/blender.exe -b stages/S001/whitebox.blend --python-exit-code 1 --python scripts/check_s001_whitebox.py
& .tools/blender-5.2.3-windows-x64/blender.exe -b --factory-startup --python-exit-code 1 --python scripts/build_s001_openings.py
& .tools/blender-5.2.3-windows-x64/blender.exe -b stages/S001/openings-study.blend --python-exit-code 1 --python scripts/check_s001_openings.py
& .tools/blender-5.2.3-windows-x64/blender.exe -b stages/S001/openings-study.blend --python-exit-code 1 --python scripts/check_s001_door_sweep.py
& .tools/blender-5.2.3-windows-x64/blender.exe -b --factory-startup --python-exit-code 1 --python scripts/study_furniture_layout.py
& .tools/blender-5.2.3-windows-x64/blender.exe -b --factory-startup --python-exit-code 1 --python scripts/build_a019_study.py
& .tools/blender-5.2.3-windows-x64/blender.exe -b --factory-startup --python-exit-code 1 --python scripts/texture_a019_study.py
& .tools/blender-5.2.3-windows-x64/blender.exe -b stages/S002/A019-study/study-textured.blend --python-exit-code 1 --python scripts/check_a019_study.py
& .tools/blender-5.2.3-windows-x64/blender.exe -b stages/S002/A019-study/study-textured.blend --python-exit-code 1 --python scripts/check_study_textures.py
& .tools/blender-5.2.3-windows-x64/blender.exe -b --factory-startup --python-exit-code 1 --python scripts/build_a030_study.py
& .tools/blender-5.2.3-windows-x64/blender.exe -b stages/S002/A030-study/study.blend --python-exit-code 1 --python scripts/check_a030_study.py
& .tools/blender-5.2.3-windows-x64/blender.exe -b --factory-startup --python-exit-code 1 --python scripts/texture_a030_study.py
& .tools/blender-5.2.3-windows-x64/blender.exe -b stages/S002/A030-study/study-textured.blend --python-exit-code 1 --python scripts/check_study_textures.py -- A030
& .tools/blender-5.2.3-windows-x64/blender.exe -b --factory-startup --python-exit-code 1 --python scripts/build_a030_continuous_study.py
& .tools/blender-5.2.3-windows-x64/blender.exe -b stages/S002/A030-study/continuous-study.blend --python-exit-code 1 --python scripts/render_study_closeup.py -- A030 continuous-closeup.png
& .tools/blender-5.2.3-windows-x64/blender.exe -b --factory-startup --python-exit-code 1 --python scripts/build_a103_bowl_study.py
& .tools/blender-5.2.3-windows-x64/blender.exe -b stages/S002/A103-study/study.blend --python-exit-code 1 --python scripts/check_a103_bowl_study.py
& .tools/blender-5.2.3-windows-x64/blender.exe -b stages/S002/A103-study/study.blend --python-exit-code 1 --python scripts/render_a103_views.py
```

A019 和 A030 结构研究稿分别依赖 `stages/S002/experiments/A019-generated-shape.glb` 和 `A030-hunyuan-textured.glb`。连续袋身试验以 A030 的 `study-textured.blend` 为输入，单独保存，不覆盖原研究稿。纹理研究稿的图片路径为相对 `.blend` 文件的 `textures/`；移动时须一并保留。检查脚本只覆盖尺寸、指定槽口或贴图连接，不能代替视觉、碰撞及完整 PBR 验收。

## 多视角渲染预览（可选，不影响正式画质）

已有 Tripo GLB 的材质对照可使用：

```powershell
& .tools/blender-5.2.3-windows-x64/blender.exe -b -t 4 --factory-startup --python-exit-code 1 --python scripts/render_tripo_views.py -- tripo/outputs/reading-chair/tripo-original.glb tripo/outputs/reading-chair/material-diagnostic material-diagnostic
```

该模式先渲染原材质，再仅将粗糙度替换为常数 0.5，恢复原粗糙度连接后断开 Normal，最后再替换 Base Color 为中性色；金属度始终保持原样。不同结果用于缩小排查范围，不证明 UV、贴图或去光的单一根因；不会修改输入 GLB。输出目录若已有同名结果会被覆盖，应为新的试验指定独立目录。省略最后一个参数时沿用原来的五向渲染。

当需要同时比较正面、背面、侧面和近景等多张 Blender 渲染图时，优先用仓库自带的 `scripts/preview_views.py` 生成**一张小型联系表**，再把联系表提供给 Codex 查看。这样避免同一轮直接输入四五张完整PNG，减少长会话的历史图片负载。

在项目根目录执行（本机已安装 Pillow 的 Python 位于 `D:\Python\python.exe`）：

```powershell
& D:\Python\python.exe scripts\preview_views.py "stages\S002\A031-study\reconstructed-v2-views"
```

脚本输出生成的 JPEG 文件路径，位置为 `.tools/view-previews/`（Git 已忽略）。支持读取**指定目录中**的 PNG/JPG/WebP，按 `front/back/left/right/top/close` 优先排序、带标签排列；输入图有更新时重新生成。再次查看同一批未修改图片可直接复用预览。在其他环境中可用已安装 Pillow 的 Python 调用，无需依赖 Blender，也不要求修改 Magpie 或 Codex 设置。

**质量边界**：此工具仅供总览；不修改原始渲染图、2K/4K贴图、模型或Blender工程。需要检查织纹、缝合、拓扑、UV/PBR或真实成品验收时，照常打开对应原始图片/必要的局部放大，绝不能把联系表当作最终质量验收。工具可选，不应拖慢建模与生产。

单张高清渲染图也可以用同一脚本生成较轻的JPEG预览；需局部像素级核对时使用无缩放、无损PNG裁切，参数为原图中的左上角XY坐标和宽高（像素）。裁切不修改原图：

```powershell
& D:\Python\python.exe scripts\preview_views.py tripo\outputs\reading-chair\views\close.png
& D:\Python\python.exe scripts\preview_views.py tripo\outputs\reading-chair\views\close.png --crop 180 160 512 512
```

图片生成工具可能把完整新图直接返回给Codex会话，**该脚本无法拦截或消除已经返回的图片数据**。需要Images 2.6时继续使用，但应按必要角度分阶段生成、及时保存原始参考图；后续反复核对优先用联系表/单张轻量预览/针对性裁切，避免重复打开同一张整图。对于工具/网页/命令的大量文本输出，先用精准搜索与限量摘要定位，再按需读取局部，不将全部日志和重复全文带入长会话。若经过较大阶段积累，先把关键进展、路径、当前阻断与下一步写入HANDOFF.md、REPORT.md、tripo/WORK_LOG.md并核对Git状态，再使用Codex官方压缩功能；不得直接裁剪、修改或删除会话数据库和原始证据。

### 整条图像制作链的低负载查看方式（已实测）

除原先的单目录联系表、单张高保真JPEG预览和无损原像素裁切，现在还可直接处理 Codex 已落盘生图、跨目录多来源参考与前后版本对比。以下均从项目根目录运行；请把 `<实际会话ID>` 改为当前 Codex 正式会话ID：

```powershell
# Images 2.6自动保存过的原始生图：只读最新6张，输出一张联系表；原图不复制不修改
& D:\Python\python.exe scripts\preview_views.py "$env:USERPROFILE\.codex\generated_images\<实际会话ID>" --newest 6

# 8-12张或更多参考图：同一目录自动每6张一页；最多24张，避免单次大量回传
& D:\Python\python.exe scripts\preview_views.py references\reading-chair

# 参考图分布在不同目录：选入同一分批联系表，无需复制源文件
& D:\Python\python.exe scripts\preview_views.py --files references\reading-chair\front-candidate.png tripo\outputs\reading-chair\views\left.png

# 旧版与新版的相同视角严格成对比较；有缺失视角则报错，绝不悄悄跳过
& D:\Python\python.exe scripts\preview_views.py stages\S002\A031-study\reconstructed-views --compare stages\S002\A031-study\reconstructed-v2-views

# 在同一原像素坐标处无损并排查看两个文件，RGB/RGBA像素和alpha都原样保留
& D:\Python\python.exe scripts\preview_views.py tripo\outputs\A030\material-diagnostic\original.png --compare tripo\outputs\A030\material-diagnostic\without-normal.png --crop 150 160 512 512
```

所有预览仍只生成在Git忽略的 `.tools/view-previews/`，每张联系表旁附有同名 `.json`，记录各格对应的**原始完整路径、尺寸及位置**，供Codex在发现问题时精准回到高清原件。多图自动分页，单页最多6张；前后对照单页最多3组。变更输入后缓存失效，生成时原子写入以避免留下半张损坏图片。缓存只是查看证据，不可作为Tripo正式输入、UV/PBR数值判断或最终验收替代品。8/16位材质通道请查看原始数值贴图，16位不允许伪装成8位“像素无损”并排图。

**生产顺序**：多源高质量原始参考图完整保存 → 用本工具选择/核对视角一致性 → 用真正的原图生成/上传Tripo（而非轻量JPEG）→ Blender保留GLB、2K/4K PBR与正式渲染 → 小联系表查看形体 → 必要时单张高保真预览/无损ROI/原图定位缺陷 → 使用本工具严格成对对比修复前后 → **只按原图、模型、UV/PBR和真实房间近景做最终验收**。质检不能因为缩图看不清就宣布通过。

回归命令：`D:\Python\python.exe scripts\test_preview_views.py -v`。已运行的测试、压缩数据、已知限制与交接留痕参见 `scripts/IMAGE_PREVIEW_QUALITY.md`、`tripo/WORK_LOG.md`。

## 三维生成环境

已验证的环境为 WSL Ubuntu、Python 3.11、PyTorch 2.6.0+cu124，完整包版本见 `requirements-hunyuan-linux.txt`；Hunyuan3D-2 代码版本及官方权重修订见 `REPORT.md`。从项目根目录用 `bash scripts/run_hunyuan.sh shape 输入图片 输出.glb` 启动形状生成，或用 `bash scripts/run_hunyuan.sh texture 网格.glb 参考.png 输出.glb` 启动纹理试验。入口在 Python 启动前设置项目内 OpenGL 库路径，并默认使用项目内模型与缓存；`HY3DGEN_MODELS` 和 `HF_HOME` 可覆盖默认值。形状生成只输出几何。

纹理试验需要 CUDA 编译器、GCC、CPU/GPU 扩展、`libOpenGL.so.0`、官方权重和足够内存。当前构建环境位于 WSL 的 `~/.cache/house-building-mamba/cuda-build`，不随项目自动迁移；可用 `HOUSE_CUDA_BUILD` 指向等价环境，并执行 `bash scripts/build_texture_extensions.sh` 编译。`check_texture_extensions.py` 使用 GPU 三角形验证光栅器。`hunyuan_texture_smoke.py 网格.glb 参考.png 输出.glb` 使用 CPU 内存卸载生成颜色纹理；它不是完整 PBR 管线。环境安装记录、权重校验及未完成事项见 `REPORT.md`。
