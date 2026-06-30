# 自演化 AI 数学教育系统 · 开发计划（蓝图对齐版）

> 依据：《Strategic Planning and Architectural Blueprint for Self-Evolving Autonomous Software Systems》
> 对象：本仓库现有代码库（`backend/app/` + `web/`）
> 性质：**新增文档，不覆盖任何现有文件**。本文件是路线图，不是对既有代码的改写。
> 版本：v1 · 2026-06-24

---

## 0. 文档目的

蓝图描述的是一个"自演化软件系统"的通用工程范式；而本仓库的实现，正是该蓝图在
**教育（Socratic 数学辅导）领域**的一个落地实例（蓝图脚注 7 即"Developing an AI
Math Solver"）。本计划做三件事：

1. **现状映射** —— 把蓝图的每一个支柱对到现有的具体文件 / 类 / 接口，标注"已实现 /
   部分 / 仅描述 / 缺失"。
2. **差距分析** —— 指出"数学辅导产品"与"自演化元系统"之间真正缺的部分。
3. **分阶段路线图** —— 给出可验证、可增量交付的演进路径，每一阶段都绑定到具体文件与
   验收标准。

> **★ 方向调整（2026-06-26，覆盖以下部分原则）：去符号化 · 全程 Claude 自主推理为正解。**
> SymPy 确定性验证自此被定性为**过渡性脚手架，目标彻底废止**——终局是 Claude 端到端自主
> 推理给出正解，不再依赖 CAS 当裁判。现阶段 SymPy 仅作复核安全网；随着**自我迭代推理**
> （多路独立生成 → 共识/择优 → 不一致再推理 → 收敛到最简正解）成熟到能自证正确，SymPy
> 验证逐步退役。本文中所有"SymPy 验证/锚点"描述均按此过渡方向理解。详见 §4「下一首要目标」。

贯穿原则（部分随上方方向调整）：

- ~~**SymPy 是确定性验证锚点**~~ → **过渡性脚手架，待彻底废止**；终局以**全程 Claude 自主推理**
  为正解，正确性由自我迭代/多路共识保障（而非 CAS 硬门）。
- **Socratic 约束不可绕过** —— 系统在架构上被禁止直接给出最终答案。
- **Compliance-by-Design** —— 策略在规划阶段就介入，而非事后过滤（SEPGA）。
- **生成与验证职责分离** —— 任何"自我修改"能力都必须接受独立验证（Zero-Trust）。

---

## 1. 现状映射：蓝图支柱 × 现有实现

| # | 蓝图支柱 | 现有实现 | 位置 | 状态 |
|---|---------|---------|------|------|
| 1 | 四层架构：前端 | 多页前端，nex-n2-pro 视觉 OCR 把手写转表达式 | `web/*.html`、`backend/recognize.py` | ✅ 已实现 |
| 2 | 四层架构：编排与逻辑层 | FastAPI 路由 + 会话状态 | `backend/main.py`（ALMAS Pipeline 注释）| 🟡 部分（缺"自演化触发器/监控环"）|
| 3 | 四层架构：认知处理层（复合 AI）| Claude 经 Anthropic 兼容网关 + SymPy 共同推理 | `backend/claude_service.py`、`config.py` | 🟡 部分（缺多模型 conductor/expert）|
| 4 | 四层架构：执行与验证层 | SymPy CAS 对**数学**确定性求解/校验 | `NeuroSymbolicEngine`（main.py） | 🟡 部分（无**代码**沙箱）|
| 5 | Data Manager（JSON 架构树）| `/architecture` 返回手写的元数据树 | `ArchitectureNode`、`@app.get("/architecture")` | 🟠 仅描述（静态、非自动从目录/AST 生成）|
| 6 | Blending Instructions（情境工程）| 把表达式+会话+动作编译成上下文 | `BlendingInstructions` 类 | 🟡 部分（用于提示词，未含"架构边界/不可变文件"）|
| 7 | Meta-Prompting（conductor/expert）| —— | —— | ❌ 缺失 |
| 8 | AST 变换（LibCST）+ SPA 自精炼环 | —— | —— | ❌ 缺失（系统尚不修改自身代码）|
| 9 | ALMAS 多智能体（Sprint/Supervisor/Summary/Control/Developer/Peer）| 六个 Agent 仅作为 `/architecture` 元数据 + 注释存在 | main.py `build_architecture_tree`、各处注释 | 🟠 仅描述（无真实编排）|
| 10 | 工作流拓扑（Router/Pipeline/Reflection/Parallelization）| `/analyze` 为线性硬编码流水线 | `analyze_math` | 🟠 仅描述 |
| 11 | 神经-符号集成（SymPy CAS 验证）| 方程求解、化简、验证、分类、步骤生成 | `NeuroSymbolicEngine.solve_with_steps` | ✅ 已实现，但**按新方向将退役**（放弃 SymPy，改大模型自行运算，见 §4 下一首要目标）|
| 12 | 递归智能 / 经验记忆 | 持久经验记忆、自适应难度（SQLite，跨重启留存）| `backend/app/memory.py::PersistentExperienceMemory`、`data/memory.db` | ✅ 已实现（2026-06-26；技能固化仍可深化）|
| 13 | SEPGA 策略治理 | 输入策略校验 + 罚分 | `PolicyEngine.evaluate` | 🟡 部分（作用于用户输入，未作用于"代码生成计划"）|
| 14 | 教学护栏（Socratic 约束）| 5 级提示、绝不直接给答案、Claude 系统提示强制 | `SocraticEngine`、`backend/prompts.py` | ✅ 已实现（强）|
| 15 | Lattice（护栏自演化 / 对抗）| —— | —— | ❌ 缺失 |
| 16 | Zero-Trust（生成与验证分权）| —— | —— | ❌ 缺失（无代码生成，故暂无需分权）|
| — | （附加）用户账户与持久化 | SQLite 账户 + 考试题库，PBKDF2、会话令牌、限速 | `auth.py`、`exam.py`、`data/*.db` | ✅ 已实现 |

**结论**：项目把蓝图中**面向用户的教学侧**（前端多模态、神经-符号验证、Socratic 护栏、
策略、经验记忆）做成了可运行的演示；而蓝图最具野心的**自演化软件工程侧**
（ALMAS 真编排、AST/SPA、meta-prompting、Lattice、零信任验证沙箱）目前是
**描述性的占位**。本计划即围绕"把占位变成可运行"展开。

---

## 2. 目标架构（四层）与代码对齐

```
┌──────────────────────────────────────────────────────────────────────┐
│ L1 前端 / 多模态交互层                                                 │
│   web/index・signin・signup・demo_sellection・demo_exam・demo_standalone │
│   手写 OCR(recognize.py→nex-n2-pro) · 白板(Canvas/Excalidraw) · MathJax │
├──────────────────────────────────────────────────────────────────────┤
│ L2 编排与逻辑层（FastAPI · main.py）                                   │
│   会话状态 · 路由 · ★自演化触发器(待建) · BlendingInstructions          │
├──────────────────────────────────────────────────────────────────────┤
│ L3 认知处理层（复合 AI）                                               │
│   Claude(claude_service) ＋ SymPy(NeuroSymbolicEngine) ＋ ★ALMAS(待建)  │
├──────────────────────────────────────────────────────────────────────┤
│ L4 执行与验证层                                                        │
│   SymPy 确定性验证(已有)（待彻底废止，全程 Claude 自行推理方才为正解） ＋ ★代码沙箱/AST/SPA(待建) ＋ ★Zero-Trust 分权  │
├──────────────────────────────────────────────────────────────────────┤
│ 横切：SEPGA 策略治理(PolicyEngine) · 经验记忆(ExperienceMemory) ·       │
│        Socratic 护栏(SocraticEngine) · ★Lattice 护栏演化(待建)          │
└──────────────────────────────────────────────────────────────────────┘
★ = 蓝图要求但当前缺失/仅描述
```

---

## 3. 差距分析（按"价值/风险"排序）

1. **经验记忆不持久** —— `ExperienceMemory` 在进程内字典中，重启即失。蓝图要求"durable
   repository memory"（如 AGENTS.md 式状态文件）。→ 现已有 SQLite 基础设施，迁移成本低，
   价值高。**优先。**
2. **策略只管输入、不管"计划"** —— `PolicyEngine` 校验用户表达式，但蓝图的 SEPGA 是对
   **Agent 的行动计划**用 Constrained MDP 罚分剪枝。当引入任何自动化动作时必须补齐。
3. **Data Manager 是静态手写树** —— 应能从真实目录 + AST 自动生成 JSON 元数据树，
   否则"让 AI 理解自身架构"无从谈起。
4. **ALMAS / 工作流拓扑仅是文字** —— `/analyze` 是线性硬编码。要落地 Router/Pipeline/
   Reflection/Voting，需要一个真正的多智能体编排器。
5. **无自我代码修改能力** —— AST(LibCST)+SPA 自精炼环 + 零信任验证沙箱整套缺失；这是
   蓝图皇冠，但风险最高，应**最后**且**默认 dry-run**。
6. **无 Lattice 对抗护栏演化** —— 静态护栏易被绕过；需要周期性"自我攻击 → 补丁 → 验证"。
7. **网关性能/稳定性** —— `computinger.com` 时延高且抖动大（曾见 5s–150s），任何多智能体/
   多轮调用都会放大此问题，需要超时、断路器、缓存与降级（部分已在 `claude_service` 具备）。

---

## 4. 分阶段开发计划

> 每阶段：**目标 → 交付物（绑定文件）→ 验收标准（可运行观测）**。
> 遵循仓库既有习惯：每个特性都用"运行应用 + 观测真实行为"验证（headless 浏览器 / curl）。

### ★ 下一首要目标 · 去符号化：全程 Claude 自主推理为正解（2026-06-26 立项｜2026-06-27 推进中）
> 这是**当前最高优先级**的方向，凌驾于下方按蓝图编号的阶段之上。阶段 0–1 已完成；
> 阶段 2+ 的蓝图工作继续有效，但**本目标先行**。
>
> **进度（2026-06-27）**：下方分步落地的 **第 1、2 步已落地，并已通过真链路（密钥到位）验收**——
> 新增多路共识推理器 `backend/app/reasoner.py`，并已让 `/verify` 判分**以共识为正解来源**；SymPy 降级为
> **离线兜底 + 非权威交叉校验**（`judged_by` = `consensus(k/n)` 或兜底 `sympy-fallback`）。
> **第 3 步仍未做**：`NeuroSymbolicEngine` 尚未迁入 `legacy/`（它仍为 `/analyze`·`/hint`·
> `/animate`·`/plot` 提供 latex/分类/步骤渲染，属非正确性用途，留待整体迁移）。

- **目标（用户定向）**：**放弃 SymPy，换为大模型自行运算**。`/verify`、`/analyze`、`/hint` 的
  求解与判分由 **Claude 端到端自主完成**，SymPy 确定性验证从主链路**彻底移除**（代码降级为
  `legacy/` 对照工具）。正确性靠 **Claude 自身审慎推理 + 自我迭代/多路共识**，而非 CAS：同一题
  多路独立计算 → 互检/投票 → 不一致再算 → 收敛到一致且**最简、最优、最妙**的正解。
- **为什么**：SymPy 只能覆盖小学课标的一小部分（方程/化简/算术），几何/统计/量与计量/应用题
  本就只能靠 Claude。把 CAS 钉为"唯一事实来源"既不全面也违背产品方向；终局是可信的自主推理。
- **诚实的风险提示（必读）**：LLM 单次算术会出错。**所以"放弃 SymPy"必须与"自我迭代/多路共识"
  同时落地**——后者是替代 CAS 的正确性来源。若只删 SymPy 而不上共识，等于把正确性押在单次生成，
  是退步。Socratic 护栏、策略门禁、优雅降级**不受影响，继续强制**。
- **分步落地（每步可独立验收、可回退）**：
  1. **✅ 自我迭代推理器**（`backend/app/reasoner.py`，已新增）：同一题 **N 路独立生成**（temperature
     抖动 0.2/0.6/0.9 + 不同提示视角 `_ANGLES`）→ 结构化抽取每路的最终答案与步骤 → **多数共识**定
     答案、置信度/最简步数定讲解。答案比较用**自带的去 SymPy 数值归一器**（`fractions`+`ast`，
     `1/2`=`0.5`=`50%`）。无网关 / 少于 2 路可解析时返回"未判定"，优雅降级。
  2. **✅ 接管判分（`/verify`）**：`_check_student_answer` 已改为**共识优先**——`reasoner_engine.grade`
     给出 `correct`/`agreement`/`ground_truth`；`/verify` 暴露 `judged_by`（如 `consensus(3/3)`）、
     `agreement`、`votes_label`。SymPy 仅在共识不可用/分歧时作**兜底**（`sympy-fallback`）。原
     单次 `claude+sympy` 判分簇（`_claude_grade`/`_eval_closed_form`/`build_grade_prompt`）**已删除**。
     `/analyze`·`/hint` 暂未切换（它们生成提示而非判分，Claude 已可自行运算，留待第 3 步统一处理）。
  3. **🟡 移除 SymPy 主链路（判分部分已落地 2026-06-27）**：
     - **✅ 3a 判分 SymPy 退役到 `app/legacy/`**：原 `_sympy_grade` + `_compare_answer` 已从 `main.py`
       移入 `backend/app/legacy/sympy_grader.py`（新建 `app.legacy` 包），成为**明确标注的非权威离线兜底**。
       `_check_student_answer` 经依赖注入（把 `NeuroSymbolicEngine.solve_with_steps` 作为 `solver` 传入）
       调用它，避免回指 `main` 的循环导入。**主判分路径不再于 `main.py` 内含 SymPy 判分代码**——共识为唯一
       事实来源，SymPy 仅在网关不可用/分歧时兜底（行为不变，已离线 + 真 HTTP 验收无回归）。
     - **☐ 3b 渲染引擎 `NeuroSymbolicEngine` 暂留 `main.py`**：仍为 `/analyze`·`/hint`·`/animate`·`/plot`
       提供 latex/分类/步骤渲染（**非正确性用途**），整体迁 `app/legacy/` 属更大改动，留待渲染侧一并迁移。
- **交付物**：✅ `reasoner.py`（多路推理 + 共识 + 择简）、✅ `prompts.build_solve_prompt`（每路输出
  "答案 + 步骤 + 自评置信度"）、✅ `/verify` 暴露 `agreement`/`votes_label`；✅ 判分 SymPy 退役到
  `app/legacy/sympy_grader.py`（依赖注入、无循环导入）；☐ 渲染引擎 `NeuroSymbolicEngine` 整体退役。
- **验收（运行观测）**：同一应用题，多路推理收敛到 1 个正解并附"为何最简"理由；改高难度题能看到
  "分歧→再推理→收敛"；主链路不再调用 SymPy。**注意：真实验证需 `.env`/网关在位**（多路调用，
  注意 §5 网关并发/缓存约束）。
  - **✅ 已验收（2026-06-27，密钥到位后跑真链路）**：① 应用题"5+7"多路 **3/3 共识** 得 12；
    ② `reasoner_engine.grade` 对算式 `3x-5=16`：学生答 `7`→`correct=True`、答 `5`→`correct=False`，
    均 `judged_by=consensus(3/3)`、`ground_truth=7`；③ 较难的两管注水题（分数解）**4/4 共识** 得 `24/5`，
    去 SymPy 归一器正确处理分数答案；④ **`POST /verify` 真 HTTP**（UTF-8 urllib，避开 Windows curl
    中文乱码坑）对 `2x+4=10`：答 `3`→`answer_correct=True`、答 `4`→`False`，响应
    `judged_by=consensus`、`votes_label=consensus(3/3)`——判分确经多路共识、**未走 SymPy 兜底**。
    时延：3 路顺序约 10s、4 路约 25s（网关当时健康；顺序调用，未触发 §5 并发坑）。

---

### ★ v2.0 愿景 → 现状映射与差距（2026-06-27 录入；源：`AI辅助math tutor最终目标.txt` 草案）

> 用户的 v2.0 北极星愿景（10 条 + 一条核心诉求）已整理成结构化草案。本节把它逐条对到**现有代码/状态**，
> 标注差距，并与下方蓝图阶段挂钩，便于把"愿景"落成"可验收增量"。**核心诉求**（最高权重）：
> **按「难度」+「逻辑思维（解决问题）类型」标签分类与训练，从解决学生逻辑问题出发——而非传统按知识点/题型刷题。**

| v2.0 目标 | 现状 | 位置 | 差距 / 备注 |
|---|---|---|---|
| 1 苏格拉底不直接给答案 + 答案入库 | ✅ 强 | `SocraticEngine`、`prompts.py`、`memory.py` | 已具备；答案已可入经验记忆 |
| 2 自出题 / 难度可调 / 按缺陷出题 | 🟡 部分 | `exam.py`、`memory.py` 自适应 | 难度仅按 `success_rate` 调；**未按逻辑类型/缺陷**出题；无"幼儿园↔大学"跨度 |
| 3 逻辑校验（自身/学生答案对错） | 🟡 部分 | `reasoner.py` 多路共识判分 | 已真链路验收；可继续扩到 `/analyze`·`/hint` |
| 4 析题 + 引导 + 方法**简洁最优** | 🟡 部分 | `SocraticEngine`、`reasoner` 择最简步 | 引导已有；"最优/最妙"尚无形式化度量 |
| 5 诊断**自身/学生逻辑缺陷**并自我优化 | ❌ 缺（核心差异点）| — | 对应蓝图 §阶段5 SPA 自精炼 / §阶段6 Lattice |
| 6 诊断**自身/学生逻辑不完备/可优化**并自我优化 | ❌ 缺（核心差异点）| — | 同上 |
| 7 接纳**学生**更优解并在其上改进自身 | ❌ 缺 | `memory.py`（基础在）| 需"解法采纳/固化（skills）"机制 |
| 8 自我发现更优解并改进自身 | ❌ 缺 | `reasoner.py`（可作种子）| 多路共识已会择最简，可作"更优解"发现的起点 |
| 9 题库自动推荐 / 自动优化解答 | ❌ 缺 | `exam.py`（题库在）| — |
| 10 形象化（**Manim**）讲解，多选项 | 🟠 占位 | `ManimAnimator`（模板，非真渲染）| 需真 Manim 代码生成；风格参照 Brilliant |
| **核心诉求** 按**逻辑思维类型**标签分类 | 🟡 **草案已立**（待接线）| `docs/LOGIC_TAXONOMY.md` + `exam.py::LOGIC_CATALOGUE` | 已落**正交**于 25 知识点的逻辑思维类型维度（13 类/5 族）+ 0–9 难度刻度，纯增量未改现有流程；**出题/诊断接线待定** |

**落地次序建议（把愿景接到下方蓝图阶段）：**
1. **核心诉求先行**：设计"逻辑思维/解决问题类型"标签法（与现 25 知识点标签正交、可并存），
   作为出题/诊断/推荐的新主键。这是 v2.0 与传统刷题平台的根本分野，应优先立项。
   **✅ 草案已落地（2026-06-27）**：见 `docs/LOGIC_TAXONOMY.md` + `exam.py`（`DIM_LOGIC`/
   `LOGIC_CATALOGUE` 13 类·5 族 + `DIFFICULTY_LEVELS` 0–9），纯增量、可导入自检；分类待用户审定，
   出题/诊断接线为下一步。
2. **目标 3 已达成**：多路共识判分（本节上方）已交付逻辑校验；其"多路分歧"信号天然可作
   **目标 5/6（逻辑缺陷/不完备诊断）** 的种子——分歧出现处往往就是推理薄弱处。
3. **目标 5–8（自/生诊断 + 自我进化）** 对应蓝图 §阶段3（多智能体编排：Reflection/Voting）、
   §阶段5（SPA 自精炼，默认 dry-run）、§阶段6（Lattice）；风险最高，**务必在策略治理（阶段4）就绪后**再推进。
4. **目标 10（Manim 真生成）** 可独立推进、风险低，作为面向学生的高价值演示增量。

> 注：本映射是规划性陈述；任何一条落地前请以"运行—观测"复核当时真实代码（代码是唯一事实来源）。

---

### ★ 核心后端三管线架构（2026-06-30 录入；源：用户架构草图 · 已补全）

> 用户给出的「核心后端架构」草图（出题 / 作答 / AI 反馈三条管线）经补全后录入本计划，作为
> 面向学生侧主链路的**结构总图**。老师 / 家长侧暂未开发。`★` = 用户新设计、**待实现**；
> 其余为现有代码已具备。本节末尾的「差距清单」中的 4 项已立项落地（见 CHANGELOG `v0.2.5a`）。

#### A. 分层结构图（三管线 × 6 层）

```text
                     【学生端 · 老师/家长端暂未开发】
┌──┬──────────────────────────────────────────────────────────────────────┐
│1 │                          学生输入(选知识点 / 白板作答 / submit)        │
├──┼───────────────────────┬───────────────────────┬──────────────────────┤
│2 │                            网页前端(React + P5.js 白板)               │
├──┼───────────────────────┼───────────────────────┼──────────────────────┤
│  │      ① 出题管线         │      ② 作答管线         │     ③ AI 反馈管线     │
├──┼───────────────────────┼───────────────────────┼──────────────────────┤
│3 │   题目传输层            │    作答传输层           │    AI 反馈层          │
│4 │   前后端链接(REST)     │    前后端链接(REST)    │    前后端链接(REST)  │
│  │   /practice/next        │    /recognize          │    /verify /hint     │
│  │   /exam/generate        │    (上传白板 PNG/笔画) │    /analyze /chat    │
├──┼───────────────────────┼───────────────────────┼──────────────────────┤
│5 │ 后台出题(三选一):     │ 笔画→文字 二选一:      │ AI 处理 / 分析 / 甄别 │
│  │  · AI 生成(Claude)    │  1. 渲染成图片 → nex   │  · 苏格拉底分级提示    │
│  │  · 数据库按标签随机     │     OCR → latex+md     │    (0–4 级,不给答案) │
│  │  · 学科网 API 按标签★  │  2. 笔画直传 AI 识字★  │  · 策略引擎 SEPGA 守门 │
├──┼───────────────────────┼───────────────────────┼──────────────────────┤
│6 │ 持久化 & 编号(本层补全)│ OCR 网关 & 预处理       │ 判定 & 诊断 & 记忆     │
│  │  · exams.db 题库        │  · nex-n2-pro 视觉模型  │  · 多路共识=真值源     │
│  │  · tags.db 自进化标签   │  · 图像裁剪/增粗/放大   │    (reasoner.py)      │
│  │  · 题号分配(300/200…) │  · 状态:ok/empty/     │  · SymPy 离线兜底      │
│  │  · 模板兜底(离线可跑) │    timeout/error       │  · diagnosis.db 缺陷诊断│
│  │                        │                        │  · memory.db 经验记忆  │
└──┴───────────────────────┴───────────────────────┴──────────────────────┘
                                                       ★ = 用户新设计,待实现
```

#### B. 后端流程图（状态机记法）

```text
// in <state> 表示可自跳转;  if <cond ? {s1}:{s2}> 真→s1,假→s2

<选知识点>
   选定知识点标签(读 tags.db,可多选;支持 知识维 × 逻辑思维维 × 难度)
        │
        ▼
<选出题方式>  ← 用户选择,或用默认值
   if <方式 == AI生成 ?
        {走 出题·AI} :
   if <方式 == 数据库 ?
        {走 出题·DB随机} :
        {走 出题·学科网★} >>
        │
   ┌────┴───────────────┬────────────────────────┐
   ▼                    ▼                         ▼
<出题·AI>            <出题·DB随机>             <出题·学科网★>
 Claude 按标签生成    exams.db 按标签随机取      学科网 API 按标签拉取
 →写回新标签到 tags   (复用已有题号,不新建)    →归一化成 Problem
 →分配题号 300+…     ─────────────┐            →分配题号 200+…
 →存 exams.db        if <取到题? │ {返回}      →存 exams.db
   ↑ if <Claude挂?>  : {降级到模板兜底}>        ↑ if <API挂?>
   {降级到模板兜底}                              {降级到 DB随机/模板}
        │                    │                         │
        └────────────────────┴─────────────────────────┘
                              ▼
            <题目出屏>  题面下方追加免责声明★(不计入题面):
                       「本题由 AI 生成,请注意甄别。」(仅 300 来源)
                              │
                              ▼
            <学生作答>  in <学生作答>  ← 白板可全屏,可反复涂改
               按 submit 提交笔画/图片
                              │
                              ▼
            <识别作答>  if <笔画直传AI★ ?
                          {笔画→AI(Claude视觉)→文字} :
                          {渲染PNG→nex OCR→latex+markdown} >>
               if <识别状态==ok ? {继续} : {提示重写, 回 <学生作答>} >>
                              │
                              ▼
            <AI 判定>  reasoner.grade():3~4 路独立解题 + 共识投票
               if <共识达成? {correct=真值} :
                  if <SymPy可判? {SymPy兜底} : {存疑, 转人工/提示}> >>
                              │
                              ▼
            <反馈 & 沉淀>(并行)
               · 对 → 进阶 / 错 → 苏格拉底 0–4 级提示(永不直给答案)
               · 写 diagnosis.db:学生该逻辑类型 成功率(<0.6=弱项)
               · 写 diagnosis.db:AI 自身该标签 共识一致度(<0.67=自身薄弱)
               · 写 memory.db:成功率 / 是否需更多引导 / 是否进阶
                              │
                              ▼
            <下一题>  if <开启自适应? {按最弱逻辑类型定向出题, 回<出题方式>} :
                                       {回<选知识点>}>
```

#### C. 题目编号规范（用户规则细化为可解析格式）

用户规则：`AI=300`、`学科网=200`，后接 `时间(YYYYMMDD)` + `题号(1→∞)`。直接拼接有歧义，
故细化为**带分隔、可排序、可解析**格式，并补齐缺的来源码：

| 来源码 | 含义 | 何时分配新号 |
|:---:|---|---|
| `300` | AI 生成(Claude) | 每次新生成 |
| `200` | 学科网 API | 每次拉取入库 |
| `100` | 本地模板/种子 | 首次播种 |
| `000` | 其它/未知来源 | 兜底 |
| —   | 数据库按标签随机 | **不新建**，复用原题号 |

**格式**：`{来源}-{YYYYMMDD}-{SEQ}`，例 `300-20250416-000123`
- `SEQ` = 全局自增序列（`1→∞`，补零 6 位便于排序；越界自然加长，符合"到无穷"）。
- 排序天然按"来源→日期→序号"；一眼可辨题源。落地于 `exam.save_question`（meta 表存计数器）。

#### D. 现状 vs 用户设计：差距清单（4 项，已立项）

| # | 用户设计 | 落地点 | 状态 |
|:--:|---|---|---|
| 1 | **学科网 API** 按标签取题 | `main.XuekeProvider` + `config.XUEKE_*`（替代占位的 `OpenTDBProvider`）| ✅ 标量(网关待配) |
| 2 | **题号** `300/200+日期+序号` | `exam.save_question` / `exam._make_id` | ✅ 已落地 |
| 3 | **AI 免责声明**（题面下方，不计入题面）| 出题响应 `disclaimer` 字段（仅 `300` 来源）| ✅ 已落地 |
| 4 | **笔画直传 AI** 识字（路径2）| `recognize.recognize_via_claude` + `/recognize?method=` | ✅ 已落地(网关待配) |

> 「标量(网关待配)」= 代码已就绪并优雅降级，待 `.env` 填入对应网关地址/密钥后即真链路可用。

---

### ★ v0.3 学生端「试卷测试」多屏交互重构（2026-06-30 立项 · 规划稿；源：用户前端功能草图 · 已补全）

> **⟳ 平台变更（2026-06-30，v0.4 起执行）**：用户定向「html 过时且不便维护，改为 nodejs 维护，
> 直接重构」。本节的五屏设计**不变**，但实现从静态 HTML 改到 **Vite + React + TypeScript** 工程
> `frontend/`（见 [[frontend-build-location]]）。**后端零改动**，React 经 HTTP 调既有端点。版本线随之
> 进入 **v0.4.x**（大迭代 +1 = 新增前端构建子系统）：原计划 v0.3.0a→v0.3.5b 的各屏落地对应到
> v0.4.0a（骨架，已完成）→ v0.4.1a 选区 → v0.4.2a 校对+草稿库 → v0.4.3a 助手 → v0.4.4a 答疑 →
> v0.4.5b 真 Manim。旧静态页整组归档至 `web/legacyweb/`（不删除）。下列 §C/§D/§E 端点契约与后端
> 模块计划仍然有效，逐屏在 React 中实现。

> **性质**：本节是**计划与流程**，不是代码改动。落地前以"运行—观测"复核当时真实代码。
> **范围**：只重构面向学生的核心练习/测试界面 `web/demo_standalone.html`——把"白板 + 侧栏求解"
> 的**单页工具**重排为**五屏引导式流程**，并补齐对应后端。老师/家长侧、`index/signin/demo_exam`
> 等其它页不在本次范围。
> **版本线**：按 **v0.3.x** 推进（大迭代 +1，因属学生端主链路 UX 大改），每步遵循
> [[commit-versioning-scheme]]：`vX.Y.Zℓ` 戳号 + CHANGELOG 记一条。
> **不破坏内核**：共识判分（`reasoner.py`）、苏格拉底护栏、逻辑诊断（`diagnosis.py`）、
> 经验记忆（`memory.py`）、标签自进化（`tags.py`）一律保留，仅在其上**新增 UI 层与编排**。

#### A. 设计目标
1. 把单页拆成五个**互斥屏幕**（屏路由：show/hide `<section>`，沿用现有
   `showWhiteboard/activateHintBoard/activateAIBoard` 的切换范式，泛化为通用 router + 返回栈）。
2. **作答前先"选区"**：提交给 OCR 的不再是整块白板，而是学生**框选的笔画/区域**（可拖动改大小）。
3. **OCR 必经"校对"**：识别结果回显给学生**核对纠错**后才入库/送批改——避免 OCR 噪声污染判分。
4. **逐行 AI 辅导**：AI 助手屏把"学生书写"与"逐行分析"**对齐成两列**，无误的行留空；可对**某一行**追问；
   需要时以 `<manim>…</manim>` 触发形象化可视化。
5. **个人草稿库**：学生的"书写过程/答案"可命名暂存（按题号），断点续作。
6. 复用既有能力（三选一出题、OCR 双路、共识判分、聊天、Manim 故事板），把缺口补成端点（见 §D/§E）。

#### B. 五屏导航流程（状态机记法；`in <s>` 可自跳转，`if <cond ? {真}:{假}>`）

```text
<题目屏 problem>  in <题目屏>  ← 选来源(AI/学科网/题库) · 看标签 · 白板作答(可全屏/双引擎)
   三个底部动作:
     if <点「提问 / 不会做」?     {flow=ask    →直接进 答疑屏, 不经 OCR}>
     if <点「提交」(需二次确认) ? {flow=submit →选区屏}>
     if <点「AI 助手」(亦即提交) ?{flow=assist →选区屏}>
        │  (submit / assist 两条都经"选区 → 校对")
        ▼
<选区屏 select>  框选/套索要发送的笔画, 拖动手柄改区域大小; 选 OCR 模型
   点「提交选区」→ POST /recognize (仅选中区域导出为 PNG, method=所选模型)
        │
        ▼
<校对屏 check>  态1: "服务器正在识别文本，请稍后…"(等 /recognize 返回)
              态2: 回显识别文本 → 选渲染方式(1 全渲染 / 2 源码风 / 3 纯文本)
                   → 编辑纠错(md/latex 工具) → 命名
                   →「存草稿」POST /work/save(status=tmp)  |  「提交」POST /work/save(status=final)
        │
        ├─ if <flow==submit ? { → 判分&沉淀:
        │                        POST /verify (共识判分) + 诊断/记忆 + 苏式 0–4 级提示
        │                        → <下一题> GET /practice/next(可 ?adaptive=) }>
        └─ if <flow==assist ? { → AI 助手屏 }>
                              │
                              ▼
<AI 助手屏 assistant>  题目 + 逐行(学生书写 | AI 分析; 无误留空; 可含 <manim> 可视化)
   选某行(内容+分析) → 跳到下方"追问区"
   追问区 = 聊天(POST /assistant/ask) + 渲染方式下拉 + 换行键下拉 + 特殊符号识别多选 + 发送
        │  (随时可 <返回> 上一屏)
        ▼
<答疑屏 ask>  (从题目屏「提问/不会做」进入, 不需白板)
   题目 +「解析此题」(可选 POST /analyze) + 聊天(POST /claude/chat) + 同款输入控件
```

> **设计决策（请审定）**：`提交` 与 `AI 助手` **都**走"选区 → 校对"，区别只在校对"提交"后的去向——
> `提交`→**共识判分 + 诊断**，`AI 助手`→**逐行分析**。若你希望 `提交` 后也顺带打开 AI 助手、或
> `AI 助手` 不计入判分，告诉我即可调整路由。

#### C₀. 屏幕线框图（用户原始草图 → 结构化补全）

> 下面 6 张线框是用户手绘草图的**结构化重绘 + 补全**（补了标题/简介、白板引擎切换、二次确认、
> 工具条、路由去向等）。`〈…〉` = 动态内容，`▾` = 下拉，`☑` = 多选。注：含中文为全角字符，
> 编辑器里右边框不会逐像素对齐，看结构即可。每屏的逐元素契约见 §C1–C5。

**① 题目屏 `#screen-problem`**
```text
┌──────────────────────────────────────────────────────────────────┐
│                       AI-based math tutor                          │  ← 标题
│  简介：按「难度 × 逻辑思维类型」因材施教的苏格拉底数学辅导          │  ← 一句话项目简介
├──────────────────────────────────────────────────────────────────┤
│ Problem:  [🏷 显示标签]            来源 ▾ 1.AI生成 2.学科网 3.题库   │  ← 标签开关 + 出题来源
├──────────────────────────────────────────────────────────────────┤
│  〈题面 statement + latex 渲染〉                                    │
│  （AI 来源追加免责声明：本题由 AI 生成，请注意甄别。）             │
├──────────────────────────────────────────────────────────────────┤
│  Whiteboard          引擎 ▾ 原生/Excalidraw          [⛶ 全屏]      │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │                    〈白板作答区，可反复涂改〉                  │ │
│  └──────────────────────────────────────────────────────────────┘ │
│  [✏ 笔] [笔画橡皮] [像素橡皮] [清空]                                              │
├──────────────────────────────────────────────────────────────────┤
│  [提交 ⚠二次确认]  [提问 / 不会做]  [AI 助手（求助＝同时提交）]    │
└──────────────────────────────────────────────────────────────────┘
   提交 / AI助手 → 选区屏        提问 / 不会做 → 答疑屏
```

**② 选区屏 `#screen-select`**
```text
┌──────────────────────────────────────────────────────────────────┐
│ [← 返回]                选择要提交的内容                            │
├──────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │   〈白板（含已画的全部笔画）〉                                 │ │
│  │        ┌╌╌╌╌╌╌╌╌┐  ← 框选；四角句柄可拖动改选区大小            │ │
│  │        ╎ 选中区 ╎                                             │ │
│  │        └╌╌╌╌╌╌╌╌┘                                             │ │
│  └──────────────────────────────────────────────────────────────┘ │
│  [套索] [矩形] [拖动/缩放]        预览：仅“选中笔画”导出为 PNG      │
├──────────────────────────────────────────────────────────────────┤
│  [提交选区]               OCR 模型 ▾ 1.nex  2.claude  3.auto       │
└──────────────────────────────────────────────────────────────────┘
   提交选区 → POST /recognize（仅选中区域 PNG, method=所选）→ 校对屏
```

**③a 校对屏 `#screen-check`（态1 · loading）**
```text
┌──────────────────────────────────────────────────────────────────┐
│                          AI math tutor                             │
├──────────────────────────────────────────────────────────────────┤
│                                                                    │
│                ⏳ 服务器正在识别文本，请稍后…                       │
│                     （等待 /recognize 返回）                       │
│                                                                    │
└──────────────────────────────────────────────────────────────────┘
```

**③b 校对屏 `#screen-check`（态2 · review）**
```text
┌──────────────────────────────────────────────────────────────────┐
│                          AI math tutor                             │
├──────────────────────────────────────────────────────────────────┤
│ 你的书写过程         渲染方式 ▾ 1.全渲染 2.源码风 3.纯文本(默认)    │
│ 选 1/2 时挂出：[ƒ 公式][Σ 符号][√][分式]… md+latex 工具条          │
├──────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │  〈识别文本，可逐字纠错〉                                      │ │
│  │  2x + 4 = 10                                                  │ │
│  │  x = 3                                                        │ │
│  └──────────────────────────────────────────────────────────────┘ │
├──────────────────────────────────────────────────────────────────┤
│  [存草稿]  文件名:[______________]                  [提交]         │
└──────────────────────────────────────────────────────────────────┘
   存草稿 → POST /work/save status=tmp（按题号入个人库）
   提交  → POST /work/save status=final → 判分路径(/verify) | 助手路径
```

**④ AI 助手屏 `#screen-assistant`**
```text
┌──────────────────────────────────────────────────────────────────┐
│ [← 返回]                    AI assistant                           │
│  欢迎！我来逐行看看你的解法。                                      │
│  题目：〈the problem〉                                             │
├─────────────────────────────────┬────────────────────────────────┤
│  学生作答（识别内容）           │  AI 分析（无误/无可优化则留空）  │
├─────────────────────────────────┼────────────────────────────────┤
│  2x + 4 = 10                   │  （留空 — 这步没问题）           │
│  2x = 10 + 4                   │  ⚠ 移项要变号，应为 10 − 4       │
│  x = 7                         │  承上一步之误；见 <manim> 演示   │
│  …                             │  …                              │
├─────────────────────────────────┴────────────────────────────────┤
│  （点某一行 → 跳到下方追问区，并带该行为上下文）                   │
│  ── Q&A ───────────────────────────────────────────────────────   │
│  我：……                                                          │
│  AI：……（苏格拉底式；需要时含 <manim> 可视化）                    │
│  ……（聊天框，可拉伸）                                             │
├──────────────────────────────────────────────────────────────────┤
│ 渲染方式▾(1/2/3)  换行▾(Enter/Alt/Ctrl)  ☑特殊符号(正则 \n 转义…)   │
│  [输入框 — 支持 latex 与 md，可拉伸]                     [发送]    │
└──────────────────────────────────────────────────────────────────┘
   进屏 → POST /assistant/analyze   行级追问 → POST /assistant/ask
```

**⑤ 答疑屏 `#screen-ask`**
```text
┌──────────────────────────────────────────────────────────────────┐
│ [← 返回]                        Q&A                                │
│  题目：〈problem〉                                  [解析此题]      │
├──────────────────────────────────────────────────────────────────┤
│  我：……                                                          │
│  AI：……（项目规则：苏格拉底式、不直接给答案；可含 <manim>）        │
│  ……（聊天框，可拉伸）                                             │
├──────────────────────────────────────────────────────────────────┤
│ 渲染方式▾(1/2/3)  换行▾(Enter/Alt/Ctrl)  ☑特殊符号(正则 \n 转义…)   │
│  [输入框 — 支持 latex 与 md，可拉伸]                     [发送]    │
└──────────────────────────────────────────────────────────────────┘
   解析此题 → POST /analyze（苏式 0 级）    问答 → POST /claude/chat
```

#### C. 逐屏规格（关键元素 × 交互 × 后端调用）

**C1 题目屏 `#screen-problem`**
- 顶部：标题「AI-based math tutor」+ 一句话项目简介（如"按『难度 × 逻辑思维类型』因材施教的苏格拉底数学辅导"）。
- `Problem` 行：①「显示标签」按钮（toggle，读题卡 tags / `GET /tags`）；②来源下拉「选择出题来源：1.AI 生成 2.学科网 API 3.后台数据库」→ 直接映射 `GET /practice/next?source=ai|xueke|bank`（已支持，含降级与 `disclaimer`）。
- 题面区：复用 `loadProblem()` 渲染（statement/latex/meta）；AI 来源（300-）追加"请注意甄别"免责声明（后端已给 `disclaimer`）。
- 白板：复用现有 native/Excalidraw 双引擎 + 全屏（`switchBoardMode/toggleBoardFullscreen/captureBoardBlob`，无需改）。
- 底部动作行：`提交`（二次确认弹窗"确认已完成作答？"，含"实际未完成也可提交"提示）｜`提问 / 不会做`｜`AI 助手（点此求助，同时提交）`。

**C2 选区屏 `#screen-select`**
- 目的：让学生选择**究竟把白板的哪部分**发给服务器；可改选区大小。
- native canvas：已有 `strokes[]`（含每笔 points）——在其上叠加**套索/矩形框选 + 句柄缩放**，导出时只把**命中选区的笔画**重绘到离屏 canvas → PNG。
- Excalidraw：复用其原生选择，`exportToBlob({elements: 选中元素})` 仅导出选中件。
- 控件：`选区工具/拖动`、内容预览、`提交选区` + 「选择 OCR 模型」下拉（→ `GET /recognize/models`，值映射 `POST /recognize?method=`）。
- 调用：`POST /recognize`（multipart `file`=选区 PNG, `method`=所选）。

**C3 校对屏 `#screen-check`**
- 态1（loading）：标题「AI math tutor」+「服务器正在识别文本，请稍后…」+ spinner（等 `/recognize`）。
- 态2（review）：
  - 回显「你的书写过程」识别文本；「渲染方式」下拉：**1** md+latex 全渲染（直接最终形式）/ **2** md+latex 源码风（如 VSCode 预览）/ **3** 纯文本（默认）。
  - 选 1/2 时挂出 **md & latex 辅助工具条**（插入公式/符号/环境）。
  - 学生可**改字纠错**（OCR 可能识别错）。
  - 底部：`存草稿`+文件名输入（→ `POST /work/save status=tmp`，按题号存个人库）｜`提交`（→ `POST /work/save status=final`，再按 §B 去向继续）。
- 新依赖：前端引入 **marked.js**（Markdown）+ 现有 **MathJax**（LaTeX）实现三种渲染方式。

**C4 AI 助手屏 `#screen-assistant`**
- 顶部：`返回` + 「AI assistant」+ 欢迎语 + 题面。
- 主体：**两列逐行**——左「学生作答识别内容」｜右「AI 分析」。**逐行对齐**；某行无错误/无可优化则**右列留空**；用 markdown+latex；需要可视化时 AI 在分析里产出 `<manim>…</manim>` 块，前端渲染（先走 `/animate` 故事板，后续 §E5 真渲染）。
- 交互：点选某一行（内容+分析）→ 滚动/跳转到页面下方**追问区**，并把该行作为上下文。
- 追问区（聊天框）：`POST /assistant/ask`（在 `/claude/chat` 基础上带 `focus 行上下文 + render_mode + allow_special`）；底部控件见 §C-公共。
- 调用：进屏时 `POST /assistant/analyze`（题 + 学生作答 → 逐行分析）。

**C5 答疑屏 `#screen-ask`**
- 顶部：`返回` + 「Q&A」+ 题面 + 「解析此题」按钮（可选 `POST /analyze`，仍是苏式不直接给答案）。
- 主体：聊天框（`POST /claude/chat`，带题面 `expression` 接地）+ §C-公共控件。
- 入口：题目屏「提问 / 不会做」，**无需白板/OCR**，给"卡住了"的学生即时求助。

**C-公共 · 聊天输入控件（C4/C5 共用一个组件）**
- 「渲染方式」下拉（1 全渲染 / 2 源码风 / 3 纯文本，默认 3）；选 1/2 时挂 md+latex 工具条。
- 「选择换行」下拉：1 Enter / 2 Alt+Enter / 3 Ctrl+Enter（选 Enter 则换行只能点"发送"提交）。
- 「允许识别特殊符号与表达式」**多选**表单：正则 / `\n\r` 换行 / 转义 等——决定是否把输入按字面/转义解释（前端行为 + 透传后端 `allow_special`）。
- 输入框可拉伸；支持 latex 与 md；`发送`。

**复用 / 改造的现有前端函数**：`loadProblem`、`captureBoardBlob/submitWhiteboard`（拆出"选区导出"）、`sendAIChat/addAIMessage`（升级为公共聊天组件）、`renderAIAnalysis`（升级为逐行两列）、`showNextHint`（submit 反馈仍用苏式分级）、`triggerManimAnimation`（接 `<manim>` 块）。

#### D. 前后端契约（复用既有 + 新增端点）

**复用（无需或仅小改）**
| 端点 | 用途（本次） |
|---|---|
| `GET /practice/next?source=ai\|xueke\|bank[&tag&focus_logic&difficulty&adaptive]` | 题目屏来源下拉 + 自适应下一题 |
| `GET /tags` · `GET /tags/catalogue` | 「显示标签」开关 |
| `POST /recognize?method=nex\|claude\|auto` (multipart `file`) | 选区屏 OCR（前端只导出选中区域 PNG，后端不变） |
| `POST /verify` `{expression,answer,session_id,question_id,model}` | submit 路径共识判分 + 诊断 + 记忆（已具备） |
| `POST /claude/chat` `{session_id,message,expression,model,history}` | 答疑/追问聊天底座 |
| `POST /analyze` | 答疑屏「解析此题」（苏式 0 级） |
| `POST /animate` `{expression}` | `<manim>` 块的故事板渲染（占位，待 §E5 升级） |

**新增**
| 端点 | body → 返回 | 落点 |
|---|---|---|
| `GET /recognize/models` | → `{models:[{id,label}], default}` | `recognize.list_models()`；选区屏下拉 |
| `POST /work/save` | `{session_id,question_id,filename,content_md,render_mode,status:"tmp"\|"final"}` → `{id,status}` | 新 `workspace.py` → `data/workspace.db` |
| `GET /work?session=&question_id=` · `GET /work/{id}` | → 草稿列表/单条 | 同上；支持"存草稿后续作" |
| `POST /assistant/analyze` | `{question_id\|problem, student_work_md, session_id, model, render_mode}` → `{lines:[{idx,content,analysis,has_issue,manim?}], summary, provider}` | 新 `assistant.py` + `prompts.build_line_analysis_prompt` |
| `POST /assistant/ask` | `/claude/chat` 字段 + `{focus:{idx,content,analysis}, render_mode, allow_special:[…]}` → `{reply,provider}` | `assistant.py` + `prompts.build_assistant_chat_system` |
| （分阶段）`POST /manim/render` | `{manim_code\|spec}` → `{video_url\|frames, status}` | 新 `manim_render.py`，不可用降级回故事板 |

#### E. 后端架构补全（新模块 / 新表）
1. **`backend/app/workspace.py`（新）** — 个人草稿/答案库 CRUD，复用 `auth.py/exam.py` 的 sqlite 范式与 `data/` 目录。表 `work_drafts(id, owner, question_id, filename, content_md, render_mode, status, created_at, updated_at)`；`owner` = 登录用户名或 `session_id`。这就是草图里的"个人 tmp 数据库（带问题编号）"。
2. **`backend/app/assistant.py`（新）** — 逐行分析编排：把 `student_work_md` 切行 → 结合题目对**每行**产出对齐分析（错误/可优化点；无则空）+ 可选 `<manim>`；底层走 `claude_service`（含 `reasoner` 多路一致性可选增强），模板降级。`/assistant/*` 路由在此。
3. **`prompts.py` 扩展** — `build_line_analysis_prompt`（逐行、对齐、留空规则、`<manim>` 触发约定）、`build_assistant_chat_system`（含 `render_mode` 与"特殊符号/转义"处理约束）；（分阶段）`build_manim_prompt`（真 AI 生成 Manim CE 代码）。
4. **`recognize.py` 扩展** — `list_models()`（驱动 §D 的 `GET /recognize/models`）；`method` 增可选模型；选区图复用现路径（仍是 PNG，无需新解码）。
5. **Manim 真渲染（分阶段，风险低、可独立）** — 现 `/animate` 升级为"AI 生成 Manim 代码 + 故事板"，真视频渲染另起 `POST /manim/render`（新 `manim_render.py`，需 Manim CE + ffmpeg；**沿用 `claude_service` 降级范式**：环境不全时回落到浏览器故事板，保证始终可跑）。对应北极星目标 10。

#### F. 迁移与 legacy 备份策略（落实用户指示"原先旧的都移动到 legacy 文件夹备份"）
- **规则**：任何将被**整体改写**的文件，改写前先把**当前版本复制**到就近 `legacy/`，命名 `*.v<旧版本>.<ext>`，并在文件头注明"历史只读、非生产路径"——与现有 `docs/legacy/*.od.md`、`backend/app/legacy/sympy_grader.py` 范式一致。
- **本次具体**：
  - `web/demo_standalone.html` → `web/legacy/demo_standalone.v0.2.html`（`web/legacy/` 已存在）。
  - 若 `prompts.py` 大改 → 先备份 `backend/app/legacy/prompts.v0.2.py`（仅备份，**不被 import**）。
  - 其余被大改的后端文件同理备份到 `backend/app/legacy/`。
- **不删除**：legacy 只增不删，保留可回溯。**本次仅文档**，备份动作列为 §G 第 0 步，待批准编码时执行。

#### G. 分阶段实施计划（每步：目标 → 交付物 → 验收；均可独立交付/回退）
- **v0.3.0a · 备份 + 屏路由骨架**：执行 §F 备份；把单页改造成 5-`<section>` + router + 返回栈；题目屏接来源下拉/标签开关/三动作（先桩接）。**验收**：五屏可互相跳转、返回栈正确；现有出题/白板不回归。
- **v0.3.1a · 选区屏**（→ 已作为 **v0.4.1a** 在 React 落地）：native `strokes[]` 套索/框选 + 句柄缩放 + 只导出选中区；OCR 模型下拉（`/recognize/models`）。**验收**：只发送选中笔画的 PNG，`/recognize` 正常返回。
  - **已实现（v0.4.1a）**：`frontend/src/board/selection.ts`（`exportRect`/`exportLasso` 直接从白板 canvas 拷像素，忽略擦除 op）+ `SelectScreen`（矩形 8 句柄缩放/平移 + 套索；进屏默认=墨迹包围盒）+ 后端 `GET /recognize/models`（`recognize.list_models()`）。验收达成：真后端只裁选中区 OCR 返回 `2+3=5`/status ok；headless Chrome 对 `selection.ts` 11 断言全过（含空白区导出 0 墨迹）。
- **v0.3.2a · 校对屏 + 个人草稿库**：三渲染方式（marked.js+MathJax）+ 纠错工具 + `workspace.py`/`/work/*`。**验收**：识别→改字→存草稿→重开续作；`final` 提交后 submit 路径进 `/verify` 判分。
- **v0.3.3a · AI 助手屏（逐行分析）**：`assistant.py` + `/assistant/analyze` + 两列对齐 + 行级追问 `/assistant/ask`；公共聊天控件（渲染/换行键/特殊符号）。**验收**：学生作答逐行对齐分析，无误行留空；点行可带上下文追问。
- **v0.3.4a · 答疑屏**：题目屏「提问/不会做」→ 答疑屏；`/analyze` 解析 + `/claude/chat` 问答 + 公共控件。**验收**：不经白板即可就本题问答，苏式不直接给答案。
- **v0.3.5b · 真 Manim（可选、独立）**：`/manim/render` + `manim_render.py`，`<manim>` 块真渲染，环境不全降级故事板。**验收**：助手屏某行触发的 `<manim>` 能出真动画；无 Manim 时自动回落且不报错。

> 验收一律遵循仓库习惯：**运行应用 + 观测真实行为**（headless 浏览器 / `curl`），而非只跑单测。
> 真链路涉及网关的步骤注意 §5 的并发/缓存/超时约束（多路推理与逐行分析都会放大网关抖动）。

---

### 阶段 0 · 基线加固（1 周）—— 把"演示"变"可靠"
- **目标**：在不加新能力前提下，消除已知脆弱点。
- **交付物**：
  - 移除前端 head 里失效的 `polyfill.io` 同步脚本（曾导致页面卡死）。
  - `claude_service` / `recognize` 的超时、断路器、限速集中到 `config.py`，文档化。
  - `README.md` 更新为现状（`web/` 入口、`.env` 配置、nex OCR、Claude、auth、exam）。
- **验收**：冷启动后 `web/index.html` → 各页可达；后端 `/docs` 200；关键接口烟测通过。

### 阶段 1 · 持久化经验记忆（Recursive Intelligence）（✅ 已完成 2026-06-26）
- **蓝图**：§"Recursive Intelligence and Experience-Based Memory"。
- **目标**：把 `ExperienceMemory` 落到 SQLite，跨会话/重启留存；沉淀"可复用技能"。
- **交付物（已落地）**：
  - ✅ `backend/app/memory.py::PersistentExperienceMemory`：表 `mem_sessions`、
    `mem_messages`、`mem_interactions`（按 `session_id` 建索引），复用 `data/` 目录与
    `auth.py`/`exam.py` 的 sqlite 模式。`get_or_create_session` 从这些表重建会话字典，
    `successful_strategies` / `struggle_patterns` / `hint_levels_used` 由交互记录派生。
  - ✅ `main.py` 接入：方法签名与原进程内版本一致，`/analyze`、`/hint`、`/claude/chat`、
    `GET /session/{id}` 调用点未改即获得持久化；启动时 `memory_store.init_db()` 建表。
  - ✅ 自适应难度从持久统计计算（替换进程内字典）。
- **验收（已通过，运行观测）**：`/hint` 连续调用提示等级 [1,2,3] 递增；**重启后**
  `/session/{id}` 仍含会话历史与等级，且下一次 `/hint` 续接到 4（非重置为 1）。
- ✅ **收尾（2026-06-26）：接通"学生已解出"信号** —— `POST /verify` 接受学生 `answer`，由
  **SymPy 判对错**（待彻底废止，全程 Claude 自行推理方才为正解），把真实 `user_solved` 写入经验记忆。修复了原先
  `record_interaction` 调用点恒传 `False` 导致 `success_rate` 永为 0、自适应难度无法爬升的缺陷。
  已运行验证：答对后 `success_rate` 0→0.2、`successful_strategies` 记 `hints_needed`、跨新进程读盘留存。
- **后续可深化**：`skills` 技能固化表、`GET /memory/{session}` 聚合视图（非阻塞，留待需要时）。

### 阶段 2 · Data Manager：自动架构 JSON 树（1–2 周）
- **蓝图**：§"Foundational Architecture / Data Manager"。
- **目标**：`/architecture` 不再手写，而是扫描真实仓库目录 + Python AST 自动生成节点元数据
  （路径、用途摘要、依赖、导出符号）。
- **交付物**：
  - `backend/data_manager.py`：用标准库 `ast` 解析 `backend/*.py`，产出 JSON 树；
    可选用 Claude 为每个模块生成一句"功能摘要"（带模板降级）。
  - 重构 `@app.get("/architecture")` 读取自动树；保留旧手写树作为 `/architecture/legacy`。
- **验收**：新增一个函数后，`/architecture` 即时反映；树含真实文件与依赖。

### 阶段 3 · 真·多智能体编排（ALMAS + 工作流拓扑）（2–3 周）
- **蓝图**：§"ALMAS Framework" 与 §"Workflow Topologies"。
- **目标**：把六个 Agent 从"元数据"变成"可执行角色"，先在**只读/建议**范围内编排。
- **交付物**：
  - `backend/orchestrator.py`：以 Claude 为后端实现
    - **Router**：依请求路由到专家提示；
    - **Pipeline**：Control(Meta-RAG 定位，复用阶段 2 的 JSON 树) → Developer(产出建议) → Peer(审查)；
    - **Reflection**：Developer 先自审一轮再交 Peer；
    - **Voting**：同一问题多次生成、择优（对冲幻觉）。
  - 首个落地用例（**低风险、纯产出文本**）：用 ALMAS 编排**生成一份新练习/讲解**，
    而非改代码；接口 `POST /almas/author`。
- **验收**：对同一知识点，Voting 产出 N 份、Peer 选 1 份并给出理由；全过程可观测、可复跑。
- **风险控制**：此阶段 Agent **不触碰文件系统**，仅产出文本/JSON。

### 阶段 4 · SEPGA 计划级策略治理（2 周）
- **蓝图**：§"Policy Governance and the SEPGA Framework"。
- **目标**：把 `PolicyEngine` 从"校验用户输入"升级为"校验 Agent 行动计划"。
- **交付物**：
  - `backend/policy.py`：策略库（禁止动作、不可变文件清单、资源/库白名单）；
    对阶段 3 编排器产出的"计划"逐步罚分，超阈值则从搜索空间剪除（Constrained MDP 近似）。
  - 全量决策审计日志写入 `data/policy_audit.db`。
- **验收**：构造一个违规计划（如"修改 auth.py"），被策略引擎拒绝并留审计记录。

### 阶段 5 · 自修改能力（AST/SPA）—— 默认 Dry-Run（3–4 周，高风险）
- **蓝图**：§"Mechanics of Autonomous Architecture Reconstruction"。
- **目标**：在**严格沙箱 + 零信任分权**下，让系统对**自身非核心模块**提出并验证补丁。
- **交付物**：
  - 引入 `libcst` 做 AST 级补丁（保留格式/注释）；
  - `backend/spa_loop.py`：补丁 → 在**隔离副本**(git worktree/临时目录)运行 `pytest`+静态指标
    （圈复杂度≤10、覆盖率≥80%）→ 失败则回灌反馈再精炼；
  - **Zero-Trust 分权**：生成层无权改动验证层与测试参数；
  - **默认 `--dry-run`**：只产出 diff 与验证报告，**人工合并**；自动合并需显式开启且经 SEPGA。
- **验收**：对一个示例工具函数自动生成补丁，沙箱测试通过，输出 diff，但**不自动落盘**。
- **护栏**：不可变清单至少含 `auth.py`、`policy.py`、`config.py`、`.env`、`data/`。

### 阶段 6 · Lattice 护栏自演化 + 对抗加固（2–3 周）
- **蓝图**：§"Adversarial Threats and Continuous Guardrail Optimization"。
- **目标**：周期性"风险评估 → 用例扩展(自我攻击) → 护栏优化 → 性能评估(可回滚)"。
- **交付物**：
  - `backend/lattice.py`：定时任务，用隔离 Claude 实例生成越狱/注入变体，发现 Socratic 与
    SEPGA 护栏缺口，自动建议护栏补丁（仍走人工/SEPGA 审批）。
  - 教学侧专项：检测"诱导直接给答案"的提问，验证 Socratic 约束不被绕过。
- **验收**：注入一个已知绕过样本，Lattice 报告缺口并给出护栏更新建议；回归不降低教学有效性。

---

## 5. 横切关注点

- **★ 去符号化：大模型自行运算（2026-06-26 定向，取代下方旧的"神经-符号"原则）**：**放弃 SymPy
  确定性验证，改由 Claude 自行完成运算与判分**。正确性不再靠 CAS，而靠**审慎链式推理 + 自我迭代/
  多路共识**：同一题多路独立计算 → 互检/投票 → 不一致再算 → 收敛到一致且**最简**的解。诚实提醒：
  LLM 算术会出错，所以"多路共识/自我迭代"是替代 CAS 的**正确性保障**，必须与去符号化**一并落地**
  （否则就是把正确性完全押在单次生成上）。详见 §4「下一首要目标」。
  - **当前过渡态**：代码仍是混合（应用题走 Claude 翻 `computation`→SymPy 复核，`judged_by` =
    `sympy`/`claude+sympy`/`claude`），这只是**迁移起点**；目标是把 SymPy 移出判分/求解主链路
    （保留为 `legacy/` 对照工具），不再让 CAS 当裁判。
  - ✅ **门禁已放宽**：`PolicyEngine.domain_restriction` 现接受自然语言应用题（只拦符号垃圾），
    注入/长度仍硬拦截。`solve_with_steps` 新增自然语言识别（CJK/`?`/>3 自由符号 → `unparseable`）。
- **网关韧性**：所有 LLM/OCR 调用统一经 `claude_service` 风格封装（超时、断路器、限速、降级）。
  多智能体阶段务必加**结果缓存**与**并发上限**，否则 `computinger.com` 抖动会被放大。
- **安全与隐私**：`data/` 已 gitignore（含密码哈希）；阶段 4 起所有自动化动作必须留审计。
- **验证文化**：沿用仓库既有做法——用 headless 浏览器 / curl **运行并观测**，而非只跑单测。

---

## 6. 里程碑与验收指标

| 里程碑 | 对应阶段 | 关键验收指标 |
|--------|---------|-------------|
| M0 可靠基线 | 0 | 冷启动全链路烟测通过；polyfill 卡死消除 |
| M1 记忆持久 ✅ | 1 | 重启后经验记忆留存；自适应随历史变化（2026-06-26 达成）|
| M2 架构自省 | 2 | `/architecture` 由真实代码自动生成 |
| M3 多智能体产出 | 3 | ALMAS 编排生成讲解/练习，Voting+Peer 可观测 |
| M4 计划级治理 | 4 | 违规计划被 SEPGA 拒绝并审计 |
| M5 自修改(dry-run) | 5 | 沙箱内补丁通过测试并产出 diff，不自动落盘 |
| M6 护栏自演化 | 6 | Lattice 发现并建议修补已知绕过样本 |

**总体节奏建议**：M0–M2 为"低风险、高确定性"基础，先做；M3–M4 引入智能体与治理，价值显著
且风险可控；M5–M6 为蓝图皇冠，**务必在 M4 的策略治理就绪后**再启动，并始终默认 dry-run +
人工合并。

---

## 7. 与现有文件的对应索引（便于落地）

| 蓝图概念 | 落地文件（现有/新增） |
|---------|----------------------|
| 神经-符号验证 | `backend/main.py::NeuroSymbolicEngine`（现有）|
| Socratic 护栏 | `backend/main.py::SocraticEngine`、`backend/prompts.py`（现有）|
| Blending Instructions | `backend/main.py::BlendingInstructions`（现有，待扩展架构边界）|
| 复合 AI 网关 | `backend/claude_service.py`、`config.py`（现有）|
| 多模态前端 | `web/*.html`、`backend/recognize.py`（现有）|
| 经验记忆 | `backend/app/memory.py::PersistentExperienceMemory`（阶段1 已完成，SQLite 持久化）|
| Data Manager | `/architecture`（现有静态）→ `backend/data_manager.py`（新增，阶段2）|
| ALMAS 编排 | `backend/orchestrator.py`（新增，阶段3）|
| SEPGA 治理 | `PolicyEngine`（现有输入级）→ `backend/policy.py`（新增计划级，阶段4）|
| AST/SPA 自修改 | `backend/spa_loop.py`（新增，阶段5，依赖 libcst）|
| Lattice 护栏演化 | `backend/lattice.py`（新增，阶段6）|

> 本计划为增量演进蓝图；任何阶段落地前应再次以"运行—观测"方式校核当时的真实代码状态，
> 因为代码是唯一事实来源，本文档是对它的规划性陈述。
