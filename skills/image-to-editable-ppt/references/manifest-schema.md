# Manifest Schema

本文件描述 `editppt` run/page JSON 文件的职责、owner 和当前字段 contract。所有关键状态由 `editppt` 命令推进；页面重建者只写 page-local 文件。

## `deck_manifest.json`

Owner：`editppt prepare` 创建，`editppt run backend` 可更新 image backend，`editppt run finalize` 读取并写入完成时间。

用途：

- 输入类型。
- page 顺序。
- page manifest 路径。
- notes manifest 路径。
- final output 路径。
- run-level image backend contract。
- 用户原始要求。

关键字段：

```json
{
  "schema_version": 1,
  "run_id": "job-id",
  "input_type": "image|images|pdf|pptx",
  "max_concurrent_pages": 6,
  "image_backend": {},
  "pages": [],
  "notes_manifest": "notes_manifest.json",
  "output": "final/origin_edited.pptx"
}
```

`image_backend` 由 `editppt prepare` 写入默认值，必要时由 `editppt run backend` 覆盖。

## `page_jobs.json`

Owner：`editppt prepare` 创建，`editppt run` 命令更新。

用途：

- page 状态 source of truth。
- dispatch 记录。
- result 记录。

结构：

```json
{
  "schema_version": 1,
  "run_id": "job-id",
  "max_concurrent_pages": 6,
  "pages": [
    {
      "page_id": "page_001",
      "status": "pending",
      "page_dir": "pages/page_001",
      "page_request": "pages/page_001/page_request.json",
      "source": "pages/page_001/source.png",
      "dispatch": null,
      "result": null
    }
  ]
}
```

`dispatch` 由 `editppt run dispatch` 写。`result` 由 `editppt run record` 写。`accepted` 由 `editppt run finalize` 写。

## `page_request.json`

Owner：`editppt prepare`。

用途：给 page worker 的任务边界。

包括：

- page id
- page dir
- source image
- slide size
- content box
- max concurrent pages
- allowed write scope
- required outputs
- user constraints
- image backend contract

不得包含：

- page type 预判。
- imagegen_required 预判。
- object-level 决策。

如果本 run 使用 image backend，`page_request.json` 必须包含同一份 `image_backend`。

`slide` 和 `content_box` 由 `editppt prepare` 自动计算。接近 16:9 的输入使用标准宽屏画布；其他输入按源图像素尺寸换算成 custom 画布。agent 必须复制这两个字段到页面 `manifest.json`，不要自行压缩、拉伸或重算画幅。

## `page_result.json`

Owner：page worker 创建，`editppt run record` 校验。

包括：

- manifest path
- imagegen jobs path
- page pptx path
- preview path
- contact sheet path
- validation path
- page-local output hashes，可由 `editppt run record` 补充

## `pages/page_NNN/manifest.json`

Owner：page worker。

用途：page-level PPTX 构建 source of truth。

必须包含：

- `slide`
- `content_box`
- `source`
- `text_inventory`
- `visual_inventory`
- `background_strategy`
- `quality_checks`
- `text_boxes`
- `shapes`
- `images`
- `asset_provenance`
- page strategy

`slide`、`content_box` 和 `source.width_px/source.height_px` 必须来自 `page_request.json`。所有 `box_px`、`points_px` 和 `polygon_px` 均使用 `source.png` 像素坐标；runtime 会把这些坐标映射到 `content_box`，而不是强行拉伸到整张 slide。

`quality_checks` 至少包含：

```json
{
  "font_size_calibrated": true,
  "visual_inventory_matched": true,
  "background_strategy_checked": true,
  "shape_corner_geometry_checked": true
}
```

`background_strategy` 至少说明：

- mode：`native-or-script`、`source-preserving-local-cleanup`、`imagegen-full-clean-base` 等。
- source consistency：保留哪些构图、透视、物体、颜色、光照和细节。
- removed foreground：哪些前景会被移除并重建。
- comparison note：preview 对照 source 后的背景一致性结论。

`roundRect` shape 必须记录 `source_corner_radius_px`，可以额外记录 `corner_reason`。原图是直角矩形时必须使用 `rect`。

推荐记录：

```json
{
  "type": "roundRect",
  "box_px": [64, 169, 472, 187],
  "source_corner_radius_px": 12,
  "corner_category": "small-radius",
  "corner_reason": "source card corners are lightly rounded"
}
```

`corner_category` 可选值：`straight`、`small-radius`、`large-radius`、`pill`。`straight` 不应使用 `roundRect`。

`source-derived-rasterization` 资产必须记录：

```json
{
  "path": "assets/example.png",
  "source": "source.png",
  "source_type": "source-derived-rasterization",
  "source_region_px": [100, 200, 60, 60],
  "require_edge_safe_alpha": true,
  "provenance_note": "Small isolated non-icon object cropped to preserve source identity."
}
```

`source_region_px` 使用 `[x, y, width, height]`。如果使用 `[left, top, right, bottom]`，字段名必须写成 `source_bbox_px`。

`require_edge_safe_alpha` 是可选严格校验：仅当该资产应完整落在透明画布内时设置为 `true`；默认不因为可见像素贴边直接判失败。

它只允许用于无可读文字、非图标、非 pictogram、已经天然孤立且没有背景结构粘连的小型视觉对象，不能用于图标分离、整页、整卡片、整图表或文字区域。图标、pictogram、symbol、logo-like mark 和语义徽章必须通过 image backend 做 source-faithful separation。

`latex-rendered-formula` 公式资产必须记录：

```json
{
  "images": [
    {
      "id": "formula_c2_1",
      "path": "assets/formula_c2_1.svg",
      "box_px": [105, 392, 390, 90],
      "alt": "LaTeX rendered formula formula_c2_1",
      "z_index": 220
    }
  ],
  "asset_provenance": [
    {
      "path": "assets/formula_c2_1.svg",
      "source": "assets/formula_c2_1.tex",
      "source_type": "latex-rendered-formula",
      "provenance_note": "Rendered from LaTeX by editppt formula render-latex; visual fidelity is prioritized over formula editability."
    }
  ],
  "formula_inventory": [
    {
      "id": "formula_c2_1",
      "decision": "latex-rendered-image",
      "editable": false,
      "image": "assets/formula_c2_1.svg",
      "tex_source": "assets/formula_c2_1.tex"
    }
  ]
}
```

公式图片必须由 `editppt formula render-latex` 生成。不要使用 source crop 裁切公式，也不要用手写 native text boxes 拼复杂公式。

## `pages/page_NNN/imagegen-jobs.json`

Owner：`editppt prepare` 创建，`editppt image` 命令更新。

用途：记录 clean base、asset sheet 和已选 bitmap asset 的生成和处理过程。

状态和 provenance 记录规则见 `SKILL.md` 的 State Principles 和 `cli-helper.md` 的资产处理示例。

## `notes_manifest.json`

Owner：`editppt prepare` 创建，`editppt run finalize` 读取。

用途：

- PPT/PPTX speaker notes 原文。
- notes hash。
- page 映射。

notes 不交给 page worker，不翻译、不摘要、不改写。
