import logging
import time
from dataclasses import dataclass

import aiohttp

from auth import AuthClient, TokenExpiredError
from config import Settings

logger = logging.getLogger(__name__)


@dataclass
class AuditLogsResponse:
    """Response from the audit logs API."""

    events: list[dict]
    next_cursor: str | None


class AuditLogClient:
    """Client for fetching audit logs from Selectel API."""

    def __init__(self, settings: Settings, auth: AuthClient):
        self.settings = settings
        self.auth = auth

    async def fetch_logs(self, cursor: str | None = None) -> AuditLogsResponse:
        """
        Fetch audit logs from the API.

        Args:
            cursor: Pagination cursor for fetching next page

        Returns:
            AuditLogsResponse with events and optional next_cursor

        Raises:
            TokenExpiredError: If the auth token has expired
            Exception: On other API errors
        """
        cursor_info = f"cursor={cursor[:20]}..." if cursor else "no cursor"
        logger.info(f"Fetching audit logs ({cursor_info})")
        start_time = time.time()

        async with aiohttp.ClientSession() as session:
            params = {"limit": "100"}
            if cursor:
                params["cursor"] = cursor

            try:
                async with session.post(
                    self.settings.audit_logs_url,
                    headers={"X-Auth-Token": self.auth.token},
                    params=params,
                ) as response:
                    elapsed_time = time.time() - start_time
                    logger.info(
                        f"Audit logs request completed in {elapsed_time:.3f}s "
                        f"with status {response.status}"
                    )

                    if response.status == 200:
                        data = await response.json()
                        events = data.get("data", [])
                        next_cursor = data.get("pagination", {}).get("next_cursor")
                        logger.info(f"Received {len(events)} events from API")
                        return AuditLogsResponse(events=events, next_cursor=next_cursor)

                    if response.status == 401:
                        logger.warning("Token expired (401), need to refresh")
                        raise TokenExpiredError()

                    logger.error(
                        f"Failed to fetch audit logs: status={response.status}"
                    )
                    raise Exception(f"Failed to fetch audit logs: {response.status}")

            except TokenExpiredError:
                raise
            except Exception as e:
                elapsed_time = time.time() - start_time
                logger.error(f"Audit logs request failed after {elapsed_time:.3f}s: {e}")
                raise
