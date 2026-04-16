import os
import requests

class LLMClientConfig:
    """Configuration for UIPath LLM client (Planner model)."""
    def __init__(self):
        # Planner model URL (set via UIPATH_PLANNER_URL env var)
        self.planner_url = os.getenv("UIPATH_PLANNER_URL", "")
        # API key (set via UIPATH_PLANNER_API_KEY or SERVICE_KEY env var)
        self.api_key = os.getenv("UIPATH_PLANNER_API_KEY", "") or os.getenv("SERVICE_KEY", "")
        # Whether to use OpenAI-compatible format
        self.use_openai_format = os.getenv("UIPATH_USE_OPENAI_FORMAT", "true").lower() == "true"


# Global config instance
_config = LLMClientConfig()


def configure(planner_url: str = None, api_key: str = None, use_openai_format: bool = True):
    """
    Configure the LLM client programmatically.

    Args:
        planner_url: URL for the planner model service
        api_key: API key for the planner service
        use_openai_format: Whether to use OpenAI-compatible format
    """
    if planner_url is not None:
        _config.planner_url = planner_url
    if api_key is not None:
        _config.api_key = api_key
    _config.use_openai_format = use_openai_format


def send_messages(payload):
    """
    Send messages to the planner LLM and get response.

    Configuration (in order of priority):
    1. Programmatic config via configure()
    2. Environment variables:
       - UIPATH_PLANNER_URL: Planner model service URL
       - UIPATH_PLANNER_API_KEY: API key for planner service
       - UIPATH_USE_OPENAI_FORMAT: Use OpenAI format (default: true)

    The payload should contain:
    {
        "model": "model-name",
        "messages": [...],
        "max_completion_tokens": 5000,
        ...
    }
    """
    if not _config.planner_url:
        raise ValueError(
            "Planner URL is not configured. "
            "Please set UIPATH_PLANNER_URL environment variable or call configure() first."
        )

    headers = {
        "Content-Type": "application/json",
    }

    if _config.api_key:
        headers["X-API-KEY"] = _config.api_key

    # OpenAI-compatible format uses different headers
    # Check if URL contains /v1/ (OpenAI-compatible endpoint) or "openai"
    is_openai_compatible = (
        _config.use_openai_format and
        _config.api_key and
        ("openai" in _config.planner_url.lower() or "/v1/" in _config.planner_url.lower())
    )
    if is_openai_compatible:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {_config.api_key}"
        }

    retries = 3
    last_error = None

    for attempt in range(retries):
        try:
            response = requests.post(_config.planner_url, headers=headers, json=payload, timeout=120)
            if response.status_code == 200:
                data = response.json()
                # Support both OpenAI and custom response formats
                if "choices" in data:
                    return data["choices"][0]["message"]["content"]
                else:
                    # Custom format - return content directly
                    return data.get("content", str(data))
            else:
                last_error = f"HTTP {response.status_code}: {response.text}"
        except requests.exceptions.RequestException as e:
            last_error = str(e)

    raise ValueError(f"LLM request failed after {retries} retries. Last error: {last_error}")
