# 阶段脚本

这些脚本和结果尚未构成最终住宅交付。所有路径均相对 `house-building/`。

## Blender 阶段

使用 Blender 5.2.3 LTS，以下命令从项目目录运行；`--python-exit-code 1` 确保 Python 异常产生非零退出码。

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

## 三维生成环境

已验证的环境为 WSL Ubuntu、Python 3.11、PyTorch 2.6.0+cu124，完整包版本见 `requirements-hunyuan-linux.txt`；Hunyuan3D-2 代码版本及官方权重修订见 `REPORT.md`。从项目根目录用 `bash scripts/run_hunyuan.sh shape 输入图片 输出.glb` 启动形状生成，或用 `bash scripts/run_hunyuan.sh texture 网格.glb 参考.png 输出.glb` 启动纹理试验。入口在 Python 启动前设置项目内 OpenGL 库路径，并默认使用项目内模型与缓存；`HY3DGEN_MODELS` 和 `HF_HOME` 可覆盖默认值。形状生成只输出几何。

纹理试验需要 CUDA 编译器、GCC、CPU/GPU 扩展、`libOpenGL.so.0`、官方权重和足够内存。当前构建环境位于 WSL 的 `~/.cache/house-building-mamba/cuda-build`，不随项目自动迁移；可用 `HOUSE_CUDA_BUILD` 指向等价环境，并执行 `bash scripts/build_texture_extensions.sh` 编译。`check_texture_extensions.py` 使用 GPU 三角形验证光栅器。`hunyuan_texture_smoke.py 网格.glb 参考.png 输出.glb` 使用 CPU 内存卸载生成颜色纹理；它不是完整 PBR 管线。环境安装记录、权重校验及未完成事项见 `REPORT.md`。
