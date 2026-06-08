# QA Rubric

确定性验证必要但不充分。谁负责页面复原，谁就负责对该页面检查一次 preview 和 contact sheet。主 agent 记录 page worker 结果时不重复做页面视觉 QA。

## 结构 QA

- PPTX 是有效 zip/package。
- slide count 与输入页数一致。
- PDF/PPTX 页码映射正确。
- media relationship 完整。
- manifest 引用的 asset 文件都存在。
- media hash 与 manifest provenance 匹配。
- speaker notes hash 匹配。
- 不存在 full-slide source raster + editable text overlay 的违规模式。

## 文本 QA

- `text_inventory` 覆盖所有可读文字。
- 每个可编辑文字都是真实可见的 native PPT text box。
- 没有隐藏文本、透明文本、1 pt 文本、off-canvas 文本。
- 预览中没有明显裁切、错误换行、容器文字溢出。
- 中文预览不应显示方框或乱码；必要时使用稳定 CJK 字体。
- 字号和位置必须按 source 校准，不允许默认放大标题、正文或标签。
- 如果 preview 中同层级文字比 source 明显更大、更粗、更拥挤或换行更多，必须在当前页修正。

## 资产 QA

- `visual_inventory` 覆盖所有必需非文字视觉对象。
- 每个必需非文字视觉对象有独立表示，除非明确记录为背景。
- 每个非文字视觉对象的来源决策必须符合 `page-decision-tree.md`。QA 不另设页面对象分类规则；只检查 manifest、asset provenance、preview/contact sheet 是否遵守该决策树。
- asset sheet 切分结果没有粘连、缺边、错名、碎片、跨对象阴影。
- alpha 边缘没有明显 chroma-key 残留。
- 每个最终 raster asset 有 provenance。
- `page-decision-tree.md` 判定为必须 source-faithful separation 的资产不能漏项，不能被替换成同类但不同的符号，不能使用决策树禁止的替代来源。
- source-derived raster asset 必须符合 `page-decision-tree.md` 的例外条件，并记录 source 区域。

## 背景 QA

- clean base 无可读文字。
- clean base 无会被后续重建的前景对象。
- 背景修复区域无明显 ghost、模糊块、涂抹块、伪文字。
- 纯色/规则背景不应浪费 image backend 调用。
- 复杂背景 clean base 必须和 source 是同一背景：构图、透视、主要物体位置、色彩、光照和关键细节不能明显漂移。
- 如果 image backend 生成了同主题但不同背景，即使 deterministic validation 通过，也必须在当前页修正。

## 形状 QA

- source 是直角矩形、表格外框或方形面板时，manifest 必须用 `rect`。
- `roundRect` 只在 source 明确为圆角时使用，并记录 `source_corner_radius_px`。
- 重建圆角半径必须接近 source，轻微圆角不能被放大成胶囊。
- 不要因为设计偏好把普通矩形改成圆角矩形。
- 不要把文字笔画当装饰线重复绘制；出现多一横、多一点、多一符号时需要回看 source 判断是文字笔画还是独立装饰线，再在当前页修正。

## 视觉 QA

- `preview.png` 必须存在。
- `split_assets_contact.png` 必须存在，并展示 origin 与 preview 对比。
- 视觉漂移、缺标签、低质量占位图，以及任何违反 `page-decision-tree.md` 的对象来源决策都必须在当前页修正。
- 大容器角形、表格边界、卡片边框要和 source 对齐；圆角误判属于当前页修正项，不是低风险 warning。

## 检查结果

必须在当前页修正：

- 输入无法归一化。
- final PPTX 无法打开。
- page 缺少 buildable manifest/page.pptx。
- 必需视觉对象缺失。
- 对象来源决策违反 `page-decision-tree.md`。
- 复杂背景 clean base 明显失真或变成不同背景。
- source 直角矩形被重建成圆角矩形，且未能证明 source 有圆角。
- 文字字号/位置明显偏离 source，导致布局拥挤、溢出或遮挡。

warning：

- 非图标、非关键装饰的轻微视觉漂移。
- 图标轻微线宽、抗锯齿、比例、阴影或细节差异。
- 部分非关键装饰未完全一致。
- 已记录的低风险字体差异。

warning 可以随当前 PPT 交付。
