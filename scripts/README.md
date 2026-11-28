# 阶段脚本

这些脚本和结果尚未构成最终住宅交付。所有路径均相对 `house-building/`。

## Blender 阶段

S003 起居装配及玄关、餐厨扩展。读取现有 S002/S003 研究文件，重建 `assets/README.md` 所列 12 个 BLEND/GLB 包、根目录 `house.blend` 和 `renders/S003/` 实景。房间需要保持与 `assets/` 的相对目录。

```powershell
& .tools/blender-5.2.3-windows-x64/blender.exe -b --factory-startup --python-exit-code 1 --python scripts/build_s003_living.py
```

S003 餐厨阶段从含餐桌和托盘的根目录工程接续。先安装 A105 双灶，再由双灶阶段工程安装餐椅。两个脚本分别另存阶段工程，重跑会更新对应的资产包和实景图。

```powershell
& .tools/blender-5.2.3-windows-x64/blender.exe -b --factory-startup --python-exit-code 1 --python scripts/build_s003_cooktop.py --
& .tools/blender-5.2.3-windows-x64/blender.exe -b --factory-startup --python-exit-code 1 --python scripts/build_s003_dining_seating.py --
```

[餐椅阶段工程](../stages/S003/dining-seating/house.blend)依赖 `assets/` 的相对路径。两条命令可用 `--source` 和 `--output` 指定输入和输出工程。重放双灶阶段时，以历史提交 `8786a34` 中的根目录工程作为 `--source`。旧版 `build_s003_dining.py` 提供餐桌、托盘和餐椅的几何与装配，直接执行会将结果保存至根目录工程。

从餐椅阶段重跑 A106 马克杯、A107 餐垫和[餐桌陈设工程](../stages/S003/table-setting/house.blend)。脚本更新这两个资产库和餐桌对应视图。

```powershell
& .tools/blender-5.2.3-windows-x64/blender.exe -b --factory-startup --python-exit-code 1 --python scripts/build_s003_table_setting.py --
```

从餐桌陈设阶段接续 A108 床架和 A109 床品，补齐主卧木地板并另存[主卧阶段工程](../stages/S003/bedroom-bed/house.blend)。脚本更新床架、床品资产库及两个房间镜头。

```powershell
& .tools/blender-5.2.3-windows-x64/blender.exe -b --factory-startup --python-exit-code 1 --python scripts/build_s003_bedroom.py --
```

从主卧床架阶段重跑 A110 双轨移门衣柜、[衣柜阶段工程](../stages/S003/bedroom-wardrobe/house.blend)以及关门实景和回导后的两个开启视图。

```powershell
& .tools/blender-5.2.3-windows-x64/blender.exe -b --factory-startup --python-exit-code 1 --python scripts/build_s003_wardrobe.py --
```

从衣柜阶段重跑 A111 双幅帘、A112 床头柜、[主卧陈设工程](../stages/S003/bedroom-furnishings/house.blend)及两件资产的实景和 GLB 正反面检查图。

```powershell
& .tools/blender-5.2.3-windows-x64/blender.exe -b --factory-startup --python-exit-code 1 --python scripts/build_s003_bedroom_furnishings.py --
```

从主卧陈设阶段重跑 A113 盥洗组、地砖、西墙釉砖和照明，另存[卫浴盥洗阶段](../stages/S003/bathroom-vanity/house.blend)及实景、近景、回导图。

```powershell
& .tools/blender-5.2.3-windows-x64/blender.exe -b --factory-startup --python-exit-code 1 --python scripts/build_s003_bathroom_vanity.py --
```

从盥洗组继续构建 [A114 淋浴](../stages/S003/bathroom-shower/house.blend) 和 [A115 坐便区](../stages/S003/bathroom-toilet/house.blend)。脚本另存阶段工程及实景、GLB 回导视图。

```powershell
& .tools/blender-5.2.3-windows-x64/blender.exe -b --factory-startup --python-exit-code 1 --python scripts/build_s003_bathroom_shower.py --
& .tools/blender-5.2.3-windows-x64/blender.exe -b --factory-startup --python-exit-code 1 --python scripts/build_s003_bathroom_toilet.py --
```

沙发背部剖切负面试验（依赖原 GLB；覆盖独立试验目录，当前结果未采用）：

```powershell
& .tools/blender-5.2.3-windows-x64/blender.exe -b -t 4 --factory-startup --python-exit-code 1 --python scripts/study_sofa_back_repair.py
```


起居沙发原始模型试放（依赖阅读椅房间试验和沙发 GLB；覆盖独立试验目录）：

```powershell
& .tools/blender-5.2.3-windows-x64/blender.exe -b -t 4 --factory-startup --python-exit-code 1 --python scripts/study_sofa_in_room.py
```


阅读椅第二版材质的房间试放（依赖边几研究稿及 v2 椅工程；覆盖独立试验目录）：

```powershell
& .tools/blender-5.2.3-windows-x64/blender.exe -b -t 4 --factory-startup --python-exit-code 1 --python scripts/study_chair_fabric_in_room.py
```


阅读椅布料遮罩与真实贴图试验（依赖原 GLB 和 Terlenka 2K，覆盖 `fabric-study/`）：

```powershell
& .tools/blender-5.2.3-windows-x64/blender.exe -b -t 4 --factory-startup --python-exit-code 1 --python scripts/study_chair_fabric.py
```


起居木边几试验（依赖台灯电线试验稿；覆盖独立试验目录）：

```powershell
& .tools/blender-5.2.3-windows-x64/blender.exe -b -t 4 --factory-startup --python-exit-code 1 --python scripts/study_living_side_table.py
```


台灯电线试验（依赖台灯试放工程；覆盖独立试验目录）：

```powershell
& .tools/blender-5.2.3-windows-x64/blender.exe -b -t 4 --factory-startup --python-exit-code 1 --python scripts/study_lamp_power.py
```


起居台灯试放（依赖书架结构研究稿和台灯原始 GLB；覆盖独立试验目录）：

```powershell
& .tools/blender-5.2.3-windows-x64/blender.exe -b -t 4 --factory-startup --python-exit-code 1 --python scripts/study_living_table_lamp.py
```


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

### S003 家政与玄关

从卫浴阶段接续 A116 洗衣机、A117 折叠台及吊柜，再装配 A118 家政高柜、A119 玄关衣帽柜。各入口保存对应工程、实景和 GLB 回导图。

```powershell
& .tools/blender-5.2.3-windows-x64/blender.exe -b --python-exit-code 1 --python scripts/build_s003_utility.py
& .tools/blender-5.2.3-windows-x64/blender.exe -b --python-exit-code 1 --python scripts/build_s003_storage.py
& .tools/blender-5.2.3-windows-x64/blender.exe -b stages/S003/utility-and-entry-storage/house.blend --python-exit-code 1 --python scripts/check_s001_door_sweep.py -- --assets A116 A117 A118 A119 entry-bench
```

### S003 餐厨烹饪工位

从储物阶段重跑烟罩、烤箱和东侧分舱柜，输出房间实景及三件 GLB 的诊断视角。

```powershell
& .tools/blender-5.2.3-windows-x64/blender.exe -b --python-exit-code 1 --python scripts/build_s003_cooking_station.py
```

### S003 餐厨洗涤工位

从烹饪工位重跑北侧开孔台面、连续钢盆和高弯龙头，另存独立阶段工程及两个实景镜头。

```powershell
& .tools/blender-5.2.3-windows-x64/blender.exe -b --python-exit-code 1 --python scripts/build_s003_sink.py
```

## S003 餐厨日用炊具

从洗涤工位装配奶锅、砧板、沥水架和泵头瓶，输出阶段工程与三个实景镜头。

```powershell
& .tools/blender-5.2.3-windows-x64/blender.exe -b --python-exit-code 1 --python scripts/build_s003_kitchen_props.py
```

## S003 主卧阅读角

从餐厨日用阶段装配主卧的臂式床头灯和西窗罗马帘，渲染日光、床头近景及黄昏。

```powershell
& .tools/blender-5.2.3-windows-x64/blender.exe -b --python-exit-code 1 --python scripts/build_s003_bedroom_lighting.py
```

从主卧照明阶段生成庭院和双坡屋盖，再装配餐区吊灯和版画。庭院默认使用已归档的 A131/A132 集合，`--plant-source` 可指定含官方两组 glTF 子目录的源目录。餐区需要 A136 印画原图。

```powershell
& .tools/blender-5.2.3-windows-x64/blender.exe -b -t 10 --factory-startup --python-exit-code 1 --python scripts/build_s003_garden.py
& .tools/blender-5.2.3-windows-x64/blender.exe -b -t 10 --factory-startup --python-exit-code 1 --python scripts/build_s003_dining_lighting.py
```

地面使用 Poly Haven 的 CC0 2K 材质，三组目录名与资源名一致。颜色图使用 sRGB，粗糙度与 OpenGL 法线图使用非颜色数据。[草地](https://polyhaven.com/a/grass_ground)、[落叶碎石](https://polyhaven.com/a/leaf_scattered_gravel)、[磨面混凝土](https://polyhaven.com/a/concrete_floor_worn_001)。

从餐区照明阶段接续制作墙挂厨具、布巾及餐桌器皿。正式资产验收脚本追加同名 BLEND 集合并在另一干净场景回导 GLB，输出实际尺寸、UV、打包图和两种格式的边界差。可选 `--house` 检查同批资产在住宅里实际链接，外观与使用仍按 [B 级标准](../assets/资产质量基准.md)查看渲染实图。

```powershell
& .tools/blender-5.2.3-windows-x64/blender.exe -b -t 10 --factory-startup --python-exit-code 1 --python scripts/build_s003_kitchen_everyday.py
& .tools/blender-5.2.3-windows-x64/blender.exe -b -t 10 --factory-startup --python-exit-code 1 --python scripts/build_s003_breakfast.py
& .tools/blender-5.2.3-windows-x64/blender.exe -b --factory-startup --python-exit-code 1 --python scripts/check_asset_library.py -- --house stages/S003/breakfast/house.blend A104 A146 A147 A148
```

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
