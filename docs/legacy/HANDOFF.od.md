# 项目交接文档 / Project Handoff（已归档 · OUTDATED）

> 🗄️ **已归档 · OUTDATED（od）** —— 本文件是 **2026-06-27 的事实快照，已停止维护**，与当前代码（v0.2.5a）多处不符
> （例如：运行改用 `py -3.12`；已新增 `tags.py`/`diagnosis.py` 与逻辑思维类型 v2.0；学科网题源 `XuekeProvider`、
> 结构化题号、笔画直传 AI 等）。**当前事实来源**：[`docs/DEVELOPMENT_PLAN.md`](../DEVELOPMENT_PLAN.md) ＋
> [根 `CHANGELOG.md`](../../CHANGELOG.md) ＋ `.claude/context/01-CURRENT-STATE.md`。
> 归档于 2026-06-30，仅作历史参考（文内相对链接为归档前路径，可能已失效）。

---

> 面向接手的 AI 开发者（Codex 等）。本文件描述**当前真实状态**，是事实快照；
> 路线图见 [`DEVELOPMENT_PLAN.md`](DEVELOPMENT_PLAN.md)。
> 一句话：这是一个 **Socratic（苏格拉底式）AI 数学辅导系统**——FastAPI 后端
> （Claude 自主推理；SymPy 确定性验证为**过渡，方向上待废止**）+ 纯静态多页前端 + 手写 OCR +
> 账户/考试 SQLite 存储。
> 最后更新：2026-06-27。
>
> **★ 方向（2026-06-26）：放弃 SymPy，换为大模型自行运算。** 求解与判分将由 Claude 端到端自主
> 完成，SymPy 确定性验证从主链路彻底移除（正确性改靠自我迭代/多路共识）。本文描述的仍是**当前
> 过渡态**（混合）；下一首要目标见 [`DEVELOPMENT_PLAN.md`](DEVELOPMENT_PLAN.md) §4。

---

## 0. TL;DR — 30 秒上手

```bash
# 后端（必须在 backend 目录内运行；app 是 Python 包，入口为 app.main:app）
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
# 前端：直接用浏览器打开（静态文件，无需构建）
#   web/index.html   ← 入口
```

- **Python**：3.14（系统已装；依赖见 `backend/requirements.txt`，纯标准库 + fastapi/uvicorn/sympy/pillow/python-multipart）。
- **密钥**：`backend/.env`（**已 gitignore**，当前含真实 key——交接时注意脱敏/轮换）。所有模块只经 `backend/app/config.py` 读取密钥，源码里无硬编码 key。
- **数据**：`backend/data/{users.db, exams.db}`（SQLite，已 gitignore）。
- **外部服务**：一个 **new-api 网关** `https://www.computinger.com`，同时提供 Claude（Anthropic 兼容）和 `nex-n2-pro`（OpenAI 兼容视觉 OCR）。**该网关延迟高且抖动大**（见 §6 坑）。
- **当前后端进程**：**未运行**（需手动启动）。

---

## 1. 这是什么 / 产品形态

一个小学数学（义务教育课标）AI 辅导 + 出题 + 考试系统，核心原则：

1. **判分以"多路共识"为正解来源（去 SymPy，2026-06-27 落地第 1-2 步）**：判分不再依赖 CAS，而是让 **Claude 对同一题独立求解多路**（不同视角 + temperature 抖动，见 `backend/app/reasoner.py` 的 `_ANGLES`/`_TEMPS`），**多数路一致的答案**即正解；答案比较用推理器**自带的去 SymPy 数值归一器**（`fractions`+`ast`，`1/2`=`0.5`=`50%`、集合无序、带单位也能比）。`/verify` 判分走 `reasoner_engine.grade`，返回 `judged_by="consensus(k/n)"`、`agreement`、`ground_truth`（共识答案）。**✅ 真链路已验收（2026-06-27，密钥到位后）**：`POST /verify` 真 HTTP 对 `2x+4=10` 答 `3`→`answer_correct=True`、答 `4`→`False`，`judged_by=consensus`、`votes_label=consensus(3/3)`，确经多路共识而非 SymPy 兜底（详见 `DEVELOPMENT_PLAN.md` §4 验收）。**SymPy 已降为兜底**：仅当网关不可用或多路不一致时，用它对可解代数做非权威交叉校验（`judged_by="sympy-fallback"`）；判不出就返回"未判定"（`correct=null`），绝不瞎猜。原单次 `claude+sympy` 判分簇（`_claude_grade`/`_eval_closed_form`/`build_grade_prompt`）**已删除**。原"SymPy 唯一事实来源、不得另算"的绝对约束早已废止。<br>　**✅ 第 3 步（判分部分，2026-06-27 落地）**：判分用的 SymPy（原 `_sympy_grade`+`_compare_answer`）已从 `main.py` 移入 **`backend/app/legacy/sympy_grader.py`**（新建 `app.legacy` 包），作明确标注的**非权威离线兜底**；`_check_student_answer` 经依赖注入调用（把 `NeuroSymbolicEngine.solve_with_steps` 当 `solver` 传入，避免循环导入）。主判分路径在 `main.py` 内**已无 SymPy 判分代码**；行为不变，已离线 + 真 HTTP 验收无回归。<br>　**仍未做（第 3 步渲染部分）**：渲染引擎 `NeuroSymbolicEngine` 仍留 `main.py`，为 `/analyze`·`/hint`·`/animate`·`/plot` 提供 latex/分类/步骤渲染（非正确性用途），整体迁 `app/legacy/` 留待渲染侧一并迁移。
   - **门禁已放宽**：`PolicyEngine.domain_restriction` 现接受自然语言应用题（CJK/字母/数字均算"内容"，只拦符号垃圾）；注入 token 与长度仍是硬拦截，安全不变。
   - **自然语言识别**：`NeuroSymbolicEngine.solve_with_steps` 现会识别应用题（含 CJK/`?`/解析出>3 个自由符号即判为 prose），标 `verification_status="unparseable"`、`solution=None`，避免 SymPy 把"小明有3个苹果"硬解成垃圾符号还自称 verified。
2. **Socratic 约束不可绕过**：默认不直接给最终答案，分 5 级渐进提示。
3. **AI 不可用时优雅降级**：未配置 `.env` 时，提示退回模板引擎，OCR 退回 mock，系统始终可跑。

---

## 2. 目录地图

```
math/
├── README.md                       ← 项目说明（已更新到当前结构）
├── .gitignore                      ← 忽略 .env / data/ / backup/ / __pycache__ 等
│
├── docs/                           ← 文档
│   ├── HANDOFF.md                  ← 本文件
│   ├── DEVELOPMENT_PLAN.md         ← 蓝图对齐的分阶段路线图（v1）
│   └── design/                     ← 设计/蓝图原文
│       ├── Designing AI Math Education Software.md
│       ├── Evolving AI Math.pdf
│       └── pdf_content.txt
│
├── lesson/README.md                ← 知识点分类法（考试出题的数据源，见 §5）
│
├── web/                            ← 前端（纯静态 HTML+CSS+JS，CDN 加载库，无构建步骤）
│   ├── index.html                  ← 首页/落地页（含可选登录态导航）
│   ├── signin.html / signup.html   ← 登录 / 注册
│   ├── demo_sellection.html        ← 选年级(1–6)+知识点（两张表，可加多个）→ 启动 demo
│   ├── demo_exam.html              ← 自动出题考试入口（见 §5）
│   ├── demo_standalone.html        ← 核心辅导界面（白板/OCR/Claude 聊天/提示/动画）+ 考试模式
│   └── legacy/                     ← 早期 React/Vite 原型（仅供参考，**未使用**）
│
└── backend/                        ← 后端（FastAPI）
    ├── app/                        ← ★Python 包，入口 app.main:app
    │   ├── __init__.py
    │   ├── main.py                 ← ★主程序（2100+ 行单体，所有路由+核心类）
    │   ├── config.py               ← .env 加载 + Claude/OCR 配置（唯一读密钥处；自写 dotenv，无 python-dotenv 依赖）
    │   ├── claude_service.py       ← Claude 网关客户端（urllib，超时/断路器/限速）
    │   ├── recognize.py            ← nex-n2-pro 视觉 OCR（urllib，含图像预处理）
    │   ├── prompts.py              ← Claude 系统提示（Socratic / 聊天 / 出题 / 多路求解 JSON）
    │   ├── reasoner.py             ← ★多路共识推理器（去 SymPy 判分的正解来源；自带数值归一器）
    │   ├── legacy/                 ← ★退役实现（仅离线兜底，非事实来源）
    │   │   └── sympy_grader.py     ← 退役的 SymPy 判分器（依赖注入，无循环导入；网关不可用时兜底）
    │   ├── auth.py                 ← 账户/会话（SQLite, PBKDF2, 限速）
    │   ├── exam.py                 ← 考试题库（SQLite, 知识点分类法 + 模板题）
    │   └── memory.py               ← 持久经验记忆（SQLite, 自适应难度，跨重启留存）
    ├── requirements.txt            ← 依赖（已移除 easyocr/pytesseract）
    ├── test_reasoner_offline.py    ← ★去符号化判分核心的离线回归（归一器+共识投票，44 例，无网关/无 pytest）
    ├── .env                        ← 密钥（gitignore；含真实值）
    ├── .env.example                ← 密钥模板
    └── data/{users.db,exams.db,memory.db}  ← SQLite 数据（gitignore）
```

> 注：包内模块改用相对导入（`from . import config` 等）；`.env` 与 `data/` 位于
> `backend/` 根（包外一层），`config.py` 用 `__file__.parent.parent / .env` 定位。

---

## 3. 后端架构

### 3.1 运行与启动注意
- **必须从 `backend/` 目录启动**（`uvicorn app.main:app`），否则报 `Could not import module "app.main"`。
- 启动日志会打印三行健康状态：OCR 网关是否配置、用户数、题库题数。
- 单进程；SQLite 每次操作开新连接（FastAPI 线程池下安全，demo 规模够用）。
- `@app.post("/recognize")` 用 `run_in_threadpool` 包裹阻塞的 urllib OCR 调用，避免冻结事件循环。

### 3.2 接口清单（全部在 `main.py`）
| 方法 | 路径 | 作用 | 鉴权 |
|------|------|------|------|
| GET | `/` | 服务信息 | 否 |
| GET | `/problems`, `/problems/random` | 随机练习题（本地题库 + OpenTDB） | 否 |
| POST | `/recognize` | 手写图片→表达式（nex-n2-pro），含 `status` 字段(ok/empty/timeout/error/unconfigured) | 否 |
| POST | `/analyze` | 入口分析：SymPy 求解 + Socratic L0 提示（Claude，模板降级），返回 `ai_provider` | 否 |
| POST | `/hint` | 渐进提示（L1–L4），Claude/模板 | 否 |
| POST | `/claude/chat` | 自由聊天（以 SymPy 结果为锚），降级返回 `provider:unavailable` | 否 |
| GET | `/claude/models` | 模型下拉列表 + 可用性 | 否 |
| POST | `/exam/generate?grade=` | 生成覆盖全部 25 知识点的题集并入库（Claude，模板兜底保证 25/25） | 否 |
| GET | `/exam/catalogue` | 知识点分类法 + 覆盖率 | 否 |
| GET | `/exam/questions` | 题库全部题目 | 否 |
| GET | `/exam/by-tag?tag=&dimension=` | 按标签即时检索题目（SQL 索引） | 否 |
| POST | `/auth/signup`,`/signin`,`/signout` · GET `/auth/me` | 账户/会话 | Bearer（me/signout） |
| GET | `/session/{id}`, `/architecture`, `/policies` | 会话/架构元数据/策略 | 否 |
| POST | `/verify`, `/plot`, `/animate` | SymPy 渲染步骤 / 绘图数据 / 模板动画；`/verify` 可传 `answer`+`session_id`，**判分以多路 LLM 共识为准**（SymPy 仅兜底），返回 `judged_by`（如 `consensus(3/3)`/`sympy-fallback`）`/agreement/ground_truth`，并把"已解出"信号写入经验记忆 | 否 |

> **重要**：曾短暂用 `require_user` 给 `/analyze /hint /recognize /claude/chat` 加鉴权，
> 后**按用户要求移除**（demo 不需登录即可用）。`require_user` / `optional_user` 依赖仍在
> `main.py` 中定义但未使用，可随时复用。

### 3.3 核心类（多在 `main.py`，蓝图命名）
- `LLMReasoner`（`reasoner.py`，单例 `reasoner_engine`）— **判分正解来源**：多路独立求解 +
  共识投票 + 自带去 SymPy 数值归一器；`solve()` 返回共识，`grade()` 比对学生答案。无网关优雅降级。
- `NeuroSymbolicEngine` — SymPy 求解/化简/验证/分类/步骤生成；**判分上已降为兜底**（`/analyze`·
  `/hint`·`/animate`·`/plot` 仍用它做 latex/分类/步骤渲染，待第 3 步迁 `legacy/`）。
- `SocraticEngine` — 5 级提示模板，绝不直接给答案。
- `PolicyEngine` — 输入级策略校验 + 罚分（SEPGA 的输入侧）。
- `ExperienceMemory` → 已迁移为 `backend/app/memory.py::PersistentExperienceMemory`，
  **SQLite 持久化**（`data/memory.db`），跨会话/重启留存；自适应难度由持久统计计算。
  方法签名不变（`get_or_create_session`/`record_interaction`/`add_message`/
  `get_conversation`/`get_adaptive_context`），main.py 调用点未改。
- `BlendingInstructions` — 把表达式/会话/动作编译成提示上下文。
- `Problem` / `OpenTDBProvider` — 练习题模型与外部题源。
- `ManimAnimator` / `SymPyPlotter` — 模板动画 / 绘图数据（非真渲染）。
- `ArchitectureNode` + `/architecture` — **手写**的架构元数据树（非自动生成）。

### 3.4 数据存储（SQLite，`backend/data/`）
- `users.db`：`users`（PBKDF2 盐哈希）、`sessions`（令牌+过期）。
- `exams.db`：`questions`、`question_tags`（按 `(dimension, tag)` 建索引，支持即时按类型检索）。
- `memory.db`：`mem_sessions`、`mem_messages`、`mem_interactions`（持久经验记忆，按
  `session_id` 建索引）。`get_or_create_session` 从这些表重建会话字典。
- 当前数据：1 个账户、~150 道题（每次 `/exam/generate` **追加**一套，会累积增长）。

---

## 4. 前端（`web/`，纯静态）

- 无构建步骤；通过 CDN 加载 MathJax、（demo 页）React+Excalidraw。直接浏览器打开即可。
- 统一调用 `http://localhost:8000`（绝对地址硬编码）。CORS 后端开 `*`。
- 主题：深色玻璃拟态，Outfit 字体，蓝→紫渐变。各页风格一致。
- 流程：`index` →（可选 `demo_sellection` 选年级/知识点）→ `demo_standalone`（核心）。
  另有 `demo_exam`（自动出题）→ "Start the Exam" → 进入 `demo_standalone?exam=1` 分页答题。
- 登录态存 `localStorage`（`mt_token` / `mt_user`）；登录非强制。

### `demo_standalone.html` 两种模式
1. **普通**：随机题 + 白板（原生 Canvas / Excalidraw 可切换 + 全屏）+ 提交 OCR + "Solve with Voice/Text" + AI 聊天/提示/SymPy 绘图。
2. **考试模式**（`?exam=1`）：从 `sessionStorage.mt_exam_questions` 读题，复用题卡+白板 UI，分页（Prev/Next/Exit），每题一个 **"🏷️ Show tags"** 按钮（标签默认隐藏，点击展开两个维度的知识点）。

---

## 5. 考试出题子系统（重点特性）

- **数据源**：`lesson/README.md` 的小学数学六大维度，归并为 **2 个维度/表**：
  - `核心知识领域`（数与代数·图形与几何·量与计量·统计与概率，17 个标签）
  - `综合与思想方法`（综合与实践·数学思想方法，8 个标签）= 共 **25 个知识点标签**。
- **生成**：`POST /exam/generate` 让 Claude 为每个标签出 1 题（每维度 1 次批量调用，返回 JSON 数组），
  每题可跨维度带多个标签（"一个维度可有多个标签"）。任何漏掉的标签由 `exam.py::TEMPLATES`
  确定性补齐 → **覆盖率永远 25/25**。
- **存储/检索**：入库到 `exams.db`，`/exam/by-tag` 经 `(dimension,tag)` 索引即时检索同类题。
- **前端**：`demo_exam.html` 直接访问即自动生成 → 显示 "Start the Exam" → 跳 `demo_standalone?exam=1` 分页答题，标签隐藏在按钮后。
- ⚠️ **慢**：一次生成约 **50s+**（网关慢，见 §6），前端有 spinner。

---

## 6. 已知坑 / 重要经验（接手必读）

1. **`nex-n2-pro` 是推理模型**：先输出 `reasoning_content` 再给 `content`。`max_tokens` 太小会在"思考"中耗尽 → `content` 为空。已设 `NEX_OCR_MAX_TOKENS=1500` 并发送 `chat_template_kwargs:{enable_thinking:false}`。
2. **网关延迟极不稳定**：同一请求见过 5s / 27s / 37s / >150s。是 `computinger.com`（new-api）侧拥塞，非代码问题。`NEX_OCR_TIMEOUT=90`。**不要并发猛打同一 token**（会自我拥塞导致超时）。多智能体/批量调用务必加并发上限与缓存。
3. **`recognize.py` 输出清洗**：模型常返回 `$$...$$`、`\text{}`、并把字符空格化（"1 5"），清洗器会去 `$`、LaTeX、并删除**所有空格**，使 SymPy 可解析。
4. **`polyfill.io` 脚本（历史坑，已修）**：曾在 `demo_standalone.html` `<head>` 引用已失效的 `polyfill.io` 同步脚本拖死加载，现已删除。若日后从旧备份恢复页面，注意别把它带回来。
5. **uvicorn 必须在 backend 目录启动**（否则 import 失败）。
6. **Windows 控制台 cp1252**：用 Python 打印中文会 `UnicodeEncodeError`，调试时加 `PYTHONIOENCODING=utf-8`。
7. **Git Bash 的 `/tmp` ≠ 可被 Python 直接读的路径**：跨 curl→python 传文件用绝对路径或 stdin 管道。
8. **`exam_generate` 会累积题目**：每次访问 `demo_exam.html` 都追加一套 25 题。若要"覆盖式"需改 `exam.py`。
9. **`.env` 含真实密钥且未脱敏**：交接前请轮换 `NEX_OCR_API_KEY` 与 `CLAUDE_API_KEY`。

---

## 7. 待办 / 清理项（给接手者的建议起点）

**已完成（2026-06-26 结构化重构）：**
- [x] **仓库结构化**：删除 `math-tutor-demo/` 套层 → `backend/` + `web/` 提升到根；后端归入 `backend/app/` 包（相对导入，入口 `app.main:app`）；文档归入 `docs/`（设计稿在 `docs/design/`）。
- [x] **完成 `app/` 分包重构**：原空脚手架已替换为真实包，`main.py` 等全部迁入，导入/路径已修复并运行验证通过。
- [x] **删 `polyfill.io`** 那行 `<script>`（坑 #4，已删）。
- [x] **更新 `README.md`**（已重写到当前结构 + 密钥设置说明）。
- [x] **初始化 git 仓库并接 GitHub**：`git@github.com:SkyPhy/math-tutor`（SSH），`.env`/`data/`/`backup/` 均已 gitignore，未上传密钥。
- [x] **合并 `frontend/`**：早期 React 原型迁到 `web/legacy/`（仅参考，去掉 `dist/` 构建产物）。

**仍待办：**
- [x] **`ExperienceMemory` 持久化**到 SQLite（DEVELOPMENT_PLAN 阶段 1，2026-06-26 完成）——
      `backend/app/memory.py`（`data/memory.db`，gitignore）。已验证：提示分级 [1,2,3] 递增，
      重启后会话历史与提示等级留存、续接到 4；接口面与原进程内版本一致。
- [x] **修复 `success_rate` 恒为 0**（Phase 1 收尾，2026-06-26）——`POST /verify` 接受学生
      `answer`，判对错后写入真实 `user_solved` 信号；自适应难度可随历史爬升。已运行验证：答对后
      `success_rate` 0→0.2，跨新进程读盘留存。（判分当前为混合；按新方向将改为 Claude 自主判分，
      见 §1 方向说明。"AI 不判数学对错"的旧铁律**已废止**。）
- [ ] **★ 下一首要目标：放弃 SymPy，大模型自行运算**——求解/判分改 Claude 端到端自主，SymPy 退役，
      正确性靠自我迭代/多路共识。落地方案见 `DEVELOPMENT_PLAN.md` §4「下一首要目标」。
- [ ] **轮换密钥**：`.env` 含真实 key（坑 #9），交接后请轮换 `NEX_OCR_API_KEY` 与 `CLAUDE_API_KEY`。
- [ ] 安全：`/exam/*`、`/analyze` 等均无鉴权（按设计）；如需多用户隔离再用 `require_user`。

---

## 8. 验证文化（沿用此法）

本项目历来用"**运行并观测真实行为**"验证，而非只跑单测：
- **去符号化判分核心**（归一器+共识投票，纯 Python、无网关）：跑 `py -3.12 backend/test_reasoner_offline.py`
  （44 例回归，失败非零退出）。此核心即使在 `.env` 密钥空缺、真链路无法验证时也始终可验。
- 后端：`curl` / Python `urllib` 打接口看返回。
- 前端：headless Chrome（`puppeteer-core`，Chrome 在 `C:/Program Files/Google/Chrome/Application/chrome.exe`）驱动页面、截图、断言 DOM。
- 接手后改任何东西，请同样"跑起来看"，并注意网关慢调用要给足超时。

---

## 9. 关键文件速查

| 想改… | 看这里 |
|-------|--------|
| 接口/路由/核心类 | `backend/app/main.py` |
| Claude 连接 | `backend/app/claude_service.py` + `config.py`（`CLAUDE_*`）|
| 手写 OCR | `backend/app/recognize.py` + `config.py`（`NEX_OCR_*`）|
| 提示词（Socratic/聊天/出题） | `backend/app/prompts.py` |
| 密钥/配置 | `backend/.env`（真实值，gitignore）+ `backend/app/config.py`（唯一读取处）|
| 账户/登录 | `backend/app/auth.py` + `web/sign{in,up}.html` |
| 经验记忆/自适应 | `backend/app/memory.py`（`data/memory.db`）+ `/session/{id}` |
| 出题/题库/标签 | `backend/app/exam.py` + `web/demo_exam.html` + `lesson/README.md` |
| 核心辅导/白板/考试模式 | `web/demo_standalone.html` |
| 路线图 | `docs/DEVELOPMENT_PLAN.md` |
```
