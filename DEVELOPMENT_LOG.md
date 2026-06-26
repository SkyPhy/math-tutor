# 开发流程总结 / Development Log

> 面向接手的下一位 AI 开发者。本文件记录**项目是怎么一步步建起来的**（开发历程 + 关键决策 +
> 踩过的坑），是过程叙事；**当前真实状态**见 [`docs/HANDOFF.md`](docs/HANDOFF.md)，**未来路线图**见
> [`docs/DEVELOPMENT_PLAN.md`](docs/DEVELOPMENT_PLAN.md)。三者互补，建议按此顺序读：
> 本文（怎么来的）→ HANDOFF（现在是什么）→ DEVELOPMENT_PLAN（往哪去）。
>
> 最后更新：2026-06-26。

---

## 0. 一句话定位

一个**苏格拉底式（引导而非直接给答案）小学数学 AI 辅导系统**：FastAPI 后端用 **SymPy 做确定性
验证锚点** + **Claude 组织自然语言引导** + **nex-n2-pro 视觉模型做手写 OCR**；纯静态多页前端
提供白板、聊天、自动出题/考试。**核心铁律：SymPy 是唯一事实来源，AI 永不自行另算答案。**

---

## 1. 贯穿全程的设计原则（先理解这些，再读代码）

1. **神经-符号分工**：神经网络（Claude）负责"创造/表达"，符号系统（SymPy）负责"保证正确"。
   任何数学结论必须经 `NeuroSymbolicEngine` 求解/校验，Claude 只能围绕已验证结果组织语言。
2. **Socratic 约束不可绕过**：默认不直接给最终答案，分 5 级渐进提示（系统提示词强制）。
3. **优雅降级**：未配置 `.env` 时——提示退回模板引擎、OCR 退回 mock、Claude 不可用返回
   fallback——系统**始终可跑**。
4. **零额外依赖**：只用标准库 + fastapi/uvicorn/sympy/pillow。**不引入** anthropic SDK、
   python-dotenv、torch/easyocr——所有外部调用用 `urllib` 手写，`.env` 用自写小加载器。
5. **12-factor 密钥隔离**：所有密钥只存在 `backend/.env`（gitignore），只经
   `backend/app/config.py` 读取，源码里无硬编码 key。
6. **验证文化**：用"**运行应用 + 观测真实行为**"（curl / urllib / headless 浏览器）验证，
   **而非只跑单测**。每个特性都跑起来看真实返回。

---

## 2. 开发历程（按时间）

### 阶段 A — Claude 集成（2026-06-23）
把 Claude 接入既有 SymPy 后端，作为推理增强。
- 传输层选 **Anthropic 兼容网关**（自建 new-api 代理 `https://www.computinger.com`），
  标准 `x-api-key` 头，`urllib` 调 `/v1/messages`——刻意**不引入 anthropic SDK**。
- 新增 `config.py`（.env 加载 + 设置）、`claude_service.py`（超时 / 断路器 / 每会话限速）、
  `prompts.py`（Socratic + 聊天系统提示，把 SymPy 结果钉为 ground truth，4 级前不许泄底）。
- `/analyze`、`/hint` 改为先调 Claude、失败回退模板；新增 `GET /claude/models`、
  `POST /claude/chat`。响应带 `ai_provider`（`claude:<id>` 或 `template`）。

### 阶段 B — OCR 换血：EasyOCR → nex-n2-pro（2026-06-23）
移除 torch/easyocr/pytesseract（重、装不动），改用 **OpenAI 兼容视觉模型** `nex-n2-pro`。
- `recognize.py` 重写为 urllib：PNG 预处理 → base64 data URL → `Bearer` 鉴权 →
  读 `choices[0].message.content`。
- **三个坑全踩过并修好**（详见 §4）：推理模型耗尽 token、阻塞冻结事件循环、网关延迟剧烈抖动。

### 阶段 C — 多页前端 + 账户系统（2026-06-23）
- 深色玻璃拟态多页前端（`index` / `signin` / `signup` / `demo_sellection` /
  `demo_standalone` / `demo_exam`）。
- `auth.py`：SQLite + PBKDF2-HMAC-SHA256(200k) + 每用户盐 + `hmac.compare_digest` +
  令牌会话（30 天）+ 暴力破解限速（5 次/5 分钟 → 429）。

### 阶段 D — 自动出题 / 考试子系统（2026-06-23）
- `exam.py`：把 `lesson/README.md` 的六大维度归并为 **2 个维度共 25 个知识点标签**；
  `POST /exam/generate` 让 Claude 每标签出 1 题（每维度 1 次批量调用，返回 JSON 数组），
  任何漏标签由 `TEMPLATES` 确定性补齐 → **覆盖率永远 25/25**。
- SQLite 存 `questions` + `question_tags`（按 `(dimension,tag)` 建索引，即时按类型检索）。

### 阶段 E — 仓库结构化 + 接 GitHub（2026-06-26）
把散乱的 `math-tutor-demo/` 套层重构为规范布局，并首次接入版本控制。
- 后端归入 **`backend/app/` Python 包**（相对导入 `from . import config`，入口
  `app.main:app`）；前端提升到 `web/`（旧 React 原型移到 `web/legacy/`）；文档归入 `docs/`。
- 密钥隔离落实：`.env`(gitignore) + `.env.example`(模板) + README 教新人怎么建。
- 双备份：备份①= git 历史/GitHub；备份②= 本地全量副本（不上传）。
- 推到 `git@github.com:SkyPhy/math-tutor`（SSH）。**未上传任何密钥/DB。**

### 阶段 F — 持久化经验记忆（Phase 1，2026-06-26）✅
把 `ExperienceMemory` 从进程内字典（重启即失）迁到 SQLite。
- 新增 `backend/app/memory.py::PersistentExperienceMemory`，表 `mem_sessions` /
  `mem_messages` / `mem_interactions`（按 session_id 建索引），`data/memory.db`（gitignore）。
- `get_or_create_session` 从表**重建**原来的会话字典结构 → main.py 调用点零改动；
  `add_message` 用鸭子类型（`.role/.content/.hint_level`）以免 memory.py 反向依赖 main 的模型。
- **运行验证**：`/hint` 分级 `[1,2,3]` 递增；**重启进程后** `/session/{id}` 仍有历史，
  下一次 `/hint` 续接到 4（非重置为 1）。同时复测了慢接口（auth 全生命周期、/recognize、
  /exam/generate 25/25）全部通过。

---

## 3. 当前架构速览

```
math/
├── README.md  DEVELOPMENT_LOG.md(本文)  .gitignore
├── backend/
│   ├── app/                  ← Python 包，入口 app.main:app
│   │   ├── main.py           ← 主程序（2100+ 行单体：所有路由 + 核心类）
│   │   ├── config.py         ← .env 加载 + Claude/OCR 配置（唯一读密钥处）
│   │   ├── claude_service.py ← Claude 网关客户端（urllib，超时/断路器/限速）
│   │   ├── recognize.py      ← nex-n2-pro 视觉 OCR（urllib，图像预处理）
│   │   ├── prompts.py        ← Claude 系统提示（Socratic/聊天/出题 JSON）
│   │   ├── auth.py           ← 账户/会话（SQLite, PBKDF2）
│   │   ├── exam.py           ← 考试题库（SQLite, 25 知识点 + 模板兜底）
│   │   └── memory.py         ← ★持久经验记忆（SQLite, 跨重启留存）
│   ├── requirements.txt  .env.example
│   ├── .env(gitignore)   data/{users,exams,memory}.db(gitignore)
├── web/                      ← 纯静态前端（无构建）+ legacy/（旧 React 原型，仅参考）
├── docs/  HANDOFF.md · DEVELOPMENT_PLAN.md · design/（蓝图原文）
└── lesson/README.md         ← 知识点分类法（出题数据源）
```

**运行**（必须在 `backend/` 目录内，因为 app 是包）：
```bash
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
# 前端：浏览器直接打开 web/index.html（静态，调 http://localhost:8000）
```

核心类（均在 `main.py`，蓝图命名）：`NeuroSymbolicEngine`(SymPy，最可靠) ·
`SocraticEngine`(5 级提示) · `PolicyEngine`(输入级策略) · `BlendingInstructions`(提示上下文)。
经验记忆已外移到 `memory.py`。

---

## 4. 必读的坑（接手前先看，能省几小时）

1. **`nex-n2-pro` 是推理模型**：先吐 `reasoning_content` 再给 `content`，`max_tokens` 太小
   会在"思考"中耗尽 → content 空。已设 `NEX_OCR_MAX_TOKENS=1500` + 发
   `chat_template_kwargs:{enable_thinking:false}`。
2. **网关延迟极不稳定**：同一请求见过 2.7s / 7s / 16s / 27s / >150s，是 `computinger.com`
   侧拥塞，非代码问题。`NEX_OCR_TIMEOUT=90`。**别并发猛打同一 token**（会自我拥塞）。
   多智能体/批量调用务必加并发上限 + 缓存。
3. **OCR 输出清洗**：模型常返回 `$$...$$`、`\text{}`，并把字符空格化（"1 5"）；清洗器去
   `$`/LaTeX/**所有空格**，使 SymPy 可解析。
4. **uvicorn 必须在 `backend/` 目录启动**，否则 `Could not import module "app.main"`。
5. **Windows 控制台 cp1252**：Python 打印中文会 `UnicodeEncodeError`，调试加
   `PYTHONIOENCODING=utf-8`。
6. **`/exam/generate` 会累积**：每次访问 `demo_exam.html` 追加一套 25 题。要"覆盖式"需改 `exam.py`。
7. **`recognize` 返回 `text` 字段**（不是 `expression`）；状态机 `ok/empty/timeout/error/
   unconfigured` 经 `status` 透传给前端。
8. **`.env` 含真实密钥未脱敏**：交接前请轮换 `NEX_OCR_API_KEY` 与 `CLAUDE_API_KEY`。

---

## 5. 给下一位 AI 开发者的建议起点

**未完成 / 建议优先级**（详见 `docs/DEVELOPMENT_PLAN.md`，按"价值/风险"排）：

1. **轮换密钥**（唯一带安全后果的待办，坑 #8）。
2. **Phase 1 深化**：`memory.py` 已落地基础；可加 `skills` 技能固化表 + `GET /memory/{session}`
   聚合视图。注意 `success_rate` 现恒为 0——`record_interaction` 调用点从不传 `user_solved=true`，
   若要自适应难度真正爬升，需接一个"学生已解出"信号。
3. **让 demo 真正消费选择参数**：`demo_sellection.html` 传了 `?grade=&core=&methods=`，
   但 `demo_standalone.html` 尚未使用。
4. **Phase 2 起**（DEVELOPMENT_PLAN）：Data Manager 自动架构树 → ALMAS 多智能体编排 →
   SEPGA 计划级治理 → AST/SPA 自修改（默认 dry-run）→ Lattice 护栏演化。M5–M6 风险最高，
   务必在 M4 策略治理就绪后再启动。

**工作方式约定**（沿用，很重要）：
- 改任何东西后，**跑起来看真实返回**（curl/urllib/headless），不要只跑单测；慢调用给足超时。
- 保持零额外依赖、密钥只走 `config.py`、SymPy 永远是数学结论的最终裁判。

---

## 6. 关键文件速查

| 想改… | 看这里 |
|-------|--------|
| 接口/路由/核心类 | `backend/app/main.py` |
| Claude 连接 | `backend/app/claude_service.py` + `config.py`（`CLAUDE_*`）|
| 手写 OCR | `backend/app/recognize.py` + `config.py`（`NEX_OCR_*`）|
| 提示词 | `backend/app/prompts.py` |
| 密钥/配置 | `backend/.env`（gitignore）+ `backend/app/config.py`（唯一读取处）|
| 账户/登录 | `backend/app/auth.py` + `web/sign{in,up}.html` |
| 经验记忆/自适应 | `backend/app/memory.py`（`data/memory.db`）+ `/session/{id}` |
| 出题/题库/标签 | `backend/app/exam.py` + `web/demo_exam.html` + `lesson/README.md` |
| 核心辅导/白板/考试 | `web/demo_standalone.html` |
| 现状快照 / 路线图 | `docs/HANDOFF.md` / `docs/DEVELOPMENT_PLAN.md` |
