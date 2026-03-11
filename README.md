<div align="center">

# TaskCaptain

**把目标变成持续执行，直到交付结果。**

TaskCaptain 是面向 Codex 的本地任务执行控制台：
它把 **User ↔ Agent**、**Agent ↔ Codex**、**执行日志** 明确拆开，让任务推进过程可见、可控、可追踪。

[English](./README-EN.md) · [用户指南](./docs/USER_GUIDE.md) · [部署说明](./docs/DEPLOYMENT.md)

</div>

![TaskCaptain hero](./hero1.png)

---

## 概述

TaskCaptain 不是一个普通聊天界面。

它的定位是：**接管任务推进，持续驱动 Codex 执行，并把状态、对话和日志保留在一个可检查的本地工作台里。**

对于需要持续推进、反复迭代、随时插入新约束的任务，TaskCaptain 提供的是一个更接近“执行控制台”的工作方式，而不是一次性回答。

---

## 核心能力

### 持续推进，而不是一次性回答

TaskCaptain 会把任务作为连续执行流来处理，而不是在给出一轮建议后结束。

### Agent 与 Codex 分工清晰

- **Agent**：负责理解目标、规划步骤、监督进度、整理新增要求
- **Codex**：负责在工作目录内执行实现、产出交付物、返回执行结果

### 全程可见、便于排障

界面保留三类信息：

- **User ↔ Agent** 控制对话
- **Agent ↔ Codex** 执行对话
- **原始日志**

这使得任务为什么继续、为什么失败、卡在什么位置，都有迹可查。

### 本地优先，结构清晰

每个任务拥有独立的：

- 配置
- 状态
- 日志
- Agent Profile
- Codex 会话

状态以磁盘文件形式持久化，便于检查、备份、迁移和手工修复。

---

## 适用场景

TaskCaptain 适合以下类型的工作：

- 需要 AI 连续推进，而不是只回答问题
- 需要在后台持续执行的开发或自动化任务
- 需要保留完整过程以便复盘、调试或继续推进的项目
- 需要复用稳定 Agent 身份与配置的多任务工作流
- 需要把“监督者”和“执行者”明确分离的 Codex 工作台

---

## 产品结构

### 首页

首页提供：

- 任务列表
- Agent Profiles 列表
- 创建新任务
- 创建可复用 Profile
- 批量删除非运行中任务

### 任务详情页

任务详情页提供：

- 配置详情
- User ↔ Agent 对话区
- Agent ↔ Codex 对话区
- Self-Test 结果
- Agent 日志
- Codex 日志

### 可复用 Agent Profile

Profile 用于保存 Agent 的默认身份与行为配置，例如：

- model
- thinking
- soul
- skills
- description

任务可继承 Profile，并在单任务范围内进行局部覆盖。

---

## 主要功能

- 本地浏览器 UI
- 每个任务独立状态与日志
- 可复用 Agent Profiles
- Self-Test 自检
- Start / Continue Run
- Stop Run
- 中途追加新要求
- 保存当前 Agent 为可复用 Profile
- 中英双语界面
- 无前端构建步骤

---

## 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/LongWeihan/taskcaptain.git
cd taskcaptain
```

### 2. 启动

```bash
chmod +x run.sh restart.sh
./run.sh
```

默认访问地址：

```text
http://127.0.0.1:8765
```

### 3. 可选：加载本地环境配置

```bash
cp .env.example .env
set -a
source .env
set +a
./run.sh
```

---

## 运行要求

- Linux / WSL2 推荐
- Python 3.10+
- `bash`
- `ss`
- `acpx` 已安装，或通过 `ACPX_BIN` 指定路径

---

## 配置项

TaskCaptain 支持通过环境变量调整启动行为。

### 常用环境变量

```bash
export PRODUCTS_UI_HOST=127.0.0.1
export PRODUCTS_UI_PORT=8765
export PRODUCTS_UI_DEFAULT_LANG=zh
export PRODUCTS_UI_DEFAULT_OPENAI_BASE_URL=http://127.0.0.1:8317/v1
export PRODUCTS_UI_DEFAULT_PRODUCT_FOLDER="$PWD/workspace"
export PRODUCTS_UI_PROXY=
export PRODUCTS_UI_NO_PROXY=127.0.0.1,localhost,::1
export ACPX_BIN=/absolute/path/to/acpx
```

### 示例

```bash
export PRODUCTS_UI_PORT=8877
export PRODUCTS_UI_DEFAULT_OPENAI_BASE_URL=http://127.0.0.1:8317/v1
./run.sh
```

更多部署说明见：[docs/DEPLOYMENT.md](./docs/DEPLOYMENT.md)

---

## 运行方式说明

### `run.sh`

- 若端口未占用，则后台启动 TaskCaptain
- 若服务已在运行，则直接提示现有地址和日志位置，不重复拉起

### `restart.sh`

- 停止当前端口上的 TaskCaptain 进程
- 等待端口释放
- 必要时强制结束残留进程
- 清空日志后重新启动

---

## 目录结构

```text
taskcaptain/
├── app/
│   └── server.py
├── data/
│   ├── claw-profiles/
│   ├── products/
│   └── trash/
├── docs/
│   ├── ARCHITECTURE.md
│   ├── DATA_MODEL.md
│   ├── DEPLOYMENT.md
│   └── USER_GUIDE.md
├── logs/
├── runs/
├── workspace/
├── .env.example
├── .gitignore
├── CONTRIBUTING.md
├── LICENSE
├── Makefile
├── README.md
├── README-EN.md
├── SECURITY.md
├── hero.png
├── restart.sh
└── run.sh
```

---

## 文档

- [英文 README](./README-EN.md)
- [用户指南](./docs/USER_GUIDE.md)
- [部署说明](./docs/DEPLOYMENT.md)
- [架构说明](./docs/ARCHITECTURE.md)
- [数据模型](./docs/DATA_MODEL.md)
- [贡献指南](./CONTRIBUTING.md)
- [安全策略](./SECURITY.md)

---

## 安全说明

TaskCaptain 当前定位为**可信本地环境中的本地控制台**。

仓库当前不包含：

- 多用户认证
- 权限隔离
- 面向公网暴露的访问控制

如果需要远程访问，请务必在反向代理之后部署，并自行补充：

- 身份认证
- HTTPS
- IP 限制
- 最小权限运行策略

详细建议见：[SECURITY.md](./SECURITY.md)

---

## 开源与规范

- License: [MIT](./LICENSE)
- Contributing: [CONTRIBUTING.md](./CONTRIBUTING.md)
- Security: [SECURITY.md](./SECURITY.md)

---

## License

本项目采用 [MIT License](./LICENSE)。
