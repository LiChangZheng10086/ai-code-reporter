# ai-code-reporter

AI 驱动的 Git 仓库监控与自动报告机器人。自动追踪代码提交、执行代码审核，通过 Telegram Bot 推送日结/周结/月结报告，并支持自然语言对话查询历史数据。

## 目录

- [项目背景](#项目背景)
- [核心功能](#核心功能)
- [效果预览](#效果预览)
- [技术栈](#技术栈)
- [系统架构](#系统架构)
- [快速开始](#快速开始)
- [详细配置](#详细配置)
- [使用指南](#使用指南)
- [LangGraph 图详解](#langgraph-图详解)
- [API 文档](#api-文档)
- [数据库说明](#数据库说明)
- [项目结构](#项目结构)
- [开发指南](#开发指南)
- [部署](#部署)
- [常见问题](#常见问题)
- [License](#license)

## 项目背景

程序员日常工作中的一个隐形痛点：**写周报、月报、日报**。

无论是团队管理者还是开发者，每到固定时间节点都需要回顾这段时间的代码变更——查 Git 日志、翻 commit 记录、回顾 code review 结果，然后手动整理成报告。这个过程不仅耗时，而且容易遗漏关键信息。

ai-code-reporter 的目标就是将这个流程完全自动化：

1. **自动记录** — 接入 Git 仓库后，系统持续追踪每一次提交和变更
2. **智能分析** — 每次提交自动触发代码审核，发现问题即时标记
3. **主动推送** — 按固定时间节点（日/周/月）自动生成报告并推送到 Telegram
4. **随时查询** — 通过 Telegram Bot 用自然语言随时查询历史数据，不需要打开 Git 命令行

## 核心功能

### Git 仓库监控

- 支持任意 Git 仓库（GitHub、GitLab、Gitee、自建 Git 服务等）
- 支持 HTTPS 协议接入，通过 Token 进行身份认证
- 定时轮询检测新提交，自动拉取最新代码
- 可选 Webhook 模式，接收推送事件实时响应
- 自动提取每次提交的 diff 内容，便于后续分析

### AI 代码审核

每次检测到新提交时，自动触发基于 DeepSeek-v4 的代码审查。覆盖以下维度：

| 维度 | 具体内容 |
|---|---|
| 代码质量 | 命名规范、代码结构、可读性、重复代码 |
| 潜在 Bug | 逻辑错误、边界条件、空指针、并发问题 |
| 安全漏洞 | SQL 注入、XSS、敏感信息泄露、权限缺陷 |
| 性能问题 | 不必要的开销、资源泄漏、慢查询、N+1 问题 |
| 最佳实践 | 框架规范、设计模式、测试覆盖、错误处理 |

审核结果会按风险等级分级：

- **高风险（High）** — 存在安全漏洞或严重 Bug，触发额外的详细修复建议通道
- **中风险（Medium）** — 存在需要关注的质量或性能问题
- **低风险（Low）** — 轻微改进建议或无问题

### 定时报告生成

按三个时间节点自动生成结构化报告，并通过 Telegram Bot 推送：

| 报告类型 | 触发时间 | 内容摘要 |
|---|---|---|
| **日结** | 每天 18:00 | 当日提交概览、涉及作者、修复的问题 |
| **周结** | 每周一 09:00 | 本周数据统计、代码质量趋势、遗留问题 |
| **月结** | 每月 1 号 09:00 | 里程碑回顾、技术债务分析、下月规划 |

报告内容由 DeepSeek-v4 根据原始数据自动撰写，每份报告包含：
- 数据统计（提交数、作者数、审核数）
- AI 生成的趋势总结和改进建议
- 按项目维度分别生成

### 多项目管理

- 支持接入多个 Git 仓库
- 通过 `/addproject` 命令逐一添加
- 通过 `/switch` 命令随时切换当前活动项目
- 活动项目决定：代码监控范围、报告生成范围、对话查询范围
- 也支持跨项目查询（如"所有项目上周情况"）

### 智能对话查询

在 Telegram Bot 中直接发送自然语言消息即可查询历史数据。支持：

- **查询提交记录** — "昨天有谁提交了代码？"、"查一下 user1 上周的提交"
- **查询审核结果** — "上周发现了哪些严重的 Bug？"、"最近有哪些高风险审核"
- **查询报告** — "上个月的月结报告是什么？"、"给我看本周的周报"
- **跨项目查询** — "在 project-a 中查找昨天的提交"

查询流程：用户消息 → 意图识别 → 参数提取（时间/项目/关键词） → 数据库检索 → LLM 组织回答

## 技术栈

| 层 | 技术 | 说明 |
|---|---|---|
| AI/LLM | DeepSeek-v4 | 主要 AI 模型，代码审核和报告生成 |
| 备选 LLM | Ollama（Qwen2.5 等） | 支持切成本地模型 |
| 编排框架 | LangChain、LangGraph | 构建有向图驱动的 AI 工作流 |
| 后端框架 | FastAPI | 异步 Web 框架，提供 API 和生命周期管理 |
| 数据库 | SQLite（WAL 模式） | 零运维成本的嵌入式数据库 |
| ORM | SQLAlchemy | 数据库操作与模型定义 |
| 定时任务 | APScheduler | 异步定时任务调度，支持 cron 表达式 |
| 消息推送 | python-telegram-bot | Telegram Bot API 的 Python 实现 |
| Git 集成 | GitPython | Git 仓库操作（克隆、拉取、diff 提取） |
| 部署 | Docker + Compose | 容器化一键部署 |

## 系统架构

```
┌──────────────────────────────────────────────────────────────────┐
│                        用户配置层                                  │
│    Git 仓库地址 + Token / Telegram Bot Token / TG 用户 ID          │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│                       FastAPI 主服务                              │
│                                                                   │
│  ┌─────────────────────┐     ┌─────────────────────────────┐     │
│  │   Git 监控模块        │     │      代码审核模块             │     │
│  │                     │────▶│                             │     │
│  │  · 定时轮询仓库       │     │  · LangGraph 工作流          │     │
│  │  · Webhook（可选）    │     │  · 风险分级：high/med/low    │     │
│  │  · Diff 提取         │     │  · 高风险触发修复建议通道     │     │
│  └──────────┬──────────┘     └──────────────┬──────────────┘     │
│             │                               │                    │
│             │         ┌─────────────────────┘                    │
│             │         ▼                                         │
│             │  ┌─────────────────────────────────────────┐       │
│             │  │           报告生成引擎                      │       │
│             │  │                                         │       │
│             │  │  · 报告基类（BaseReporter）                │       │
│             │  │  · 日结报告（DailyReporter）               │       │
│             │  │  · 周结报告（WeeklyReporter）              │       │
│             │  │  · 月结报告（MonthlyReporter）             │       │
│             │  │  · DeepSeek-v4 生成总结与建议              │       │
│             │  └───────────────────┬─────────────────────┘       │
│             │                      │                             │
│             │                      ▼                             │
│             │  ┌─────────────────────────────────────────┐       │
│             │  │        定时任务调度器                       │       │
│             │  │                                         │       │
│             │  │  · 每 30 分钟：拉取+审核 → 写数据库         │       │
│             │  │  · 每天 18:00：生成日结 → 推送到 TG         │       │
│             │  │  · 每周一 09:00：生成周结 → 推送到 TG       │       │
│             │  │  · 每月 1 号 09:00：生成月结 → 推送到 TG    │       │
│             │  └───────────────────┬─────────────────────┘       │
│             │                      │                             │
│             ▼                      ▼                             │
│  ┌────────────────────┐  ┌────────────────────────────────┐      │
│  │  项目管理器          │  │   Telegram Bot 模块              │      │
│  │  (ProjectManager)   │  │                                │      │
│  │                     │  │  · 命令处理器（7 个命令）         │      │
│  │  · 添加/移除仓库     │  │  · 自然语言对话处理器            │      │
│  │  · 项目切换          │  │  · 报告推送                     │      │
│  │  · 获取活跃项目      │  │  · 多语言支持                   │      │
│  └────────────────────┘  └──────────────┬─────────────────┘      │
│                                          │                       │
│                                          ▼                       │
│                          ┌──────────────────────────────────┐    │
│                          │        智能对话引擎                  │    │
│                          │                                  │    │
│                          │  · LangGraph 对话工作流            │    │
│                          │  · 意图识别：commit/review/report  │    │
│                          │  · 参数提取：时间/项目/关键词        │    │
│                          │  · 数据库检索 → LLM 回答生成        │    │
│                          │  · 多轮对话上下文管理               │    │
│                          └──────────────────────────────────┘    │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌───────────────────────────────────────────────────────────────────┐
│                          SQLite 数据库                              │
│                                                                   │
│  ┌─────────────┐  ┌──────────┐  ┌────────┐  ┌───────────────┐    │
│  │ user_configs│  │repositories│  │ commits│  │    reviews    │    │
│  │ 用户配置     │  │ 仓库信息   │  │ 提交记录 │  │ 审核结果      │    │
│  └─────────────┘  └──────────┘  └────────┘  └───────────────┘    │
│  ┌─────────────┐  ┌──────────────────┐                            │
│  │   reports   │  │conversation_history│                           │
│  │   报告       │  │    对话历史        │                           │
│  └─────────────┘  └──────────────────┘                            │
└───────────────────────────────────────────────────────────────────┘
```

## 快速开始

### 前置要求

- Python 3.11+
- Git（系统级别安装）

### 第一步：安装

```bash
# 克隆项目
git clone <your-repo-url> ai-code-reporter
cd ai-code-reporter

# 创建虚拟环境（推荐）
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# 安装依赖
pip install -r requirements.txt
```

### 第二步：创建 Telegram Bot

1. 在 Telegram 中搜索 [@BotFather](https://t.me/BotFather)
2. 发送 `/newbot` 创建一个新 Bot
3. 跟随提示设置 Bot 名称和用户名
4. 创建成功后，BotFather 会返回一个 Token，格式如 `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`
5. （可选）发送 `/setcommands` 设置 Bot 命令列表，以获得更好的交互体验：

```
start - 绑定 TG 账号开始使用
addproject - 添加 Git 仓库
projects - 查看所有已接入项目
switch - 切换当前活动项目
removeproject - 移除项目
report - 查看最新报告
help - 查看帮助信息
```

### 第三步：获取 DeepSeek API Key

1. 访问 [DeepSeek 开放平台](https://platform.deepseek.com/)
2. 注册账号并登录
3. 在 API Keys 页面创建一个新的 API Key
4. 复制 Key 备用

### 第四步：配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入你的配置：

```env
# LLM 配置（DeepSeek）
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-your-deepseek-api-key-here
DEEPSEEK_MODEL=deepseek-v4

# Telegram Bot
TG_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11

# 数据库路径
DATABASE_PATH=./data/ai-code-reporter.db

# Git 仓库工作目录
GIT_WORK_DIR=./repos

# 时区
TZ=Asia/Shanghai
```

### 第五步：运行

```bash
# 开发模式
uvicorn app.main:app --reload

# 生产模式（推荐）
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

启动后访问 http://localhost:8000/health 确认服务正常运行。

### 第六步：在 Telegram Bot 中添加仓库

1. 打开你的 Telegram Bot
2. 发送 `/start` 绑定账号
3. 发送 `/addproject myapp | https://github.com/your/repo.git | ghp_your_token | main`
   - 各部分用 `|` 分隔
   - 顺序：项目别名 | 仓库地址 | Git Token | 分支（可选，默认 main）
4. 系统验证成功后，即可开始自动监控

## 详细配置

### 环境变量参考

| 变量名 | 必需 | 默认值 | 说明 |
|---|---|---|---|
| `LLM_PROVIDER` | 否 | `deepseek` | LLM 提供商，可选 `deepseek` 或 `ollama` |
| `DEEPSEEK_API_KEY` | 条件必需 | `""` | DeepSeek API Key，使用 DeepSeek 时必填 |
| `DEEPSEEK_MODEL` | 否 | `deepseek-v4` | DeepSeek 模型名称 |
| `OLLAMA_BASE_URL` | 条件必需 | `http://localhost:11434/v1` | Ollama 服务地址 |
| `OLLAMA_MODEL` | 否 | `qwen2.5:32b` | Ollama 模型名称 |
| `TG_BOT_TOKEN` | 是 | `""` | Telegram Bot Token |
| `DATABASE_PATH` | 否 | `./data/ai-code-reporter.db` | SQLite 数据库文件路径 |
| `GIT_WORK_DIR` | 否 | `./repos` | Git 仓库克隆的工作目录 |

### 切换本地模型

如果希望使用本地 Ollama 部署的模型：

1. 安装 [Ollama](https://ollama.ai/) 并拉取模型，例如 `ollama pull qwen2.5:32b`
2. 修改 `.env`：

```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_MODEL=qwen2.5:32b
# DEEPSEEK_API_KEY=  # 不再需要
```

3. 如果使用 Docker Compose 部署，取消 `docker-compose.yml` 中 Ollama 服务的注释

**注意**：本地模型在代码审核质量上会弱于 DeepSeek-v4，尤其是小参数模型（7B-14B）在处理复杂代码审查时可能出现误判。建议至少使用 32B 以上模型。

## 使用指南

### 添加多个 Git 仓库

```bash
/addproject 项目A | https://github.com/user/repo-a.git | ghp_token1 | main
/addproject 项目B | https://gitlab.com/user/repo-b.git | glpat_token2 | develop
```

添加成功后，系统会为每个仓库分配一个 ID。

### 切换项目

```bash
/projects       # 查看所有项目，找到目标 ID
/switch 2       # 切换到 ID 为 2 的项目
```

切换后，报告生成和对话查询都默认针对当前活动项目。

### 查看报告

```bash
/report         # 查看当前项目的最新报告
```

### 对话查询示例

在 Bot 中直接发送自然语言消息：

| 你的消息 | Bot 的理解与行为 |
|---|---|
| "昨天谁提交了代码？" | 检索当前项目昨天的 commits，列出作者和提交信息 |
| "上周发现了哪些严重的问题？" | 检索当前项目上周的 reviews，筛选 high/medium 风险 |
| "给我看上个月的月结报告" | 检索当前项目上个月的 report |
| "在 项目A 中查一下 user1 的提交" | 切换到项目A，检索 user1 的 commits |
| "今天有审核记录吗？" | 检索当前项目今天的 reviews |
| "你好" | 闲聊模式，不会触发数据库查询 |

## LangGraph 图详解

项目包含两个核心的 LangGraph 有向图。以下从状态定义、节点逻辑到条件路由进行详细说明。

### 图 1：代码审核流水线

#### 状态定义

```python
class ReviewState(TypedDict):
    commit_id: int           # 正在审核的提交 ID
    diff_content: str        # 代码变更内容
    analysis: str            # LLM 初步分析结果（JSON）
    risk_level: str          # 风险等级：high / medium / low
    issues: list             # 发现的问题列表
    suggestions: list        # 修复建议列表
    score: int               # 代码质量评分 0-100
    final_review: str        # 最终审核报告
```

#### 图结构

```
          ┌──────────────┐
          │  analyze_code │  ← 节点 1：LLM 审核代码变更
          └──────┬───────┘
                 ▼
          ┌──────────────┐
          │ classify_risk │  ← 节点 2：解析审核结果，提取风险等级
          └──────┬───────┘
                 │
        ┌────────┴────────┐
        ▼                 ▼
  ┌──────────┐     ┌──────────┐
  │ escalate  │     │ finalize  │  ← 条件分支：high 走 escalate，其他走 finalize
  └─────┬────┘     └─────┬────┘
        │                │
        └────────┬───────┘
                 ▼
          ┌──────────────┐
          │     save      │  ← 节点 4：持久化审核结果
          └──────┬───────┘
                 ▼
                END
```

#### 节点说明

| 节点 | 输入 | 逻辑 | 输出 |
|---|---|---|---|
| `analyze_code` | diff_content | 调用 DeepSeek-v4 按五个维度审查变更，要求以 JSON 格式输出 | analysis（JSON 字符串） |
| `classify_risk` | analysis（JSON） | 解析 JSON，提取 risk_level、issues、score | risk_level + issues + score |
| `escalate` | analysis | 仅 high 风险触发，LLM 生成详细的修复方案和示例代码 | suggestions |
| `finalize` | analysis + suggestions | 合并初步分析和修复建议，生成最终审核报告 | final_review |
| `save` | 所有字段 | 创建 Review 记录，写入数据库 | — |

#### 条件边路由

```python
def _route_by_risk(state: ReviewState) -> Literal["escalate", "finalize"]:
    return "escalate" if state["risk_level"] == "high" else "finalize"
```

#### 核心代码

```python
from langgraph.graph import StateGraph, END

builder = StateGraph(ReviewState)
builder.add_node("analyze_code", self._analyze_code)
builder.add_node("classify_risk", self._classify_risk)
builder.add_node("escalate", self._escalate_review)
builder.add_node("finalize", self._finalize)
builder.add_node("save", self._save_review)

builder.set_entry_point("analyze_code")
builder.add_edge("analyze_code", "classify_risk")
builder.add_conditional_edges(
    "classify_risk",
    self._route_by_risk,
    {"escalate": "escalate", "finalize": "finalize"},
)
builder.add_edge("escalate", "finalize")
builder.add_edge("finalize", "save")
builder.add_edge("save", END)

graph = builder.compile()
result = graph.invoke({"commit_id": 1, "diff_content": "..."})
```

#### 运行示例

当一个新的 commit 被检测到时：

1. `analyze_code` — 系统将 diff 内容发送给 DeepSeek-v4，要求从代码质量、Bug、安全、性能、最佳实践五个维度进行审查，并以 JSON 格式输出评分、风险等级和问题列表
2. `classify_risk` — 解析 JSON，识别出风险等级。例如发现 SQL 注入风险 → `risk_level = "high"`
3. `escalate`（仅 high） — 触发额外通道，要求 LLM 给出具体修复方案和示例代码
4. `finalize` — 合并初步分析和修复建议
5. `save` — 将审核结果写入 `reviews` 表

### 图 2：智能对话查询

#### 状态定义

```python
class ConvState(TypedDict):
    user_id: int            # 用户 ID
    message: str            # 用户发送的消息
    intent: str             # 识别到的意图
    params: dict            # 提取的查询参数
    data: str               # 数据库检索结果
    response: str           # LLM 生成回答
```

#### 图结构

```
          ┌──────────────────┐
          │  classify_intent  │  ← 节点 1：确定用户意图
          └────────┬─────────┘
                   │
          ┌────────┴────────┐
          ▼                 ▼
  ┌──────────────┐   ┌──────────────┐
  │ extract_params│   │ chitchat     │  ← 条件分支
  └───────┬──────┘   └──────┬───────┘
          ▼                 │
  ┌──────────────┐          │
  │ retrieve_data│          │  ← 闲聊不走数据库
  └───────┬──────┘          │
          ▼                 │
  ┌──────────────┐          │
  │generate_resp │          │
  └───────┬──────┘          │
          │                 │
          └────────┬────────┘
                   ▼
                  END
```

#### 节点说明

| 节点 | 输入 | 逻辑 | 输出 |
|---|---|---|---|
| `classify_intent` | user_message | LLM 判断意图：`list_commits` / `list_reviews` / `get_report` / `chitchat` | intent |
| `extract_params` | user_message | LLM 提取时间范围、项目名、关键词等参数 | params（JSON） |
| `retrieve_data` | intent + params | 根据意图查询 commits / reviews / reports 表 | data（文本） |
| `generate_response` | question + data | LLM 根据检索到的数据组织自然语言回答 | response |
| `chitchat_response` | message | 闲聊直接走 LLM，不查询数据库 | response |

#### 核心代码

```python
builder = StateGraph(ConvState)
builder.add_node("classify_intent", self._classify_intent)
builder.add_node("extract_params", self._extract_params)
builder.add_node("retrieve_data", self._retrieve_data)
builder.add_node("generate_response", self._generate_response)
builder.add_node("chitchat_response", self._chitchat_response)

builder.set_entry_point("classify_intent")
builder.add_conditional_edges(
    "classify_intent",
    self._route_intent,
    {"query": "extract_params", "chitchat": "chitchat_response"},
)
builder.add_edge("extract_params", "retrieve_data")
builder.add_edge("retrieve_data", "generate_response")
builder.add_edge("generate_response", END)
builder.add_edge("chitchat_response", END)
```

#### 运行示例

用户发送："上周 project-a 有谁提交了代码？"

1. `classify_intent` → `list_commits`
2. `extract_params` → `{"time_range": "上周", "project": "project-a", "keyword": ""}`
3. `retrieve_data` → 查询 commits 表，返回匹配的提交记录
4. `generate_response` → "project-a 上周共有 5 次提交：张三 3 次、李四 2 次..."

## API 文档

服务启动后，FastAPI 自动生成 OpenAPI 文档，访问 http://localhost:8000/docs 即可查看。

### 健康检查

```
GET /health
```

响应：

```json
{
  "status": "ok",
  "llm_provider": "deepseek"
}
```

### 根路径

```
GET /
```

响应：

```json
{
  "app": "ai-code-reporter",
  "version": "0.1.0",
  "description": "AI-powered Git repository monitoring and reporting bot"
}
```

## 数据库说明

### 表结构

#### user_configs — 用户配置

| 字段 | 类型 | 说明 |
|---|---|---|
| id | INTEGER | 主键 |
| tg_bot_token | TEXT | Telegram Bot Token |
| tg_user_id | TEXT | 用户 TG ID（唯一） |
| active_project_id | INTEGER | 当前活动项目 ID |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

#### repositories — 仓库信息

| 字段 | 类型 | 说明 |
|---|---|---|
| id | INTEGER | 主键 |
| user_id | INTEGER | 外键 → user_configs.id |
| name | TEXT | 项目别名 |
| git_url | TEXT | Git 仓库地址 |
| git_token | TEXT | Git 访问令牌 |
| branch | TEXT | 监听分支（默认 main） |
| is_active | INTEGER | 是否启用（0/1） |
| last_fetched_at | DATETIME | 最后拉取时间 |
| created_at | DATETIME | 创建时间 |

#### commits — 提交记录

| 字段 | 类型 | 说明 |
|---|---|---|
| id | INTEGER | 主键 |
| repo_id | INTEGER | 外键 → repositories.id |
| commit_hash | TEXT | Commit SHA（唯一） |
| author | TEXT | 提交作者 |
| message | TEXT | Commit 消息 |
| diff_content | TEXT | 代码变更内容 |
| committed_at | DATETIME | 提交时间 |
| fetched_at | DATETIME | 系统拉取时间 |

#### reviews — 审核记录

| 字段 | 类型 | 说明 |
|---|---|---|
| id | INTEGER | 主键 |
| commit_id | INTEGER | 外键 → commits.id |
| risk_level | TEXT | 风险等级（low/medium/high） |
| score | INTEGER | 代码评分（0-100） |
| issues | JSON | 发现的问题列表 |
| suggestions | JSON | 修复建议列表 |
| review_content | TEXT | 完整审核报告 |
| created_at | DATETIME | 创建时间 |

#### reports — 报告

| 字段 | 类型 | 说明 |
|---|---|---|
| id | INTEGER | 主键 |
| user_id | INTEGER | 外键 → user_configs.id |
| repo_id | INTEGER | 外键 → repositories.id |
| report_type | TEXT | 类型（daily/weekly/monthly） |
| period_start | DATETIME | 统计开始时间 |
| period_end | DATETIME | 统计结束时间 |
| content | TEXT | 报告内容 |
| status | TEXT | 状态（pending/sent/failed） |
| sent_at | DATETIME | 推送时间 |
| created_at | DATETIME | 创建时间 |

#### conversation_history — 对话历史

| 字段 | 类型 | 说明 |
|---|---|---|
| id | INTEGER | 主键 |
| user_id | INTEGER | 外键 → user_configs.id |
| session_id | TEXT | 会话 ID（按天分组） |
| role | TEXT | 角色（user/assistant） |
| message | TEXT | 消息内容 |
| repo_context | INTEGER | 对话关联项目 ID |
| created_at | DATETIME | 创建时间 |

### ER 关系

```
user_configs  1──N  repositories  1──N  commits  1──1  reviews
     │                                          
     └──── 1──N  reports (通过 user_id + repo_id)
     └──── 1──N  conversation_history
```

## 项目结构

```
ai-code-reporter/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI 入口与服务生命周期
│   ├── config.py                  # 配置管理（pydantic-settings）
│   ├── database.py                # SQLite 数据库连接与初始化
│   ├── models.py                  # SQLAlchemy 数据模型（6 张表）
│   ├── schemas.py                 # Pydantic 数据验证模型
│   ├── llm.py                     # LLM 客户端工厂（DeepSeek / Ollama）
│   │
│   ├── git_monitor/               # Git 仓库监控模块
│   │   ├── __init__.py
│   │   ├── fetcher.py             # Git 克隆/拉取、diff 提取
│   │   └── parser.py              # 提交记录查询与解析
│   │
│   ├── reviewer/                  # 代码审核模块 ★ LangGraph
│   │   ├── __init__.py
│   │   ├── engine.py              # LangGraph 审核流水线图
│   │   └── prompts.py             # 审核提示词模板
│   │
│   ├── reporter/                  # 报告生成模块
│   │   ├── __init__.py
│   │   ├── base.py                # 报告基类（公共方法）
│   │   ├── daily.py               # 日结报告生成
│   │   ├── weekly.py              # 周结报告生成
│   │   ├── monthly.py             # 月结报告生成
│   │   └── templates.py           # 报告模板
│   │
│   ├── bot/                       # Telegram Bot 模块
│   │   ├── __init__.py
│   │   ├── bot.py                 # Bot 初始化与启动
│   │   ├── handlers.py            # 命令处理器
│   │   └── project_manager.py     # 项目管理器
│   │
│   ├── conversation/              # 对话引擎 ★ LangGraph
│   │   ├── __init__.py
│   │   ├── engine.py              # LangGraph 对话工作流
│   │   ├── retriever.py           # 数据库检索器
│   │   ├── memory.py              # 多轮对话上下文管理
│   │   └── prompts.py             # 意图分类/参数提取提示词
│   │
│   └── scheduler/                 # 定时任务调度
│       ├── __init__.py
│       └── tasks.py               # APScheduler 任务定义
│
├── tests/                         # 测试
│   └── __init__.py
│
├── data/                          # 数据持久化（SQLite）
├── repos/                         # Git 仓库克隆目录
├── .env.example                   # 环境变量模板
├── .gitignore
├── docker-compose.yml             # Docker Compose 编排
├── Dockerfile                     # 容器镜像
├── requirements.txt               # Python 依赖
└── README.md                      # 项目文档
```

## 开发指南

### 本地开发

```bash
# 克隆项目
git clone <your-repo-url> ai-code-reporter
cd ai-code-reporter

# 使用虚拟环境
python -m venv .venv
source .venv/bin/activate

# 安装开发依赖
pip install -r requirements.txt

# 启动开发服务器（自动热加载）
uvicorn app.main:app --reload --log-level debug
```

### 代码规范

- Python 版本：3.11+
- 命名规范：模块名小写蛇形，类名大驼峰，函数/变量小写蛇形
- 类型注解：所有函数必须包含类型注解
- 数据库操作：通过 SQLAlchemy ORM，禁止裸 SQL

### 测试

```bash
# 运行测试（待完善）
pytest tests/
```

### 添加一个新的报告类型

1. 在 `app/reporter/` 下创建新的报告类，继承 `BaseReporter`
2. 在 `app/reporter/templates.py` 中添加对应的模板
3. 在 `app/scheduler/tasks.py` 中添加对应的定时任务函数和调度

## 部署

### Docker 部署

```bash
# 构建并启动
docker compose up -d

# 查看日志
docker compose logs -f

# 停止
docker compose down
```

### 服务器推荐配置

| 场景 | 配置 | 参考月成本 |
|---|---|---|
| 仅 DeepSeek API | 2C4G 云服务器 | ~¥50-80 |
| DeepSeek API + 本地 Ollama（7B） | 4C8G + T4 显卡 | ~¥500-800 |
| 大量仓库 + 高并发 | 4C8G 起 | ~¥200+ |

### 环境变量管理

生产环境建议使用 Docker 的 env_file 方式管理配置，不要将 `.env` 文件提交到版本控制。

```bash
# 服务器上
scp .env user@your-server:/path/to/ai-code-reporter/.env
```

## 常见问题

### Q：是否需要提供 Git 仓库的写入权限？

不需要。Git Token 只需要 **只读权限**（pull），系统不会对仓库做任何写入操作。

### Q：可以同时监控多少个 Git 仓库？

没有硬性限制。每个仓库会定时轮询，30 分钟的轮询间隔下，10 个仓库对系统资源的影响可以忽略不计。

### Q：DeepSeek API 的费用大概是多少？

取决于代码变更量。按日均 50 次 commit 计算，每次审核消耗约 2000-8000 tokens，日消耗约 10 万 tokens，约 **¥0.10/天**（按 DeepSeek 定价）。报告生成消耗更少。

### Q：是否支持私有化部署？

完全支持。所有组件（包括数据库）都在本地运行，不依赖外部 SaaS 服务（除 LLM API 调用外）。如需完全离线，可切换为本地 Ollama 模型。

### Q：是否可以接入 Gitee 或自建 GitLab？

可以。只要仓库支持 HTTPS 协议和 Token 认证即可。GitLab 的自建实例也可以正常接入。

### Q：如果某个仓库在轮询时不可用会怎样？

系统会记录错误日志并跳过该仓库，不会影响其他仓库的正常运行。下一次轮询时会重新尝试。

### Q：如何更新系统？

```bash
git pull                     # 拉取最新代码
docker compose down          # 停止容器
docker compose build --no-cache  # 重新构建
docker compose up -d         # 重新启动
```

## License

MIT
