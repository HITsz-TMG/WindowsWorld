# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a **multi-agent desktop environment evaluation framework** for benchmarking AI agents on realistic desktop automation tasks. The system orchestrates parallel execution across multiple Virtual Machines (VMs) and supports multiple AI agent frameworks including PromptAgent, Agent-S3, CoAct, and UIPath.

## Core Architecture

### Entry Points

- **`main.py`** - Multi-VM parallel benchmark runner. Splits benchmark tasks across multiple worker processes, each controlling a separate VM.
- **`hf_run.py`** - Single VM execution script. The core evaluation engine that runs tasks sequentially.
- **`show_result.py`** - Results aggregator and analyzer.

### Key Components

**`desktop_env/`** - Core environment module
- `desktop_env.py` - Main `DesktopEnv` class: VM management, action execution, observation capture
- `providers/` - VM provider implementations (VMware, AWS, Azure, GCP, Docker, VirtualBox, etc.)
- `controllers/` - Application-specific controllers (Python, Setup)
- `evaluators/` - Task evaluation system with metrics for various applications (Chrome, VLC, LibreOffice, VSCode, etc.)

**`mm_agents/`** - Agent implementations
- `agent.py` - `PromptAgent`: Baseline agent using simple LLM prompting
- `s3_agent.py` - Agent-S3 adapter with UI-TARS visual grounding and reflection
- `coact_agent.py` - CoAct multi-agent framework (Orchestrator + Coding + CUA)
- `uipath_adapter.py` - UIPath Computer Use adapter
- `agi_agent.py` - AGI agent implementation
- `openai_cua_agent.py` - OpenAI Computer Use Agent

### Agent Factory Pattern

All agents are created via `create_agent()` in `hf_run.py:17`. The function takes:
- `agent_type`: "prompt", "s3", "coact", or "uipath"
- `args`: Dictionary of configuration parameters
- `env`: DesktopEnv instance (required for S3, CoAct, UIPath)

**Important**: Advanced agents (S3, CoAct, UIPath) require `initialize_with_env(env)` to be called before `predict()`.

### Action Spaces

- **`pyautogui`** - Python code generation (e.g., `pyautogui.click(x=100, y=200)`)
- **`computer_13`** - Structured action format with 13 action types

### Observation Types

- **`screenshot`** - Base64 encoded PNG screenshots
- **`a11y_tree`** - Accessibility tree as XML
- **`screenshot_a11y_tree`** - Both screenshot and accessibility tree
- **`som`** - Screenshot with visual bounding box tags

## Common Commands

### Installation

```bash
pip install -r requirements.txt
```

### Running Benchmarks

**Single VM (hf_run.py):**
```bash
python hf_run.py \
    --benchmark-path benchmark.json \
    --vmx-path "path/to/vm.vmx" \
    --model-name "gpt-4o" \
    --action-space "pyautogui" \
    --observation-type "screenshot" \
    --agent-type "prompt"
```

**Multi-VM parallel (main.py):**
```bash
python main.py \
    -c 4 \
    -m "gpt-4o" \
    -a "pyautogui" \
    -o "screenshot" \
    --agent-type "s3"
```

**Using shell scripts:**
- `run_s3.sh` / `run_s3.bat` - Agent-S3
- `run_coact.sh` / `run_coact.bat` - CoAct
- `run_uipath.sh` / `run_uipath.bat` - UIPath

### Viewing Results

```bash
python show_result.py
```

Results are stored in `hf_result/` directory with task IDs as subdirectories.

## Benchmark Format

Tasks are defined in JSON format (`benchmark.json`). Each task contains:

```json
{
  "task_id": "unique_id",
  "instruction": "Task description",
  "task_category": "L1|L2|L3|L4",
  "evaluation_metrics": {
    "intermediate_checks": {...},
    "success_criterion": "Final success condition"
  },
  "environment": {
    "setup": [...],
    "files": {...},
    "urls": [...]
  }
}
```

**Task categories** determine default max steps:
- L1: 15 steps (simple)
- L2: 25 steps (medium)
- L3: 40 steps (complex)
- L4: 20 steps (high complexity - often fails with explicit "FAIL" expected)

## Agent-Specific Configuration

### Agent-S3

Requires UI-TARS grounding model for visual element localization:

```bash
--agent-type s3 \
--model-provider openai \
--ground-provider huggingface \
--ground-url "http://localhost:8000/v1" \
--ground-model "ui-tars-1.5-7b" \
--grounding-width 1920 \
--grounding-height 1080
```

**Dependencies**: `pip install gui-agents`, Tesseract OCR

### CoAct

Multi-agent system with Orchestrator, Coding Agent, and CUA:

```bash
--agent-type coact \
--orchestrator-model "o3" \
--coding-model "o4-mini" \
--cua-model "computer-use-preview" \
--cut-off-steps 200
```

**Note**: CoAct handles full task execution internally via `run_task()` method, bypassing standard step loop.

### UIPath

Professional RPA capabilities:

```bash
--agent-type uipath \
--uipath-model-name "gpt-4o" \
--max-steps 15
```

## Environment Variables

Required environment variables:

```bash
# OpenAI / GPT models
export OPENAI_API_KEY="sk-..."
export OPENAI_API_BASE="https://api.openai.com"  # Optional custom endpoint

# Anthropic / Claude
export ANTHROPIC_API_KEY="sk-..."

# Google / Gemini
export GOOGLE_API_KEY="..."
export GEMINI_API_BASE="..."  # Often required for Gemini

# HuggingFace (for UI-TARS)
export HF_TOKEN="hf_..."

# Azure OpenAI
export AZURE_OPENAI_API_KEY="..."
export AZURE_OPENAI_ENDPOINT="..."

# Qwen (Alibaba)
# API key often embedded in code for evaluation
```

## Important Implementation Details

### Accessibility Tree Namespaces

The code uses platform-specific XML namespaces for accessibility trees:
- Windows: `https://accessibility.windows.example.org/ns/*`
- Ubuntu: `https://accessibility.ubuntu.example.org/ns/*`

See `agent.py:39-48` for namespace definitions used in parsing.

### Trajectory Length Defaults

- **PromptAgent**: 3 steps (`max_trajectory_length=3`)
- **S3/CoAct/UIPath**: 8 steps (`max_trajectory_length=8`)

This affects how much conversation history is included in each LLM call.

### Coordinate System

Different models use different coordinate systems. The code includes coordinate transformation logic (see `agent.py:678-696`) that scales coordinates by 1.92x (width) and 1.08x (height) for certain model responses.

### VM Management

VMs are managed through the `providers/` module. The default is VMware (`provider_name="vmware"`). The VM path template in `main.py` uses `{i}` placeholder for worker ID:
```
"C:\\Users\\...\\Windows{i}\\Windows{i}.vmx"
```

### Evaluation Logic

Evaluation is performed by calling `evaluate()` in `hf_run.py:331` which:
1. Uses a vision model (qwen3-vl-plus) to analyze screenshots
2. Checks intermediate checkpoints and final success state
3. Returns JSON with intermediate_results and final_result

For L4 tasks, evaluation is simplified: checks if last action contains "fail".

## Adding a New Agent

1. Create adapter class in `mm_agents/your_agent.py`
2. Implement wrapper class with:
   - `initialize_with_env(env)` - Setup with DesktopEnv
   - `predict(instruction, obs)` - Return (response, actions)
   - `reset(logger, vm_ip)` - Reset internal state
3. Add to `create_agent()` factory in `hf_run.py:17`
4. Add argument group in `get_parser()` in `hf_run.py:532`
5. Update agent_kwargs handling in `hf_run.py:main()`

## Troubleshooting

**"ModuleNotFoundError: No module named 'gui_agents'"**
```bash
pip install gui-agents
# or install from source
cd /path/to/Agent-S && pip install -e .
```

**"Agent not initialized"**
Call `agent.initialize_with_env(env)` before first `predict()` call.

**Tesseract OCR errors (S3 agent)**
- macOS: `brew install tesseract`
- Linux: `sudo apt-get install tesseract-ocr`
- Windows: Download from https://github.com/tesseract-ocr/tesseract

**Context length exceeded**
The code automatically truncates message history (see `hf_run.py:606-621` for retry logic).

## Multi-VM Parallel Execution

`main.py` uses Python multiprocessing to run tasks in parallel:
1. Loads benchmark JSON
2. Shuffles tasks for balanced distribution
3. Splits into N chunks (where N = `--count`)
4. Creates N worker processes, each with:
   - Separate VMX path (using template)
   - Subset of benchmark tasks
5. Monitors worker status via Queue
6. Aggregates results with `show_result.py`

## Related Documentation

- `MULTI_AGENT_GUIDE.md` - Comprehensive guide for multi-agent integration (Chinese)
- `S3_INTEGRATION.md` - Agent-S3 specific documentation (Chinese)
