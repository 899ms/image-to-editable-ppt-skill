# CLI Helper

这是 `editppt` 命令操作手册，用于减少手写脚本、手写状态 JSON 和反复试错的次数。

使用原则：

- 能用 `editppt` 完成的确定性动作，直接调用 CLI，不要改写为临时 Python 脚本。
- 需要完整参数时，先读 `editppt <command> --help` 或 `editppt image <command> --help`。

## 命令目录树

```text
editppt
├── setup
├── doctor
├── config
├── prepare
├── run
│   ├── next
│   ├── status
│   ├── backend
│   ├── prompt
│   ├── dispatch
│   ├── record
│   └── finalize
├── image
│   ├── generate
│   ├── edit
│   ├── batch
│   ├── import
│   ├── process-sheet
│   └── crop
└── formula
    └── render-latex
```

## 常用帮助入口

```bash
editppt --help
editppt run --help
editppt image --help
editppt image edit --help
editppt image batch --help
editppt formula render-latex --help
```

`editppt image` 会自动选择图片后端：优先 Codex OAuth，缺失时使用 `~/.editppt/config.yaml` 或环境变量中的 OpenAI-compatible API 配置。

## 运行前检查

`editppt` CLI 是本 skill 的必需运行面。先确认 CLI 是否可用：

```bash
editppt --help
```

如果 shell 返回 command not found，或刚更新过 skill，从 skill-local CLI 做 editable 安装：

```bash
pipx install --editable <skill-root>/cli
```

`<skill-root>` 是包含 `SKILL.md` 的 `image-to-editable-ppt` 目录。Windows 下同样使用该目录的 `cli` 子目录路径。

CLI 可用后再做本地运行态检查：

```bash
editppt setup
editppt doctor
editppt config --api-key "<key>" --base-url "<openai-compatible-base-url>" --model "<image-model>"
```

只有在需要 API fallback，或用户明确提供第三方图片 API 时，才写入 `editppt config`。不要把 API key 写入项目目录、run 目录、prompt 或 manifest。

## 单页输入常用命令

```bash
editppt prepare input.png
```

作用：把单张图片规范化成 run 目录，生成 `deck_manifest.json`、`page_jobs.json`、`notes_manifest.json`、`pages/page_001/source.png` 和 `pages/page_001/page_request.json`。

```bash
editppt run record <run> --page page_001 --agent-id main
```

作用：单页由主 agent 直接完成当前页、自检并写齐 page-local 输出后，记录该页结果。

```bash
editppt run finalize <run>
```

作用：记录完成后，组装并验证最终 PPTX。

## 多页输入常用命令

```bash
editppt prepare input.pdf
```

作用：把 PDF、PPTX 或多张图片规范化成多页 run 目录，并为每页生成 `pages/page_NNN/source.png` 和 `page_request.json`。

```bash
editppt run next <run> --json
```

作用：读取当前 run 状态，返回下一步阶段。`stage=rebuild_page` 时主 agent 直接完成单页；`stage=dispatch_pages` 时读取 `suggested_pages`；`stage=wait` 时等待已分派页面完成；`stage=finalize` 时进入最终组装。

```bash
editppt run prompt <run> --page page_001 --out <run>/pages/page_001/worker-prompt.md
```

作用：为指定页面生成 page worker prompt。prompt 会指向该页的 `page_request.json`、`source.png` 和必须读取的 references。

```bash
editppt run dispatch <run> --page page_001 --agent-id <worker-id> --prompt-file <run>/pages/page_001/worker-prompt.md
```

作用：记录页面已经分派给某个 worker。该命令只记录真实已发生的分派。

```bash
editppt run record <run> --page page_001 --agent-id <worker-id>
```

作用：在页面 worker 写齐 `manifest.json`、`page.pptx`、`preview.png`、`split_assets_contact.png`、`validation.json`、`page_result.json` 后，校验并记录该页结果。

```bash
editppt run finalize <run>
```

作用：所有页面已 record 后，组装、验证并输出最终 PPTX。

并发槽位来自 `page_jobs.json.max_concurrent_pages`，默认是 6。正常流程优先用 `editppt run next` 决定下一步；`editppt run status` 只用于 debug 或人工排查。

## 图片后端命令

生成新图：

```bash
editppt image generate \
  --prompt-file prompt.txt \
  --out pages/page_001/assets/support.png
```

基于原图做 clean base 或前景素材板：

```bash
editppt image edit \
  --image pages/page_001/source.png \
  --prompt-file clean-base.prompt.txt \
  --out pages/page_001/assets/clean-base.png

editppt image edit \
  --image pages/page_001/source.png \
  --prompt-file asset-sheet.prompt.txt \
  --out pages/page_001/assets/asset-sheet.png
```

批量生成或编辑：

```bash
editppt image batch \
  --input pages/page_001/image-jobs.jsonl \
  --out-dir pages/page_001/assets \
  --concurrency 6
```

JSONL job 没有 `image` / `images` 字段时是 generate；带 `image` / `images` 字段时是 edit。

## 资产处理命令

记录已选择的图片输出：

```bash
editppt image import pages/page_001 \
  --job-id icon-sheet \
  --source-image /tmp/generated.png \
  --dest assets/icon-sheet.png \
  --role asset_sheet
```

处理 chroma-key 素材板：

```bash
editppt image process-sheet pages/page_001 \
  --job-id icon-sheet \
  --asset-sheet-source assets/icon-sheet.png \
  --assets-dir assets/icons
```

裁剪允许 source-derived 的规则大块内容：

```bash
editppt image crop pages/page_001 \
  --source source.png \
  --box 100,120,460,320 \
  --out assets/chart-block.png
```

## 公式命令

```bash
editppt formula render-latex pages/page_001 \
  --tex "\\sum_{i \\in N} p_{ij}x_{ij} \\ge a_j u_j" \
  --out assets/formula_001.svg \
  --box 100,120,360,80 \
  --id formula_001 \
  --fragment assets/formula_001.fragment.json
```

公式由 agent 从 source 转写为 LaTeX，CLI 只负责渲染成图片资产和 manifest fragment。
