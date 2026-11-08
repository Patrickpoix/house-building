# 声明式布局

每份 JSON 就是一栋房屋的配置：`src/02_scene/assemble.py` 读它，从母库
`assets/_library/asset_library.blend` 按资产 ID 实例化，用共享 4K 贴图生成
建筑壳体，输出 `scene/assembled/<id>.blend` 与俯视预览。

**改 JSON = 换一栋房，不碰建模代码。** 完整字段手册见
[`docs/09_任意组装指南.md`](../../docs/09_任意组装指南.md)。

| 文件 | 房型 | 面积 | 资产数 |
| --- | --- | --- | --- |
| `family_100.json` | 家庭三居 · 7 分区 / 8 隔墙 | 100 ㎡ | 27 |
| `studio_45.json` | 单身公寓 · 紧凑高效 | 45 ㎡ | 20 |
| `loft_open.json` | 开放 Loft · 零隔墙 / 3.4 m 挑高 | 96 ㎡ | 25 |

```bash
# 查可拼的资产（36 类 / 144 个）
blpython src/02_scene/assemble.py -- --list-categories
blpython src/02_scene/assemble.py -- --pick 03

# 组装 / 重建
blpython src/02_scene/assemble.py -- scene/layouts/studio_45.json --render
blpython src/02_scene/assemble.py -- --all --render
```

复制任一 JSON、改 `shell` 尺寸 / `rooms` / `partitions` / `assets` 就能拼自己的房型。
`assets` 里的 ID 必须来自 `assets/catalog.csv`（每类 4 个变体）。
