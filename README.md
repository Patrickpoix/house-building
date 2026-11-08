# house-building

约100㎡原创超写实住宅工程。最终目标是完成建筑、家具家电、软装、真实PBR、房间布景及整屋渲染，不把白模或试验资产当作交付。现行执行规范见 [AGENTS.md](AGENTS.md)，进度与约束见 [HANDOFF.md](HANDOFF.md)，验收见 [goal.md](goal.md)。

## Blender：5.2.3 LTS（本地及云端版本基准）

- 正式生产目标版本为 **Blender 5.2.3 LTS**（5.2长期支持系列）。本地Windows使用官方x64免安装ZIP；Linux Codex Cloud应安装对应的**Linux x64**版本，不能使用Windows文件。
- 本地约定路径：`.tools/blender-5.2.3-windows-x64/blender.exe`。原有`.tools/blender-5.0.1-windows-x64/`保留作为回退，不覆盖或删除，也不直接用新版本覆盖已有`.blend`源文件。`.tools/`本身不上传GitHub。
- [Blender官方版本说明](https://www.blender.org/releases/5-2/) · [官方安装包目录](https://download.blender.org/release/Blender5.2/) · [官方SHA256校验文件](https://download.blender.org/release/Blender5.2/blender-5.2.3.sha256)。
- 首次安装后核对`blender --version`、SHA256、原有住宅`.blend`可打开、关键建模脚本、PBR材质、Cycles及去噪可用性。**仅检查不等于整屋最终验收**；未通过的测试如实记录，禁止改动旧工程掩盖兼容问题。
- Blender 5.2.3是生产版本要求，不强制所有工作都在同一机器完成。云端可跑脚本及轻量检查，正式大规模渲染结合GPU与实际可用资源安排。对于云端下载限制，需在环境设置允许官方`download.blender.org`域名并验证后发布；修改本仓库不会自动改变云端环境。

## 开发和验证

在Windows项目根目录运行 `& .\.tools\blender-5.2.3-windows-x64\blender.exe --version`。分项的可重跑命令见 [scripts/README.md](scripts/README.md)。场景源文件、模型、PBR及渲染随阶段记录验证结果并同步GitHub；`.tools/`、下载缓存及其他依赖环境不进入版本库。

## 多视角预览（可选）

本地 Codex 进行多视角渲染总览时，可使用 [scripts/preview_views.py](scripts/preview_views.py) 将同目录多张 PNG/JPG/WebP 合成一张小型联系表；运行命令、依赖和输出位置见 [scripts/README.md](scripts/README.md)。这**只减少会话图片负载**，不修改原图、PBR、模型或工程，近景细节和正式质量验收仍按需看原图。新会话也应阅读 [HANDOFF.md](HANDOFF.md) 与 [AGENTS.md](AGENTS.md)。
