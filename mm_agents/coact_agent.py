"""
CoAct Agent Adapter for HF Benchmark
Adapts CoAct (Orchestrator + GUI + Coding) framework to work with the desktop_env benchmark.
"""

import base64
import json
import logging
import os
import sys
import glob
import shutil
import traceback
from typing import Dict, List, Tuple, Any

logger = logging.getLogger("desktopenv.agent")

# Task description for the orchestrator
TASK_DESCRIPTION = """# Your role
You are a task solver, you need to complete a computer-using task step-by-step.
1. Describe the screenshot.
2. Provide a detailed plan, including a list of user requirements like specific file name, file path, etc.
3. Follow the following instructions and complete the task with your skills.
    - If you think the task is impossible to complete (no file, wrong environment, etc.), reply with "INFEASIBLE" to end the conversation.
    - **Do not** do (or let coding/GUI agent do) anything else out of the user's instruction like change the file name. This will make the task fail.
    - Check every screenshot carefully and see if it fulfills the task requirement.
    - You MUST try the Coding Agent first for file operation tasks like spreadsheet modification.
4. Verify the result and see if it fulfills the user's requirement.

# Your helpers
You can use the following tools to solve the task. You can only call one of gui agent or coding agent per reply:

## Programmer
Let a programmer to solve a subtask you assigned. 
The Programmer can write python or bash code to modify almost everything in the computer, like files, apps, system settings, etc. 
It requires a environment description and a detailed task description. As detailed as possible.
Can use any python package you instructed.
Will return a summary with the output of the code.
When letting coding agent to modify the spreadsheet, after the task completed, you MUST make sure EVERY modified value in the spreadsheet is in the desired position (e.g., filled in the expected cell) by a GUI Operator.
After that, if anything is wrong, tell the programmer to modify it.

## GUI Operator
Let a GUI agent to solve a subtask you assigned. 
GUI agent can operate the computer by clicking and typing (but not accurate). 
Require a detailed task description.
When you call GUI agent, it will only have a **20-step** budget to complete your task. Each step is a one-time interaction with OS like mouse click or keyboard typing. Please take this into account when you plan the actions.
If you let GUI Operator to check the result, you MUST let it close and reopen the file because programmer's result will NOT be updated to the screen. 
"""


class CoActAgentAdapter:
    """
    Adapter class to wrap CoAct framework for use with desktop_env benchmark.

    CoAct uses an orchestrator agent that coordinates between:
    - GUI Agent (CUA - Computer Use Agent)
    - Coding Agent (for programmatic operations)
    """

    def __init__(
        self,
        # Model configuration
        orchestrator_model: str = "o3",
        coding_model: str = "o4-mini",
        cua_model: str = "computer-use-preview",

        # Step limits
        orchestrator_max_steps: int = 15,
        coding_max_steps: int = 20,
        cua_max_steps: int = 25,
        cut_off_steps: int = 200,

        # API configuration for Orchestrator and Coding Agent
        api_base: str = "",
        api_key: str = "",
        # API configuration for CUA (GUI Agent) - uses OpenAI Computer Use API
        cua_api_base: str = "",
        cua_api_key: str = "",
        compatibility_mode: bool = False,  # Enable for transit/proxy APIs that don't support advanced features

        # Environment configuration
        platform: str = "windows",
        screen_width: int = 1920,
        screen_height: int = 1080,
        sleep_after_execution: float = 0.5,

        # OAI config
        oai_config_path: str = "",

        # Provider config
        provider_name: str = "vmware",
        region: str = "",
        client_password: str = "",

        # Other
        action_space: str = "pyautogui",
        observation_type: str = "screenshot",
        **kwargs
    ):
        """
        Initialize CoAct Agent Adapter.
        """
        self.orchestrator_model = orchestrator_model
        self.coding_model = coding_model
        self.cua_model = cua_model
        self.api_base = api_base
        self.api_key = api_key
        self.cua_api_base = cua_api_base
        self.cua_api_key = cua_api_key
        self.compatibility_mode = compatibility_mode

        self.orchestrator_max_steps = orchestrator_max_steps
        self.coding_max_steps = coding_max_steps
        self.cua_max_steps = cua_max_steps
        self.cut_off_steps = cut_off_steps
        
        self.platform = platform
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.sleep_after_execution = sleep_after_execution
        
        self.oai_config_path = oai_config_path
        self.provider_name = provider_name
        self.region = region
        self.client_password = client_password
        
        self.action_space = action_space
        self.observation_type = observation_type
        
        self.env = None
        self.logger = logger
        self.vm_ip = None
        self.history_save_dir = ""
        
        # Will be initialized when needed
        self.llm_config = None
        self.orchestrator = None
        self.orchestrator_proxy = None
        
    def reset(self, logger=None, vm_ip=None):
        """Reset agent state."""
        if logger is not None:
            self.logger = logger
        if vm_ip is not None:
            self.vm_ip = vm_ip
            
    def initialize_with_env(self, env):
        """Initialize the CoAct agent with the desktop environment."""
        self.env = env
        self.logger.info(f"CoAct Agent initialized with orchestrator: {self.orchestrator_model}")
        
    def set_history_dir(self, history_dir: str):
        """Set the directory for saving history."""
        self.history_save_dir = history_dir
        os.makedirs(history_dir, exist_ok=True)
        
    def run_task(self, instruction: str, task_config: dict = None) -> Tuple[float, Dict]:
        """
        Run a complete task using CoAct framework.
        
        This method handles the full orchestration loop internally.
        
        Args:
            instruction: Task instruction
            task_config: Task configuration dictionary
            
        Returns:
            Tuple of (score, result_info)
        """
        if self.env is None:
            raise RuntimeError("Environment not initialized. Call initialize_with_env() first.")
            
        try:
            # Import CoAct components
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'OSWorld'))
            from mm_agents.coact.operator_agent import OrchestratorAgent, OrchestratorUserProxyAgent
            from mm_agents.coact.autogen import LLMConfig
        except ImportError as e:
            self.logger.error(f"Failed to import CoAct components: {e}")
            raise ImportError("CoAct framework not available. Please install from OSWorld.")
        
        retry = 0
        max_retries = 3

        while retry < max_retries:
            try:
                # Create LLM config
                if self.oai_config_path and os.path.exists(self.oai_config_path):
                    llm_config = LLMConfig.from_json(path=self.oai_config_path).where(model=self.orchestrator_model)
                else:
                    # Build config dict with api_base and api_key if provided
                    config_dict = {
                        "api_type": "openai",
                        "model": self.orchestrator_model,
                    }
                    if self.api_base:
                        config_dict["base_url"] = self.api_base
                    if self.api_key:
                        config_dict["api_key"] = self.api_key

                    # Compatibility mode for proxy/transit APIs
                    # Only enabled when explicitly set via compatibility_mode=True
                    # This prevents errors from unsupported parameters like reasoning_effort, tools, etc.
                    if self.compatibility_mode:
                        # Enable compatibility mode - use basic parameters only
                        config_dict["extra_body"] = {}
                        config_dict["temperature"] = 0.5
                        # Note: Official APIs (Qwen, OpenAI, etc.) should keep compatibility_mode=False
                        #       to use all features like tools, thinking, reasoning_effort, etc.

                    llm_config = LLMConfig(config_list=[config_dict])

                with llm_config:
                    orchestrator = OrchestratorAgent(
                        name="orchestrator",
                        system_message=TASK_DESCRIPTION
                    )
                    orchestrator_proxy = OrchestratorUserProxyAgent(
                        name="orchestrator_proxy",
                        is_termination_msg=lambda x: x.get("content", "") and (
                            x.get("content", "")[0]["text"].lower() == "terminate" or
                            x.get("content", "")[0]["text"].lower() == "infeasible"
                        ),
                        human_input_mode="NEVER",
                        llm_config=llm_config,  # Pass llm_config to enable coding agent and GUI agent
                        provider_name=self.provider_name,
                        path_to_vm=None,  # We use existing env
                        os_type="Windows" if self.platform.lower() == "windows" else "Ubuntu",  # OS type for coding agent
                        screen_width=self.screen_width,
                        screen_height=self.screen_height,
                        sleep_after_execution=self.sleep_after_execution,
                        code_execution_config=False,
                        history_save_dir=self.history_save_dir,
                        llm_model=self.coding_model,
                        truncate_history_inputs=self.cua_max_steps + 1,
                        cua_max_steps=self.cua_max_steps,
                        coding_max_steps=self.coding_max_steps,
                        region=self.region,
                        client_password=self.client_password,
                        user_instruction=instruction,
                        cua_api_base=self.cua_api_base,  # CUA-specific API base URL
                        cua_api_key=self.cua_api_key   # CUA-specific API key
                    )
                
                # Use existing environment
                orchestrator_proxy.env = self.env
                
                # Reset environment if task_config provided
                if task_config:
                    orchestrator_proxy.reset(task_config=task_config)
                
                # Get initial screenshot
                screenshot = self.env.controller.get_screenshot()
                
                with open(os.path.join(self.history_save_dir, 'initial_screenshot_orchestrator.png'), "wb") as f:
                    f.write(screenshot)
                
                # Start chat
                orchestrator_proxy.initiate_chat(
                    recipient=orchestrator,
                    message=f"""{instruction}
Check my computer screenshot and describe it first. If this task is possible to complete, please complete it on my computer. If not, reply with "INFEASIBLE" to end the conversation.
I will not provide further information to you.""" + "<img data:image/png;base64," + base64.b64encode(screenshot).decode("utf-8") + ">",
                    max_turns=self.orchestrator_max_steps
                )
                
                # Save chat history
                chat_history = []
                key = list(orchestrator_proxy.chat_messages.keys())[0]
                chat_messages = orchestrator_proxy.chat_messages[key]
                for item in chat_messages:
                    item.pop('tool_responses', None)
                    if item.get('role', None) in ['tool', 'assistant'] and item.get('content', None):
                        for msg in item['content']:
                            if msg.get('type', None) == 'image_url':
                                msg['image_url'] = "<image>"
                    chat_history.append(item)
                
                with open(os.path.join(self.history_save_dir, 'chat_history.json'), "w") as f:
                    json.dump(chat_history, f)
                
                # Check for INFEASIBLE
                if chat_history[-1]['role'] == 'user' and 'INFEASIBLE' in chat_history[-1]['content'][0]['text']:
                    self.env.action_history.append("FAIL")
                
                # Count steps for cut-off
                cua_steps = len(glob.glob(f"{self.history_save_dir}/cua_output*/step_*.png"))
                coding_paths = glob.glob(f"{self.history_save_dir}/coding_output*/chat_history.json")
                coding_steps = 0
                for hist in coding_paths:
                    with open(hist, 'r') as f:
                        hist_content = json.dumps(json.load(f))
                        coding_steps += hist_content.count('exitcode:')
                
                result_info = {
                    "cua_steps": cua_steps,
                    "coding_steps": coding_steps,
                    "total_steps": cua_steps + coding_steps,
                    "chat_history": chat_history
                }
                
                return result_info
                
            except Exception as e:
                retry += 1
                if retry < max_retries:
                    self.logger.warning(f"Retry {retry}/{max_retries}, error: {str(e)}")
                    traceback.print_exc()
                    # Clean up and retry
                    if os.path.exists(self.history_save_dir):
                        shutil.rmtree(self.history_save_dir)
                        os.makedirs(self.history_save_dir)
                    continue
                else:
                    self.logger.error(f"Fatal error after {max_retries} retries: {e}")
                    traceback.print_exc()
                    return {"error": str(e)}
        
        return {"error": "Max retries exceeded"}
    
    def predict(self, instruction: str, obs: Dict) -> Tuple[Dict, List[str]]:
        """
        Single-step prediction (for compatibility with standard interface).
        
        Note: CoAct is designed to run complete tasks, not single steps.
        This method provides a simplified interface.
        """
        self.logger.warning("CoAct is designed for full task execution. Using simplified single-step mode.")
        
        # For CoAct, we return a placeholder since it handles full task internally
        return {"info": "CoAct handles full task execution"}, ["WAIT"]


class CoActPromptAgentWrapper:
    """
    Wrapper to provide PromptAgent-compatible interface for CoAct Agent.
    """

    def __init__(
        self,
        model: str = "o3",
        max_tokens: int = 10000,
        top_p: float = 0.9,
        temperature: float = 0.5,
        action_space: str = "pyautogui",
        observation_type: str = "screenshot",
        max_trajectory_length: int = 8,
        a11y_tree_max_tokens: int = 50000,
        # CoAct specific parameters
        orchestrator_model: str = "o3",
        coding_model: str = "o4-mini",
        cua_model: str = "computer-use-preview",
        orchestrator_max_steps: int = 15,
        coding_max_steps: int = 20,
        cua_max_steps: int = 25,
        cut_off_steps: int = 200,
        oai_config_path: str = "",
        # API configuration for Orchestrator and Coding Agent
        api_base: str = "",
        api_key: str = "",
        # API configuration for CUA (GUI Agent) - uses OpenAI Computer Use API
        cua_api_base: str = "",
        cua_api_key: str = "",
        compatibility_mode: bool = False,  # Enable for transit/proxy APIs
        # Environment
        platform: str = "windows",
        screen_width: int = 1920,
        screen_height: int = 1080,
        sleep_after_execution: float = 0.5,
        provider_name: str = "vmware",
        region: str = "",
        client_password: str = "",
        **kwargs
    ):
        """Initialize CoAct agent wrapper."""
        self.coact_adapter = CoActAgentAdapter(
            orchestrator_model=orchestrator_model if orchestrator_model else model,
            coding_model=coding_model,
            cua_model=cua_model,
            orchestrator_max_steps=orchestrator_max_steps,
            coding_max_steps=coding_max_steps,
            cua_max_steps=cua_max_steps,
            cut_off_steps=cut_off_steps,
            api_base=api_base,
            api_key=api_key,
            cua_api_base=cua_api_base,  # CUA-specific API base URL
            cua_api_key=cua_api_key,   # CUA-specific API key
            compatibility_mode=compatibility_mode,
            platform=platform,
            screen_width=screen_width,
            screen_height=screen_height,
            sleep_after_execution=sleep_after_execution,
            oai_config_path=oai_config_path,
            provider_name=provider_name,
            region=region,
            client_password=client_password,
            action_space=action_space,
            observation_type=observation_type,
        )
        
        self.initialized = False
        self.logger = logger
        self.vm_ip = None
        
    def reset(self, logger=None, vm_ip=None):
        """Reset agent state."""
        if logger is not None:
            self.logger = logger
        if vm_ip is not None:
            self.vm_ip = vm_ip
        self.coact_adapter.reset(logger=logger, vm_ip=vm_ip)
        
    def initialize_with_env(self, env):
        """Initialize with environment."""
        self.coact_adapter.initialize_with_env(env)
        self.initialized = True
        
    def set_history_dir(self, history_dir: str):
        """Set history save directory."""
        self.coact_adapter.set_history_dir(history_dir)
        
    def run_task(self, instruction: str, task_config: dict = None) -> Dict:
        """Run complete task using CoAct framework."""
        if not self.initialized:
            raise RuntimeError("Agent not initialized. Call initialize_with_env() first.")
        return self.coact_adapter.run_task(instruction, task_config)
    
    def predict(self, instruction: str, obs: Dict) -> Tuple[Dict, List[str]]:
        """Single-step prediction interface."""
        if not self.initialized:
            raise RuntimeError("Agent not initialized. Call initialize_with_env() first.")
        return self.coact_adapter.predict(instruction, obs)
