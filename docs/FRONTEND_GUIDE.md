# 前端开发指南 / Frontend Guide

> 本文件是 **math-tutor 前端的权威参考**：讲清每个模块干什么、构建前端遵循的标准、以及
> 常见修改怎么下手、去哪找。给后来者用——先读这份，再动代码。
>
> 技术栈：**Vite + React 18 + TypeScript**（函数组件 + Hooks，无重型状态库）。
> 后端是 **FastAPI**（判分共识 / 诊断 / 自进化标签 / 记忆），是「正确性内核」，前端只调用它、
> **不改它**。根 README 的「Layout / Status」章节已过时，以本文件为准。

---

## 1. 整体架构（先建立心智模型）

- **五屏引导流**：① 出题 `problem` → ② 选区 `select` → ③ 校对 `check` → ④ 逐行助手 `assistant`
  → ⑤ 答疑 `ask`。同一时刻只显示一个屏（`.screen` / `.screen.active`）。
- **配置驱动，不写死**（项目铁律）：屏、题目来源、动作按钮、难度阶梯都是 `config.ts` 里的**数据表**，
  不是散落在 JSX 里的魔法值。改流程/加来源/加按钮 → 改 `config.ts`，别在组件里硬编码。
- **单一 store**：`store.tsx` 是一个 React Context，管**路由（含返回栈）+ 白板引擎 + 当前题目 + 屏间交接
  数据**。它刻意小巧（useState/useRef），不用 Redux/zustand。
- **一层 API 客户端**：所有后端调用只在 `api.ts`。组件不直接 `fetch`。
- **数学渲染**靠 MathJax（`index.html` 的 CDN 脚本），经 `useMathJax` / `MathText` / `lib/markdown` 使用。
- **白板**是 Excalidraw（`board/ExcalidrawBoard.ts` 封装），实例挂在 store 上、**跨屏存活**。
- **动画**：`<manim>` 块 → `ManimView` → `POST /manim/render` → 真 MP4，装不了则回退浏览器故事板。
- **主题**：深/浅色 + 可选主题色，CSS 变量驱动（见 §5），持久化到 localStorage。

数据流一图流：
```
用户操作 → 屏组件(screens/*) → api.ts(fetch) → FastAPI
              （屏间交接数据经 store.tsx 往返）
  白板(board/*)、数学(hooks/lib)、聊天(ChatBox)、动画(ManimView) 为可复用能力
```

---

## 2. 目录地图（每个文件干什么 / 何时改它）

### 顶层
| 文件 | 职责 | 什么时候动它 |
|---|---|---|
| `main.tsx` | 入口，挂 `<StoreProvider><App/></StoreProvider>`。**故意不套 `<React.StrictMode>`**（白板是命令式 canvas + rAF，StrictMode 双挂会挂两次）。 | 几乎不动。 |
| `App.tsx` | 全局页头（`<ThemeControls/>` + 渐变标题 + 副标题）+ 五个屏容器。 | 加全局 UI（如页头控件）时。 |
| `index.html` | HTML 壳：字体、MathJax 配置、Excalidraw 资源路径、**首绘前套用主题的内联脚本**（防闪烁）。 | 改 MathJax 配置 / 主题初始化时。 |
| `styles.css` | **全站唯一样式表**（§5）。CSS 变量主题系统 + 所有组件类。 | 所有视觉改动。 |
| `config.ts` | 配置驱动的数据表：`API_BASE`、`SCREEN_DEFS`、`SOURCES`、`PROBLEM_ACTIONS`、`DIFFICULTY_LADDER`。 | 加屏/来源/按钮/难度档。 |
| `types.ts` | 全站共享类型：`Problem`、`ProblemTag`、`RenderMode`、`AssistLine`、`Op/Tool/BoardMode` 等。 | 新增后端返回结构 / 领域类型时。 |
| `api.ts` | **唯一** 的 FastAPI 客户端：每个端点一个 typed 函数 + 请求/响应接口。 | 加/改任何后端调用。 |
| `store.tsx` | 全局 store：`screen/navTo/navBack/navHome/startWorkFlow`、`board/captureBlob`、`problem`、`ocrText`、`studentWork`、`renderMode`、`sessionId`。 | 加跨屏共享状态 / 交接数据。 |

### `screens/`（每屏一个，只有 active 的那个渲染内容）
| 文件 | 屏 | 干什么 | 主要调用 |
|---|---|---|---|
| `ProblemScreen.tsx` | ① 出题 | 来源选择、标签开关、题卡（`ProblemCard`）、定向练习（`PracticeControls`）、白板、底部动作行 | `/practice/next`、`/tags` |
| `SelectScreen.tsx` | ② 选区 | 在白板快照上框选/套索要 OCR 的区域 | `board/selection` + `/recognize` |
| `CheckScreen.tsx` | ③ 校对 | 编辑 OCR 结果（`EditorToolbar` + `lib/markdown` 预览），确认后提交 | `/work/save`、`/verify` |
| `AssistantScreen.tsx` | ④ 助手 | 逐行分析（左解法 / 右批注），点某行展开 `ChatBox` 追问；行可带 `<manim>` | `/assistant/analyze`、`/assistant/ask` |
| `AskScreen.tsx` | ⑤ 答疑 | 就本题自由问答（`ChatBox`） | `/claude/chat` |

### `components/`（可复用 UI）
| 文件 | 职责 |
|---|---|
| `ScreenHeader.tsx` | ②–⑤ 的返回按钮 + 渐变标题 + 副标题。 |
| `ProblemCard.tsx` | 题卡：主题/难度/标签芯片 + 题面（`ProblemBody`）。 |
| `ProblemBody.tsx` | 把 Chinese `statement` 里**无分隔符的 LaTeX**就地 typeset 成一段流式文本（关键渲染逻辑）。 |
| `MathText.tsx` | 把一段 LaTeX 当 display math `\[...\]` 渲染，变化即重排。 |
| `PracticeControls.tsx` | 定向练习：从**实时标签库**选思维类型 + 开放式难度 → 生成一题。 |
| `Whiteboard.tsx` | 挂载 Excalidraw 画布容器（引擎实例来自 store，跨屏存活）。 |
| `ChatBox.tsx` | **公共聊天控件**（助手/答疑共用）：消息渲染（3 种渲染模式）、换行键选择、允许识别多选、`<manim>` 块识别（`manimProps`）。 |
| `EditorToolbar.tsx` | 校对屏的 Markdown + LaTeX 编辑工具条（配 `lib/editorOps`）。 |
| `ManimView.tsx` | `<manim>` 块 → 动画：调 `/manim/render`，出 MP4 或回退故事板；含清晰度下拉、`looksLikeManimCode`/`manimProps`（判定块内是自然语言还是现成 Manim 代码）。 |
| `ThemeControls.tsx` | 全局主题选择器（深/浅切换 + 5 预设主题色 + 自定义色）；写 localStorage 并即时套用到 `<html>`。 |

### `lib/`（纯逻辑，框架无关、可单测）
| 文件 | 职责 |
|---|---|
| `markdown.ts` | Markdown + LaTeX 渲染。**关键坑**：marked 会吃掉 `\(...\)` 的反斜杠——先用占位符保护数学段，marked 之后再还原交给 MathJax。`renderMarkdownMath`（全渲染）/`renderSource`（源码风）/`escapeHtml`。 |
| `editorOps.ts` | 校对屏工具条的纯文本编辑操作（加粗切换、自动 `$$` 包裹、标题、列表、表格…），返回新值 + 新光标区间。 |
| `theme.ts` | 主题运行时：模式/主题色的 load/apply/save + `lighten()`（从单个自定义色推第二个渐变端点）。§5。 |

### `hooks/`
| 文件 | 职责 |
|---|---|
| `useMathJax.ts` | `dep` 变化后对某 ref 子树跑 MathJax typeset；MathJax 可能还没加载 → 守卫 + 吞异常。 |

### `board/`（白板）
| 文件 | 职责 |
|---|---|
| `ExcalidrawBoard.ts` | **当前唯一**绘图引擎的封装：无限画布、快照 `snapshot()`、导出 `captureBlob()`。 |
| `BoardEngine.ts` | 旧的原生 canvas 引擎（已退役，保留作参考）。 |
| `selection.ts` | 选区几何 + 区域导出：从**已渲染的画布**直接拷像素（矩形 `exportRect` / 套索 `exportLasso`），忠实还原墨迹与擦除。 |

---

## 3. 构建前端的标准（改代码前必读）

1. **配置驱动，不写死**。屏、来源、动作、难度——进 `config.ts` 的数据表。宁可加一行配置，不在 JSX 里塞 if。
2. **后端调用只进 `api.ts`**。新端点：加 `XxxReq`/`XxxResp` 接口 + 一个 `async function`，组件调它，不裸 `fetch`。
3. **类型集中在 `types.ts`**（领域/后端结构）；组件私有的小类型可就地定义。
4. **跨屏共享/交接的数据走 store**（如 OCR 文本 select→check、批改稿 check→assistant）。屏内临时状态用局部 `useState`。
5. **样式只写在 `styles.css`，且优先用设计 token**（§5）。不要新增夸张圆角/浮起阴影的「卡片」——现在是**扁平面板**风格。
6. **数学一律走 MathJax 封装**（`useMathJax`/`MathText`/`lib/markdown`），别自己拼 typeset；注意 marked 吃反斜杠的坑。
7. **颜色用语义变量**（`var(--text-main)`/`var(--glass-bg)`/`var(--accent-blue)`…），少写死 hex；玻璃填充用 `rgba(var(--surface-rgb), α)` 以便深/浅一处翻面。
8. **纯逻辑放 `lib/` 并单测**（editorOps、markdown、theme.lighten 都有此传统）。
9. **中文优先**的用户可见文案；代码注释讲**为什么**（本仓库注释密度较高，延续它）。
10. **验收靠「运行—观测」**：`tsc --noEmit` 0 错 + `vite build` 成功 + 必要时 headless Chrome 截图（深/浅两态）。

---

## 4. 常见任务怎么做（配食谱）

- **加一个屏**：`types.ts` 的 `ScreenName` 加值 → `config.ts` 的 `SCREEN_DEFS` 加条目 → 写 `screens/XxxScreen.tsx`
  → `App.tsx` 里加 `<XxxScreen active={screen==='xxx'} />` → 用 `navTo('xxx')` 进入。
- **加一个后端调用**：`api.ts` 加接口 + 函数；返回结构进 `types.ts`；屏组件里 `await xxx()`。
- **加一个题目来源 / 动作按钮**：改 `config.ts` 的 `SOURCES` / `PROBLEM_ACTIONS`，无需碰组件。
- **加一个预设主题色**：`lib/theme.ts` 的 `ACCENTS` 数组加一项 `{name, c1, c2}`。
- **整体调圆角/边框/阴影**：只改 `styles.css` `:root` 里的 `--radius-*` / `--glass-border` / `--card-shadow` 一处，全站生效（§5）。
- **改深/浅色某个语义色**：改 `[data-theme="dark"]` / `[data-theme="light"]` 块里的变量；浅色可读性微调在其后的
  `[data-theme="light"] .xxx { color: … }` 覆盖块里加（不动深色）。
- **让 AI 回复里的 `<manim>` 直接渲染现成代码**：后端 prompt 让模型在 `<manim>` 里给 `from manim import *` + 一个
  `class …(Scene)`；前端 `manimProps()` 自动识别为代码走 `manim_code`（否则当自然语言 `spec`）。

---

## 5. 样式与主题系统（重点，最近重构）

**唯一样式表 `styles.css`**，顶部是主题系统，其后是各组件类。设计语言：**扁平、去卡片、边缘淡化、圆角克制**。

### 5.1 主题机制
- 深/浅由 `<html data-theme="dark|light">` 切换；`index.html` 内联脚本在**首绘前**读 localStorage 套用（防闪烁）。
- 大多数 UI 只读下面这批**语义变量**，所以按主题重定义它们即可**整站翻面**：
  `--bg-deep`、`--bg-gradient-from`、`--surface`、`--surface-rgb`、`--glass-bg`、`--glass-border`、
  `--text-main`、`--text-dim`、`--accent-blue`、`--accent-purple`。
- **玻璃填充统一写 `rgba(var(--surface-rgb), α)`**：深色 `--surface-rgb: 255,255,255`（白玻璃），浅色 `15,23,42`
  （深玻璃）。**一处换通道即重着色所有卡片**，各调用点自留 alpha。

### 5.2 主题色（用户可选）
- 用户选的主题色 = 一对渐变端点，写进内联 `--accent-blue` / `--accent-purple`（`ThemeControls` + `lib/theme`）。
- 预设见 `ACCENTS`；自定义色用 `lighten()` 推第二端点。渐变标题/按钮/焦点环都读这两个变量，故换色全站跟随。

### 5.3 形状 token（`:root`，与主题无关）
| token | 值 | 用途 |
|---|---|---|
| `--radius-lg` | `10px` | 大容器/面板（原 16–24px，已去夸张） |
| `--radius-md` | `8px` | 中等块、输入框 |
| `--radius-sm` | `6px` | 小控件 |
| `--radius-pill` | `999px` | 芯片/胶囊（**故意**保持圆） |
| `--card-shadow` | `none` | 面板扁平化（原 `0 25px 50px …` 浮起阴影已去除） |

> 想统一调整全站的圆润度/立体感？**只改这几个 token**。焦点环 `0 0 0 2px accent`、内阴影、按钮 hover 抬升是
> 功能性阴影，**不走** `--card-shadow`，保留。

### 5.4 去卡片化约定（延续本次风格）
- 新面板：`background: var(--glass-bg); border: 1px solid var(--glass-border); border-radius: var(--radius-lg);
  box-shadow: var(--card-shadow);`——即：**很淡的底 + 很淡的边 + 无浮起阴影 + 克制圆角**。
- 深色代码块/动画播放器面板**两主题都保持深底**（像视频播放器），是刻意例外。
- 浅色下 pastel 芯片文字在 `[data-theme="light"] .xxx` 覆盖块里改深，保证可读；**深色像素不受影响**。

---

## 6. 运行 / 构建 / 验收

```bash
# 后端（仓库根，注意用 py -3.12）
cd backend && py -3.12 -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# 前端（frontend/）
npm install
npm run dev        # Vite dev http://localhost:5173
npm run build      # → dist/
npm run preview    # 本地起 dist
npm run typecheck  # tsc --noEmit（提交前必过）
```

- `API_BASE` 默认 `http://localhost:8000`，用 `frontend/.env.local` 的 `VITE_API_BASE` 覆盖（后端 CORS 全开）。
- 视觉改动建议 headless 截图核对深/浅两态（本仓库的验收惯例）。

---

## 7. 坑位速查

- **MathJax 未就绪**：`useMathJax` 已守卫吞异常；typeset 依赖列表要包含会变的 LaTeX 依赖。
- **marked 吃反斜杠**：数学段必须经 `lib/markdown` 的占位符保护，别直接把 `\(...\)` 丢给 marked。
- **白板跨屏存活**：Excalidraw 实例在 store 上，屏切换只挂/卸 DOM，不要重建引擎。
- **`<manim>` 中文**：中文只能进 `Text()`，`MathTex/Tex` 只放 ASCII 数学（后端会静态检出并给提示）。
- **StrictMode**：`main.tsx` 故意不开，别加回去（白板会双挂）。
- **颜色写死**：新代码避免裸 hex；用语义变量，浅/深才能一起正确。
