# 页面决策树

本文件是唯一页面决策标准。每一张 `source.png` 都必须按三步判断：

1. 背景识别与修复。
2. 前景素材分离。
3. PPT 原生元素复原。

不要先画 PPT 原生元素再回头决定背景和前景资产。先把背景、前景、原生结构三类对象边界定清楚，再写 manifest。

## 决策前清单

开始三步判断前，先建立页面清单：

- 页面尺寸和页面类型。
- 所有可读文字。
- 背景类型：纯色、渐变、规则纹理、照片、插画、dashboard、空间/产品图、复杂图形背景。
- 背景是否被后续要重建的文字、图标、标签、贴纸、手绘标记或其他前景对象遮挡。
- 前景视觉对象：图标、pictogram、logo-like mark、照片、纹理、插画、人物、植物、设备、手绘标记、贴纸、装饰线、徽章。
- 可精确裁切的大块规则内容：矩形插图、矩形照片、规则截图、地图框、视频封面、规则图表块等。
- PPT 原生元素候选：文字、文本框、卡片、面板、表格、坐标轴、线条、流程框、分隔线、简单箭头。
- 公式候选：目标函数、约束、矩阵、分式、根号、cases、多行方程组、普通数学表达式。公式必须单独列出，不归入普通文字。
- 每类文字的 source 字形高度、容器高度、行距和密度。
- 每个矩形/卡片/表格外框的角形：直角、轻微圆角、明显圆角、pill。

manifest 必须记录 `visual_inventory`、`background_strategy` 和 `quality_checks`。其中 `quality_checks.font_size_calibrated`、`visual_inventory_matched`、`background_strategy_checked`、`shape_corner_geometry_checked` 都必须为 `true`。

## 1. 背景识别与修复

第一步只决定背景，不处理前景资产和文字。

### 1.1 不需要生图工具的背景

以下背景不需要 `editppt image` 修复，直接用 PPT 结构对象或确定性 runtime 复原：

- 纯色背景。
- 简单渐变。
- 普通卡片、面板、容器底色。
- 表格线、坐标轴、网格线、图表框。
- 规则重复纹理、规则分隔带、简单阴影。
- 没有被前景遮挡的空白背景区域。

这类背景应在 `background_strategy.mode` 中记录为 `native-or-script` 或等价模式。不要为了纯色或规则背景调用 image backend。

### 1.2 可以复用的背景

只有在同时满足以下条件时，才允许复用已有背景区域：

- 背景本身没有需要移除的文字、标签、图标、贴纸、手绘标记或其他前景对象。
- 复用区域不会造成“背景一份、可编辑对象一份”的重复。
- 复用区域不是整页 `source.png` 加 native text overlay。
- 复用区域是页面中的背景/插图区块，而不是为了跳过可编辑化而整卡片、整表格、整图表截图。

### 1.3 需要生图工具修复的背景

以下情况需要 `editppt image edit --image <source.png>` 做背景修复或 clean base：

- 复杂照片、空间、真实产品图、复杂 dashboard、复杂插画背景被前景文字或图标遮挡。
- 移除文字、标签、图标、贴纸、手绘标记后，需要补全被遮挡区域。
- 背景与前景粘连，简单裁切或 native shape 无法保留 source identity。

clean base 的目标是“移除后续会重建的前景对象后的同一张背景”，不是生成同主题新图。prompt 必须把 source 当作 edit target 和 strict visual reference，并明确：

- Preserve：原始画幅比例、构图、透视、物体位置、色彩、光照、材质、纹理、景深和背景身份。
- Remove：后续会重建的可读文字、标签、数字、图标、贴纸、徽章、手绘标记、装饰对象。
- 禁止：新房间、新 dashboard、新产品、新镜头角度、新物体位置、不同光照、伪文字、水印、模糊补丁、涂抹痕迹。

如果只是小范围遮挡，优先局部补全或小 patch；不要让 image backend 重新想象整张背景。

### 1.4 Dashboard 不是默认背景

dashboard 默认不是背景，也不是一个可整体截图化的图片块。

dashboard 中的标题、数字、表格、坐标轴、图例、普通图表元素、指标卡、筛选器和标签，应优先在第三步拆成 PPT 原生文字和结构对象。

只有以下区域可以作为背景或图片区域处理：

- 地图。
- 热力图。
- 复杂截图底图。
- 无法可靠恢复数据的复杂图表图像区域。
- 作为页面视觉背景存在、且不会被后续原生对象重复覆盖的复杂纹理或底图。

不要把整块 dashboard、整张表格、整张卡片或整张图表截图化来跳过可编辑结构。

### 1.5 背景记录

`background_strategy` 至少说明：

- `mode`：`native-or-script`、`source-preserving-local-cleanup`、`imagegen-full-clean-base` 等。
- `source_consistency_contract`：需要保留的构图、透视、颜色、光照、物体位置和关键细节。
- `removed_foreground`：从背景中移除、之后会重建的前景对象。
- `comparison_note`：对照 source 后的背景一致性结论。

## 2. 前景素材分离

第二步只决定非文字前景视觉对象的来源。前景对象必须先进入 `visual_inventory`，再决定来源。

### 2.1 允许精确裁切的大块规则内容

只有“大片、规则、可以精确裁剪”的内容允许使用 `editppt image crop` 或 source-derived raster：

- 矩形插图。
- 矩形照片。
- 规则截图。
- 地图框。
- 视频封面。
- 规则图表块或规则图片块。
- 已天然孤立、边界清晰、没有背景结构粘连的大块非文字视觉区域。

判断标准是“是否可以精确裁剪”：

- 有清晰矩形或规则边界。
- crop box 可以覆盖完整对象并保留安全边距。
- 不需要复杂透明边缘。
- 不需要抠出不规则轮廓。
- 不会裁进后续要独立重建的文字、图标、标签或结构对象。
- 裁出来作为一个可移动图片对象后，不会冒充整页、整卡片、整表格或整图表的可编辑化。
- 不包含必须成为 native text box 的可读文字。

使用 source-derived raster 时必须：

- 用 `editppt image crop` 裁剪，不要手写临时代码。
- 记录 `source_region_px` 或 `source_bbox_px`。
- 记录 `source_type: "source-derived-rasterization"`。
- crop box 额外留安全边距，通常至少 6-12 px。
- 如果需要透明化，用 border background removal，并复核 alpha 边缘。

### 2.2 其他前景素材默认走 image edit 分离

除 2.1 中可精确裁切的大块规则内容外，其他非文字前景视觉对象默认使用 `editppt image edit --image <source.png>` 做素材板分离：

- 图标、pictogram、symbol、logo-like mark。
- 徽章、贴纸、胶带、印章、角标。
- 手绘标记、手绘箭头、装饰下划线、圈注、对勾、叉号。
- 复杂箭头、图标化节点、带纹理或阴影的元素。
- dashboard 或图表里的语义小图标、趋势图标、警告符号、状态符号。
- 叶子、植物、人物、动物、电脑、手机、设备、场景插画和其他承载页面画风的非文字对象。

这些对象禁止用 native primitive 近似，即使它们看起来由圆、线、矩形或椭圆组成。判断标准不是“能不能画”，而是“它是否承载语义、身份或画风”。

### 2.3 素材板 prompt 原则

素材板是 source-faithful separation，不是 redraw。prompt 必须要求：

- 从 source 中分离既有对象。
- 保持原始形状、笔画、颜色、比例、内部留白、纹理和视觉身份。
- 使用平整 chroma-key 背景。
- 每个对象完整、互不接触、互不重叠、有足够 padding。
- 对象数量和顺序与 `visual_inventory` 一致。
- 不生成可读文字、标签、伪文字、水印。
- 不生成整卡片、整面板、整图表、整页片段。
- 不重绘、不美化、不简化、不替换为同义符号、不创造更干净的替代图标。

绿色主体不要用 `#00ff00` 做 key background；紫色/洋红主体不要用 `#ff00ff`。

### 2.4 素材板对账与修正

asset sheet 生成后必须对账：

- 切分出的资产数量覆盖 `visual_inventory` 中所有必需对象。
- 每个资产命名和 inventory 对应。
- 缺对象、错符号、少笔画、严重变形、背景粘连、文字污染、变成同义替代，必须重新生成或调整资产后再使用。
- 轻微线宽、抗锯齿、比例、阴影或细节差异可以作为 warning 随当前 PPT 交付。
- 用 native primitive 近似必须分离的前景对象，不属于 warning，必须改为 source-faithful separation。

## 3. PPT 原生元素复原

第三步复原所有应由 PowerPoint 原生结构承载的对象，并处理公式资产。此时背景和前景素材来源已经定好。

### 3.1 文字与文本框

所有可读文字默认成为原生 PPT text box。公式不属于本节的普通可读文字，必须按 3.2 转写 LaTeX 并渲染为公式图片资产。

不要用生成图承载可编辑文字。不要用隐藏文本、透明文本、1 pt 文本或 off-canvas 文本满足 text inventory。

例外是品牌或背景身份的一部分，而不是普通可编辑文本：

- logo 字标、品牌符号和商标文字。
- 产品包装上的品牌文字。
- 地图底图地名。
- UI 截图内部不要求编辑的小字。
- 照片背景中的招牌。
- 作为纹理存在的报纸、书页、代码等文字。
- OCR 置信度很低且不影响主要语义的极小文字。

这些例外应在 `visual_inventory` 或 `asset_provenance` 中说明，不要把主要标题、副标题、正文、表格文字、图例、坐标轴文字、数字、标签或按钮文字伪装成例外。

字号不要靠默认值猜测。先按 source 中的实际字形高度估算：

- 同一层级文字用同一组 font size，例如标题、副标题、表头、正文、标签、状态徽章。
- 对中文密集版面，初稿宁可比估算小 5%-10%，不要偏大。
- 字形高度接近容器高度时，font size 通常需要明显小于容器高度；给 PowerPoint/WPS 的 font metrics 留余量。
- 文本框要比源图字形边界更宽松，避免 PowerPoint/WPS/preview font metrics 导致裁切或错误换行。
- 构建 preview 后，逐类对比 source。如果标题、正文或标签比 source 更粗大、更拥挤或换行更多，先下调 font size 再继续。

manifest 必须通过 `quality_checks.font_size_calibrated=true` 记录字号校准完成。

### 3.2 公式处理

公式不作为普通 native text box 复原。遇到公式时必须：

- 先把 source 中的公式转写为 LaTeX。
- 使用 `editppt formula render-latex` 渲染成 SVG、PNG 或 PDF 图片资产。
- 优先使用 SVG；如果目标环境不稳定或 SVG preview/PowerPoint 兼容性有问题，再使用 PNG。
- 渲染命令必须写入 page dir，例如：

```bash
editppt formula render-latex <page_dir> \
  --tex "\\sum_{i \\in N} p_{ij} x_{ij} \\ge a_j u_j" \
  --out assets/formula_c2_1.svg \
  --box 105,392,390,90 \
  --id formula_c2_1 \
  --fragment assets/formula_c2_1.fragment.json
```

然后把 fragment 中的 `images`、`asset_provenance` 和 `formula_inventory` 合入 `manifest.json`。

公式资产记录要求：

- `visual_inventory` 中记录公式 id、LaTeX 源和 `decision: "latex-rendered-image"`。
- `asset_provenance.source_type` 必须是 `latex-rendered-formula`。
- `asset_provenance.source` 指向对应 `.tex` 文件。
- `provenance_note` 说明该公式由 LaTeX 渲染，视觉保真优先于公式对象级可编辑。
- 不要用 Unicode 下标/上标拼公式，不要手写大量公式 text boxes，不要把公式截图从 source 中裁切出来。

如果本机缺少 TeX engine、SVG/PNG converter 或 LaTeX 编译失败：

- 继续产出当前可打开 PPT。
- 在 `validation.json` 中记录公式 id、LaTeX 源、CLI 错误、需要安装/修复的工具或宏包。
- 不允许用整页截图替代。

### 3.3 结构性 primitive 与布局对象

以下对象可以使用原生 PPT shape 或结构对象：

- 直线、虚线、折线。
- 矩形、圆角矩形、圆形、椭圆。
- 普通箭头和连接线。
- 纯色卡片、面板、分隔线、边框。
- 表格、表格线、坐标轴、网格线。
- 简单柱状图、进度条、状态色块。
- 简单标注。
- 没有风格细节的基础流程框和容器。

这些对象必须只是布局结构，不承载语义图标或画风身份。圆形图标里的 DNA、锁、网络节点、靶心、放大镜、对勾等 pictogram 不属于结构性 primitive，必须在第二步分离。

### 3.4 角形与形状细节

角形选择必须保守：

- 先判断 source 角形类别：`straight`、`small-radius`、`large-radius`、`pill`。
- `straight` 用 `rect`。
- `small-radius`、`large-radius`、`pill` 用 `roundRect`，并估算 `source_corner_radius_px`。
- 圆角半径是对象级属性，不是布尔开关。大面板的 8-12 px 轻微圆角不能被重建成 70 px 大圆角。
- 不确定时放大查看 source 角点；如果仍不确定，记录判断依据并偏向较小半径。
- 每个 `roundRect` shape 必须记录 `source_corner_radius_px`，`corner_reason` 只作为补充说明，不能替代半径。

### 3.5 文字笔画与装饰拆分

文字和装饰不要重复拆分：

- 一个可读字的笔画必须只属于 native text box，不能再额外用 shape 画同一笔画。
- 独立装饰线、分隔线、按钮下划线可以作为 shape，但必须确认它不是文字的一部分。
- 如果拆分后 preview 出现多一个横杠、多一个点或重复符号，必须删除重复 shape。

### 3.6 层级

保持对象之间的分组关系，例如：

- 图标和圆形底座。
- 徽章和数字。
- 气泡框和文字。
- 手绘箭头和注释。
- 卡片背景、标题、图表和标签。

推荐 z-index：

- clean background/base：0
- native structural shapes：10-20
- separated foreground assets：30
- native editable text：40+
- 特殊情况下压在文字上方的圈注、贴纸或手绘标记：50+

不要让背景覆盖文字。不要让前景素材压错层。不要让同一个文字、图标或装饰对象在图片层和原生对象层重复出现。

## Manifest 坐标与记录

页面 manifest 使用 source-image pixel coordinates：

- `source.width_px`
- `source.height_px`
- `box_px: [x, y, width, height]`
- `points_px: [x1, y1, x2, y2]`

还必须包含：

- `text_inventory`
- `visual_inventory`
- `background_strategy`
- `quality_checks.font_size_calibrated`
- `quality_checks.visual_inventory_matched`
- `quality_checks.background_strategy_checked`
- `quality_checks.shape_corner_geometry_checked`

页面复原者负责完成一次页面级自检。自检依据记录在 manifest 的结构化字段和 `validation.json` 中。自检至少覆盖：

- 背景是否保持 source 构图、透视、颜色和物体位置。
- 背景中是否残留后续会重建的对象。
- 主要文字是否都是原生 text。
- 字号是否经过 source 对照校准。
- 前景素材是否完整。
- 是否存在整页、整卡片、整表格、整 dashboard 或整图表截图化。
- 是否存在图片层文字和原生文字重复。
- 圆角、直角和形状细节是否正确。
- dashboard 和图表是否合理拆分。
- z-index 是否正确。

## 当前页修正与 Warning 判定

必须在当前页修正：

- 背景 clean base 明显漂移，变成同主题新背景。
- 背景仍残留会被后续重建的文字、图标、标签、贴纸或手绘标记。
- 第二步判定为必须 image edit 分离的对象被 native primitive 或不合规 source crop 近似替代。
- 第二步素材板缺对象、错符号、少笔画、严重变形、背景粘连或文字污染。
- 主要可读文字留在图片里，没有做成原生 text。
- 同一段文字、图标或装饰对象既在图片层里，又作为原生对象重复出现。
- dashboard、表格、卡片或图表被整体截图化，跳过了可编辑结构。
- 文字字号/位置明显偏离 source，导致布局拥挤、溢出或遮挡。
- source 直角矩形被重建成圆角矩形，且未能证明 source 有圆角。
- z-index 错误导致文字或关键对象被遮挡。

可以作为 warning 随当前 PPT 交付：

- image backend 分离后的轻微线宽、抗锯齿、比例、阴影或细节差异。
- 非关键装饰的轻微视觉漂移。
- 已记录的低风险字体差异。

warning 不能掩盖未按三步决策执行的问题。对象来源违反本决策树时，必须在当前页修正。
