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
