# Toolbar Standardization Handoff

## Goal

Standardize the project's editor-related tool components, with the main focus on the `md` area and `latex` area used on the check/review screen.

The target spec to align against is:

- `md` area, horizontally scrollable by mouse wheel:
  - Bold, and if the selected text is already bold then unbold it
  - Heading level dropdown
  - New table
  - List
  - Quote
- `latex` area, horizontally scrollable by mouse wheel:
  - Insert formula
  - Fraction
  - Superscript
  - Subscript
  - Square root
  - n-th root
  - Log
  - Natural log
  - Equation system
  - Dropdown list for special symbols, etc.
- Extra rule:
  - After using "insert formula", if later inserted text is not inside `$$...$$`, auto-wrap it with `$$`.

## Current Component Inventory

### 1. Main toolbar implementation already exists

- `frontend/src/components/EditorToolbar.tsx`
- Current role:
  - Splits the toolbar into `MD` and `LaTeX` regions
  - Supports horizontal wheel-to-scroll behavior
  - Provides most of the requested buttons and dropdowns

Relevant details:

- MD region buttons are already present:
  - bold toggle
  - heading dropdown
  - table
  - list
  - quote
- LaTeX region buttons are already present:
  - insert formula
  - fraction
  - superscript
  - subscript
  - square root
  - n-th root
  - log
  - natural log
  - equation system
  - special-symbol dropdown

### 2. Editing behavior is extracted into pure functions

- `frontend/src/lib/editorOps.ts`
- Current role:
  - Pure text operations for toolbar actions
  - Includes:
    - `surround`
    - `insertLatex`
    - `toggleBold`
    - `lineStartPrefix`
    - `setHeading`
    - `insertTable`
    - `isInsideMath`

This is the best existing foundation for standardization.

### 3. Toolbar is currently only mounted in the check screen

- `frontend/src/screens/CheckScreen.tsx`
- Current role:
  - Manages render mode
  - Shows `EditorToolbar`
  - Shows textarea + preview
  - Saves drafts and submits final content

Important coupling:

- `EditorToolbar` currently depends on:
  - `textareaRef`
  - `content`
  - `setContent`
- This makes it reusable only for textarea-based screens with the same contract.

### 4. Styling is check-screen specific, not generic

- `frontend/src/styles.css`
- Current role:
  - toolbar classes are `check-*`
  - e.g. `.check-toolbars`, `.check-tool-region`, `.check-tool-scroll`, `.check-tool-select`

This works, but is not yet a normalized "shared editor toolbar system".

### 5. There are other tool-like components in the project

These are relevant to the broader "tool component standardization" task:

- `frontend/src/screens/SelectScreen.tsx`
  - rectangle/lasso selection toolbar
  - OCR model selector
- `frontend/src/components/Whiteboard.tsx`
  - Excalidraw board container
  - fullscreen control
  - Excalidraw itself brings its own drawing toolbar
- `frontend/src/components/PracticeControls.tsx`
  - logic category selector
  - difficulty selector
  - generate button
- `frontend/src/components/ChatBox.tsx`
  - shared chat input
  - special-symbol insertion palette

For this task, `ChatBox.tsx` matters the most because it already owns another special-symbol source, which overlaps conceptually with the LaTeX toolbar.

## Gap Analysis Against the Target Spec

## A. Already matches or is very close

### 1. MD and LaTeX regions are already separated

Already implemented in:

- `frontend/src/components/EditorToolbar.tsx`

### 2. Horizontal wheel scrolling is already implemented

Already implemented via `ScrollStrip`:

- vertical wheel is translated into horizontal scroll
- `preventDefault()` is only used when overflow exists

### 3. Requested MD actions already exist

Implemented:

- Bold toggle
- Heading dropdown
- Table insertion
- List
- Quote

### 4. Requested LaTeX actions already exist

Implemented:

- Insert formula
- Fraction
- Superscript
- Subscript
- Square root
- n-th root
- Log
- Natural log
- Equation system
- Special-symbol dropdown

### 5. Preview pipeline already exists

Implemented in:

- `frontend/src/lib/markdown.ts`
- `frontend/src/screens/CheckScreen.tsx`

So the project already has a live loop of:

- edit source
- apply toolbar operation
- preview markdown + math

## B. Partial gaps

### 1. "Insert formula" is not stateful enough for the requested rule

Current behavior:

- Clicking "insert formula" inserts `$$...$$` around the current selection or caret.
- Other LaTeX toolbar actions use `insertLatex`, which auto-wraps with `$$` if the caret is not already inside a `$$...$$` region.

What is missing:

- The requested rule says:
  - after pressing "insert formula", later inserted text should be detected and auto-wrapped if it is not inside `$$...$$`
- The current implementation does not establish a persistent "formula insertion mode"
- It only auto-wraps content inserted through toolbar commands
- It does not monitor arbitrary subsequent keyboard input

This is the single most important functional gap.

### 2. Math-context detection only understands `$$...$$`

Current behavior in `isInsideMath`:

- counts only `$$` delimiters before the caret

What is missing:

- It does not detect:
  - `$...$`
  - `\(...\)`
  - `\[...\]`
- But the preview renderer already supports these forms in `frontend/src/lib/markdown.ts`

Result:

- if the content already uses a non-`$$` math delimiter, toolbar insertion can incorrectly double-wrap or insert in the wrong mode

### 3. List/quote operations are line-local, not block-aware

Current behavior:

- `lineStartPrefix` inserts a prefix at the current line start

What is missing:

- multi-line selection behavior is not standardized
- no toggle behavior for list/quote
- only the first/current line is handled explicitly

If the desired UX is closer to standard editors, this should be improved.

### 4. The toolbar is screen-specific, not a generic standardized component

Current behavior:

- `EditorToolbar` is tightly named and styled for `CheckScreen`
- its API is textarea-specific and state-specific

What is missing:

- shared command model
- shared symbol source
- shared toolbar primitives
- reusable class naming and section naming

### 5. Special-symbol data is duplicated across components

Current behavior:

- `EditorToolbar.tsx` owns `LATEX_SYMBOLS`
- `ChatBox.tsx` owns `SPECIAL_SYMBOLS`

What is missing:

- one normalized symbol definition layer
- one place to decide:
  - display label
  - inserted text
  - plain symbol vs LaTeX command
  - where each symbol is allowed

This is a structural gap and a likely future regression source.

### 6. Toolbar visibility is tied to render modes 1 and 2

Current behavior:

- `CheckScreen` only shows the toolbar when render mode is `1` or `2`

This may be acceptable, but if the standard says the editor toolbar is part of the editor itself, then the toolbar should be decoupled from preview mode and controlled by a clearer product rule.

## C. Quality gaps

### 1. No checked-in frontend tests were found for toolbar behavior

Observations:

- `CHANGELOG.md` mentions `editorOps` tests
- but no frontend `test/spec` file was found in the repo

This means the current logic is likely validated mainly by manual behavior and build success.

### 2. No unified acceptance checklist around editor behavior

Important behaviors that should be explicitly testable:

- bold toggle on already-bold selections
- formula insertion with empty selection
- formula insertion with selected text
- LaTeX button insertion when caret is:
  - inside `$$...$$`
  - inside `$...$`
  - inside `\(...\)`
  - outside any math span
- multi-line list/quote behavior
- heading replacement when a heading already exists

## Recommended Scope for the Implementation AI

Do this as a focused refactor plus behavior completion, not as a redesign of the whole app.

### In scope

- Standardize the editor toolbar and related pure ops
- Keep `CheckScreen` working
- Unify symbol definitions where practical
- Add real test coverage for editor ops
- Preserve current visual behavior unless needed for consistency

### Out of scope

- Rebuilding Excalidraw toolbar
- Redesigning practice controls
- Reworking the entire screen flow
- Changing backend contracts

## Suggested Implementation Plan

### Phase 1. Baseline and protect current behavior

1. Read these files first:
   - `frontend/src/components/EditorToolbar.tsx`
   - `frontend/src/lib/editorOps.ts`
   - `frontend/src/lib/markdown.ts`
   - `frontend/src/screens/CheckScreen.tsx`
   - `frontend/src/components/ChatBox.tsx`
   - `frontend/src/styles.css`
2. Do not change unrelated screens first.
3. Keep `CheckScreen` behavior working throughout the refactor.

### Phase 2. Extract a reusable editor-tooling layer

Create a shared folder, for example:

- `frontend/src/editor/`

Suggested split:

- `commands.ts`
  - command definitions for md and latex sections
- `symbols.ts`
  - unified special symbol definitions
- `ops.ts`
  - move or re-export editor ops from `lib/editorOps.ts`
- `mathContext.ts`
  - math-span detection helpers
- `EditorToolbar.tsx`
  - generic toolbar component

Goal:

- separate data, UI, and text-editing logic

### Phase 3. Complete the "insert formula" rule properly

Implement one of these two approaches and document the chosen rule clearly.

Preferred approach:

1. Keep the existing explicit toolbar insertion behavior.
2. Add a lightweight "formula mode" or insertion guard for the check editor:
   - after clicking "insert formula", place caret inside `$$...$$`
   - while the caret remains in that inserted range, typed content naturally stays inside math
   - for later toolbar-triggered insertions, if not inside any supported math span, auto-wrap
3. Expand math-context detection to support:
   - `$$...$$`
   - `$...$`
   - `\(...\)`
   - `\[...\]`

Minimum acceptable fallback:

- if persistent formula mode is too invasive, at least make auto-wrap logic correct across all supported delimiter types and document that the auto-wrap rule applies to toolbar insertions, not arbitrary keyboard typing

### Phase 4. Improve block editing behavior

Upgrade MD actions so they behave predictably on multi-line selections.

Suggested rules:

- bold:
  - keep current toggle semantics
- heading:
  - operate on current line only
  - replace an existing heading marker cleanly
- list:
  - if selection spans multiple lines, prefix each selected line
- quote:
  - if selection spans multiple lines, prefix each selected line
- table:
  - keep the simple skeleton unless product requires row/column picking

### Phase 5. Normalize symbols

Unify `LATEX_SYMBOLS` and `SPECIAL_SYMBOLS` into one source of truth.

Possible structure:

```ts
type EditorSymbol = {
  id: string;
  label: string;
  insertText: string;
  kind: 'plain' | 'latex';
  surfaces: Array<'toolbar-dropdown' | 'chat-palette'>;
};
```

Important:

- the chat palette inserts display symbols
- the LaTeX dropdown often inserts LaTeX commands
- these are related but not always identical
- normalization should support both instead of forcing them into one exact rendering

### Phase 6. Decouple naming and styling from `CheckScreen`

Refactor class names from `check-*` where it improves reuse.

Example direction:

- `.editor-toolbars`
- `.editor-tool-region`
- `.editor-tool-scroll`
- `.editor-tool-select`

Keep the current visual layout unless there is a usability reason to change it.

### Phase 7. Add real tests

Add tests for the pure ops layer.

At minimum cover:

- `toggleBold`
- `setHeading`
- `insertTable`
- `lineStartPrefix`
- `isInsideMath`
- `insertLatex`

Critical cases:

- empty selection
- selected text
- already-bold text
- inside `$$`
- inside `$`
- inside `\(` `\)`
- inside `\[` `\]`
- outside math
- multi-line content

If the repo still has no test runner for frontend logic, add a minimal one only for these pure utilities.

## Acceptance Criteria

The implementation is done when all of the following are true:

1. `CheckScreen` still builds and works.
2. The toolbar still has two horizontally wheel-scrollable regions:
   - MD
   - LaTeX
3. The MD area supports:
   - bold toggle
   - heading dropdown
   - new table
   - list
   - quote
4. The LaTeX area supports:
   - insert formula
   - fraction
   - superscript
   - subscript
   - square root
   - n-th root
   - log
   - natural log
   - equation system
   - special-symbol dropdown
5. Auto-wrap logic does not incorrectly double-wrap when the caret is already inside supported math delimiters.
6. Special symbol definitions are no longer duplicated without intent.
7. Toolbar logic has real checked-in tests.
8. `npm run typecheck` passes.
9. `npm run build` passes.

## Files Most Likely to Change

- `frontend/src/components/EditorToolbar.tsx`
- `frontend/src/lib/editorOps.ts`
- `frontend/src/screens/CheckScreen.tsx`
- `frontend/src/components/ChatBox.tsx`
- `frontend/src/styles.css`

Possible new files:

- `frontend/src/editor/commands.ts`
- `frontend/src/editor/symbols.ts`
- `frontend/src/editor/mathContext.ts`
- `frontend/src/editor/ops.ts`
- tests for the editor ops layer

## Practical Notes for the Implementation AI

- The git worktree is already dirty. Do not revert unrelated user changes.
- Prefer incremental refactor over broad rewrites.
- Keep `CheckScreen` as the first and only integration surface until the shared layer is stable.
- Preserve current OCR -> check -> assistant/verify flow.
- Reuse existing `renderMarkdownMath` and preview plumbing.
- Reuse `textareaRef` behavior unless there is a clear reason to introduce a more generic editor adapter.

## Recommended Verification Commands

From `frontend/`:

```powershell
npm run typecheck
npm run build
```

If frontend tests are added:

```powershell
npm test
```

## Ready-to-Paste Prompt for Another AI

Use this as the task prompt:

```text
请在当前项目里完成“工具组件规范化”，重点是校对屏的 md / latex 工具栏。

先阅读这些文件：
- frontend/src/components/EditorToolbar.tsx
- frontend/src/lib/editorOps.ts
- frontend/src/lib/markdown.ts
- frontend/src/screens/CheckScreen.tsx
- frontend/src/components/ChatBox.tsx
- frontend/src/styles.css
- docs/TOOLBAR_STANDARDIZATION_HANDOFF.md

目标：
1. 保留现有 CheckScreen 可用性，不破坏 OCR -> 校对 -> 助手/判分 流程。
2. 将 md / latex 工具栏整理成更规范、可复用的实现，而不是只服务于 CheckScreen 的特化代码。
3. 对齐以下规范：
   - md 区域：加粗（已加粗则取消）、标题下拉、新建表格、列举、引用
   - latex 区域：插入公式、分式、右上角标、右下角标、平方根、n 次方根、对数、自然对数、方程组、特殊符号下拉
   - 两个区域都要支持鼠标滚轮左右滚动
4. 修正“插入公式 / 自动补 $$”逻辑：
   - 至少要正确识别当前插入点是否已经在数学公式区域内
   - 不要只支持 `$$...$$`，还要考虑 `$...$`、`\\(...\\)`、`\\[...\\]`
   - 如果你认为“点击插入公式后对任意后续键盘输入都做自动包裹”会过于侵入，请保留现有交互风格，但把规则、限制和原因写清楚，并确保工具栏触发的插入行为正确
5. 清理重复定义的特殊符号数据，尽量统一 `EditorToolbar` 和 `ChatBox` 的符号来源
6. 为纯文本编辑操作补上真实测试，至少覆盖：
   - toggleBold
   - setHeading
   - insertTable
   - lineStartPrefix
   - isInsideMath
   - insertLatex
7. 最终运行：
   - npm run typecheck
   - npm run build

注意：
- 不要回滚用户已有改动
- 尽量做增量重构，不要大面积推倒重来
- 如果你新增了结构层，请优先放到 frontend/src/editor/ 下
```
