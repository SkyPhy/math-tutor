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

贯穿原则（来自蓝图，且与本仓库现有做法一致）：

- **SymPy 是确定性验证锚点** —— 神经网络负责创造，符号系统负责保证正确（neuro-symbolic）。
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
| 11 | 神经-符号集成（SymPy CAS 验证）| 方程求解、化简、验证、分类、步骤生成 | `NeuroSymbolicEngine.solve_with_steps` | ✅ 已实现（项目最强项）|
| 12 | 递归智能 / 经验记忆 | 会话内经验记忆、自适应难度 | `ExperienceMemory` | 🟡 部分（进程内、非持久跨会话、无技能固化）|
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
│   SymPy 确定性验证(已有) ＋ ★代码沙箱/AST/SPA(待建) ＋ ★Zero-Trust 分权  │
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

### 阶段 0 · 基线加固（1 周）—— 把"演示"变"可靠"
- **目标**：在不加新能力前提下，消除已知脆弱点。
- **交付物**：
  - 移除前端 head 里失效的 `polyfill.io` 同步脚本（曾导致页面卡死）。
  - `claude_service` / `recognize` 的超时、断路器、限速集中到 `config.py`，文档化。
  - `README.md` 更新为现状（`web/` 入口、`.env` 配置、nex OCR、Claude、auth、exam）。
- **验收**：冷启动后 `web/index.html` → 各页可达；后端 `/docs` 200；关键接口烟测通过。

### 阶段 1 · 持久化经验记忆（Recursive Intelligence）（1–2 周）
- **蓝图**：§"Recursive Intelligence and Experience-Based Memory"。
- **目标**：把 `ExperienceMemory` 落到 SQLite，跨会话/重启留存；沉淀"可复用技能"。
- **交付物**：
  - `backend/memory.py`：表 `interactions`、`skills`（成功策略固化）、`struggles`；
    复用 `data/` 目录与 `auth.py`/`exam.py` 的 sqlite 模式。
  - `main.py` 接入：`/analyze`、`/hint` 读写持久记忆；新增 `GET /memory/{session}`。
  - 自适应难度从持久统计计算（替换进程内字典）。
- **验收**：连续两次会话，第二次的提示策略随历史变化；重启后记忆仍在（curl 观测）。

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

- **神经-符号锚点**：任何阶段，凡涉及数学结论，必须经 `NeuroSymbolicEngine` 确认；Claude 只
  能围绕已验证结果组织语言，不得另算答案（现有 prompts 已强制，需保持）。
- **网关韧性**：所有 LLM/OCR 调用统一经 `claude_service` 风格封装（超时、断路器、限速、降级）。
  多智能体阶段务必加**结果缓存**与**并发上限**，否则 `computinger.com` 抖动会被放大。
- **安全与隐私**：`data/` 已 gitignore（含密码哈希）；阶段 4 起所有自动化动作必须留审计。
- **验证文化**：沿用仓库既有做法——用 headless 浏览器 / curl **运行并观测**，而非只跑单测。

---

## 6. 里程碑与验收指标

| 里程碑 | 对应阶段 | 关键验收指标 |
|--------|---------|-------------|
| M0 可靠基线 | 0 | 冷启动全链路烟测通过；polyfill 卡死消除 |
| M1 记忆持久 | 1 | 重启后经验记忆留存；自适应随历史变化 |
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
| 经验记忆 | `ExperienceMemory`（现有）→ `backend/memory.py`（新增，阶段1）|
| Data Manager | `/architecture`（现有静态）→ `backend/data_manager.py`（新增，阶段2）|
| ALMAS 编排 | `backend/orchestrator.py`（新增，阶段3）|
| SEPGA 治理 | `PolicyEngine`（现有输入级）→ `backend/policy.py`（新增计划级，阶段4）|
| AST/SPA 自修改 | `backend/spa_loop.py`（新增，阶段5，依赖 libcst）|
| Lattice 护栏演化 | `backend/lattice.py`（新增，阶段6）|

> 本计划为增量演进蓝图；任何阶段落地前应再次以"运行—观测"方式校核当时的真实代码状态，
> 因为代码是唯一事实来源，本文档是对它的规划性陈述。
