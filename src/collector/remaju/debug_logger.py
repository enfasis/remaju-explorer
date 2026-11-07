"""Debug logging utility for HTTP requests and responses."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


class DebugLogger:
    """Logger for debugging HTTP requests and responses."""

    def __init__(self, debug_dir: Path = Path("data/debug"), enabled: bool = False):
        """Initialize debug logger.

        Args:
            debug_dir: Directory to save debug files
            enabled: Whether debugging is enabled
        """
        self.enabled = enabled
        self.debug_dir = debug_dir
        self.request_counter = 0
        self._pending_requests: dict[int, dict] = {}

        if enabled:
            self.debug_dir.mkdir(parents=True, exist_ok=True)

    def _get_next_request_number(self) -> int:
        """Get next request number and increment counter."""
        self.request_counter += 1
        return self.request_counter

    def _sanitize_filename(self, text: str) -> str:
        """Sanitize text for use in filename."""
        return "".join(c for c in text if c.isalnum() or c in "-_").strip()

    def log_request(
        self,
        url: str,
        method: str,
        headers: dict,
        payload: Optional[dict] = None,
        auction_number: Optional[str] = None,
        request_type: str = "request",
    ) -> int:
        """Log an HTTP request.

        Args:
            url: Request URL
            method: HTTP method (GET, POST, etc.)
            headers: Request headers
            payload: Request payload/body
            auction_number: Associated auction number
            request_type: Type of request (list, detail, etc.)

        Returns:
            Request number assigned to this request
        """
        if not self.enabled:
            return 0

        request_num = self._get_next_request_number()

        # Store request data for later combination with response
        self._pending_requests[request_num] = {
            "url": url,
            "method": method,
            "headers": dict(headers),
            "payload": payload,
            "auction_number": auction_number,
            "request_type": request_type,
            "timestamp": datetime.now().isoformat(),
        }

        return request_num

    def log_response(
        self,
        request_num: int,
        response_text: str,
        status_code: int,
        auction_number: Optional[str] = None,
        request_type: str = "request",
    ) -> None:
        """Log an HTTP response combined with the request.

        Args:
            request_num: Request number from log_request
            response_text: Raw response text
            status_code: HTTP status code
            auction_number: Associated auction number
            request_type: Type of request
        """
        if not self.enabled or request_num == 0:
            return

        auction_suffix = (
            f"_{self._sanitize_filename(auction_number)}" if auction_number else ""
        )
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{request_type}{auction_suffix}.txt"
        filepath = self.debug_dir / filename

        # Get request data
        req_data = self._pending_requests.pop(request_num, None)
        if req_data is None:
            # If no request data, just log the response
            req_data = {}

        # Build combined content
        content = f"""=== REQUEST ===
URL: {req_data.get("url", "Unknown")}
Method: {req_data.get("method", "Unknown")}
Timestamp: {req_data.get("timestamp", datetime.now().isoformat())}

=== REQUEST HEADERS ===
{json.dumps(req_data.get("headers", {}), indent=2, default=str)}

=== REQUEST PAYLOAD ===
{json.dumps(req_data.get("payload"), indent=2, default=str) if req_data.get("payload") else "None"}

=== RESPONSE ===
Status Code: {status_code}
Timestamp: {datetime.now().isoformat()}

=== RESPONSE BODY ===
{response_text}
"""

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

    def log_parsed_object(
        self,
        request_num: int,
        parsed_object: Any,
        auction_number: Optional[str] = None,
        request_type: str = "request",
        object_type: str = "object",
    ) -> None:
        """Log a parsed object as JSON.

        Args:
            request_num: Request number from log_request
            parsed_object: The parsed object to serialize
            auction_number: Associated auction number
            request_type: Type of request
            object_type: Type of parsed object (e.g., 'list', 'detail', 'inmuebles')
        """
        if not self.enabled or request_num == 0:
            return

        auction_suffix = (
            f"_{self._sanitize_filename(auction_number)}" if auction_number else ""
        )
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = (
            f"{timestamp}_{request_type}{auction_suffix}_{object_type}_parsed.json"
        )
        filepath = self.debug_dir / filename

        try:
            if hasattr(parsed_object, "model_dump"):
                data = parsed_object.model_dump()
            elif hasattr(parsed_object, "dict"):
                data = parsed_object.dict()
            elif isinstance(parsed_object, list) and len(parsed_object) > 0:
                if hasattr(parsed_object[0], "model_dump"):
                    data = [item.model_dump() for item in parsed_object]
                elif hasattr(parsed_object[0], "dict"):
                    data = [item.dict() for item in parsed_object]
                else:
                    data = parsed_object
            else:
                data = parsed_object

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)

        except Exception as e:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(f"Error serializing object: {e}\n\n")
                f.write(str(parsed_object))


_debug_logger: Optional[DebugLogger] = None


def get_debug_logger() -> Optional[DebugLogger]:
    """Get the global debug logger instance."""
    return _debug_logger


def init_debug_logger(
    enabled: bool = False, debug_dir: Path = Path("data/debug")
) -> DebugLogger:
    """Initialize the global debug logger.

    Args:
        enabled: Whether debugging is enabled
        debug_dir: Directory to save debug files

    Returns:
        The debug logger instance
    """
    global _debug_logger
    _debug_logger = DebugLogger(debug_dir=debug_dir, enabled=enabled)
    return _debug_logger


def is_debug_enabled() -> bool:
    """Check if debug logging is enabled."""
    return _debug_logger is not None and _debug_logger.enabled
