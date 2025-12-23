import asyncio
import logging
import sys

from auth import AuthClient
from client import AuditLogClient
from config import Settings
from processor import EventProcessor
from runner import PollingRunner
from savers import EventSaver, FileSaver, HttpSaver, SyslogSaver
from state import StateManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)

logger = logging.getLogger(__name__)


def create_saver(settings: Settings) -> EventSaver:
    """Factory function to create the appropriate saver based on transport type."""
    if settings.transport_type == "syslog":
        logger.info("Using SyslogSaver (syslog transport)")
        return SyslogSaver(
            syslog_host=settings.syslog_host,
            syslog_port=settings.syslog_port,
        )
    elif settings.transport_type == "http":
        logger.info(f"Using HttpSaver (HTTP transport to {settings.http_url})")
        return HttpSaver(
            http_url=settings.http_url,
            http_username=settings.http_username,
            http_password=settings.http_password,
            verify_ssl=settings.http_verify_ssl,
        )
    else:
        logger.info("Using FileSaver (file transport)")
        return FileSaver()


async def main() -> None:
    # Initialize components
    settings = Settings()
    settings.validate()

    state = StateManager()
    auth = AuthClient(settings, state)
    client = AuditLogClient(settings, auth)
    saver = create_saver(settings)
    processor = EventProcessor(state, saver)
    runner = PollingRunner(settings, auth, client, processor)

    try:
        await runner.run()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down gracefully")
    except Exception as e:
        logger.critical(f"Critical error in main loop: {e}", exc_info=True)
    finally:
        saver.close()
        logger.info("=" * 60)
        logger.info("Graceful shutdown completed")
        logger.info(f"Total iterations completed: {runner.iteration}")
        logger.info("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
