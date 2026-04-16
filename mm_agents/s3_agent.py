"""
S3 Agent Adapter for HF Benchmark
Adapts Agent-S3 (gui_agents) to work with the desktop_env benchmark.
"""

import logging
import os
import sys
from typing import Dict, List, Tuple

logger = logging.getLogger("desktopenv.agent")

# Try to import gui_agents
_gui_agents_available = False
AgentS3 = None
ACI = None

def _try_import_gui_agents():
    """Try to import gui_agents from various possible locations."""
    global _gui_agents_available, AgentS3, ACI
    
    if _gui_agents_available:
        return True
        
    # Possible paths for Agent-S
    possible_paths = [
        os.path.join(os.path.dirname(__file__), '..', '..', 'Agent-S'),
        os.path.join(os.path.dirname(__file__), '..', '..', '..', 'Agent-S'),
        os.path.expanduser('~/Agent-S'),
    ]
    
    for path in possible_paths:
        abs_path = os.path.abspath(path)
        if os.path.exists(abs_path) and abs_path not in sys.path:
            sys.path.insert(0, abs_path)
    
    try:
        from gui_agents.s3.agents.agent_s import AgentS3 as _AgentS3
        from gui_agents.s3.agents.grounding import ACI as _ACI
        AgentS3 = _AgentS3
        ACI = _ACI
        _gui_agents_available = True
        logger.info("Successfully imported gui_agents")
        return True
    except ImportError as e:
        logger.warning(f"gui_agents not available: {e}")
        logger.warning("Please install Agent-S: cd /path/to/Agent-S && pip install -e .")
        return False


class S3AgentAdapter:
    """
    Adapter class to wrap Agent-S3 for use with desktop_env benchmark.
    
    This adapter provides compatibility between the gui_agents S3 agent
    and the desktop_env evaluation framework.
    """
    
    def __init__(
        self,
        # Model configuration
        model: str = "gpt-4o",
        model_provider: str = "openai",
        model_url: str = "",
        model_api_key: str = "",
        model_temperature: float = None,

        # Grounding model configuration
        ground_provider: str = "huggingface",
        ground_url: str = "",
        ground_model: str = "ui-tars-1.5-7b",
        ground_api_key: str = "",
        grounding_width: int = 1920,
        grounding_height: int = 1080,

        # Agent configuration
        platform: str = "windows",
        screen_width: int = 1920,
        screen_height: int = 1080,
        max_trajectory_length: int = 8,
        enable_reflection: bool = True,
        disable_thinking: bool = False,  # Disable thinking mode for transit/proxy APIs

        # Action space (for compatibility)
        action_space: str = "pyautogui",
        observation_type: str = "screenshot",
        **kwargs
    ):
        """
        Initialize S3 Agent Adapter.
        
        Args:
            model: Main LLM model name
            model_provider: Provider for main model (openai, anthropic, etc.)
            model_url: Custom API URL for main model
            model_api_key: API key for main model
            model_temperature: Temperature for model generation
            ground_provider: Provider for grounding model
            ground_url: URL for grounding model endpoint
            ground_model: Grounding model name
            ground_api_key: API key for grounding model
            grounding_width: Width for grounding coordinate resolution
            grounding_height: Height for grounding coordinate resolution
            platform: Operating system (windows, linux, darwin)
            screen_width: Screen width for the environment
            screen_height: Screen height for the environment
            max_trajectory_length: Maximum trajectory history to keep
            enable_reflection: Enable reflection agent
            action_space: Action space type (for compatibility)
            observation_type: Observation type (for compatibility)
        """
        self.model = model
        self.model_provider = model_provider
        self.platform = platform
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.action_space = action_space
        self.observation_type = observation_type
        self.max_trajectory_length = max_trajectory_length
        self.enable_reflection = enable_reflection
        self.disable_thinking = disable_thinking

        # Engine parameters for main model
        # Pass disable_thinking to prevent Worker from using thinking mode with transit APIs
        self.engine_params = {
            "engine_type": model_provider,
            "model": model,
            "base_url": model_url if model_url else "",
            "api_key": model_api_key if model_api_key else "",
            "temperature": model_temperature,
            "disable_thinking": disable_thinking,  # Passed to Worker
        }
        
        # Engine parameters for grounding model
        # For local services (localhost), use a dummy API key if none provided
        _ground_api_key = ground_api_key if ground_api_key else ""
        if not _ground_api_key and ground_url and ("localhost" in ground_url or "127.0.0.1" in ground_url):
            _ground_api_key = "sk-dummy-key-for-local-service"

        self.engine_params_for_grounding = {
            "engine_type": ground_provider,
            "model": ground_model,
            "base_url": ground_url,
            "api_key": _ground_api_key,
            "grounding_width": grounding_width,
            "grounding_height": grounding_height,
        }
        
        self.grounding_width = grounding_width
        self.grounding_height = grounding_height
        
        # Will be initialized in reset() when we have env reference
        self.env = None
        self.grounding_agent = None
        self.agent = None
        self.logger = logger
        self.vm_ip = None
        
    def reset(self, logger=None, vm_ip=None):
        """
        Reset the agent state.
        
        Args:
            logger: Logger instance (optional)
            vm_ip: VM IP address (optional, for env reference)
        """
        if logger is not None:
            self.logger = logger
        if vm_ip is not None:
            self.vm_ip = vm_ip
            
        # Reset the agent if already initialized
        if self.agent is not None:
            self.agent.reset()
    
    def initialize_with_env(self, env):
        """
        Initialize the S3 agent with the desktop environment.
        
        Args:
            env: DesktopEnv instance
        """
        # Ensure gui_agents is available
        if not _try_import_gui_agents():
            raise ImportError("gui_agents not available. Please install Agent-S.")
            
        self.env = env

        # Import OSWorldACI from Agent-S
        try:
            from gui_agents.s3.agents.grounding import OSWorldACI as _OSWorldACI
        except ImportError as e:
            raise ImportError(
                f"Failed to import OSWorldACI from Agent-S: {e}\n"
                "Please ensure Agent-S is installed: cd /path/to/Agent-S && pip install -e ."
            )

        # Create grounding agent with correct parameters
        # OSWorldACI accepts: env, platform, engine_params_for_generation, engine_params_for_grounding, width, height, code_agent_budget, code_agent_engine_params
        self.grounding_agent = _OSWorldACI(
            env=env,
            platform=self.platform,
            engine_params_for_generation=self.engine_params,
            engine_params_for_grounding=self.engine_params_for_grounding,
            width=self.screen_width,
            height=self.screen_height,
            code_agent_budget=10,  # Reduced code agent step budget (was 20)
            code_agent_engine_params=self.engine_params,  # Code agent uses main model
        )
        
        # Create main S3 agent
        self.agent = AgentS3(
            worker_engine_params=self.engine_params,
            grounding_agent=self.grounding_agent,
            platform=self.platform,
            max_trajectory_length=self.max_trajectory_length,
            enable_reflection=self.enable_reflection,
        )
        
        self.logger.info(f"S3 Agent initialized with model: {self.model}, platform: {self.platform}")
    
    def predict(self, instruction: str, obs: Dict) -> Tuple[Dict, List[str]]:
        """
        Predict the next action based on the current observation.
        
        Args:
            instruction: Task instruction
            obs: Observation dictionary containing screenshot and optional a11y tree
            
        Returns:
            Tuple of (response_info dict, list of action strings)
        """
        if self.agent is None:
            raise RuntimeError("Agent not initialized. Call initialize_with_env() first.")
        
        # Prepare observation in the format expected by S3 agent
        # NOTE: S3 agent's encode_image() treats strings as file paths.
        # We need to decode base64 string back to bytes to avoid file path error.
        import base64
        screenshot = obs.get("screenshot", "")

        if isinstance(screenshot, bytes):
            # Already bytes - use directly
            observation = {"screenshot": screenshot}
        elif isinstance(screenshot, str) and screenshot.startswith("iVBORw0KGgo"):
            # Base64-encoded PNG string (starts with PNG magic header) - decode to bytes
            observation = {"screenshot": base64.b64decode(screenshot)}
        elif isinstance(screenshot, str) and screenshot:
            # Could be data URL format or file path - try to handle
            if screenshot.startswith("data:image"):
                # Data URL format - extract base64 part
                _, encoded = screenshot.split(",", 1)
                observation = {"screenshot": base64.b64decode(encoded)}
            else:
                # Assume it's already a valid format or pass as-is
                observation = {"screenshot": screenshot}
        else:
            # Empty or invalid - use empty bytes
            observation = {"screenshot": b""}

        # Add accessibility tree if available (support both key names)
        a11y_tree = obs.get("accessibility_tree") or obs.get("a11y_tree")
        if a11y_tree:
            observation["accessibility_tree"] = a11y_tree
        
        # Call S3 agent prediction
        try:
            info, actions = self.agent.predict(instruction, observation)
            
            # Log prediction results
            self.logger.info(f"S3 Agent predicted {len(actions)} action(s)")
            for i, action in enumerate(actions):
                self.logger.debug(f"Action {i}: {action[:200] if len(action) > 200 else action}")
            
            return info, actions
            
        except Exception as e:
            self.logger.error(f"S3 Agent prediction error: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            # Return FAIL action on error
            return {"error": str(e)}, ["FAIL"]


class S3PromptAgentWrapper:
    """
    Wrapper to provide PromptAgent-compatible interface for S3 Agent.
    This allows S3 agent to be used as a drop-in replacement for PromptAgent.
    """
    
    def __init__(
        self,
        model: str = "gpt-4o",
        max_tokens: int = 10000,
        top_p: float = 0.9,
        temperature: float = 0.5,
        action_space: str = "pyautogui",
        observation_type: str = "screenshot",
        max_trajectory_length: int = 8,
        a11y_tree_max_tokens: int = 50000,
        # S3 specific parameters
        model_provider: str = "openai",
        model_url: str = "",
        model_api_key: str = "",
        model_temperature: float = None,
        ground_provider: str = "huggingface",
        ground_url: str = "",
        ground_model: str = "ui-tars-1.5-7b",
        ground_api_key: str = "",
        grounding_width: int = 1920,
        grounding_height: int = 1080,
        platform: str = "windows",
        screen_width: int = 1920,
        screen_height: int = 1080,
        enable_reflection: bool = True,
        disable_thinking: bool = False,
        **kwargs
    ):
        """
        Initialize S3 agent with PromptAgent-compatible interface.
        """
        self.s3_adapter = S3AgentAdapter(
            model=model,
            model_provider=model_provider,
            model_url=model_url,
            model_api_key=model_api_key,
            model_temperature=model_temperature if model_temperature else temperature,
            ground_provider=ground_provider,
            ground_url=ground_url,
            ground_model=ground_model,
            ground_api_key=ground_api_key,
            grounding_width=grounding_width,
            grounding_height=grounding_height,
            platform=platform,
            screen_width=screen_width,
            screen_height=screen_height,
            max_trajectory_length=max_trajectory_length,
            enable_reflection=enable_reflection,
            disable_thinking=disable_thinking,
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
        self.s3_adapter.reset(logger=logger, vm_ip=vm_ip)
        
    def initialize_with_env(self, env):
        """Initialize with environment (must be called before predict)."""
        self.s3_adapter.initialize_with_env(env)
        self.initialized = True
        
    def predict(self, instruction: str, obs: Dict) -> Tuple[Dict, List[str]]:
        """
        Predict next action(s).
        
        Returns:
            Tuple of (response_dict, list of action strings)
        """
        if not self.initialized:
            raise RuntimeError("Agent not initialized. Call initialize_with_env() first.")
            
        info, actions = self.s3_adapter.predict(instruction, obs)
        
        # Convert info dict to response string for compatibility
        response = info if isinstance(info, dict) else {"info": info}
        
        return response, actions
