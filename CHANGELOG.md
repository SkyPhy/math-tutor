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
