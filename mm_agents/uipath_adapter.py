"""
UIPath Agent Adapter for HF Benchmark (Windows)
Adapts UIPath Computer Use framework to work with the desktop_env benchmark.

This is a wrapper that adapts the OSWorld UIPath agent for use with
the Windows desktop_env evaluation framework.
"""

import asyncio
import base64
import json
import logging
import os
import re
import sys
from typing import Dict, List, Tuple

logger = logging.getLogger("desktopenv.agent")


def parse_actions_from_string(input_string):
    """Parse action JSON from response string."""
    if input_string.strip() in ["WAIT", "DONE", "FAIL"]:
        return [input_string.strip()]
    actions = []
    matches = re.findall(r"```json\s+(.*?)\s+```", input_string, re.DOTALL)
    if matches:
        try:
            for match in matches:
                action_dict = json.loads(match)
                actions.append(action_dict)
            return actions
        except json.JSONDecodeError as e:
            return f"Failed to parse JSON: {e}"
    else:
        matches = re.findall(r"```\s+(.*?)\s+```", input_string, re.DOTALL)
        if matches:
            try:
                for match in matches:
                    action_dict = json.loads(match)
                    actions.append(action_dict)
                return actions
            except json.JSONDecodeError as e:
                return f"Failed to parse JSON: {e}"
        else:
            try:
                action_dict = json.loads(input_string)
                return [action_dict]
            except json.JSONDecodeError:
                raise ValueError("Invalid response format: " + input_string)


def map_key(key):
    """Map UIPath key names to pyautogui key names."""
    key = key.lower()
    key_map = {
        "space": " ",
        "back": "backspace",
        "super": "win",
        "arrowdown": "down",
        "arrowup": "up",
        "arrowright": "right",
        "arrowleft": "left",
    }
    return key_map.get(key, key)


def map_uipath_agent_actions_to_osworld(actions):
    """Convert UIPath actions to OSWorld/desktop_env action format."""
    results = []

    def handle_click(params):
        x, y = tuple(params["position"])
        if "button" in params:
            if params["button"] == "right":
                return {"action_type": "RIGHT_CLICK", "x": x, "y": y}
            elif params["button"] == "left":
                return {"action_type": "LEFT_CLICK", "x": x, "y": y}
            else:
                raise ValueError(f"Unknown click button: {params['button']}")
        elif "click_type" in params:
            if params["click_type"] == "double":
                return {"action_type": "DOUBLE_CLICK", "x": x, "y": y}
            elif params["click_type"] == "triple":
                return {"action_type": "TRIPLE_CLICK", "x": x, "y": y}
            else:
                raise ValueError(f"Unknown click type: {params['click_type']}")
        else:
            return {"action_type": "CLICK", "x": x, "y": y}

    def handle_keypress(params):
        keys = [map_key(k) for k in params["keys"]]
        if len(keys) == 1:
            return {"action_type": "PRESS", "key": keys[0]}
        return {"action_type": "HOTKEY", "keys": keys}

    def handle_key_event(params, event_type):
        key = map_key(params["keys"][0])
        return {"action_type": event_type, "key": key}

    for action in actions:
        method = action["method_type"].lower()
        params = action["parameters"]

        if method == "click":
            result = handle_click(params)
        elif method == "type_into":
            result = {"action_type": "TYPING", "text": params["value"]}
        elif method == "wait_load_completed":
            result = "WAIT"
        elif method == "keypress":
            result = handle_keypress(params)
        elif method == "keydown":
            result = handle_key_event(params, "KEY_DOWN")
        elif method == "keyup":
            result = handle_key_event(params, "KEY_UP")
        elif method == "finish":
            status_map = {"failure": "FAIL", "success": "DONE"}
            result = status_map.get(params.get("status"), "DONE")
        elif method == "scroll":
            x, y = tuple(params["position"])
            if "offset" in params:
                dx, dy = tuple(params["offset"])
            else:
                dy = 5 if params.get("direction") == "up" else -5
                dx = 5 if params.get("direction") == "left" else -5
            result = [
                {"action_type": "MOVE_TO", "x": x, "y": y},
                {"action_type": "SCROLL", "dx": dx, "dy": dy},
            ]
        elif method == "mouse_move":
            x, y = tuple(params["position"])
            result = {"action_type": "MOVE_TO", "x": x, "y": y}
        elif method == "drag":
            path = params["path"]
            x1, y1 = path[0]["x"], path[0]["y"]
            x2, y2 = path[1]["x"], path[1]["y"]
            result = [
                {"action_type": "MOVE_TO", "x": x1, "y": y1},
                {"action_type": "DRAG_TO", "x": x2, "y": y2},
            ]
        else:
            raise ValueError(f"Unknown method type: {method}")

        results.append(result)

    return json.dumps(results)


class UIPathAgentAdapter:
    """
    Adapter class to wrap UIPath Computer Use for use with desktop_env benchmark.
    """
    
    def __init__(
        self,
        model: str = "gpt-5-mini-2025-08-07",
        uipath_model_name: str = "gpt-5-2025-08-07",
        platform: str = "windows",
        action_space: str = "computer_13",
        observation_type: str = "screenshot",
        client_password: str = "",
        max_steps: int = 15,
        # UIPath model configuration
        planner_url: str = "",
        planner_api_key: str = "",
        grounder_url: str = "",
        grounder_api_key: str = "",
        grounder_model: str = "",
        grounding_width: int = 1920,
        grounding_height: int = 1080,
        **kwargs
    ):
        """
        Initialize UIPath Agent Adapter.

        Args:
            model: Model name (for compatibility)
            uipath_model_name: Model name for UIPath API
            platform: Operating system platform
            action_space: Action space type
            observation_type: Observation type
            client_password: Client password for sudo operations
            max_steps: Maximum steps for task execution
            planner_url: URL for the planner LLM service (or set UIPATH_PLANNER_URL env var)
            planner_api_key: API key for the planner service (or set UIPATH_PLANNER_API_KEY env var)
            grounder_url: URL for the grounder/vision service (or set UIPATH_GROUNDER_URL env var)
            grounder_api_key: API key for the grounder service (or set UIPATH_GROUNDER_API_KEY env var)
            grounder_model: Model name for UI-TARS service (e.g., UI-TARS-1.5-7B)
            grounding_width: Screen width for coordinate scaling (default: 1920)
            grounding_height: Screen height for coordinate scaling (default: 1080)
        """
        self.model = model
        self.uipath_model_name = uipath_model_name
        self.platform = platform
        self.action_space = action_space
        self.observation_type = observation_type
        self.client_password = client_password
        self.max_steps = max_steps

        # Store UIPath model configuration
        self.planner_url = planner_url
        self.planner_api_key = planner_api_key
        self.grounder_url = grounder_url
        self.grounder_api_key = grounder_api_key
        self.grounder_model = grounder_model
        self.grounding_width = grounding_width
        self.grounding_height = grounding_height

        self.env = None
        self.logger = logger
        self.vm_ip = None

        # UIPath specific state
        self.thoughts = []
        self.actions = []
        self.observations = []
        self.uipath_hist = []

        # Will be initialized when available
        self.uipath_computer_use_model = None
        
    def _init_uipath_model(self):
        """Initialize UIPath model if not already done."""
        if self.uipath_computer_use_model is None:
            try:
                # Configure LLM client (planner) before importing
                import mm_agents.uipath.llm_client as llm_client
                if self.planner_url or self.planner_api_key:
                    llm_client.configure(
                        planner_url=self.planner_url,
                        api_key=self.planner_api_key,
                        use_openai_format=True
                    )

                # Import and initialize UiPath agent with grounder config
                from mm_agents.uipath.agent import UiPathComputerUseV1
                self.uipath_computer_use_model = UiPathComputerUseV1(
                    grounder_url=self.grounder_url,
                    grounder_api_key=self.grounder_api_key,
                    grounder_model=self.grounder_model,
                    grounding_width=self.grounding_width,
                    grounding_height=self.grounding_height
                )
            except ImportError as e:
                self.logger.error(f"Failed to import UIPath components: {e}")
                raise ImportError("UIPath framework not available. Please ensure mm_agents.uipath is properly installed.")
                
    def reset(self, logger=None, vm_ip=None):
        """Reset agent state."""
        if logger is not None:
            self.logger = logger
        if vm_ip is not None:
            self.vm_ip = vm_ip
            
        self.thoughts = []
        self.actions = []
        self.observations = []
        self.uipath_hist = []
        
    def initialize_with_env(self, env):
        """Initialize the UIPath agent with the desktop environment."""
        self.env = env
        self._init_uipath_model()
        self.logger.info(f"UIPath Agent initialized with model: {self.uipath_model_name}")
        
    def update_history(self, rsp, img_base64):
        """Update UIPath conversation history."""
        self.uipath_hist.append({
            "actions": rsp["step"]["actions"],
            "description": rsp["step"]["description"],
            "additional_parameters": {
                "review": rsp["step"]["additional_parameters"]["review"],
                "thought": rsp["step"]["additional_parameters"]["thought"],
                "action_description": rsp["step"]["additional_parameters"]["action_description"],
                "plan_action": rsp["step"]["additional_parameters"]["plan_action"],
            },
            "image": img_base64,
        })
        
    def predict(self, instruction: str, obs: Dict, step_idx: int = 0) -> Tuple[Dict, List]:
        """
        Predict the next action based on current observation.
        
        Args:
            instruction: Task instruction
            obs: Observation dictionary containing screenshot
            step_idx: Current step index
            
        Returns:
            Tuple of (response_info dict, list of actions)
        """
        if self.uipath_computer_use_model is None:
            self._init_uipath_model()
            
        # Build message with password hint
        if step_idx == self.max_steps - 1:
            message = (
                instruction
                + f" The sudo password is {self.client_password}, if needed. "
                + "This is the last step, you must return the finish actions with either success or failure, depending on the result. No further steps are allowed."
            )
        else:
            message = instruction + f" The sudo password is {self.client_password}, if needed."
            
        img_base64 = base64.b64encode(obs["screenshot"]).decode("utf-8")
        
        payload = {
            "previousSteps": self.uipath_hist,
            "userTask": message,
            "image": img_base64,
            "model_name": self.uipath_model_name,
        }
        
        try:
            rsp = asyncio.run(
                self.uipath_computer_use_model.predict_request(
                    payload, self.uipath_model_name
                )
            )
            self.update_history(rsp, img_base64)
            
            uipath_actions = map_uipath_agent_actions_to_osworld(rsp["step"]["actions"])
            actions = self.parse_actions(uipath_actions)
            self.thoughts.append(rsp)
            
        except Exception as e:
            self.logger.error(f"UIPath prediction failed: {e}")
            actions = None
            self.thoughts.append("")
            return {"error": str(e)}, ["FAIL"]
            
        # Flatten nested actions
        if len(actions) != 0:
            while actions and isinstance(actions[0], list):
                actions = [action for multi_action in actions for action in multi_action]
                
        response_info = rsp.get("step", {})
        return response_info, actions
    
    def parse_actions(self, response: str, masks=None):
        """Parse actions from response string."""
        if self.observation_type in ["screenshot"]:
            if self.action_space == "computer_13":
                actions = parse_actions_from_string(response)
            else:
                raise ValueError("Invalid action space: " + self.action_space)
            self.actions.append(actions)
            return actions
        else:
            raise ValueError("Invalid observation type: " + self.observation_type)


class UIPathPromptAgentWrapper:
    """
    Wrapper to provide PromptAgent-compatible interface for UIPath Agent.
    """

    def __init__(
        self,
        model: str = "gpt-5-mini-2025-08-07",
        max_tokens: int = 10000,
        top_p: float = 0.9,
        temperature: float = 0.5,
        action_space: str = "computer_13",
        observation_type: str = "screenshot",
        max_trajectory_length: int = 8,
        a11y_tree_max_tokens: int = 50000,
        # UIPath specific parameters
        uipath_model_name: str = "gpt-5-2025-08-07",
        platform: str = "windows",
        client_password: str = "",
        max_steps: int = 15,
        # UIPath model configuration
        planner_url: str = "",
        planner_api_key: str = "",
        grounder_url: str = "",
        grounder_api_key: str = "",
        grounder_model: str = "",
        grounding_width: int = 1920,
        grounding_height: int = 1080,
        **kwargs
    ):
        """Initialize UIPath agent wrapper."""
        self.uipath_adapter = UIPathAgentAdapter(
            model=model,
            uipath_model_name=uipath_model_name if uipath_model_name else model,
            platform=platform,
            action_space=action_space,
            observation_type=observation_type,
            client_password=client_password,
            max_steps=max_steps,
            planner_url=planner_url,
            planner_api_key=planner_api_key,
            grounder_url=grounder_url,
            grounder_api_key=grounder_api_key,
            grounder_model=grounder_model,
            grounding_width=grounding_width,
            grounding_height=grounding_height,
        )
        
        self.max_steps = max_steps
        self.current_step = 0
        self.initialized = False
        self.logger = logger
        self.vm_ip = None
        
    def reset(self, logger=None, vm_ip=None):
        """Reset agent state."""
        if logger is not None:
            self.logger = logger
        if vm_ip is not None:
            self.vm_ip = vm_ip
        self.current_step = 0
        self.uipath_adapter.reset(logger=logger, vm_ip=vm_ip)
        
    def initialize_with_env(self, env):
        """Initialize with environment."""
        self.uipath_adapter.initialize_with_env(env)
        self.initialized = True
        
    def set_max_steps(self, max_steps: int):
        """Set maximum steps for the task."""
        self.max_steps = max_steps
        self.uipath_adapter.max_steps = max_steps
        
    def predict(self, instruction: str, obs: Dict) -> Tuple[Dict, List[str]]:
        """
        Predict next action(s).
        
        Returns:
            Tuple of (response_dict, list of action strings/dicts)
        """
        if not self.initialized:
            raise RuntimeError("Agent not initialized. Call initialize_with_env() first.")
            
        response, actions = self.uipath_adapter.predict(instruction, obs, self.current_step)
        self.current_step += 1
        
        return response, actions
