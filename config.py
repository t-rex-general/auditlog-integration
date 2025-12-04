import logging
import os

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class Settings:
    def __init__(self):
        self.audit_logs_url: str = os.getenv(
            "AUDIT_LOGS_URL", "https://api.selectel.ru/audit-logs/v1/logs"
        )
        self.username: str = os.getenv("USERNAME", "")
        self.password: str = os.getenv("PASSWORD", "")
        self.account_id: str = os.getenv("ACCOUNT_ID", "")

        # Transport settings (file, syslog, or http)
        self.transport_type: str = os.getenv("TRANSPORT_TYPE", "file").lower()

        # Syslog settings
        self.syslog_host: str = os.getenv("SYSLOG_HOST", "127.0.0.1")
        self.syslog_port: int = int(os.getenv("SYSLOG_PORT", "5514"))

        # HTTP settings
        self.http_url: str = os.getenv("HTTP_URL", "")
        self.http_username: str = os.getenv("HTTP_USERNAME", "")
        self.http_password: str = os.getenv("HTTP_PASSWORD", "")
        self.http_verify_ssl: bool = os.getenv("HTTP_VERIFY_SSL", "true").lower() in (
            "true",
            "1",
            "yes",
        )

        # Polling settings
        self.poll_interval: int = int(os.getenv("POLL_INTERVAL", "30"))

        logger.info(
            f"Settings initialized: audit_logs_url={self.audit_logs_url}, "
            f"account_id={self.account_id}, transport_type={self.transport_type}"
        )

    def validate(self) -> None:
        """Validate required settings are present."""
        if not self.username or not self.password or not self.account_id:
            raise ValueError("USERNAME, PASSWORD, and ACCOUNT_ID are required")

        if self.transport_type == "http":
            if not self.http_url or not self.http_username or not self.http_password:
                raise ValueError(
                    "HTTP transport requires HTTP_URL, HTTP_USERNAME, and HTTP_PASSWORD"
                )

        if self.transport_type not in ("file", "syslog", "http"):
            raise ValueError(
                f"Unknown transport type: {self.transport_type}. "
                "Must be 'file', 'syslog', or 'http'"
            )
