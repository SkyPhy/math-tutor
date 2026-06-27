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
