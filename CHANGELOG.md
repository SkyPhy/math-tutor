# 版本记录 / Changelog

> **版本号规则（用户定义，2026-06-27 起执行）**：`0.<大迭代>.<小迭代><进度字母>`
> - 前导 **`0.`** — 项目尚未完成的大版本（pre-1.0）。
> - 第二位 **`<大迭代>`** — 一个大版本内的「大迭代」（新增子系统 / 重构数据流等）。
> - 第三位 **`<小迭代>`** — 「小修改 / 小迭代」（修补、增量）。
> - 末尾 **`<进度字母>`** — 当前进度（`a` → `b` → `c` …，随该迭代推进）。
> - 例：`0.1.0a` = 第 1 个大迭代的首个产出、进度 a；`0.1.1a` = 其后的第 1 个小迭代、进度 a。
>
> 每次提交在此追加一条，提交信息标题以 `vX.Y.Zℓ` 开头。

---

## v0.4.9b — 去卡片化 + 圆角克制 + 边缘淡化（用户反馈）+ 前端开发指南文档

按用户反馈把「卡片风」改为「正常扁平面板」：去浮起阴影、淡化边缘、收敛夸张圆角；并沉淀一份详细的前端
指南文档供后人查改。**判分/共识/诊断内核零改动；纯前端 + 文档。**

- **形状设计 token（`styles.css` `:root`）**：新增 `--radius-lg/md/sm/pill` 与 `--card-shadow`，全站圆角/立体
  感集中可调。把原来散落的 `border-radius: 24/20/16/14/12/10/8px` 机械收敛到 token（大容器 24→`--radius-lg`
  10px，中块→`--radius-md` 8px，小控件→`--radius-sm` 6px，芯片保持 `--radius-pill`）。
- **去浮起阴影**：14 处 `0 25px 50px…` / `0 10px 30px…` 之类「卡片浮起」阴影统一改走 `--card-shadow: none`；
  焦点环 `0 0 0 2px accent`、内阴影、按钮 hover 抬升是功能性阴影，保留。
- **边缘淡化**：`--glass-border` 深色 0.1→0.06、浅色 0.14→0.08；`--glass-bg` 略降透明度——面板与背景更融，
  不再是硬边卡片。
- **前端指南文档（新 `docs/FRONTEND_GUIDE.md`）**：整体架构与数据流、**每个模块干什么/何时改**的目录地图
  （顶层/screens/components/lib/hooks/board 全覆盖）、**构建前端的 10 条标准**、常见任务食谱、**样式与主题
  系统**（语义变量 + 主题色 + 形状 token + 去卡片约定）、运行构建验收、坑位速查。`frontend/README.md` 顶部
  加指针指向本指南（README 的 Layout/Status 已过时）。
- **验收（运行—观测）**：`tsc --noEmit` 0 错、`vite build` 成功；**headless Chrome 两张截图**确认深/浅两态
  均为扁平面板——淡边、无浮起阴影、10px 克制圆角，主题色与可读性不受影响。

## v0.4.9a — 深色/浅色模式 + 可选主题色（用户反馈）：全站主题系统

给所有页面加**深色/浅色双主题**，并让**主题色由用户自选**。**判分/共识/诊断内核零改动；纯前端。**

- **主题变量系统（`styles.css`）**：把 `:root` 重构为「基础 accent 变量 + `[data-theme=dark|light]` 两套语义
  变量」——全站原本就走的 7 个变量（`--glass-bg/-border`、`--text-main/-dim`、`--accent-blue/-purple`、
  `--bg-deep`）按主题重定义即可整站翻面。玻璃拟态填充统一改用 `rgba(var(--surface-rgb), α)`——深色 `--surface-rgb`
  是白 `255,255,255`、浅色是深 `15,23,42`，**一处换通道即重着色所有卡片**（16 处 `rgba(255,255,255,…)` 机械替换，
  各自 alpha 不变）。body 渐变、`<select>` option 底色改用 `--bg-gradient-from`/`--surface`；为浅色补了几处
  pastel 芯片/标签文字的深色覆盖（仅影响浅色，深色像素不变）。深色代码/播放器面板两主题都保持深底（如视频播放器）。
- **主题运行时（新 `lib/theme.ts` + `components/ThemeControls.tsx`）**：深浅切换 + 5 个预设主题色（海蓝/紫罗兰/
  翡翠/玫瑰/琥珀）+ `<input type=color>` 自定义（自定义色自动 `lighten()` 推出第二个渐变端点）。选择持久化到
  `localStorage` 并即时应用到 `<html>`（`data-theme` + 内联 `--accent-*`）。控件固定在页头右上角，**五屏通用**。
- **防闪烁（`index.html`）**：`<head>` 内联脚本在首次绘制前读 `localStorage` 套用主题，避免加载时先闪深色再变浅色。
- **验收（运行—观测）**：`tsc --noEmit` 0 错、`vite build` 成功；**headless Chrome 两张截图**确认深色（默认海蓝）
  与浅色（切翡翠）全站正确翻面——页头渐变标题、玻璃卡片、芯片/下拉、白板容器在两主题下均清晰可读，主题色即时生效。

## v0.4.8d — Manim 渲染清晰度可选（用户反馈）：默认提到 720p，可选 480p→4K

此前渲染写死 `manim -ql`（480p15，最低档）。现**清晰度可由用户下拉选择**，默认档也从 480p 提到
**720p30**（更清晰且仍渲染得快）。**判分/共识/诊断内核零改动；渲染管线仅参数化质量档。**

- **后端（`manim_render.py`）**：新增 `QUALITY_FLAGS`（`low -ql`480p15 / `medium -qm`720p30 /
  `high -qh`1080p60 / `2k -qp`1440p60 / `4k -qk`2160p60）+ `_quality_flag()`（**只映射白名单键**，绝不把任意
  字符串拼到命令行）；`render()`/`_render_subprocess()` 接受 `quality`，替换写死的 `-ql`。默认 `medium`，可用
  `MANIM_RENDER_QUALITY` 环境变量覆盖。
- **接口（`main.py`）**：`ManimRenderRequest` 加 `quality` 字段，透传 `render()`。
- **前端（`ManimView.tsx` + `api.ts` + `styles.css`）**：生成动画按钮旁加**清晰度下拉**（流畅 480p / 清晰
  720p / 高清 1080p / 超清 1440p / 4K 2160p），默认「清晰 720p」；`ManimRenderReq` 加 `ManimQuality` 类型与
  `quality` 字段。tooltip 提示"越高越清晰但更慢、文件更大"。
- **验收（运行—观测）**：同一场景 `quality=low`→**854x480**、`high`→**1920x1080**、缺省→**1280x720**（ffmpeg
  探测分辨率确认档位生效）；`tsc --noEmit` 0 错、`vite build` 成功、后端 `py_compile` 通过。

## v0.4.8c — Manim 中文渲染修复（用户反馈 UnicodeDecodeError）：中文走 Text()，MathTex 只放 ASCII

修第二类「Manim 渲染失败」：报错是 `UnicodeDecodeError ... tex_file_writing.py`，真凶是**中文被放进了
`MathTex`/`Tex`/`Title`**。基础版 `latex` 引擎无法排版 CJK → 编译失败 → 更糟的是 manim 自己读 MiKTeX 的
GBK `.log` 时按 UTF-8 解码又崩了，把真因盖住。已复现确认：`Tex('连续…')`→error；`Text('连续…')`+
`MathTex('E=6')`→ok。**判分/共识/诊断内核零改动。**

- **模板（`main.py ManimAnimator`）**：新增 `_is_ascii()` + `_formula()`；`_render_code` 把 `Title(...)` →
  `Text(...).to_edge(UP)`、字幕 `Tex(action)` → `Text(action)`（action 是中文步骤说明）；**公式按内容择器**：
  ASCII 数学用 `MathTex`，含 CJK 则用 `Text`——这样中文应用题（`eq_latex` 回退成中文原题）也能渲染而非崩。
  两侧都是 Tex 才用 `TransformMatchingTex`，否则退回 `ReplacementTransform`（任意 mobject 可用，且正确把旧式
  换下、新式加上，`eq = step_eq` 仍成立）。
- **AI 提示（`prompts.py build_manim_prompt`）**：加**关键规则**——`MathTex`/`Tex` 经 LaTeX，**不能含中文/
  非 ASCII**；一切文字/中文标题字幕用 `Text(...)`，`MathTex`/`Tex` 只放 ASCII 数学；不要用 `Title(...)`（LaTeX
  底），标题用 `Text("…").to_edge(UP)`。
- **渲染兜底（`manim_render.py`）**：新增 `_cjk_in_tex()`——渲染前**静态检出** MathTex/Tex/Title 里的 CJK，
  直接快速失败给清晰中文提示（不空跑子进程）；子进程失败时若命中 CJK 或 `UnicodeDecodeError...tex` 也归到
  同一提示。前端 `ManimView` 展示 `reason` 并回退浏览器故事板。
- **验收（运行—观测）**：中文应用题模板 → `status:"ok"` 真 MP4；可解方程（ASCII MathTex + 中文 Text 字幕 +
  5 步 TransformMatchingTex）→ `status:"ok"`；`Tex('连续…')` → 秒级 `status:"error"` + `cjk_in_tex` 清晰提示；
  `_cjk_in_tex`/CJK 正则离线单测全过；后端 `py_compile` 通过。

## v0.4.8b — `<manim>` 可直接放 Manim 代码（用户反馈）：AI 输出代码即原样渲染，跳过二次生成

顺着 v0.4.8a：让答疑/助手 AI 可在 `<manim>…</manim>` 里**直接写可运行的 Manim CE 代码**，前端识别后走
`manim_code` 原样渲染（而非当自然语言 `spec` 再让后端二次生成代码）——更快、AI 对动画更可控。**判分/共识/
诊断内核零改动；渲染管线（v0.4.8a）零改动，仅调整"什么进 `manim_code` vs `spec`"。**

- **后端提示（`prompts.py` 四处）**：`build_chat_system`、`build_assistant_chat_system`、逐行批改
  (`build_line_analysis`) 的规则与其 docstring——`<manim>` 块内容从"**一两句话**说明"放宽为"**二选一**：
  一两句话说明 **或** 可运行 Manim CE 代码（`from manim import *` + 恰好一个 `class …(Scene)`）"；应用对代码
  原样渲染，只给说明时才自动生成。
- **前端识别归一（`ManimView.tsx`）**：把原本散在 `ChatBox` 里的 `looksLikeManimCode()` 提取并导出，新增
  `manimProps(content)` → 返回 `{code}` 或 `{spec}`。`ChatBox`（聊天回复里的 `<manim>` 段）与 `AssistantScreen`
  （逐行批改的 `focusLine.manim`）**共用同一判定**——此前 `AssistantScreen` 恒当 `spec`，现也能识别代码走
  `manim_code`。
- **验收**：`tsc --noEmit` 0 错、`vite build` 成功；`prompts.py` `py_compile` 通过；`manim_render.render(
  manim_code=…)` 早已验证可把现成代码渲成真 MP4（v0.4.8a）。

## v0.4.8a — Manim 渲染修复（用户反馈「渲染失败：未知错误」）：装 LaTeX + 缺失可诊断 + 跨平台可移植

修「Manim 渲染失败：未知错误」。**根因不是 manim/ffmpeg**——纯文本场景一直能出片；应用为每题生成的
场景都含 `MathTex`/`Tex`/`Title`（`main.py` `ManimAnimator._render_code`），manim 排版公式要调 `latex`，
而机器上**没装 LaTeX**，故每次数学渲染必失败；"未知错误"是 `manim_render.py` 把 manim 的 Rich 框线报错
`[-600:]` 截断后剩空串的兜底文案。**判分/共识/诊断内核零改动。**

- **① 安装 LaTeX（basic MiKTeX，系统级）**：`choco install miktex` → `C:\Program Files\MiKTeX\...\bin\x64`
  （已在机器 PATH，start.bat 起的新 shell 可见 `latex`/`dvisvgm`）。开 `[MPM]AutoInstall=1` 按需补包；应用
  模板所需宏包已预热缓存，**无代理/离线**重跑新公式仍 `status:"ok"`。下载走用户 clash 代理。
- **② `manim_render.py` 加固（跨平台可移植）**：新增 `latex_available()`（探 `latex`/`xelatex`/`pdflatex`/
  `lualatex`，`shutil.which` 跨 MiKTeX/TeX Live/MacTeX/TinyTeX）+ `_needs_latex()`（静态检出 MathTex/Tex/
  Title/TransformMatchingTex）——**缺 LaTeX 时快速失败**并给**分平台**安装提示（Win/macOS/Linux），不空跑
  子进程；`_clean_tail()` 剥 Rich 框线字符让**真实错误浮现**（如 "LaTeX compilation error: Missing $"），
  告别"未知错误"；LaTeX 编译失败（缺宏包/语法错）与缺发行版分别给不同文案；子进程 `encoding=utf-8,
  errors=replace` 防编码错乱盖住真错；`status()` 增 `latex` 布尔字段。前端 `ManimView` 本就展示 `reason`，
  这些提示直达用户并优雅回退浏览器故事板。
- **③ 跨平台启动脚本 `start.sh`**（macOS/Linux 对应 `start.bat`）：venv 引导 + 从 imageio-ffmpeg 软链本地
  `ffmpeg` + LaTeX 缺失非致命提示 + 后端后台/前端前台启动。
- **验收（运行—观测）**：用应用**真实模板场景**（Title+MathTex+Tex+TransformMatchingTex）跑 `manim_render.
  render()` → `status:"ok"`、64KB 真 MP4；**无代理**下渲染新公式 `\frac{x}{2}=5` 仍 `status:"ok"`（宏包本地
  命中）；`_needs_latex`/`_clean_tail`/`latex_install_hint` 离线单测全过；模块 import + `py_compile` 通过。

## v0.4.7a — 公共聊天控件补全（用户反馈）：恢复「渲染方式」下拉 + 「换行键」下拉 + 「允许识别」多选表单

补齐 `docs/DEVELOPMENT_PLAN.md` §C-公共 里聊天输入控件规定、但此前未落地的三件套（`ChatBox` 底部一排：
渲染方式 · 换行键 · 允许识别 · 发送）。**判分/共识/诊断内核零改动；助手/答疑屏仅改 `onSend` 签名。**

- **① 恢复「渲染方式」下拉（md+latex 渲染 / 源码风 / 纯文本）**（`ChatBox` + `lib/markdown`）：此前聊天消息**恒按
  全渲染**，用户反馈"选 latex+md 渲染还是仅文本的下拉不见了"。现 `ChatBox` 自带 `RenderMode`（`1` 全渲染 /
  `2` 源码风 / `3` 纯文本，聊天默认 `1`）——`3` 纯文本经新 `renderPlain` 包 `<pre class="chat-plain">`（MathJax
  `skipHtmlTags` 含 `pre`/`code`，故 `\(…\)` 原样显示不被排版），`2` 复用 `renderSource`。切换即重排（typeset key
  改成 `渲染模式:消息数`）。
- **② 「换行键」下拉：Enter / Alt+Enter / Ctrl+Enter**（`ChatBox`）：下拉选**哪个组合键换行**；选 **Enter 换行**则
  Enter 只换行、**发送只能点「发送」**；选 Alt/Ctrl+Enter 则该组合换行、裸 Enter 发送（默认 Ctrl+Enter，保留
  Enter 发送习惯）。裸 Alt/Ctrl+Enter 浏览器默认不插换行，故在光标处手动插入；IME 组合中的 Enter 一律放行。
- **③ 「允许识别特殊符号与表达式」多选表单**（`ChatBox`；透传后端 `allow_special`）：`<details>` 弹层多选——
  特殊符号（默认勾）/ 正则表达式 / `\n \r` 换行 / 转义（`\t` 等）。**前端行为**：勾"换行"则把字面 `\n``\r\n``\r`
  转真换行；勾"转义"则 `\t` 转制表符——**刻意收窄，绝不动 LaTeX 反斜杠**（`\frac`/`\times` 原样保留，已单测）。
  勾选项汇成 `allow_special` 数组透传后端：`/assistant/ask` 早有该字段（改为取控件选项，去掉写死的 `SPECIAL_SYMBOLS`）；
  `/claude/chat` **新增** `allow_special`（`ChatRequest` + `prompts.build_chat_system` 各加一行提示，让模型知道这些
  符号/表达式是**有意为之、按字面理解**，非笔误）。
- **验收（运行—观测）**：`tsc --noEmit` 0 错 + `vite build` 成功；`applySpecial`/`buildAllowSpecial` Node 单测 9/9
  过（含"LaTeX 反斜杠在换行+转义均开时仍存活"的关键用例）；`build_chat_system` 注入/不注入 `allow_special` 两路
  Python 冒烟过；**headless Chrome 两张截图**确认底部三控件 + 「允许识别」多选弹层按规格渲染，AI 消息 md+latex 正常。

## v0.4.6a — 五屏细化（用户反馈 4 项）：答疑随用户语言 + OCR 全文保留换行 + 校对屏工具条扩充 + 聊天内 `<manim>` 渲染

按用户反馈精修四处，横跨③校对④助手⑤答疑与 OCR/聊天底座。**判分/共识/诊断内核零改动。**

- **#1 · 答疑随使用者语言**（`prompts.py`）：`build_chat_system`/`build_assistant_chat_system` 加"**用学生
  提问所用的语言回答**（中文↔英文，逐轮跟随）"。真网关验证：英文提问→英文回复（ascii 占比 0.92）。
- **#2 · OCR 全文识别 + 保留换行**（`recognize.py`）：`_OCR_PROMPT` 从"只转录单个数学式"改为"**转录图中
  一切**——数学、符号、以及任何英文/中文文字，**按原样保留换行**，勿在数字/单词字符间插空格"。
  `_clean_math_text`→`_clean_transcription`：**不再折叠所有空白**（旧逻辑会删掉换行与词间空格，破坏散文），
  改为仅规整行尾/连续多空格、**保留换行**。识别文本送服务器时换行完整（学生在校对屏纠错）。
- **#3 · md/latex 工具组件（校对屏 editor + AI 交流屏共用）**（新 `components/EditorToolbar.tsx` +
  `lib/editorOps.ts`；接入 `CheckScreen` 与 `ChatBox`）：**一套共享工具组件**拆成**两区、可鼠标滚轮左右
  滚动**——**MD 区**：加粗（已加粗则**取消**）/ 标题（下拉选 H1–H6，替换已有 #）/ 新建表格 / 列举 / 引用；
  **LaTeX 区**：插入公式（`$$$$`）/ 分式 / 右上角标 / 右下角标 / 平方根 / n 次方根 / 对数 / 自然对数 /
  方程组 / 特殊符号（下拉 25 个）。**「插入公式」之后**的 LaTeX 按钮**自动判断插入点是否已在 `$$…$$` 内，
  不在则自动两侧补 `$$`**（`insertLatex`/`isInsideMath` 纯函数）。滚轮横滚用非被动 `wheel` 监听、仅在溢出时
  `preventDefault`。**关键修正（用户反馈）**：此前工具组件只在 CheckScreen、且被渲染模式 1/2 门控（默认纯文本
  模式 3 下**看不到**），而 ChatBox 只有一排纯符号——现改为 `EditorToolbar` **同时进 CheckScreen（始终显示，
  不再受渲染模式门控）与 ChatBox（取代旧符号排）**，两处工具完全一致。`editorOps.ts` 纯函数经 Node+esbuild
  单测（auto-`$$`、加粗 toggle、标题替换）；headless Chrome 截图确认两屏工具组件一致渲染。
- **#4 · 聊天回答用 `<manim>` 出形象化演示**（`prompts.py` + `ChatBox`/`ManimView`）：A) 提示词让 AI"**用图/
  动画更好懂时，先想清楚演示什么，再附一个 `<manim>…</manim>` 说明**"（真网关验证：请求可视化→回复确含
  `<manim>` 故事板）。B) `ChatBox` 渲染消息时**切分出 `<manim>…</manim>` 段**，各渲染成 `ManimView`（其余走
  md+latex）；`ManimView` 新增 `code` 入参（块内是 Manim 代码则整段送 `manim_code`，是描述则送 `spec`），
  经 `/manim/render` 出真视频或降级故事板。助手/答疑屏把题面作 `manimExpression` 传入 ChatBox。
- **验收（运行—观测）**：`tsc --noEmit` 0 错 + `vite build` 成功；`editorOps` Node 单测全过；`recognize`
  `_clean_transcription` 单测（换行 + 中英散文保留）过；**真网关**：`/claude/chat` 英文问→英文答、可视化
  请求→含 `<manim>` 段；后端 `recognize`/`prompts` 导入无回归。

## v0.4.5b — 真 Manim 渲染（React）：`<manim>` 块出真视频（`manim_render.py` / `/manim/render`），无 Manim 自动回落故事板

落地五屏流程的可选独立能力（`docs/DEVELOPMENT_PLAN.md` §E5 / 北极星目标 10，原计划 v0.3.5b）。助手屏
逐行分析产出的 `<manim>` 故事板注记，现可**按需渲染成真视频**：服务器装了 Manim CE + ffmpeg 时出
真 MP4，否则**自动回落**到浏览器故事板（逐帧 MathJax 演示）+ 附上生成的 Manim 代码——**始终 200、
不报错**（沿用 `claude_service`/`recognize` 的降级范式）。判分/共识/诊断内核零改动。

- **后端 `backend/app/manim_render.py`（新）**：纯编排 + subprocess（无 FastAPI，沿用 assistant.py/
  workspace.py 分层）。`available()` 仅当 `manim` 与 `ffmpeg` **都在 PATH** 时为真；`generate_code`
  调 `claude_service` + `prompts.build_manim_prompt` 生成自包含 Manim CE Scene（剥离代码围栏）；
  `render()` 代码来源优先级 **显式 manim_code → AI 生成 → 模板代码**，装了 Manim 则写临时 `.py` →
  `subprocess.run(["manim","-ql",…], timeout=150)` → glob 出 mp4 拷进 `data/manim_media/` 返回
  `video_url`；未装/失败/超时→`status: unavailable|error` + 原因，**从不抛异常**（都变状态字段）。
- **`prompts.build_manim_prompt`（新）**：让模型只输出可运行的 Manim CE 代码（单 Scene、标准 mobject、
  ≤40 行 / ≤15s，快而稳），围绕 `<manim>` 注记要讲清的点。
- **新端点 + 静态挂载**（`main.py`）：`POST /manim/render`（`{expression|spec|manim_code}` → `{status,
  video_url?, storyboard, manim_code, provider, reason?}`；先 `ManimAnimator.build` 出 SymPy 驱动的
  **模板故事板**作兜底，再 `run_in_threadpool` 委托 `manim_render.render`——重渲染不堵事件循环）；
  `app.mount("/manim-media", StaticFiles(...))` 供真视频回放。含题面策略校验。
- **前端 `ManimView`（`frontend/src/components/ManimView.tsx`，新）**：`<manim>` 块的「▶ 生成动画」
  按钮 → `/manim/render`。`status==='ok'` 播 `<video>`（`API_BASE + video_url`，自动循环）；否则**故事板
  播放器 `Storyboard`**（逐帧 MathJax + 标题 + 说明，自动步进 + 上/下一步 + 重播）+ `<details>` 展开
  生成的 Manim 代码 + 诚实说明为何无真视频。接入 `AssistantScreen`：点开带 `<manim>` 的行时，追问区
  上方出现该动画块（expression=题面、spec=该行注记）。
- **验收（运行—观测）**：`tsc --noEmit` 0 错 + `vite build` 成功。**真后端 HTTP**：`/manim/render`
  在**无 Manim 环境**返回 `status:"unavailable"`、`provider:"claude"`（AI 已生成 Manim 代码）、
  6 帧模板故事板、完整 `manim_code`、中文降级原因——**HTTP 200、不报错**（满足"无 Manim 时自动回落
  且不报错"）；`/manim-media/<缺失>` 返回 404（挂载已注册，非路由错误）；`manim_render` 离线单测：
  `available()` 检测、场景名提取、代码围栏剥离均正确。真渲染路径（装 Manim 时出 MP4）代码就绪，
  待有 Manim CE 的环境端到端确认。

## v0.4.4a — 答疑屏（React）：不经白板就本题问答（`解析此题` /analyze + Q&A /claude/chat + 公共聊天控件）

落地五屏流程的第 5 屏（`docs/DEVELOPMENT_PLAN.md` §C5，原计划 v0.3.4a）。题目屏点「🙋 提问 / 不会做」
直达答疑屏，**不经白板**即可就当前题目问答；苏格拉底式**不直接给最终答案**。复用 v0.4.3a 建的公共
聊天控件 `ChatBox`。后端零改动——直接复用既有 `/analyze` 与 `/claude/chat`。

- **答疑屏 `AskScreen`（v0.4.4a 真实现，取代占位）**：顶部题目卡（`ProblemBody` 就地渲染题面数学 +
  AI 免责声明）；「🔍 解析此题」→ `POST /analyze`（苏式 0 级解析，`analyzeText` 抽取 socratic 消息文本）
  作为对话首条 AI 消息；下方 `ChatBox` 自由问答 → `POST /claude/chat`（带 `expression` grounding +
  会话历史），每条回复流式追加。换题即开新对话。
- **api 层**：`analyzeProblem`（typed `AnalyzeResp`）+ `analyzeText`（合并 socratic tutor/system 文本，
  回退 legacy `steps`）。
- **验收（运行—观测）**：`tsc --noEmit` 0 错 + `vite build` 成功。**真后端 HTTP**（真网关
  `claude-opus-4-8`）：`/analyze` 就「求 2x+4=10 中 x」返回 1 条 tutor 苏式解析（337 字，未直接给答案）；
  `/claude/chat`「第一步该怎么想？」返回引导式回复；公共 `ChatBox`（渲染 md+latex / Enter 发送·
  Shift+Enter 换行 / 特殊符号）复用无回归。

## v0.4.3a — AI 助手屏（React）：逐行对齐分析（`assistant.py` / `/assistant/analyze`）+ 行级追问 + 公共聊天控件

落地五屏流程的第 4 屏（`docs/DEVELOPMENT_PLAN.md` §C4 / §E2，原计划 v0.3.3a）。学生经③校对屏
「提交（求助）」后，作答被**逐行对齐分析**：左列学生的每一步、右列 AI 的点评——**无误的行留空**
（右列不写字），只有出错/可改进的行才给分析。点**任意行**可就那一步**带上下文追问**。判分/共识/
诊断内核零改动，仅在其上新增编排层 + UI 层。

- **后端 `backend/app/assistant.py`（新）**：逐行分析编排（纯逻辑，无 DB / 无路由——沿用 v0.4.2a
  `workspace.py` 的分层：新逻辑独立成模块，`@app` 路由留在 `main.py`）。`split_lines` 把作答切成非空
  行（1 起编号），`analyze` 调 `claude_service` 让模型对**每行**产出对齐分析（JSON 对象 `{summary,
  lines:[{idx,has_issue,analysis}]}`），再**按 idx 对齐回本地行**（模型漏行/多行都不会错位——正确行
  自然留空）；`<manim>…</manim>` 故事板注记从 analysis 抽出到 `manim` 字段（真渲染留待 v0.4.5b）。
  含 LaTeX 反斜杠修复的宽松 JSON 解析（复用 `main.py` 范式）。网关不可用/解析失败→**模板降级**
  （按行列出但不点评，`provider:"template"`，附 `reason`）。`ask` 复用 `/claude/chat` 那套，把
  **点开的那一行**（`focus={idx,content,analysis}`）+ 题目作为额外 grounding，苏格拉底式作答。
- **`prompts.py` 扩展**：`build_line_analysis_prompt`（逐行、对齐、**留空规则**"不为正确行凑评语"、
  `<manim>` 触发约定、按 `render_mode` 提示如何理解学生书写）、`build_assistant_chat_system`（含
  `focus` 行上下文、`render_mode` 与 `allow_special` 特殊符号约束）。
- **新端点**（`main.py`）：`POST /assistant/analyze`（`{question_id|problem, student_work_md,
  session_id, model, render_mode}` → `{lines,summary,provider}`）、`POST /assistant/ask`（`/claude/chat`
  字段 + `{focus, render_mode, allow_special}` → `{reply,provider}`）；`_resolve_problem_text` 优先用
  前端传来的题面，缺省时按 `question_id` 从 `exam.get_question` 还原。两端点恒 200（`provider` 标明
  是否降级），空消息 400。
- **公共聊天控件 `ChatBox`（`frontend/src/components/ChatBox.tsx`，新）**：可复用聊天控件——**渲染**
  （每条消息走 `renderMarkdownMath` + MathJax）、**换行键**（Enter 发送 / Shift+Enter 换行，兼容
  中文输入法 composition）、**特殊符号**（`× ÷ ± √ π ≤ ≥ ≠ ∑ ∫ …` 20 个，按光标插入；同一份清单
  作为 `allow_special` 传给后端）。导出 `SPECIAL_SYMBOLS`；助手屏用它做行级追问，⑤答疑屏（v0.4.4a）
  可复用。
- **助手屏 `AssistantScreen`（v0.4.3a 真实现，取代占位）**：进屏（`workFlow==='assist'` 提交后）用
  `store.studentWork` + `renderMode` 调 `/assistant/analyze`；**两列对齐网格**——左列逐行渲染学生书写
  （md+latex），右列出错行显示分析、无误行显示「✓ 这步没问题」、有 `manim` 显示 🎬 故事板注记。整行
  可点，点开→底部 `ChatBox` 就**该行**追问（`/assistant/ask`），**每行各自保留一条对话线程**；顶部
  summary 条 + provider 徽标 +「🔄 重新分析」。`store.tsx` 新增 `renderMode` 交接（校对屏提交时带上）。
- **验收（运行—观测）**：`tsc --noEmit` 0 错 + `vite build` 成功。**真后端 HTTP**（uvicorn + 真网关
  `claude-opus-4-8`）：对 `2x+4=10 → 2x=10+4 → 2x=14 → x=7` 的作答，**第 1 行（正确）右列留空**、
  第 2 行判出"移项未变号（应 \(2x=10-4\)）"并附 `<manim>` 故事板、第 3/4 行标出连锁错误，summary
  给整体点评；行级 `/assistant/ask`「为什么移项要变号？」返回**苏格拉底式**引导（反问而非直接给答案）；
  空消息→400；空作答→`provider:"empty"` 优雅返回；仅传 `question_id`（无题面）时后端从题库还原题面
  正常分析。模板降级路径经离线单测（网关关时按行列出、`provider:"template"`）。

## v0.4.2a — 校对屏（React）：OCR 文本回显纠错 + 三渲染方式 + 个人草稿库（workspace.py / `/work/*`）

落地五屏流程的第 3 屏（`docs/DEVELOPMENT_PLAN.md` §C3 / §E1）。OCR 识别**必经校对**——学生先核对纠错
再入库/送批改，避免识别噪声污染判分。新增**个人草稿库**：作答可命名暂存（按题号），断点续作。
**判分/共识/诊断内核零改动**，仅在其上新增 UI 层 + 一个新 SQLite 子系统。

- **后端 `backend/app/workspace.py`（新）**：个人草稿/答案库（`data/workspace.db`，纯标准库 sqlite3，
  复用 `exam.py`/`auth.py` 范式）。表 `work_drafts(id, owner, question_id, filename, content_md,
  render_mode, status, created_at, updated_at)`；`owner` = 登录用户名（`user:<name>`）或匿名
  `session_id`（`sess:<id>`）。`save_draft`（带 `draft_id` 则**原地更新**——「存草稿→续作→再存」复用
  一行不堆重复）、`list_drafts`（按 owner+题号、最新在前）、`get_draft`（带 owner 校验）、`delete_draft`。
- **新端点**（`main.py`）：`POST /work/save`（`status=tmp` 存草稿 / `status=final` 提交，返回整条草稿
  以便前端保留 id 续作）、`GET /work?session=&question_id=`（我的草稿列表）、`GET /work/{id}`、
  `DELETE /work/{id}`——均按 `_work_owner` 归属隔离（他人 session 取不到 → 404）。
- **校对屏 `CheckScreen`（v0.4.2a 真实现，取代占位）**：可编辑 `textarea` 回显并**逐字纠错** OCR 文本；
  「渲染方式」下拉 **1 全渲染（md+latex）/ 2 源码风 / 3 纯文本（默认）**——1/2 时挂出 md&latex 工具条
  （公式块/行内/分式/根号/上下标/Σ/加粗，按光标位置插入）+ 实时预览。底部：文件名输入 +「存草稿」
  （`POST /work/save status=tmp`）/「提交」（`status=final`）；提交后按流程去向——`submit` 流→
  `POST /verify` 共识判分并显示**判定面板**（对/错/未判定 + `judged_by`/`votes_label`/参考答案/理由），
  `assist` 流→ AI 助手屏；「我的草稿（本题）」列表可一键载入续作。纠错后的内容经
  `store.studentWork` 传给后续屏。
- **Markdown+LaTeX 渲染（`frontend/src/lib/markdown.ts`，新）**：用 `marked@16`（提升为直接依赖）渲染
  Markdown + 现有 MathJax 渲染公式。关键修复：marked 会把 `\(`/`\[` 的反斜杠当转义吃掉——故**先用占位符
  保护所有公式段**（`$$…$$`/`\[…\]`/`\(…\)`，单 `$…$` 归一为 `\(…\)`）→ marked 解析散文 → 还原公式段，
  使 LaTeX 原样抵达 MathJax。
- **验收（运行—观测）**：`tsc --noEmit` 0 错 + `vite build` 成功。**真后端 HTTP**（uvicorn）：`/work/save`
  存 tmp → 带 `draft_id` 更新同一行（续作，内容确被改写）→ `/work` 列表 1 条 → `/work/{id}` 取回 →
  **他人 session 取不到（404，归属隔离）** → 改 `final` → `DELETE` 成功；含中文文件名 UTF-8 往返正确。
  **真 marked**（Node + 真依赖）：行内 `\(…\)`/行间 `$$…$$` 经 marked 后**原样存活**、`**粗体**` 渲染、
  单 `$…$`→`\(…\)`、`\n`→`<br>`。所有新增/改动前端模块经**实时 Vite dev server** 转译 200 且 marked
  预打包可解析（组件可在浏览器加载，无转译/导入错误）。

## v0.4.1a — 选区屏（React）：白板笔画上叠加矩形/套索框选 + 句柄缩放 + 仅导出选中区 → OCR

落地五屏流程的第 2 屏（`docs/DEVELOPMENT_PLAN.md` §C2）。学生作答前先**框选白板的哪一部分**发给
OCR——只把**选中区域**重绘为 PNG 上传，未选中的内容不外发。**后端仅新增一个只读端点**，判分/共识/
诊断内核零改动。

- **后端 `GET /recognize/models`（`recognize.list_models()`）**：列出 OCR 引擎
  `nex`（nex-n2-pro 专用 OCR）/`claude`（Claude 视觉）/`auto`（nex 失败回退 Claude），每个带
  `available`（按 `.env` 是否配置网关）+ `default`（首个可用引擎）。`id` 即回传 `POST /recognize?method=` 的值。
- **选区几何 / 导出（`frontend/src/board/selection.ts`，纯函数）**：`normRect`/`clampRect`（翻转负宽高、
  钳进画布）、`inkBounds`（笔画包围盒，忽略擦除 op）、`polyBounds`、`exportRect`（裁出矩形区域）、
  `exportLasso`（裁出多边形内部）。导出**直接从已渲染的白板 canvas 拷像素**（而非从 op 列表重推），
  天然正确处理擦除、忠实于真实墨迹。
- **选区屏 `SelectScreen`（v0.4.1a 真交互）**：在白板快照上叠加两张 canvas（底图 + 选区层）；
  **矩形**工具（8 句柄：四角 + 四边可拖动改大小、框内拖动整体平移、空白处重新框选）与**套索**工具
  （自由勾勒多边形）；进屏默认选区 = 墨迹包围盒（留白 24px）。底部「OCR 模型」下拉由
  `GET /recognize/models` 填充（失败回退内置 3 项），「提交选区」→ `exportRect/exportLasso` 出 PNG →
  `POST /recognize?method=<所选>` → OCR 文本入 store → 进③校对屏；含识别中态、失败原因提示。
  `BoardEngine` 加 `width`/`height` getter 供选区屏取画布尺寸（不再硬编码 800×600）。
- **校对屏小改**：`CheckScreen`（仍是 v0.4.2a 占位）现回显 store 里的真实 OCR 文本，使
  选区→识别→校对链路**可观测**（无结果时显示提示文案）。
- **验收（运行—观测）**：`tsc --noEmit` 0 错 + `vite build` 成功（47 模块）；**真后端 HTTP**：
  `GET /recognize/models` 返回 3 引擎 + `default=nex`；合成一张含「2+3=5」（上）与「999 wrong」（下）
  的白板，**只裁上半区**发 `POST /recognize?method=nex` → `{"text":"2+3=5","engine":"nex-n2-pro","status":"ok"}`
  ——选中区正确识别、未选中的干扰内容不外发。**真浏览器**（Vite + headless Chrome）对真实
  `selection.ts` 跑 11 条断言全过（含「空白区域导出 0 墨迹」证明只发选中区）；app 启动回归正常。

## v0.4.0a — 学生端前端「重平台化」：静态 HTML → Vite + React + TS（`frontend/`）

按用户定向（2026-06-30：「改为动态页面！直接重构！…html 过时了且不方便维护，改为 nodejs 维护，
旧的页面移动到 web/legacyweb」）把学生端核心 tutor 从单页静态 HTML 迁到 **Node 构建的 React 工程**。
属**大迭代 +1**（新增前端构建子系统）。**后端零改动**——共识判分 `reasoner.py`、诊断、标签自进化、
记忆全部保留，React 仅经 HTTP 调用（CORS 已开）。技术栈经 AskUserQuestion 选定：**Vite + React + TS**。

- **新工程 `frontend/`（用户定向「前端构建在 frontend」）**：`package.json`/`vite.config.ts`/`tsconfig`/
  `index.html` + `src/`。`npm run dev` 起 Vite 开发服务器（:5173，含 `/api` 代理）；`npm run build` →
  `dist/` 静态资源。`VITE_API_BASE` 可改后端地址（默认 `http://localhost:8000`）。
- **配置驱动（落实「动态、可改、不要死成 html」）**：`SCREEN_DEFS`/`SOURCES`/`PROBLEM_ACTIONS` 落为
  **类型化配置模块**（`src/config.ts`）；五屏路由 + 返回栈为 React 状态（`src/store.tsx`：`navTo/navBack/
  navHome/startWorkFlow`）。
- **白板引擎忠实移植**（`src/board/BoardEngine.ts`）：原生 `<canvas>` 的 `strokes[]`
  （`{mode:'pen',weight,points} | {mode:'erasePixels',radius,points}`）、指针 down/move/up、笔 / 区域擦 /
  整笔擦、live 预览、`repaint`、PNG 导出 —— 与旧引擎逐行对齐。引擎实例常驻 store，画布元素随屏挂载/脱离
  以**跨屏保留笔迹**（为 v0.4.1a 选区屏铺路）。
- **题目屏接线**（`ProblemScreen` + `ProblemCard` + `PracticeControls` + `Whiteboard`）：来源下拉
  （1 AI / 2 学科网 / 3 题库 → `/practice/next?source=`）、🏷 标签开关（默认隐藏）、MathJax 题面、
  🎯 按思维类型 / 难度出题（`/tags/catalogue` + 开放难度梯）、🎲 换一题、底部三动作（提交·二次确认 /
  提问 / AI 助手）。
- **屏 ②–⑤ 为诚实占位**（命名将调端点）：选区 `/recognize`、校对 `/work/save`+`/verify`、助手
  `/assistant/analyze`+`/assistant/ask`、答疑 `/analyze`+`/claude/chat`；真交互在 v0.4.1a→v0.4.4a 落地
  （对应原 v0.3.1a–v0.3.4a 计划）。Excalidraw 第二引擎本步先禁用（需 Vite 专门配置），下个版本恢复；
  原生引擎完整可用。
- **旧静态站归档**：`web/{index,signin,signup,demo_sellection,demo_exam,demo_standalone}.html` **整组**
  `git mv` 到 `web/legacyweb/`（彼此相对链接保持可用、可独立运行；不删除，遵迁移规则）。其余页（登录 /
  选题 / 批量考试）后续增量迁移到 `frontend/`。
- **验收（运行—观测）**：`npm install`（68 包）→ `tsc --noEmit` 0 错 → `vite build` 成功（46 模块、
  `dist/` 产出）→ `vite preview` 200；**真链路** headless Chrome 渲染：React 挂载、`/practice/next` 拉到
  真题（标题「化归转化」非加载占位）、白板 / canvas / 三动作渲染、思维类型下拉由 `/tags/catalogue` 填充。

## v0.3.0b — 题目屏清理（用户反馈）：移除旧「Solve with Voice or Text」侧栏 + 去重 AI 出题 + 来源样式

按用户反馈精修题目屏，使其贴近线框图 ①（`docs/DEVELOPMENT_PLAN.md` §C₀）。仅前端、不动后端：

- **移除「Solve with Voice or Text」侧栏**（`web/demo_standalone.html`）：删掉旧单页解题器
  （文本/语音输入 🎤、SymPy/Manim/AI 方法下拉、▶ Start）。白板改为整宽。其能力并入引导式流程
  （OCR → 校对 → 判分 / 逐行分析 / 答疑）。
- **不回归地保住作答链路**：白板 `📤 Submit → OCR → analyze` 仍可用——把 `#mathInput` 降级为
  隐藏中继、`#result` 移到白板下方整宽显示；该内联路径将于 v0.3.2a 正式并入「提交→选区→校对」。
- **去重「AI 出题」**：删除题卡右上角 `✨ AI 出题` 按钮（与来源下拉的「1·AI 生成」重复）；
  `🎲 换一题` 改为**按当前来源**换题（沿用 `loadProblem` 的 `source` 透传）。`loadProblem` 对
  已删除的 `ai-gen-btn` 全部 `if (aiBtn)` 守卫，无报错。
- **来源选择器改样式**：题卡新增「Problem」栏——左侧 `🏷 显示标签` 改为胶囊按钮、右侧「来源」
  下拉，顶部细分隔线与练习控件一致；来源顺序更正为 **1 AI 生成 / 2 学科网 / 3 后台题库**（原 1/3/2 乱序）。
- **验收**：4 段内联 `<script>` 语法校验 0 错；无悬挂未守卫引用；白板 / 双引擎 / 全屏 / 出题 /
  练习控制 / `?exam=1` 不回归。

## v0.3.0a — 学生端「试卷测试」多屏重构（第 1 步）：五屏路由骨架 + 配置驱动题目屏

启动 v0.3 学生端主链路 UX 大改（大迭代 +1）。本步**只搭骨架、不动内核**：共识判分 /
苏式护栏 / 诊断 / 记忆 / 标签自进化一律保留。详见 `docs/DEVELOPMENT_PLAN.md`
§「v0.3 学生端『试卷测试』多屏交互重构」§G·v0.3.0a。

- **legacy 备份（§F 第 0 步）**：整体改写前先把当前页复制到
  `web/legacy/demo_standalone.v0.2.html`（只读、非生产路径，**不删除**）。
- **五屏路由骨架（`web/demo_standalone.html`）**：单页改造为 5 个 `<section class="screen">`
  （`#screen-problem / -select / -check / -assistant / -ask`），仅 `.active` 可见；新增通用
  路由 `navTo / navBack / navHome` + **返回栈**（验收：五屏可互跳、返回栈正确）。
- **配置驱动（落实用户「动态前端、可更改、不要死成 html」）**：屏幕 / 来源 / 动作分别由
  `SCREEN_DEFS`、`SOURCES`、`PROBLEM_ACTIONS` 配置表驱动；屏 2–5 的页面体由
  `renderSelectScreen / renderCheckScreen / renderAssistantScreen / renderAskScreen` 在进屏时
  **动态生成**（非手写静态标签），改流程只需改配置。
- **题目屏接线（C1）**：① 出题来源下拉（1 AI 生成 / 2 学科网 / 3 题库）→ 直接映射
  `GET /practice/next?source=ai|xueke|bank`（`loadProblem` 增 `source` 透传，默认 `bank`，
  开机不触发 AI 调用）；②「🏷 显示标签」开关（默认隐藏知识点 / 思维类型标签，点按显隐）；
  ③ 底部三动作行：`提交`（二次确认）/ `提问·不会做` / `AI 助手`，按 §B 桩接路由
  （提交·助手 → 选区屏，提问 → 答疑屏）。
- **屏 2–5 为诚实占位**：各自标注将调用的端点（`/recognize`、`/work/save`、`/verify`、
  `/assistant/analyze`、`/analyze`、`/claude/chat`），交互在 v0.3.1a→v0.3.4a 逐步落地。
- **不回归**：原白板 / 双引擎 / 全屏 / 出题 / 练习控制 / 考试模式（`?exam=1`）全部保留可用；
  4 段内联 `<script>` 语法校验通过（`node new Function` 0 错）。

## v0.2.5a — 核心后端三管线架构补全：学科网题源 + 题号规范 + AI 免责声明 + 笔画直传 AI

把用户的「核心后端架构」草图补全并落地为可运行增量（出题 / 作答 / AI 反馈三管线）。
文档：`docs/DEVELOPMENT_PLAN.md` 新增「★ 核心后端三管线架构」节（分层结构图 + 状态机流程图 +
题号规范 + 差距清单）。代码落地差距清单 4 项：

- **题号规范（`exam.py`）**：题目 id 从随机 `q-<hex>` 改为**结构化** `{来源}-{YYYYMMDD}-{SEQ}`
  （如 `300-20250416-000123`）。来源码 `300`=AI / `200`=学科网 / `100`=模板种子 / `000`=其它；
  `SEQ` 为全局自增（`meta` 表存计数器，补零 6 位，越界自然加长）。`save_question` 按 `q["source"]`
  在事务内分配号；DB 随机取题**复用原号不新建**。旧 `q-<hex>` 行与新格式共存，读取无格式假设。
- **学科网题源（`main.XuekeProvider` + `config.XUEKE_*`）**：出题「三选一」补上第三条
  （AI 生成 / 数据库随机 / **学科网 API 按标签**）。`XuekeProvider.get_by_tag` 拉取→归一化→存库
  （得 `200-…` 号）；`_normalize` 容忍多种字段拼写（content/statement/stem、answer/solution…）。
  `/practice/next?source=xueke&tag=X` 接线；未配 `.env` 网关时**优雅降级**到本地题库。
- **AI 免责声明（`_bank_to_card`）**：题卡新增 `disclaimer` 字段，题面下方（**不计入题面**）显示
  「本题由 AI 生成，请注意甄别。」（`ai` 源）/「本题来自学科网题库。」（`xueke` 源）；其它源为 `null`。
  `/practice/next` 响应同时带 `from_source`（ai/bank/xueke）便于前端展示题源。
- **笔画直传 AI（`recognize.recognize_via_claude` + `/recognize?method=`）**：作答识别补上路径 2
  ——把白板 PNG 直接交给 **Claude 视觉**（Messages API image block），与路径 1（nex 专用 OCR）并存。
  `method=nex`（默认）/ `claude` / `auto`（nex 失败回退 Claude）；与现有 `{text,status}` 契约一致，
  未配网关时回退 mock。
- **验收（离线）**：`py -3.12` 导入全部模块通过；`exam.save_question` 三种来源分别生成
  `300-/100-/000-` 号且 SEQ 递增；学科网/Claude 视觉未配时 `available()` 返回 False 并降级。
  真链路（学科网、Claude 视觉）需 `.env` 填入对应网关后验证。

## v0.2.4a — 批量出题 `/exam/generate` 迁移到标签感知路径（逻辑类型 + 难度 + 自演化）

把 25 题批量出题从「只打知识点」升级到与单题路径一致的**标签感知 + 自演化**链路：
- **`main._ai_questions_for_dimension` 重写**：知识点仍作 **primary**（保证 `/exam/generate` 的 **25/25
  覆盖契约**不变），每题另挂 **1–3 个逻辑思维类型**标签 + **开放无上限难度**；模型提的 `new_tags`
  当场注册进 `tags.db`（`source='ai'`）并附到这道题（自演化循环）；所用标签 `bump_usage`。
  顺手**修掉局部变量 `tags` 遮蔽 `tags` 模块**的隐患（改名 `qtags`/`tag_names`）。
- **`prompts.build_exam_prompt`**：加 `logic_tags` 入参；去掉"适合小学生"上限，写入**好题观**
  （多思维/多知识点融合、题干短而内容丰富）与**按真正解出难度校准**；输出格式新增
  `logic_tags`（1–3 个）/`new_tags`/`difficulty` 字段 + 逻辑思维类型可选清单。
- **`claude_service.complete` 加 `timeout` 入参**（根因修复）：单次批量要一口气生成十余题，
  默认 30s 聊天超时会让整批**静默超时退化成模板**；批量路径传 `timeout=180` + **重试 3 次** +
  `max_tokens`→6000 + 每维度独立 `session_id`，避免第二维度被前一维度拖垮。
- **实测**：真链路 `POST /exam/generate?grade=4` → provider=claude、**coverage 25/25**、
  **25/25 题均为 AI 出**且都带逻辑标签（多为 **3 个融合**）+ 整数难度（分布 5–8）；
  题目明显变难（四位数推断、交错求和、最大公因数/最小公倍数计数、停车计费分段、奇数和归纳…）。

## v0.2.3b — 出题质量：更难、跨学段、难度校准、深度类型自扩充（用户反馈）

针对用户反馈"难度分配不对/题目太简单/初高中内容都没有/可让 AI 扩充有深度的类型"：
- **不再silent 退化成模板**（根因）：生成的 JSON 里 LaTeX 单反斜杠（`\times`/`\quad`/`\frac`）是非法
  JSON 转义，曾让**最难的题被丢弃**、`practice_next` 静默回退到小学模板题。新增 `_repair_json_backslashes`
  把非法反斜杠转义后重解析；`_ai_one_question` 失败**重试 3 次** + `max_tokens` 1500→2000。生成成功率
  实测 3/5 → **5/5**。
- **跨学段词表**：`tags.py` 新增 `ADVANCED_KNOWLEDGE` + `seed_advanced_knowledge()`（启动幂等播种、
  尊重删除）——平面几何/解析几何/三角函数/函数/数列/概率/统计/集合/向量/导数… 让出题覆盖 K-12+。
- **难度校准 + 真难**：`prompts` 去掉"适合小学生"上限，要求**以"真正解出有多难"为准**（步骤/陷阱/
  抽象/思维难度），诚实自检（一步可答必须下调）；中高难度须多步、有思维含量；目标难度要靠真正加难达成，
  不许把简单题硬标高分。
- **深度类型自扩充**：`new_tags` 指南改为**鼓励**在现有库不足时新增**有深度**的逻辑思维类型
  （构造法/反证法/不变量/对称性/极端原理/递推/母函数…）。
- **实测**：难度 8–9 真出二次方程判别式、|x²−2x−3|=k 三根、抛物线焦点弦、方程组+不等式等初高中题；
  难度 9–12 时 AI 自增 `不变量构造`/`函数方程代入法`/`裂项相消构造` 等深度类型（14→17）。

## v0.2.3a — 前端呈现逻辑思维类型 + 难度（目标可见化）

- **前端 `demo_standalone.html`**：题卡上**逻辑思维类型标签**用 🧠 + 紫色 chip 与知识点标签**视觉区分**；
  难度 chip 已显示「难度 N」。新增**定向练习控件**：「🧠 思维类型」下拉（从 `/tags/catalogue` 实时拉取
  逻辑类型，按族分组）+「难度」下拉（1–10 锚点 + 11+ 竞赛/研究级）+「🎯 按要求出题」按钮 →
  按所选逻辑类型/难度让 AI 出题。考试模式下隐藏这些控件。
- **后端**：`/practice/next` 增 `?difficulty=N`（按目标难度出题，开放无上限）；`_ai_one_question` 与
  `prompts.build_tagged_generation_prompt` 增 `target_difficulty`，把目标难度写入出题指令。
- **验证**：真链路 `?focus_logic=分类讨论&difficulty=6` → 生成"比 3:5 求另一个数的所有可能"题（主标签
  `分类讨论`、难度 6）；**headless Chrome** 实渲染确认控件存在、思维类型下拉按 5 族填充、难度下拉填充、
  逻辑 chip（🧠）渲染。
- **未做（更大改动，已记）**：本页基于白板/聊天，未接 `/verify`，故诊断闭环（答题→画像→自适应）尚未在
  此页 UI 串起；`demo_exam` 的逻辑类型/难度筛选留待批量出题迁移后。

## v0.2.2b — 难度刻度：无上限 + 结合思维难度（用户定向）

- **用户定向①**：难度**无固定上限**，可按实际设置——锚点 **1=认识数字**、**10=大学通识课**，更难可超过 10。
- **用户定向②**：难度**结合"逻辑思维难度"**给出，而非仅看知识内容层级。
- **`exam.py`**：`DIFFICULTY_LEVELS` 重锚为 1–10（原 0–9），新增 `DIFFICULTY_MIN=1`；`difficulty_label`
  对 >10 返回"竞赛/研究级（难度 N）"，不再"越界即空"。注释言明难度=知识层级⊕思维难度。
- **`main.py`**：生成时难度钳制改为 `max(DIFFICULTY_MIN, int)`（**仅设下限、不封顶**）。
- **`prompts.py`**：出题指令要求 AI **综合知识内容层级与逻辑思维难度**给分；所选逻辑类型越难可上调，
  特别难可超过 10。
- **验证**：离线 `difficulty_label` 1/10/13/0 行为符合；提示词含"无上限/结合思维难度/认识数字/重点训练"。

## v0.2.2a — 逻辑缺陷诊断 + 按薄弱逻辑类型自适应出题（目标 5/6）

- **方向**：找出学生（与 AI 自身）**薄弱的逻辑思维类型**，据此**针对性出题**——而非按知识点刷题。
- **新增 `backend/app/diagnosis.py`（`data/diagnosis.db`）**：两类信号，均按动态标签归集——
  - **学生**：`tag_outcomes(session_id, tag, kind, attempts, successes)`，由 `/verify` 判分喂入；
    `student_profile` 给每标签正确率 + **薄弱逻辑类型排名**（仅 logic 类、正确率 < 0.6 计为缺陷）；
    `weak_logic_tags` 供自适应出题取最弱项。
  - **AI 自身**：`self_signals(tag, graded, agreement_sum, low_agreement)`——记录本机**多路共识的一致度**，
    一致度低（< 0.67）即该类型自身推理薄弱；`self_profile` 按**分歧度**（1−平均一致度）排名（目标 6 自诊断种子）。
- **`main.py`**：`MathRequest` 增 `question_id`；`/verify` 判分后经 `_record_diagnosis` 按题目标签同时
  记录**学生结果**与 **AI 自一致度**；新增 `GET /diagnosis/{session_id}`（学生画像 + `suggested_focus`）、
  `GET /diagnosis/self`（AI 自画像）。`/practice/next` 增 `?focus_logic=X`（训练指定逻辑类型）与
  `?adaptive=<session>`（自动取该会话最弱逻辑类型出题）。`exam.get_question(id)` 供按题取标签。
- **`prompts.build_tagged_generation_prompt`** 增 `focus_logic`，把"重点训练某逻辑类型"写入出题指令。
- **验证**：离线（记录 1/3 正确→`逆向倒推` 判为薄弱、self 分歧度 0.6）；**真链路全闭环**——
  `?focus_logic=逆向倒推` 生成"糖果倒推"题（主标签 `逆向倒推`）→ `/verify` 答错→ `/diagnosis/{session}`
  报 `逆向倒推` 薄弱（suggested_focus）→ `?adaptive=<session>` 自动锁定 `逆向倒推` 再出题。

## v0.2.1a — 出题接入动态标签库（自演化标签循环）

- **方向**：让 AI 出题时**读取并生长** `tags.db`——按题打**逻辑思维类型 + 知识点**标签，并给 **0–9 难度**；
  现有标签**优先复用**，没有合适的就**新增标签**（`source='ai'`）并附到这道题上（自演化循环）。
- **`prompts.py`** 新增 `build_tagged_generation_prompt`：把**当前**词表（知识点 + 逻辑类型含 move/flaw）
  与难度刻度交给 AI，要求输出 `statement/latex/answer/knowledge_tags/logic_tags/new_tags/difficulty`。
- **`main.py`** `_ai_one_question` 重写为**标签感知**：从 `tags.db` 取词表 → 调 Claude → 注册 `new_tags`
  到标签库并附到该题 → 复用标签 `bump_usage` → 存题带逻辑/知识标签 + 难度。新增 `_question_tag_row`
  把标签名解析为 `question_tags` 行（逻辑→`逻辑思维类型`/族，知识→沿用 `exam` 维度映射）。`_bank_to_card`
  把整数难度渲染为「难度 N」。
- **`exam.py`**：`questions` 增 `difficulty INTEGER` 列（对旧库**安全迁移**，旧行 NULL）；`save_question`/
  `_assemble` 透传难度。
- **验证**：离线（迁移生效、提示词完整、`_question_tag_row` 解析、**monkeypatch 自演化分支**：新标签
  `极限思想` 入库[source=ai]并附到题、旧标签 usage+1、难度落库）；**真链路** `POST /practice/next?generate=1`
  生成「鸡兔同笼」并自动打标签 `假设调整`（主）+`初步代数思想`、难度 4、两标签 usage 均 +1。
- **范围**：仅单题生成路径（`/practice/next?generate=1`，前端在用）已接入；批量 `/exam/generate`（25 题）
  仍走旧硬编码目录，留待后续迁移。诊断（目标 5/6）仍未做。

## v0.2.0a — 动态、AI 自管理的标签库（独立数据库）

- **方向（用户定向）**：标签**不再固定遵循 `lesson/README.md`**——AI 可自行**新增**合适标签、
  **删除**任何已有标签（含 lesson 知识点）。标签存于**新的独立数据库**，与题库 `exams.db` 解耦。
- **新增 `backend/app/tags.py`（`data/tags.db`）**：单表 `tags`（`name` 唯一、`kind`、`parent`、
  `description`、`meta` JSON、`source` seed/ai/user、`active` 软删、`usage_count`）。API：
  - `add_tag`（按名幂等增/复活、回填缺省字段）、`list_tags`、`catalogue`（kind→parent→tags 分组视图）、
    `deactivate_tag` / `remove_tag(hard=)`（软/硬删，**无任何标签受保护**）、`bump_usage`、`count`。
  - `seed_from_catalogues()`：**仅首启**从 `exam.CATALOGUE`（25 知识点）+ `exam.LOGIC_CATALOGUE`
    （13 逻辑类型）播种；一旦有任何标签即 no-op → AI/用户的增删跨重启留存，绝不被重新播种覆盖。
- **`main.py`**：启动时 `tags.init_db()` + 首启播种；新增 `GET /tags`、`GET /tags/catalogue`、
  `POST /tags`（增/复活）、`DELETE /tags/{name}`（软删，`?hard=1` 硬删）。
- **定位变化**：`exam.py` 的硬编码目录自此降级为**初始种子**；播种后 `tags.db` 是标签词表的事实来源。
  出题/诊断接线仍为后续（将改为读 `tags.db` 而非硬编码目录）。
- **验证**：离线复核（播种 38=25+13、再播种 no-op、AI 增标签、软删 lesson 标签「货币」后不在 active
  列表但可见于 include_inactive、再增即复活、逻辑标签 meta 带 move/flaw）；**真 HTTP** 复核
  `GET /tags`（38）、`/tags/catalogue`（kinds=knowledge/logic）、`POST /tags` 新增、`DELETE /tags/货币` 软删。

## v0.1.1a — 前端练习题改由「题库 + AI 生成」驱动（替换外部 OpenTDB）

- **方向**：前端不再从外部 API（OpenTDB 英文趣味题）直接取题，改为从**本项目自有题库
  `exams.db`** 取题，空库时回退到**模板/AI 生成** —— 与产品（中文小学数学）和去符号化方向一致。
- **后端**：
  - `exam.py` 新增 `random_question(exclude_id)`（从既有题库随机取一题）、`seed_templates()`
    （库空时用 25 个模板题确定性填充，保证离线也有中文题）。
  - `main.py` 新增 `GET /practice/next`：**先取题库**，库空则播种模板再取；`?generate=1` 时若网关
    可用则**临时用 AI 生成一题**（失败回退题库/模板）。`_bank_to_card` 把题库题适配成前端题卡结构。
  - 旧 `/problems`·`/problems/random`（OpenTDB）保留为遗留接口，前端已不再使用。
- **前端 `demo_standalone.html`**：`loadProblem()` 改打 `/practice/next`；题卡渲染中文 `statement`/
  `latex` + 知识点/来源/难度 chip；新增「✨ AI 出题」按钮（带加载态）；副标题不再宣称 "symbolic
  reasoning"（已去符号化），改述多路共识 + 苏格拉底引导；按钮/提示文案中文化。
- **验证**：`exam.py` 导入自检 + 启动后端 `curl /practice/next` 取到中文题卡；**headless Chrome**
  实渲染 `demo_standalone.html` 确认题卡由 `/practice/next` 填充（标题/题面/标签 chip 均到位）。

## v0.1.0a — 逻辑思维类型标签体系（草案 + 代码基础）

- **新增 v2.0 核心差异点的数据模型**（`docs/LOGIC_TAXONOMY.md` + `backend/app/exam.py`）：
  - `DIM_LOGIC` + `LOGIC_CATALOGUE`：**13 个逻辑思维类型 / 5 族**，每类带「思维动作」+「学生逻辑
    缺陷诊断信号」，**与现有 25 知识点标签正交**。
  - `DIFFICULTY_LEVELS`：0–9 推理深度刻度（幼儿园 ↔ 大学），独立于年级/知识点。
  - 查询助手 `all_logic_tags` / `logic_tag_info` / `logic_tag_family` / `difficulty_label`。
- **纯增量、非破坏**：现有知识点出题/判分流程零改动（`all_tags()` 仍 25）。
- **分类为草案**，待用户审定；出题/诊断接线为后续步骤（见 `LOGIC_TAXONOMY.md` §4）。
- **验证**：`py -3.12` 导入自检 —— 13 类/5 族、知识点标签仍 25、越界难度返回 `''`。
