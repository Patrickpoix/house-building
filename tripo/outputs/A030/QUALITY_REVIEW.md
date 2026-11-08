# A030 挂袋样品质量检查

状态：**未通过正式资产验收**；保留原始 GLB 及研究渲染，不计入正式资产数。

- 来源：项目 `references/experiments/A030-single-view-model-unknown.png`；Studio H3.1，高精度，三角面目标200,000，2K，纹理、PBR、去光和AI增强开，超清和分部件关。上传后按钮价30；生成一次，余额由4800降为4770，减少30积分。Studio结果显示194,388面。生成和扣费证据在 `../../price-evidence/A030-before-generation.*` 及 `A030-generation-completed.*`。
- 导出：原始 `tripo-original.glb` 与 Studio 下载的 GLB 逐字节比较一致；本目录保留未经编辑的原件。Blender 导入检查为一个网格、103,620顶点、194,388面、一个 UV 层。导入尺寸约 0.689×0.469×1.000，尚未按设计实物尺度标定。
- 材质：内嵌三张 2048×2048 图。Base Color 为 sRGB；合并的 Roughness/Metallic 图为 Non-Color，分别通过绿色/蓝色通道连接；Normal 图为 Non-Color，经 Normal Map 节点连接。检查脚本对像素采样显示各图通道有变化；这证明存在变化，不证明贴图物理正确。详见 `inspection.json`。
- UV/网格：UV范围在0–1；194,388个三角形中120个UV面积小于 `1e-12`（以双倍UV面积计）。导入网格检测到12,632条非流形边；GLB导入时UV或法线拆点可能影响该计数，不能仅凭这个数字判定破洞，也不能声称网格闭合，需进一步定位和修复。
- 四向及近景：`comparison/` 的 front、back、left、right 和 original-close 已查看。袋口、双提带、前袋及织物褶皱可辨；近景织纹密度与方向不均，局部模糊且有波纹状畸变，缝线及提带接头较软。侧视提带顶部轮廓存在间隙，是否为独立提带相互遮挡还是几何断裂需进一步检查；背面也出现类似前袋结构，是否符合目标设计需核对。故不能作为完整高质量资产通过。
- 零积分派生试验：`render_tripo_a030_comparison.py` 保留UV、不重投影，将对象局部X缩放至1.12倍，并以相同镜头和照明渲染 `original-close.png` 与 `stretched-close.png`。形变后纹理和口袋一起横向拉宽；没有发现贴图断链，但原图已有的织纹畸变仍在，且固定贴图不等于视觉保真。此单一仿射缩放不是布料重模拟、模块组合或大幅重拓扑测试，不能证明其他派生方法合格，也不计为新资产。

复跑：从项目根目录执行 Blender 后台 `scripts/inspect_tripo_asset.py -- tripo/outputs/A030/tripo-original.glb tripo/outputs/A030/inspection.json`，以及 `scripts/render_tripo_a030_comparison.py`。两项已成功执行；渲染初次因空场景没有 World 而失败，添加 World 后重跑成功。

下一步：定位提带和非流形边、评估织纹与缝线，按原设计尺度处理并检查修复后的四向/近景；再根据实物质量决定能否纳入住宅。正式生产的配置与后续资产安排见项目根目录 AGENTS.md、HANDOFF.md。

## 2026-11-08 粗糙度隔离

Blender 5.2.3 在相同相机、灯光下将粗糙度单独改为常数 0.5，保留颜色、法线与金属度；结果与原材质位于 `roughness-diagnostic/`。无损局部 `(150, 160, 512, 512)` 对照可见高光变化，但袋身织纹波纹及方向异常仍在；这只说明该视角下统一粗糙度不足以消除缺陷，不能排除原粗糙度图的其他问题，也不能据此区分 UV 与颜色/法线贴图的贡献。恢复粗糙度连接后生成的 `without-normal.png` 与原诊断对应图逐像素一致。未改原 GLB，未用积分；资产仍未通过验收。后续优先定位 UV 和纹理畸变、提带连接，再评估局部重做或改用布料工艺。
