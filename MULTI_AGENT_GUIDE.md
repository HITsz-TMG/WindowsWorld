# Multi-Agent Integration Guide for Desktop Env Benchmark

本文档说明如何将 Agent-S3、CoAct 和 UIPath 智能体集成到 desktop_env 评测框架中。

## 概述

支持的智能体框架:

| Agent | 说明 | 主要特点 |
|-------|------|----------|
| **Prompt** | 基础 Prompt Agent | 简单易用，快速部署 |
| **Agent-S3** | 高级 GUI 智能体 | UI-TARS 视觉定位、反思机制 |
| **CoAct** | 协作式多智能体 | Orchestrator + CUA + Coding 协作 |
| **UIPath** | UIPath Computer Use | 专业 RPA 能力 |

---

## 📦 安装依赖

### 通用依赖

```bash
pip install -r requirements.txt
```

### Agent-S3 依赖

```bash
# 安装 gui-agents
pip install gui-agents

# 或从源码安装
cd /path/to/Agent-S
pip install -e .

# 安装 Tesseract OCR
# macOS: brew install tesseract
# Windows: 下载 https://github.com/tesseract-ocr/tesseract
# Linux: sudo apt-get install tesseract-ocr
```

### CoAct 依赖

```bash
# 安装 autogen 相关依赖
pip install pyautogen

# 进入 OSWorld 目录，安装 mm_agents
cd /path/to/OSWorld
pip install -e .
```

### UIPath 依赖

```bash
# 安装 UIPath SDK
pip install uipath

# 或从 OSWorld 目录安装
cd /path/to/OSWorld
pip install -e .
```

---

## 🔑 环境变量配置

### OpenAI

```bash
export OPENAI_API_KEY="your-openai-api-key"
```

### Anthropic (Claude)

```bash
export ANTHROPIC_API_KEY="your-anthropic-api-key"
```

### Google (Gemini)

```bash
export GOOGLE_API_KEY="your-google-api-key"
```

### HuggingFace (用于 UI-TARS)

```bash
export HF_TOKEN="your-huggingface-token"
```

### Azure/AWS (用于 CoAct)

```bash
export AZURE_OPENAI_API_KEY="your-azure-key"
export AZURE_OPENAI_ENDPOINT="https://your-endpoint.openai.azure.com/"
export AWS_ACCESS_KEY_ID="your-aws-access-key"
export AWS_SECRET_ACCESS_KEY="your-aws-secret-key"
```

---

## 🚀 快速开始

### 使用 Prompt Agent (默认)

```bash
python hf_run.py \
    --benchmark-file benchmark.json \
    --vmx-path "E:\vmx\Windows0\Windows0.vmx" \
    --model-name "gpt-4o" \
    --action-space "pyautogui" \
    --observation-type "screenshot" \
    --agent-type "prompt"
```

### 使用 Agent-S3

```bash
python hf_run.py \
    --benchmark-file benchmark.json \
    --vmx-path "E:\vmx\Windows0\Windows0.vmx" \
    --model-name "gpt-4o" \
    --action-space "pyautogui" \
    --observation-type "screenshot" \
    --agent-type "s3" \
    --model-provider "openai" \
    --ground-url "http://localhost:8000/v1" \
    --ground-provider "vllm"
```

### 使用 CoAct

```bash
python hf_run.py \
    --benchmark-file benchmark.json \
    --vmx-path "E:\vmx\Windows0\Windows0.vmx" \
    --model-name "o3" \
    --action-space "computer_13" \
    --observation-type "screenshot" \
    --agent-type "coact" \
    --orchestrator-model "o3" \
    --coding-model "o4-mini" \
    --cua-model "computer-use-preview" \
    --cut-off-steps 200
```

### 使用 UIPath

```bash
python hf_run.py \
    --benchmark-file benchmark.json \
    --vmx-path "E:\vmx\Windows0\Windows0.vmx" \
    --model-name "gpt-4o" \
    --action-space "pyautogui" \
    --observation-type "screenshot" \
    --agent-type "uipath" \
    --uipath-model-name "gpt-4o" \
    --max-steps 15
```

---

## 📊 多机并行运行 (main.py)

```bash
# 使用 4 个 VM 并行运行 S3 Agent
python main.py \
    -c 4 \
    -m "gpt-4o" \
    -a "pyautogui" \
    -o "screenshot" \
    --agent-type "s3" \
    --model-provider "openai" \
    --ground-url "http://localhost:8000/v1"

# 使用 CoAct
python main.py \
    -c 2 \
    -m "o3" \
    -a "computer_13" \
    -o "screenshot" \
    --agent-type "coact" \
    --orchestrator-model "o3" \
    --coding-model "o4-mini"

# 使用 UIPath
python main.py \
    -c 4 \
    -m "gpt-4o" \
    -a "pyautogui" \
    -o "screenshot" \
    --agent-type "uipath" \
    --max-steps 20
```

---

## 📋 完整参数说明

### 基础参数

| 参数 | 说明 | 默认值 | 必填 |
|------|------|--------|------|
| `--benchmark-file` / `-b` | Benchmark JSON 文件路径 | - | ✅ |
| `--vmx-path` / `-v` | VMX 文件路径 | - | ✅ |
| `--model-name` / `-m` | 主模型名称 | - | ✅ |
| `--action-space` / `-a` | 动作空间 (pyautogui, computer_13) | - | ✅ |
| `--observation-type` / `-o` | 观察类型 (screenshot, a11y_tree, screenshot_a11y_tree) | - | ✅ |
| `--agent-type` | Agent 类型 | "prompt" | ❌ |
| `--platform` | 操作系统 | "windows" | ❌ |
| `--max-trajectory-length` | 最大轨迹长度 | 按任务类型 | ❌ |
| `--client-password` | sudo 密码 | "" | ❌ |

### Agent-S3 参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--model-provider` | 模型提供商 (openai, anthropic, google) | "openai" |
| `--model-url` | 自定义 API URL | "" |
| `--model-api-key` | API 密钥 (默认从环境变量) | "" |
| `--model-temperature` | 生成温度 | None |
| `--ground-provider` | 定位模型提供商 | "huggingface" |
| `--ground-url` | 定位模型 URL | "" |
| `--ground-model` | 定位模型名称 | "ui-tars-1.5-7b" |
| `--ground-api-key` | 定位模型密钥 | "" |
| `--grounding-width` | 坐标分辨率宽度 | 1920 |
| `--grounding-height` | 坐标分辨率高度 | 1080 |
| `--enable-reflection` | 启用反思 | True |
| `--disable-reflection` | 禁用反思 | False |

### CoAct 参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--orchestrator-model` | Orchestrator 模型 | 使用 model-name |
| `--coding-model` | Coding Agent 模型 | "o4-mini" |
| `--cua-model` | CUA 模型 | "computer-use-preview" |
| `--orchestrator-max-steps` | Orchestrator 最大步数 | 15 |
| `--coding-max-steps` | Coding Agent 最大步数 | 20 |
| `--cua-max-steps` | CUA 最大步数 | 25 |
| `--cut-off-steps` | 总截止步数 | 200 |
| `--oai-config-path` | OpenAI 配置文件路径 | "" |
| `--sleep-after-execution` | 动作执行后等待时间 | 0.5 |
| `--region` | AWS 区域 | "" |

### UIPath 参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--uipath-model-name` | UIPath 模型名称 | 使用 model-name |
| `--max-steps` | 最大步数 | 15 |

---

## 📁 文件结构

```
desktop_env/
├── hf_run.py              # 主运行脚本
├── main.py                # 多进程运行脚本
├── benchmark.json         # 评测任务文件
├── mm_agents/
│   ├── __init__.py
│   ├── agent.py           # Prompt Agent (PromptAgent)
│   ├── s3_agent.py        # Agent-S3 适配器
│   ├── coact_agent.py     # CoAct 适配器
│   ├── uipath_adapter.py  # UIPath 适配器
│   └── uipath_agent.py    # UIPath 基础实现
├── run_s3.bat             # S3 Windows 运行脚本
├── run_s3.sh              # S3 Linux/macOS 运行脚本
└── MULTI_AGENT_GUIDE.md   # 本文档
```

---

## 🔧 架构详解

### Agent-S3 架构

```
S3AgentAdapter
├── MLLM (主模型)
│   └── gpt-4o / claude / gemini
├── Grounding (视觉定位)
│   └── UI-TARS-1.5-7B
├── OSWorldACI (动作接口)
└── Worker (任务执行器)
    └── Reflection Agent (可选)
```

**工作流程:**
1. 接收任务指令
2. 截图并识别 UI 元素
3. UI-TARS 定位目标坐标
4. 生成动作并执行
5. 反思机制验证结果

**适配器类:**
- `S3AgentAdapter`: 封装 Agent-S3 核心功能
- `S3PromptAgentWrapper`: 兼容 hf_run.py 循环接口

### CoAct 架构

```
CoAct Multi-Agent System
├── OrchestratorAgent (编排器)
│   └── o3 / o4-mini
├── CUA Agent (GUI 操作)
│   └── computer-use-preview
└── Coding Agent (代码执行)
    └── o4-mini
```

**工作流程:**
1. Orchestrator 分析任务
2. 分配子任务给 CUA 或 Coding Agent
3. Agent 执行并返回结果
4. Orchestrator 协调下一步
5. 循环直到任务完成

**适配器类:**
- `CoActAgentAdapter`: 封装 CoAct 框架
- `CoActPromptAgentWrapper`: 兼容 hf_run.py 循环接口

### UIPath 架构

```
UIPath Computer Use
├── UiPathComputerUseV1
│   └── 专业 RPA 引擎
└── Action Mapper
    └── OSWorld 动作转换
```

**工作流程:**
1. 接收任务和截图
2. UIPath 分析并规划
3. 生成 RPA 动作序列
4. 转换为 OSWorld 格式
5. 执行并获取结果

**适配器类:**
- `UIPathAgentAdapter`: 封装 UIPath SDK
- `UIPathPromptAgentWrapper`: 兼容 hf_run.py 循环接口

---

## 🛠️ 设置 Grounding Model

Agent-S3 需要 UI-TARS 视觉定位模型来识别 UI 元素坐标。

### 选项 1: 使用 HuggingFace 托管服务

```bash
export HF_TOKEN="your-huggingface-token"
```

```bash
--ground-provider "huggingface" \
--ground-url "https://api-inference.huggingface.co/models/ByteDance/UI-TARS-1.5-7B" \
--ground-model "ui-tars-1.5-7b"
```

### 选项 2: 本地部署 vLLM

```bash
# 启动 vLLM 服务
vllm serve ByteDance/UI-TARS-1.5-7B --port 8000
```

```bash
--ground-provider "vllm" \
--ground-url "http://localhost:8000/v1" \
--ground-model "ui-tars-1.5-7b"
```

### 选项 3: HuggingFace Inference Endpoints

参考 [HF Inference Endpoints 文档](https://huggingface.co/learn/cookbook/en/enterprise_dedicated_endpoints)

---

## 🐛 调试指南

### 验证安装

```python
# 验证 Agent-S3
import gui_agents
from gui_agents.s3.aci.OSWorldACI import OSWorldACI
print("Agent-S3 ✓")

# 验证 CoAct
from mm_agents.coact.operator_agent import OrchestratorAgent
print("CoAct ✓")

# 验证 UIPath
from uipath.models import UiPathComputerUseV1
print("UIPath ✓")
```

### 启用详细日志

```python
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### 常见问题

**Q1: ImportError: No module named 'gui_agents'**
```bash
pip install gui-agents
# 或
cd /path/to/Agent-S && pip install -e .
```

**Q2: Tesseract 相关错误**
```bash
# macOS
brew install tesseract

# Linux
sudo apt-get install tesseract-ocr

# Windows: 下载安装并配置 PATH
```

**Q3: CoAct 无法连接模型**
- 检查 `--oai-config-path` 配置文件
- 确认环境变量已设置
- 验证 API 密钥有效

**Q4: UIPath 动作映射失败**
- 检查 action_space 是否正确
- 确认 UIPath SDK 版本兼容
- 查看日志中的原始动作

**Q5: Grounding 模型返回空结果**
1. 检查模型服务是否运行
2. 确认分辨率设置正确 (1920x1080 或 1000x1000)
3. 尝试降低温度参数

**Q6: Agent not initialized 错误**
确保在调用 `predict()` 前已经初始化环境

---

## 📈 性能对比

| 指标 | Prompt | Agent-S3 | CoAct | UIPath |
|------|--------|----------|-------|--------|
| 单步响应 | ~2s | ~5s | ~8s | ~3s |
| 复杂任务 | ★★☆ | ★★★★ | ★★★★★ | ★★★ |
| 部署难度 | ★☆☆ | ★★★ | ★★★★ | ★★☆ |
| 资源消耗 | 低 | 中 | 高 | 中 |
| 任务成功率 | 基础 | 较高 | 最高 | 良好 |

---

## 📝 任务类型与步数配置

benchmark.json 中的任务按复杂度分为 L1-L4 四个级别:

| 级别 | 任务复杂度 | 默认最大步数 | 说明 |
|------|----------|-------------|------|
| L1 | 简单 | 8 | 单一简单操作 |
| L2 | 中等 | 15 | 多步骤操作 |
| L3 | 复杂 | 20 | 复杂多步骤任务 |
| L4 | 高复杂 | 30 | 需要推理的复杂任务 |

可通过 `--max-trajectory-length` 覆盖默认值。

---

## 📚 参考链接

- [Agent-S GitHub](https://github.com/simular-ai/Agent-S)
- [UI-TARS 模型](https://huggingface.co/ByteDance/UI-TARS-1.5-7B)
- [OSWorld Benchmark](https://github.com/xlang-ai/OSWorld)
- [UIPath Documentation](https://docs.uipath.com/)
- [AutoGen Documentation](https://microsoft.github.io/autogen/)

---

## 更新日志

- **v1.1** - 添加 CoAct 和 UIPath 智能体支持
- **v1.0** - 初始版本，支持 Prompt 和 Agent-S3
