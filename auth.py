import json
import logging
import time

import aiohttp

from config import Settings
from state import StateManager

logger = logging.getLogger(__name__)

AUTH_URL = "https://cloud.api.selcloud.ru/identity/v3/auth/tokens"


class TokenExpiredError(Exception):
    """Raised when the auth token has expired."""

    pass


class AuthClient:
    """Handles authentication with Selectel API."""

    def __init__(self, settings: Settings, state: StateManager):
        self.settings = settings
        self.state = state
        self._token: str = state.get_token()

    @property
    def token(self) -> str:
        return self._token

    async def ensure_valid_token(self) -> str:
        """Get a valid token, fetching a new one if necessary."""
        if not self._token:
            logger.info("No auth token found, requesting new token")
            await self.refresh_token()
        return self._token

    async def refresh_token(self) -> str:
        """Fetch a new auth token from Selectel API."""
        logger.info(f"Requesting auth token from {AUTH_URL}")
        start_time = time.time()

        async with aiohttp.ClientSession() as session:
            data = {
                "auth": {
                    "identity": {
                        "methods": ["password"],
                        "password": {
                            "user": {
                                "name": self.settings.username,
                                "domain": {"name": self.settings.account_id},
                                "password": self.settings.password,
                            }
                        },
                    },
                    "scope": {"domain": {"name": self.settings.account_id}},
                }
            }
            try:
                async with session.post(
                    AUTH_URL,
                    headers={"Content-Type": "application/json"},
                    data=json.dumps(data),
                ) as response:
                    elapsed_time = time.time() - start_time
                    logger.info(
                        f"Auth request completed in {elapsed_time:.3f}s "
                        f"with status {response.status}"
                    )

                    if response.status == 201:
                        token = response.headers["X-Subject-Token"]
                        self._token = token
                        self.state.set_token(token)
                        logger.info("Auth token successfully obtained")
                        return token
                    else:
                        logger.error(
                            f"Failed to fetch auth token: status={response.status}"
                        )
                        raise Exception(
                            f"Failed to fetch auth token: {response.status}"
                        )
            except Exception as e:
                elapsed_time = time.time() - start_time
                logger.error(f"Auth request failed after {elapsed_time:.3f}s: {e}")
                raise
