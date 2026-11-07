# A031 门挂围裙：原始生成检查

状态：未通过，不是正式资产。生成任务 `57cf5ae4-a5d6-412a-94bc-1c8d600aa150`。输入 `references/A031-apron/front.png` 与 `back-revised.png`，正背双视图；侧视未使用。H3.1、三角面目标 200000、2K 纹理、PBR 与去光开启，超清和分部件关闭。AI 增强状态未在本次界面确认，不推定。报价 30，余额 4770 → 4740，实扣 30 积分。界面结果显示 191408 面。原始文件 `tripo-original.glb`，未加工。

Blender 5.0.1 导入结果：一个网格，191406 面、104734 顶点，一个 UV 层；三张内嵌 2048 贴图分别接入 Base Color、打包粗糙度/金属度和 Normal，色彩空间及节点见 `inspection.json`。原始包围盒约 0.839 × 0.297 × 1.000，尚未按设计尺寸规范化。统计到 17648 条非流形边、121 个近零 UV 面；这些数字本身不能判断可见破损，需定位。

`views/` 为可重跑的四向及斜向近景，已查看全部五张：正面口袋和系带可辨，背面无口袋；但两侧均明确显示正背分成两片并形成深袋状空腔，包围盒深度约 0.297，和单层围裙结构相悖。口袋与布面缝线和织纹偏软，系带和扣件连接细节仍需核查。颜色贴图存在但不等于材质细节达标。

下一步：以正面轮廓、侧面薄层结构为约束重建或替换布身，保留原始文件作对照；核查口袋开口、系带连接、真实布厚和 UV，再按目标尺寸设置轴心，检查材质并在房间中复验。未经复验不能计入资产数量；不重复付费生成，除非明确缺陷与预期改善。

检查命令：

```powershell
& .\.tools\blender-5.0.1-windows-x64\blender.exe -b -t 4 --python scripts/inspect_tripo_asset.py -- tripo/outputs/A031/tripo-original.glb tripo/outputs/A031/inspection.json
& .\.tools\blender-5.0.1-windows-x64\blender.exe -b -t 4 --python scripts/render_tripo_views.py -- tripo/outputs/A031/tripo-original.glb tripo/outputs/A031/views
```
