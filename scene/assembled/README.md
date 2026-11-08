# 组装产物（可再生成就）

本目录由 `src/02_scene/assemble.py` 根据 [`scene/layouts/`](../layouts/) 里的
布局 JSON 生成，**不是手工资产**。整目录删掉后重跑
`blpython src/02_scene/assemble.py -- --all --render` 即可完全重建。

每栋房屋一个 `.blend` + 一张俯视预览 `.png`：

| 文件 | 房型 | 资产实例 |
| --- | --- | --- |
| `family_100.blend` / `.png` | 100㎡ 家庭三居 | 27 |
| `studio_45.blend` / `.png` | 45㎡ 单身公寓 | 20 |
| `loft_open.blend` / `.png` | 开放 Loft | 25 |
| `三栋房屋对比.png` | 三栋并排对比 | — |

三栋用的是**同一套 36 类 / 144 个高质量 PBR 资产**，只是布局不同，
用来直观证明「资产可任意组装成不同房屋」。

`.blend` 里用到的资产 Collection 已内嵌，4K 贴图仍以 `//` 相对路径引用
`assets/_textures/`；整个 `house-building/` 一起搬即可正常打开，单独拷出
需按 `docs/08_迁移指南.md` 带贴图或跑 `relink_all.py`。
