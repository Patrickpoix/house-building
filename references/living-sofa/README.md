# 起居沙发参考与预检（2026-11-09）

用途：S003 起居室三人沙发，设计目标约 2.20 × 0.90 × 0.78 m；宽度参考现有 2.20 m 占位，最终需按模型、座高和通行复核。方向为低饱和橄榄绿织物、两块坐垫和靠垫、浅橡木短腿。

`front.png` 由 Codex 内置图像生成工具制作，提示词：正面正交、白底、两坐垫两靠垫、圆角扶手、四根浅橡木脚、220×90×78 cm，柔和均匀照明、无额外物品。`left-v1.png` 基于正面推断左视，出现远侧扶手；`left-v2.png` 基于两图要求严格左视，远侧扶手不再可见。两张侧图均属 AI 推断，不是实物测量。实际工具入口为内置 image_gen；具体模型版本未单独核对，不作版本断言。

预检：颜色、双垫、木脚及大致造型相符；v2 侧视座垫前端超出扶手前缘，深高比例与文字目标未严格量化，背面与内部未见；这些属于已知不确定性，生成后须核查几何并按设计尺寸校正。Tripo 输入为 `front.png`、`left-v2.png` 原图；v1 仅作对照。

## 实际提示词

正视：

> Use case: product-mockup. Create one photorealistic clean studio reference image for a 3D model: a warm muted olive-sage upholstered three-seat residential sofa, modern understated Japanese-Scandinavian design. Straight-on FRONT orthographic elevation, centered, entire object visible including all four legs, white seamless background, soft even shadowless lighting. Physical design 220 cm wide, 90 cm deep, 78 cm high; low fully upholstered rectangular body, two separate plump seat cushions and two loose back cushions with subtle seams and natural fabric folds, narrow gently rounded arms with equal thickness, four short visible solid pale oak legs. Realistic soft woven upholstery, restrained practical lived-in appearance. Both sides symmetrical, clear structure and unoccluded silhouette. No pillows, throw, room, logos, text, diagram, multiple views, severe perspective, dramatic shadows or crop.

左视初稿（参考正视）：

> Create a photorealistic LEFT SIDE orthographic product view of the exact same sofa in the supplied image, for multi-view 3D modeling. Match precisely the olive-sage fabric, narrow rounded upholstered arm, tapered pale oak legs, base height, cushion thickness and proportions. Sofa is 220 cm wide, 90 cm deep, 78 cm high. Side view shows depth and back inclination; two legs on this side, no extra legs. Camera perfectly level, looking straight at its left end, near-orthographic, entire sofa centered against white seamless backdrop, soft even neutral light. No text, props, room, perspective distortion, extra structural details or cropping. Hidden construction is a plausible design inference, not a factual reference.

左视修订（参考正视和初稿）：

> Input image 1 is the exact front design reference; input image 2 is a side-view candidate. Produce a clean true LEFT SIDE orthographic elevation of the same single sofa in image 1. Camera exactly perpendicular to its left side at mid-height: the far arm and far legs are completely hidden behind the near arm and near legs; no view of the opposite side or seat top. Match the front image olive-sage fabric, two tapered light oak legs visible from the near side, gently rounded upholstered arm and base, back cushion height, overall proportions (90cm depth, 78cm height). Seat cushion remains within the arm front/back footprint, no projecting seat. Even soft studio illumination, whole object on plain white background, no text, no other objects. Internal structure and back not visible are design assumptions.
