# WindowsWorld: A Process-Centric Benchmark of Autonomous GUI Agents in Professional Cross-Application Environments

![Paper](https://img.shields.io/badge/Paper-ACL%202026%20Findings-blue)
![License](https://img.shields.io/badge/License-Apache%202.0-green)
![Python](https://img.shields.io/badge/Python-3.11+-yellow)

WindowsWorld is a computer-use benchmark in cross-application workflows designed to systematically assess GUI Agents on complex multistep tasks that mirror real-world professional activities.

## Installation

Support: Windows 10/11, Windows Server 2022/2025

### VMWare Workstation Pro

[Official Website](https://www.vmware.com/products/desktop-hypervisor/workstation-and-fusion)

[Onedrive: ver. 25H2](https://1drv.ms/u/c/e8642dbeac76c2db/IQCdgyZYiEbEQJXobPBkeVxEAVDPP8v1urchER7YzbMiEKI?e=p9ladN)

> You may need to sign up a Broadcom account to download the software (free). Any version is OK.
>
> *Notice: newer versions do not support Chinese.*

Require `vmrun` in PATH.

Default installation path is `C:\Program Files (x86)\VMware\VMware Workstation\vmrun.exe`, check it by:

```bash
vmrun
```

### Python

Requires (and validated on) `Python 3.11+`.

First, clone this repository:

```bash
git clone https://github.com/HITsz-TMG/WindowsWorld.git
cd WindowsWorld
```

Then, install dependencies:

```bash
pip install -r requirements.txt
```

### API Key Configure

Set the environment variables for keys:

| Model Type |         URL         |         KEY          |
|:----------:|:-------------------:|:--------------------:|
|    GPT     |  `OPENAI_API_KEY`   |  `OPENAI_API_BASE`   |
|   Gemini   |  `GEMINI_API_KEY`   |  `GEMINI_API_BASE`   |
|   Claude   | `ANTHROPIC_API_KEY` | `ANTHROPIC_API_BASE` |
|    Qwen    |   `QWEN_API_KEY`    |   `QWEN_API_BASE`    |

### VM Image

Import the virtual machine by following this guide: `./Installation Guide.md`

The virtual machine's folder structure should be like this:

```plaintext
D:\Virtual Machines
├── Windows0
│   ├── Windows0-disk1.vmx
│   ├── Windows0.vmdk
│   └── ...
├── Windows1
│   ├── Windows1-disk1.vmx
│   ├── ...
```

## Usage

### Run the Benchmark: Single Model

```bash
python hf_run.py
    -b benchmark.json \
    -v path_to_vm_image_folder \
    -m model_name \
    -a pyautogui/computer_13 \
    -o screenshot/som/a11y/screenshot_a11y \
    -c parallel_count
```

- `path_to_vm_image_folder` is the folder that contains the VM image you downloaded, such as: `D:\Virtual Machines\WindowsWorld`.
- `model_name` literally decides which model api to use (in code).
- `-a` is action space:
  - `pyautogui` is to directly use `PyAutoGUI`;
  - `computer_13` accords to this file: `./mm_agents/prompts.py (line 44)`.
- `-o` is observation type:
  - `screenshot` is to only use screenshot as observation;
  - `a11y` is to only use accessibility information as observation;
  - `screenshot_a11y` is to use both screenshot and accessibility information as observation;
  - `som` is Set-of-Mark.

Example:

```bash
python hf_run.py \
  -b benchmark.json \
  -v "D:\Virtual Machines" \
  -m gemini-3-flash-preview \
  -a computer_13 \
  -o screenshot \
  -c 1
```

### Run Agent

Support S3/UIPath...

## Acknowledgement

This project builds upon [OSWorld](https://github.com/xlang-ai/OSWorld).
A substantial portion of the evaluation framework is derived from or adapted from OSWorld.
We thank the OSWorld authors for open-sourcing their benchmark and infrastructure.

The OSWorld-derived portions of this repository remain subject to the Apache License 2.0.
