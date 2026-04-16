import httpx
import mm_agents.uipath.utils as utils
import os

class GrounderClient(object):
    def __init__(self, grounder_url: str = "", grounder_api_key: str = "",
                 grounder_model: str = "", grounding_width: int = 1920, grounding_height: int = 1080):
        """
        Initialize the Grounder Client.

        Args:
            grounder_url: URL for the grounding model service (e.g., UI-TARS server)
                         Set via UIPATH_GROUNDER_URL env var or parameter
            grounder_api_key: API key for the grounder service (optional, for localhost leave empty)
                             Set via UIPATH_GROUNDER_API_KEY env var or parameter
            grounder_model: Model name for the grounder service (e.g., UI-TARS-1.5-7B)
                            Set via UIPATH_GROUNDER_MODEL env var or parameter
            grounding_width: Screen width for coordinate scaling (default: 1920)
            grounding_height: Screen height for coordinate scaling (default: 1080)
        """
        self.url = grounder_url or os.getenv("UIPATH_GROUNDER_URL", "")
        self.api_key = grounder_api_key or os.getenv("UIPATH_GROUNDER_API_KEY", os.getenv("SERVICE_KEY", ""))
        self.model = grounder_model or os.getenv("UIPATH_GROUNDER_MODEL", "")
        self.width = grounding_width
        self.height = grounding_height

    async def predict(
        self, image_base64: str, action_description: str, action: str | None = None
    ) -> utils.GroundingOutput:
        if not self.url:
            raise ValueError("Grounder URL is not configured. Please set UIPATH_GROUNDER_URL environment variable or pass grounder_url parameter.")

        request = utils.GroundingRequest(
            description=action_description,
            image_base64=image_base64,
            action_type=action,
        )

        headers = {}
        if self.api_key:
            headers["X-API-KEY"] = self.api_key

        # Build request payload with UI-TARS compatible format
        payload = {
            "image_base64": request.image_base64,
            "action_description": request.description,
            "action": request.action_type,
        }

        # Add model name if specified
        if self.model:
            payload["model"] = self.model

        # Add width/height for coordinate scaling if needed
        if self.width and self.height:
            payload["width"] = self.width
            payload["height"] = self.height

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.url,
                json=payload,
                headers=headers,
                timeout=100.0,
            )

        if response.status_code != 200:
            raise ValueError(f"Prediction failed: {response.text}")

        data = response.json()
        return utils.GroundingOutput(
            description=data.get("description", ""),
            position=tuple(data.get("position", data.get("coords", [0, 0]))),
        )
