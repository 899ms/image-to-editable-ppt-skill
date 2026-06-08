---
name: image-to-editable-ppt
description: 当用户提供一张或多张幻灯片图片、图片版 PPT/PPTX 或 PDF，并要求转成可编辑 PowerPoint/PPTX、重建幻灯片对象、保留页面备注或做可编辑化复刻时使用。
---
# Image to Editable PPT

## Overview

这个 skill 用于把视觉型幻灯片输入重建成对象级可编辑的 PowerPoint `.pptx`。

输入可以是一张图片、多张图片、PDF、图片版 PPT/PPTX。输出始终是 `.pptx`。目标不是把整页截图包进 PPT，而是通过 `editppt` runtime 和页面级 prompt，把页面拆解、复原、验证并最终组装成可编辑 `.pptx`。

## References

```text
skills/image-to-editable-ppt/
├── SKILL.md
├── prompts/
│   └── page-worker.md
└── references/
    ├── cli-helper.md
    ├── manifest-schema.md
    ├── page-decision-tree.md
    └── qa-rubric.md
```

- `prompts/page-worker.md`：page worker 的执行模板。主 agent 生成页面 worker prompt 时使用。
- `references/cli-helper.md`：CLI 命令手册、命令目录树和常用命令示例。需要决定该调用哪个 `editppt` 命令时读取。
- `references/manifest-schema.md`：deck/page/image job JSON schema 和 artifact contract。写 manifest、page_result 或理解 run/page 文件时读取。
- `references/page-decision-tree.md`：页面对象决策的唯一标准。开始重建任何页面前读取。
- `references/qa-rubric.md`：结构、文字、资产、背景、视觉 QA 标准。页面返回前和最终交付前读取。

## Entry Contract

- 先运行 `editppt prepare <input...>` 创建 run dir；后续关键状态只能由 `editppt` 命令推进。
- 单页输入由主 agent 直接完成该页。
- 多页输入由主 agent 运行 `editppt run next`，按并发槽位直接分配 page worker/subagent 处理页面。
- 所有图片生成、编辑、背景修复、透明 bitmap 资产和 asset sheet 统一调用 `editppt image generate/edit/batch`。
- 页面级重建策略全部按 References 执行。
- page worker 使用 `prompts/page-worker.md`。
- 原始整页 `source.png` 加可编辑文本覆盖不是可接受 fallback。最终必须给出当前可打开、结构有效的 `.pptx`。

## Roles

主 agent 负责 orchestration 和用户交互：

- 运行 `editppt prepare`。
- 正常路径不需要额外运行 backend 配置；`editppt image` 会自动选择 Codex OAuth 或 API fallback。
- 单页输入时直接重建该页，并用 `editppt run record --agent-id main` 记录结果。
- 多页输入时使用 `editppt run next` 获取待分派页面。
- 为待处理页面生成 prompt、spawn page worker，并用 `editppt run dispatch` 记录 dispatch。
- 用 `editppt run record` 记录 page worker 返回结果。
- 用 `editppt run finalize` 组装和验证最终 PPTX。
- 向用户报告进度、最终路径和验证结果。

主 agent 不修改 page worker 的 page-local 输出，不重复做 page worker 已完成的页面视觉 QA，不手写关键状态 JSON。

page worker 负责一个 `pages/page_NNN/` 目录：

- 只读自己的 `page_request.json`、`source.png` 和相关 reference。
- 只写自己的 page dir。
- 使用 `page_request.json.image_backend`。
- 分析文字、结构、背景和前景视觉对象。
- 按页面决策树选择 native text、native shape、LaTeX-rendered formula asset、clean base、asset sheet 或 source-derived asset。
- 使用 `editppt image generate/edit/batch` 生成/编辑需要的 bitmap。
- 使用 `editppt formula render-latex` 渲染公式图片资产。
- 用 `editppt image import` / `editppt image process-sheet` / `editppt image crop` 记录和处理生成资产。
- 写 `manifest.json`、`page.pptx`、`preview.png`、`split_assets_contact.png`、`validation.json`、`page_result.json`。
- 作为页面复原者，自检 `preview.png`、`split_assets_contact.png` 和 `validation.json`；检查发现 page-local 问题时，在当前页内直接修正后再返回。

page worker 不得编辑 `deck_manifest.json`、`page_jobs.json`、`notes_manifest.json`、final PPTX、input 原件或其他 page 目录。

## Workflow

### Phase 1: Prepare

读取 `references/cli-helper.md` 的 prepare 示例和 `references/manifest-schema.md` 的 run/page 文件说明。

```bash
editppt prepare <input...>
```

完成后必须有 run dir、`deck_manifest.json`、`page_jobs.json`、`notes_manifest.json`、每页 `source.png` 和 `page_request.json`。正常流程不需要额外运行 `editppt run backend`。

### Phase 2: Dispatch Pages

单页输入由主 agent 在 `pages/page_001/` 完成页面输出，然后进入 Phase 3。

读取 `references/cli-helper.md` 的 run/dispatch 示例。生成 page worker prompt 前，确保 worker prompt 会要求读取 `prompts/page-worker.md`、`references/page-decision-tree.md`、`references/manifest-schema.md` 和 `references/qa-rubric.md`。

反复调用：

```bash
editppt run next <run>
```

如果返回 dispatch 阶段：

1. `editppt run prompt <run> --page <page_id> --out <run>/pages/<page_id>/worker-prompt.md`
2. spawn page worker
3. `editppt run dispatch <run> --page <page_id> --agent-id <id> --prompt-file <run>/pages/<page_id>/worker-prompt.md`

并发槽位由 `page_jobs.json.max_concurrent_pages` 控制，默认是 6。`editppt run status` 只用于 debug 或人工排查；正常主流程优先 `editppt run next`。

### Phase 3: Record

读取 `references/cli-helper.md` 的 record 示例和 `references/manifest-schema.md` 的 `page_result.json` 说明。

worker 返回后运行：

```bash
editppt run record <run> --page <page_id> --agent-id <id>
```

单页输入由主 agent 直接完成时使用：

```bash
editppt run record <run> --page page_001 --agent-id main
```

### Phase 4: Finalize

读取 `references/cli-helper.md` 的 finalize 示例和 `references/qa-rubric.md` 的 deck-level QA 要点。

当 `editppt run next <run>` 返回 finalize 阶段：

```bash
editppt run finalize <run>
```

最终回复必须报告 final PPTX 路径和验证结果。

## State Principles

Run/page 状态由 `editppt run` 命令推进。agent 只根据文件事实和 `editppt run next` 继续执行。

必要状态：

- `pending`：`editppt prepare` 创建。
- `dispatched`：`editppt run dispatch` 记录真实已 spawn worker。
- `recorded`：`editppt run record` 校验 required outputs 后写入；单页直接复原也通过该命令记录。
- `accepted` / `complete`：`editppt run finalize` 写入。

`imagegen-jobs.json` 是 page-local provenance/job record。强制文件态只保留：

- `recorded`：`editppt image import` 已复制选中输出并写入 hash、metadata。
- `processed`：`editppt image process-sheet` 或 `editppt image crop` 已完成去底、切分或裁剪。

## Delivery Principles

- 每页由复原者完成一次自检，检查依据写入 `manifest.json` 的结构化字段和 `validation.json`。
- 检查发现 page-local 问题时，当前页面作者直接修正。
- 最终必须给出当前可打开、结构有效的 `.pptx`。
- 原始整页 `source.png` 加可编辑文本覆盖不是可接受 fallback。
- 图标、图片资产、字体、位置、形状等轻微差异可以作为 warning 随 PPT 交付。

## Update Skill

更新本 skill 时，使用安装渠道重新拉取同一个 skill：

```bash
npx -y skills@latest add ningzimu/image-to-editable-ppt-skill \
  --skill image-to-editable-ppt \
  --agent <agent-id> \
  --global
```

把 `<agent-id>` 替换为目标 agent id；例如 Codex 使用 `codex`。

CLI 位于本 skill 的 `cli/` 目录，并且是必需运行面。更新 skill 后，必须用更新后的 skill 目录刷新全局 CLI：

```bash
pipx install --force --editable <skill-root>/cli
```

更新后重启对应 agent 会话，再运行：

```bash
editppt --help
editppt doctor
```
