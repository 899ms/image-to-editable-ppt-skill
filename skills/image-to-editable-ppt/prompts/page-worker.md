# Page Worker Prompt 模板

```text
重建 image-to-editable-ppt 的一个页面。

Run dir: <absolute run dir>
Page id: <page_001>
Page dir: <absolute page dir>
Source image: <absolute page dir>/source.png

你只拥有这个 Page dir。不要编辑 deck_manifest.json、page_jobs.json、notes_manifest.json、final 输出、input 原件或任何其他 page 目录。

读取并遵守这些本地 reference：
- <skill root>/SKILL.md
- <skill root>/references/cli-helper.md
- <skill root>/references/page-decision-tree.md
- <skill root>/references/manifest-schema.md
- <skill root>/references/qa-rubric.md

在任何生图或改图前，使用 `page_request.json.image_backend` 指定的 `editppt image` backend。如果 `editppt image` 不可用，先按 CLI 报错提示尝试 `codex login` 或 `editppt config`；仍不可用时使用当前可行的可编辑结构完成页面，并在 `validation.json` 写明缺失资产和原因。
需要图片后端、输入图片、batch JSONL、clean base 或 asset sheet 的参数说明时，读取 `editppt image --help` 以及对应子命令 help。

必须沿用 `page_request.json.slide` 和 `page_request.json.content_box` 写 manifest。不要自行把页面改成 16:9，不要重新计算画幅。所有 `box_px`、`points_px` 和 `polygon_px` 都以 `source.png` 像素为准，runtime 会映射到 `content_box`，避免源图被拉伸。

目标：
把 source page 重建成对象级可编辑 PowerPoint。所有页面对象分类、native shape 边界、可分离资产边界和 source-derived raster 例外都必须按 `references/page-decision-tree.md` 执行。不要在本 prompt 之外临时发明对象来源策略。

开始写 manifest 前，每张图必须按 `page-decision-tree.md` 完成三步决策：
1. 背景识别与修复：判断背景是否可由 PPT 结构对象/确定性 runtime 复原，还是需要 `editppt image edit --image <source.png>` 生成 source-preserving clean base。
2. 前景素材分离：判断哪些大片规则内容可以精确裁切；其余图标、插画、装饰等前景素材必须按决策树用 `editppt image` 的编辑模式做 source-faithful asset sheet 分离。
3. PPT 原生元素复原：文字、文本框、简单矩形/圆角矩形、简单箭头、表格等用 PPT 原生结构对象复原，并完成字号、角形和布局校准。公式不走 native text；必须先转写为 LaTeX，再用 `editppt formula render-latex` 渲染为独立图片资产放入 PPT。

必须在 Page dir 内产出：
- manifest.json
- imagegen-jobs.json
- page.pptx
- preview.png
- split_assets_contact.png
- validation.json
- page_result.json

`page_result.json` 必须是 JSON，至少包含：

```json
{
  "page_manifest": "manifest.json",
  "imagegen_jobs": "imagegen-jobs.json",
  "page_pptx": "page.pptx",
  "preview": "preview.png",
  "contact_sheet": "split_assets_contact.png",
  "validation": "validation.json",
  "page_result": "page_result.json"
}
```

使用 `editppt image generate/edit/batch` 生成 clean base、背景修复和 asset sheet。使用 `editppt formula render-latex` 生成公式图片资产和 manifest image fragment。哪些对象必须用 `editppt image edit --image <source.png>` 分离、哪些对象允许 native shape 或 source-derived raster、哪些公式必须转 LaTeX，全部按 `page-decision-tree.md`。确定性 CLI/runtime 只可用于归一化、记录、去底、切分、裁剪、公式渲染、构建、验证和 QA。

manifest.json 还必须包含：

- `visual_inventory`: 非文字视觉对象清单，至少记录 id、描述、决策和对应 asset/background。
- `background_strategy`: 背景处理方式、source-consistency 约束、是否局部修复、是否使用整张 imagegen clean base 以及原因。
- `quality_checks`: `font_size_calibrated`、`visual_inventory_matched`、`background_strategy_checked`、`shape_corner_geometry_checked` 都必须为 true。

source-derived raster asset 的允许范围和裁剪要求全部按 `page-decision-tree.md`。如果使用 source-derived raster，必须用 `editppt image crop` 生成并记录 `source_region_px` 或 `source_bbox_px`。

返回前必须：

- 从 manifest.json 构建 page.pptx
- 渲染 preview.png
- 创建 split_assets_contact.png
- 运行 page validation
- 检查 required outputs 都存在
- 作为页面复原者自检 preview/contact sheet：字号不过大、视觉对象无遗漏、复杂背景没有整体换图、矩形/圆角与 source 一致
- 检查发现 page-local 问题时，在当前页内直接修正后再返回

只返回：
page_manifest=`<absolute path>`
page_pptx=`<absolute path>`
preview=`<absolute path>`
contact_sheet=`<absolute path>`
validation=`<absolute path>`
page_result=`<absolute path>`

```

```
