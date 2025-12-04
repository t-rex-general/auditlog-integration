import base64
import json
import logging
from logging.handlers import SysLogHandler
from typing import Protocol

import aiohttp

logger = logging.getLogger(__name__)


class EventSaver(Protocol):
    """Protocol for event savers"""

    async def add_events(self, events: list[dict]) -> None:
        """Add events to storage"""
        ...

    def close(self) -> None:
        """Close the saver and release resources"""
        ...


def format_events(events: list[dict]) -> str:
    return "\n".join(json.dumps(event) for event in events)


class FileSaver:
    def __init__(self):
        self.filename = "events.txt"
        logger.info(f"FileSaver initialized with filename: {self.filename}")

    def save(self, data):
        try:
            with open(self.filename, "w") as file:
                file.write(data)
            logger.info(f"Data saved to {self.filename}")
        except Exception as e:
            logger.error(f"Failed to save data to {self.filename}: {e}")
            raise

    async def add_events(self, events: list[dict]):
        try:
            with open("events.txt", "a", encoding="utf-8") as file:
                file.write(format_events(events) + "\n")
            logger.info(f"Added {len(events)} events to {self.filename}")
        except Exception as e:
            logger.error(f"Failed to add events to {self.filename}: {e}")
            raise

    def close(self):
        """Close the file saver (no-op, maintains interface consistency)"""
        pass


class SyslogSaver:
    """Saves events to syslog server only"""

    def __init__(self, syslog_host: str, syslog_port: int):
        self.host = syslog_host
        self.port = syslog_port

        # Create syslog logger
        self.syslog_logger = logging.getLogger("auditlogs")
        self.handler = SysLogHandler(address=(self.host, self.port))
        self.syslog_logger.addHandler(self.handler)
        self.syslog_logger.setLevel(logging.INFO)
        self.syslog_logger.propagate = False

        logger.info(f"SyslogSaver initialized: syslog={syslog_host}:{syslog_port}")

    def send(self, event: dict) -> bool:
        """
        Send a single event via syslog.

        Args:
            event: Event dictionary to send

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            message = json.dumps(event, ensure_ascii=False)
            self.syslog_logger.info(message)
            self.handler.flush()  # Force send immediately
            return True
        except Exception as e:
            logger.error(f"Failed to send event: {e}")
            return False

    async def add_events(self, events: list[dict]):
        """
        Send multiple events in a batch.

        Args:
            events: List of event dictionaries to send
        """
        logger.info(f"Sending batch of {len(events)} events via syslog")

        success_count = 0
        for event in events:
            if self.send(event):
                success_count += 1

        logger.info(f"Batch send completed: {success_count}/{len(events)} events sent")

        if success_count < len(events):
            raise Exception(
                f"Only {success_count}/{len(events)} events sent successfully"
            )

    def close(self):
        """Close the syslog connection"""
        try:
            self.handler.close()
            self.syslog_logger.removeHandler(self.handler)
            logger.info("Syslog connection closed")
        except Exception as e:
            logger.error(f"Error closing syslog handler: {e}")

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


class HttpSaver:
    """Saves events to HTTP endpoint with Basic Auth"""

    def __init__(
        self,
        http_url: str,
        http_username: str,
        http_password: str,
        verify_ssl: bool = True,
    ):
        # Validate and normalize URL (add http:// if missing)
        if not http_url.startswith(("http://", "https://")):
            http_url = f"http://{http_url}"
            logger.info(f"Added http:// scheme to URL: {http_url}")

        self.http_url = http_url
        self.http_username = http_username
        self.http_password = http_password
        self.verify_ssl = verify_ssl

        # Create Basic Auth header
        credentials = f"{http_username}:{http_password}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        self.auth_header = f"Basic {encoded_credentials}"

        logger.info(
            f"HttpSaver initialized: url={self.http_url}, username={self.http_username}, verify_ssl={self.verify_ssl}"
        )

    async def send(self, event: dict) -> bool:
        """
        Send a single event via HTTP POST.

        Args:
            event: Event dictionary to send

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": self.auth_header,
                    "Content-Type": "application/json",
                }
                async with session.post(
                    self.http_url,
                    headers=headers,
                    json=event,
                    timeout=aiohttp.ClientTimeout(total=10),
                    ssl=self.verify_ssl,
                ) as response:
                    if response.status in [200, 201, 202]:
                        logger.debug(
                            f"Event sent successfully: status={response.status}"
                        )
                        return True
                    else:
                        logger.error(f"Failed to send event: status={response.status}")
                        return False
        except Exception as e:
            logger.error(f"Failed to send event via HTTP: {e}")
            return False

    async def add_events(self, events: list[dict]):
        """
        Send multiple events in a batch.

        Args:
            events: List of event dictionaries to send
        """
        logger.info(f"Sending batch of {len(events)} events via HTTP")

        success_count = 0
        for event in events:
            if await self.send(event):
                success_count += 1

        logger.info(f"Batch send completed: {success_count}/{len(events)} events sent")

        if success_count < len(events):
            raise Exception(
                f"Only {success_count}/{len(events)} events sent successfully"
            )

    def close(self):
        """Close the file saver (no-op, maintains interface consistency)"""
        pass

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
