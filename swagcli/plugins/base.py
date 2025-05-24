from typing import Any, Dict, Optional

from pydantic import BaseModel


class Plugin(BaseModel):
    name: str
    description: str
    version: str
    author: str
    enabled: bool = True

    def on_request(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]],
        data: Optional[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """Hook called before making a request."""
        return None

    def on_response(self, response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Hook called after receiving a response."""
        return None
