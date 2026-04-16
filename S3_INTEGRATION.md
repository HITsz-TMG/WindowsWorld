# Agent-S3 Integration for Desktop Env Benchmark

本文档说明如何在 desktop_env 评测框架中使用 Agent-S3。

## 前置要求

1. 安装 Agent-S (gui-agents):
   ```bash
   pip install gui-agents
   ```
   或从源码安装:
   ```bash
   cd /path/to/Agent-S
   pip install -e .
   ```

2. 安装 Tesseract (S3 agent 依赖):
   - macOS: `brew install tesseract`
   - Windows: 下载安装 [Tesseract](https://github.com/tesseract-ocr/tesseract)
   - Linux: `sudo apt-get install tesseract-ocr`

3. 配置 API Keys:
   ```bash
   export OPENAI_API_KEY=<your_openai_key>
   export ANTHROPIC_API_KEY=<your_anthropic_key>  # 如果使用 Anthropic
   ```

4. 设置 Grounding Model (推荐 UI-TARS-1.5-7B):
   - 参考 [Hugging Face Inference Endpoints](https://huggingface.co/learn/cookbook/en/enterprise_dedicated_endpoints) 设置

## 使用方法

### 方法 1: 使用命令行参数

```bash
# 使用 S3 agent 运行评测
python main.py \
    -c 1 \
    -m gpt-4o \
    -a pyautogui \
    -o screenshot \
    --agent-type s3 \
    --model-provider openai \
    --ground-provider huggingface \
    --ground-url http://localhost:8080 \
    --ground-model ui-tars-1.5-7b \
    --grounding-width 1920 \
    --grounding-height 1080 \
    --platform windows \
    --enable-reflection
```

### 方法 2: 使用脚本

Windows:
```batch
run_s3.bat
```

Linux/macOS:
```bash
chmod +x run_s3.sh
./run_s3.sh
```

### 方法 3: 直接使用 hf_run.py

```bash
python hf_run.py \
    -b benchmark.json \
    -v "E:\vmx\Windows0\Windows0.vmx" \
    -m gpt-4o \
    -a pyautogui \
    -o screenshot \
    --agent-type s3 \
    --ground-provider huggingface \
    --ground-url http://localhost:8080 \
    --ground-model ui-tars-1.5-7b
```

## 参数说明

### 基础参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `-c, --count` | 并行 VM 数量 | 必填 |
| `-m, --model-name` | 主模型名称 | 必填 |
| `-a, --action-space` | 动作空间类型 | 必填 |
| `-o, --observation-type` | 观察类型 | 必填 |
| `--agent-type` | Agent 类型 (`prompt` 或 `s3`) | `prompt` |

### S3 Agent 参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--model-provider` | 主模型提供商 | `openai` |
| `--model-url` | 自定义 API URL | `""` |
| `--model-api-key` | 主模型 API Key | `""` |
| `--model-temperature` | 生成温度 | `None` |

### Grounding Model 参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--ground-provider` | Grounding 模型提供商 | `huggingface` |
| `--ground-url` | Grounding 模型端点 URL | `""` |
| `--ground-model` | Grounding 模型名称 | `ui-tars-1.5-7b` |
| `--ground-api-key` | Grounding 模型 API Key | `""` |
| `--grounding-width` | Grounding 坐标宽度 | `1920` |
| `--grounding-height` | Grounding 坐标高度 | `1080` |

### 其他参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--platform` | 操作系统平台 | `windows` |
| `--max-trajectory-length` | 最大轨迹长度 | S3: `8`, prompt: `3` |
| `--enable-reflection` | 启用反思 agent | `True` |
| `--disable-reflection` | 禁用反思 agent | `False` |

## Grounding Model 设置

### UI-TARS-1.5-7B (推荐)
- 坐标分辨率: `1920 x 1080`
- 提供商: `huggingface`

### UI-TARS-72B
- 坐标分辨率: `1000 x 1000`
- 提供商: `huggingface`

## 注意事项

1. **S3 Agent 需要先初始化环境**: 在调用 `predict()` 之前必须调用 `initialize_with_env(env)`

2. **动作格式**: S3 agent 输出的是 Python 代码字符串，与 `pyautogui` action_space 兼容

3. **反思机制**: 默认启用反思 agent，可以通过 `--disable-reflection` 禁用

4. **轨迹长度**: S3 agent 默认保留 8 步历史，可通过 `--max-trajectory-length` 调整

## 文件结构

```
desktop_env/
├── hf_run.py              # 主运行脚本 (已适配 S3)
├── main.py                # 多进程运行入口 (已适配 S3)
├── mm_agents/
│   ├── agent.py           # 原有 PromptAgent
│   └── s3_agent.py        # S3 Agent 适配器 (新增)
├── run_s3.bat             # Windows 运行脚本
├── run_s3.sh              # Linux/macOS 运行脚本
└── S3_INTEGRATION.md      # 本文档
```

## 故障排除

### 1. ModuleNotFoundError: No module named 'gui_agents'
确保已安装 gui-agents: `pip install gui-agents`

### 2. Agent not initialized 错误
确保在调用 `predict()` 前已经初始化环境

### 3. Grounding model 连接失败
检查 `--ground-url` 配置是否正确，确保 Grounding model 服务已启动

### 4. Tesseract 相关错误
确保已安装 Tesseract 并配置了正确的 PATH
